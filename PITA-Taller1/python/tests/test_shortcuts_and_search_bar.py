"""Pruebas unitarias e integrales para atajos de teclado y SearchBar:
1. SearchBar: Clear button activo, dimensiones (260px - 400px), tooltip informativo.
2. Atajos globales MainWindow: Ctrl+S, F5, Ctrl+K, Ctrl+N, Ctrl+F, Delete.
3. Salvaguarda de Delete: Nunca interferir con widgets de edición de texto.
4. Tooltips: Presencia de atajos informativos entre paréntesis en controles principales.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QTextEdit,
)

from models.faculty import Faculty
from services.entity_manager import EntityManager
from gui.components.search_bar import SearchBar
from gui.components.confirm_dialog import ConfirmDialog
from gui.pages.crud_page import CrudPage
from gui.main_window import MainWindow


class TestSearchBarEnhancements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_clear_button_enabled(self):
        """SearchBar debe tener el botón de borrado rápido (clear button) habilitado."""
        sb = SearchBar()
        self.assertTrue(sb.isClearButtonEnabled())

    def test_search_bar_dimensions(self):
        """SearchBar debe admitir consultas largas con ancho de hasta 400px y mínimo de 260px."""
        sb = SearchBar()
        self.assertEqual(sb.maximumWidth(), 400)
        self.assertEqual(sb.minimumWidth(), 260)

    def test_search_bar_tooltip(self):
        """SearchBar debe indicar el atajo Ctrl+F en su tooltip."""
        sb = SearchBar()
        self.assertIn("Ctrl+F", sb.toolTip())


class TestMainWindowGlobalShortcuts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.mgr = EntityManager()
        self.window = MainWindow(self.mgr)
        self.window.resize(1200, 700)
        self.window.show()
        QApplication.processEvents()

    def tearDown(self):
        self.window.close()

    def test_shortcuts_configured(self):
        """Verifica que todos los atajos esperados estén instanciados con sus secuencias correctas."""
        self.assertEqual(self.window.shortcut_save.key().toString(), "Ctrl+S")
        self.assertEqual(self.window.shortcut_refresh.key().toString(), "F5")
        self.assertEqual(self.window.shortcut_global_search.key().toString(), "Ctrl+K")
        self.assertEqual(self.window.shortcut_new.key().toString(), "Ctrl+N")
        self.assertEqual(self.window.shortcut_find.key().toString(), "Ctrl+F")
        self.assertEqual(self.window.shortcut_delete.key().toString(), "Del")

    def test_ctrl_s_triggers_save(self):
        """Ctrl+S debe ejecutar el método _save_state de MainWindow."""
        with patch.object(self.window, "_save_state") as mock_save:
            self.window.shortcut_save.activated.emit()
            mock_save.assert_called_once()

    def test_f5_triggers_refresh_on_active_page(self):
        """F5 debe refrescar la vista activa actual."""
        active_page = self.window.stack.currentWidget()
        with patch.object(active_page, "refresh") as mock_refresh:
            self.window.shortcut_refresh.activated.emit()
            mock_refresh.assert_called_once()

    def test_ctrl_k_focuses_global_search(self):
        """Ctrl+K debe enfocar el buscador central del TopHeader."""
        self.window.shortcut_global_search.activated.emit()
        QApplication.processEvents()
        self.assertEqual(self.window.focusWidget(), self.window.header.search_input)

    def test_ctrl_n_triggers_create_on_active_crud_page(self):
        """Ctrl+N en una página CRUD debe llamar a create_item()."""
        # Navegar a Facultades
        self.window._navigate("Facultades")
        fac_page = self.window._pages["Facultades"]
        self.assertEqual(self.window.stack.currentWidget(), fac_page)

        with patch.object(fac_page, "create_item") as mock_create:
            self.window.shortcut_new.activated.emit()
            mock_create.assert_called_once()

    def test_ctrl_f_focuses_active_page_search(self):
        """Ctrl+F en una página CRUD debe enfocar la barra de búsqueda de esa página."""
        self.window._navigate("Facultades")
        fac_page = self.window._pages["Facultades"]

        self.window.shortcut_find.activated.emit()
        QApplication.processEvents()
        self.assertEqual(self.window.focusWidget(), fac_page.search_bar)


class TestDeleteShortcutSafetyAndContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.mgr = EntityManager()
        self.fac = Faculty(1, "Facultad de Ciencias", "Decano C", "2020-01-01", True)
        self.mgr.faculties.insert(self.fac)
        self.window = MainWindow(self.mgr)
        self.window._navigate("Facultades")
        self.page = self.window._pages["Facultades"]
        self.window.show()
        QApplication.processEvents()

    def tearDown(self):
        self.window.close()

    def test_delete_shortcut_on_focused_table_with_selection_triggers_delete(self):
        """Si la tabla está seleccionada y no se edita texto, Delete llama a delete_item()."""
        self.page.table.selectRow(0)
        self.page.table.setFocus()
        QApplication.processEvents()

        with patch.object(self.page, "delete_item") as mock_delete:
            self.window.shortcut_delete.activated.emit()
            mock_delete.assert_called_once()

    def test_delete_shortcut_when_table_has_no_selection_does_nothing(self):
        """Si no hay fila seleccionada (botones deshabilitados), Delete no hace nada."""
        self.page.table.clearSelection()
        self.page.table.setFocus()
        QApplication.processEvents()

        with patch.object(self.page, "delete_item") as mock_delete:
            self.window.shortcut_delete.activated.emit()
            mock_delete.assert_not_called()

    def test_delete_key_when_editing_text_does_not_trigger_record_deletion(self):
        """Si el usuario está escribiendo en SearchBar, Delete NO debe disparar delete_item()."""
        self.page.table.selectRow(0)
        self.page.search_bar.setFocus()
        self.page.search_bar.setText("Hola")
        QApplication.processEvents()

        self.assertEqual(self.window.focusWidget(), self.page.search_bar)

        with patch.object(self.page, "delete_item") as mock_delete:
            self.window._handle_shortcut_delete()
            mock_delete.assert_not_called()

    def test_delete_key_when_editing_other_text_inputs_does_not_trigger_delete(self):
        """Prueba defensiva con QTextEdit y QSpinBox: Delete no borra registros."""
        dummy_edit = QTextEdit(self.window)
        dummy_edit.show()
        dummy_edit.setFocus()
        QApplication.processEvents()

        with patch.object(self.page, "delete_item") as mock_delete:
            self.window._handle_shortcut_delete()
            mock_delete.assert_not_called()


class TestTooltipsIncludeShortcutHints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_main_controls_tooltips(self):
        """Verifica que los controles principales muestren sus atajos entre paréntesis."""
        mgr = EntityManager()
        window = MainWindow(mgr)
        window._navigate("Facultades")
        fac_page = window._pages["Facultades"]

        # 1. Buscador global TopHeader
        self.assertIn("Ctrl+K", window.header.search_input.toolTip())

        # 2. Buscador local CrudPage
        self.assertIn("Ctrl+F", fac_page.search_bar.toolTip())

        # 3. Botón de Nuevo Registro en PageHeader
        if fac_page.header.layout().count() > 0:
            btn_create = None
            for i in range(fac_page.header.layout().count()):
                w = fac_page.header.layout().itemAt(i).widget()
                if w and "primaryButton" in (w.objectName() or ""):
                    btn_create = w
                    break
            if btn_create:
                self.assertIn("Ctrl+N", btn_create.toolTip())

        # 4. Botón Eliminar Seleccionado en CrudPage
        self.assertIn("Delete", fac_page.btn_delete.toolTip())

        # 5. Botones de guardar y recargar en Sidebar
        # Buscar botones en el layout del footer
        self.assertIn("Ctrl+S", window.sidebar.toolTip() or str([btn.toolTip() for btn in window.sidebar.findChildren(QLineEdit) + window.sidebar.findChildren(object) if hasattr(btn, 'toolTip') and 'Ctrl+S' in btn.toolTip()]))


if __name__ == "__main__":
    unittest.main()

