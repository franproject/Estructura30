"""Pruebas unitarias e integrales para estados de interacción y accesibilidad:
1. CrudPage: Botones contextuales reactivos a itemSelectionChanged.
2. StatCard: FocusPolicy StrongFocus, teclas Enter/Return/Space y estilos :focus.
3. ConfirmDialog: Botón 'Cancelar' predeterminado seguro ante tecla Enter.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from models.faculty import Faculty
from services.entity_manager import EntityManager
from gui.pages.crud_page import CrudPage
from gui.pages.dashboard_page import DashboardPage
from gui.components.stat_card import StatCard
from gui.components.confirm_dialog import ConfirmDialog


class TestCrudPageSelectionReactivity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.mgr = EntityManager()
        self.fac1 = Faculty(1, "Facultad de Ingeniería", "Decano 1", "2020-01-01", True)
        self.fac2 = Faculty(2, "Facultad de Medicina", "Decana 2", "2021-01-01", True)
        self.mgr.faculties.insert(self.fac1)
        self.mgr.faculties.insert(self.fac2)

        self.page = CrudPage(
            title="Facultades",
            subtitle="Gestión de facultades",
            manager=self.mgr,
            collection_name="faculties",
            model_cls=Faculty,
            id_field="faculty_id",
            fields=(
                ("faculty_id", "ID", "int"),
                ("name", "Nombre", "text"),
                ("dean", "Decano", "text"),
                ("creation_date", "Fecha", "text"),
                ("active", "Activo", "bool"),
            ),
            columns=("ID", "Nombre", "Decano", "Fecha", "Estado"),
            row_builder=lambda f: (f.faculty_id, f.name, f.dean, f.creation_date, "Activo" if f.active else "Inactivo"),
            operation_name="faculty",
        )
        self.page.refresh()

    def test_buttons_initially_disabled_without_selection(self):
        """Los botones 'Editar' y 'Eliminar' deben iniciar deshabilitados sin selección."""
        self.assertFalse(self.page.btn_edit.isEnabled())
        self.assertFalse(self.page.btn_delete.isEnabled())

    def test_buttons_enable_when_row_is_selected(self):
        """Al seleccionar una fila de la tabla, ambos botones deben habilitarse."""
        self.page.table.selectRow(0)
        self.assertTrue(self.page.btn_edit.isEnabled())
        self.assertTrue(self.page.btn_delete.isEnabled())

    def test_buttons_disable_when_selection_is_cleared(self):
        """Al deseleccionar la tabla, ambos botones deben volver a deshabilitarse."""
        self.page.table.selectRow(0)
        self.assertTrue(self.page.btn_edit.isEnabled())
        self.assertTrue(self.page.btn_delete.isEnabled())

        self.page.table.clearSelection()
        self.assertFalse(self.page.btn_edit.isEnabled())
        self.assertFalse(self.page.btn_delete.isEnabled())

    def test_buttons_disabled_when_search_yields_empty_results(self):
        """Si una búsqueda no arroja resultados, los botones permanecen deshabilitados."""
        self.page.table.selectRow(0)
        self.assertTrue(self.page.btn_edit.isEnabled())

        # Filtrar por un término inexistente
        self.page.filter_data("TerminoInexistenteXYZ")
        self.assertFalse(self.page.btn_edit.isEnabled())
        self.assertFalse(self.page.btn_delete.isEnabled())

    def test_buttons_state_resets_after_refresh(self):
        """Al refrescar la página, los botones se sincronizan con la ausencia de selección."""
        self.page.table.selectRow(0)
        self.page.refresh()
        self.assertFalse(self.page.btn_edit.isEnabled())
        self.assertFalse(self.page.btn_delete.isEnabled())


class TestStatCardKeyboardAccessibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.card = StatCard(
            title="Facultades",
            value="12",
            detail="Activas",
            delta="▲ +2",
            bg_color="#DCFCE7",
            text_color="#16A34A",
        )

    def test_focus_policy_is_strong_focus(self):
        """StatCard debe tener FocusPolicy.StrongFocus para ser accesible con Tab."""
        self.assertEqual(self.card.focusPolicy(), Qt.FocusPolicy.StrongFocus)

    def test_key_press_return_emits_clicked(self):
        """Pulsar Key_Return debe emitir la señal clicked."""
        mock_handler = MagicMock()
        self.card.clicked.connect(mock_handler)

        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
        self.card.keyPressEvent(event)
        mock_handler.assert_called_once()
        self.assertTrue(event.isAccepted())

    def test_key_press_enter_emits_clicked(self):
        """Pulsar Key_Enter (teclado numérico) debe emitir la señal clicked."""
        mock_handler = MagicMock()
        self.card.clicked.connect(mock_handler)

        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Enter, Qt.KeyboardModifier.NoModifier)
        self.card.keyPressEvent(event)
        mock_handler.assert_called_once()
        self.assertTrue(event.isAccepted())

    def test_key_press_space_emits_clicked(self):
        """Pulsar Key_Space debe emitir la señal clicked."""
        mock_handler = MagicMock()
        self.card.clicked.connect(mock_handler)

        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
        self.card.keyPressEvent(event)
        mock_handler.assert_called_once()
        self.assertTrue(event.isAccepted())

    def test_unrelated_key_does_not_emit_clicked(self):
        """Pulsar una tecla no relacionada (ej. Key_A) no debe emitir clicked."""
        mock_handler = MagicMock()
        self.card.clicked.connect(mock_handler)

        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)
        self.card.keyPressEvent(event)
        mock_handler.assert_not_called()

    def test_dashboard_page_keyboard_navigation_integration(self):
        """En DashboardPage, presionar Space/Enter sobre una StatCard navega a la sección correspondiente."""
        mgr = EntityManager()
        nav_mock = MagicMock()
        dashboard = DashboardPage(mgr, nav_mock)

        card_facultades = dashboard.cards.get("Facultades")
        self.assertIsNotNone(card_facultades)

        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
        card_facultades.keyPressEvent(event)
        nav_mock.assert_called_with("Facultades")


class TestConfirmDialogSafetyDefaults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_cancel_button_is_default_and_delete_is_not(self):
        """El botón 'Cancelar' debe ser predeterminado y 'Eliminar' no debe serlo."""
        dialog = ConfirmDialog("Eliminar registro", "¿Confirmas la eliminación?")
        
        self.assertTrue(dialog.btn_cancel.isDefault())
        self.assertTrue(dialog.btn_cancel.autoDefault())
        self.assertFalse(dialog.btn_delete.isDefault())
        self.assertFalse(dialog.btn_delete.autoDefault())

    def test_enter_key_triggers_safe_rejection(self):
        """Presionar Enter en el diálogo ejecuta el botón seguro 'Cancelar' (Rejected)."""
        dialog = ConfirmDialog("Eliminar registro", "¿Confirmas la eliminación?")
        
        # Conectar espía a accepted y rejected
        mock_accepted = MagicMock()
        mock_rejected = MagicMock()
        dialog.accepted.connect(mock_accepted)
        dialog.rejected.connect(mock_rejected)

        # Simular evento Key_Return sobre el diálogo
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
        dialog.keyPressEvent(event)

        # Se debe haber rechazado de forma segura, nunca aceptado
        mock_accepted.assert_not_called()
        mock_rejected.assert_called_once()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Rejected)

    def test_enter_key_when_delete_is_focused_triggers_accept(self):
        """Si el usuario navega explícitamente con Tab a 'Eliminar', Enter sí confirma la eliminación."""
        dialog = ConfirmDialog("Eliminar registro", "¿Confirmas la eliminación?")
        dialog.btn_delete.setFocus()

        mock_accepted = MagicMock()
        mock_rejected = MagicMock()
        dialog.accepted.connect(mock_accepted)
        dialog.rejected.connect(mock_rejected)

        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
        dialog.keyPressEvent(event)

        mock_accepted.assert_called_once()
        mock_rejected.assert_not_called()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)


if __name__ == "__main__":
    unittest.main()
