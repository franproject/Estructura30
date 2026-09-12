"""Pruebas unitarias e integrales para Arquitectura de Información:
1. Componente Breadcrumb (rutas jerárquicas, navegación interactiva, indicador de cambios).
2. PageHeader con soporte de breadcrumbs.
3. Sección de Persistencia en Sidebar (encabezado, estado de sincronización, tooltips, tipografía).
4. Ciclo de vida y salvaguardas de cambios sin guardar en MainWindow.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from models.faculty import Faculty
from services.entity_manager import EntityManager
from gui.components.breadcrumb import Breadcrumb
from gui.components.page_header import PageHeader
from gui.components.sidebar import Sidebar
from gui.main_window import MainWindow


class TestBreadcrumbComponent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_default_route_dashboard(self):
        """La ruta inicial por defecto debe ser 'Inicio'."""
        bc = Breadcrumb()
        self.assertEqual(bc.get_text_path(), "Inicio")

    def test_set_page_crud_routes(self):
        """Validar mapeo jerárquico de páginas académicas y administrativas."""
        bc = Breadcrumb()
        
        bc.set_page("Facultades")
        self.assertEqual(bc.get_text_path(), "Gestión Académica › Facultades")

        bc.set_page("Estudiantes")
        self.assertEqual(bc.get_text_path(), "Gestión Académica › Estudiantes")

        bc.set_page("Administrativos")
        self.assertEqual(bc.get_text_path(), "Gestión Administrativa › Personal Administrativo")

        bc.set_page("Reportes")
        self.assertEqual(bc.get_text_path(), "Herramientas › Reportes")

    def test_set_page_with_subpath(self):
        """Validar que una sub-ruta anidada se concatene correctamente (e.g. Nómina › Detalle de período)."""
        bc = Breadcrumb()
        bc.set_page("Nómina", "Detalle de período")
        self.assertEqual(bc.get_text_path(), "Nómina › Detalle de período")

    def test_click_home_button_emits_navigation(self):
        """Hacer clic en el botón Inicio debe emitir navigate_requested con 'Dashboard'."""
        bc = Breadcrumb()
        bc.set_page("Estudiantes")
        
        # Al regresar a Inicio
        received = []
        bc.navigate_requested.connect(received.append)
        bc.set_page("Dashboard")
        
        # Encontrar el botón de inicio
        btn_home = bc.findChild(object, "breadcrumbHomeButton")
        self.assertIsNotNone(btn_home)
        btn_home.clicked.emit()
        self.assertIn("Dashboard", received)

    def test_unsaved_indicator_toggle(self):
        """La insignia de cambios sin guardar debe alternar su visibilidad."""
        bc = Breadcrumb()
        bc.show()
        QApplication.processEvents()
        self.assertFalse(bc.unsaved_badge.isVisible())

        bc.set_unsaved_indicator(True)
        self.assertTrue(bc.unsaved_badge.isVisible())

        bc.set_unsaved_indicator(False)
        self.assertFalse(bc.unsaved_badge.isVisible())
        bc.close()


class TestPageHeaderBreadcrumb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_page_header_without_breadcrumb(self):
        """PageHeader sin breadcrumb no crea etiqueta de ruta."""
        ph = PageHeader("Título", "Subtítulo")
        lbl = ph.findChild(object, "pageHeaderBreadcrumb")
        self.assertIsNone(lbl)

    def test_page_header_with_breadcrumb(self):
        """PageHeader con breadcrumb renderiza la ruta textual."""
        ph = PageHeader("Estudiantes", "Directorio", breadcrumb="Gestión Académica › Estudiantes")
        lbl = ph.findChild(object, "pageHeaderBreadcrumb")
        self.assertIsNotNone(lbl)
        self.assertEqual(lbl.text(), "Gestión Académica › Estudiantes")


class TestSidebarPersistenceSection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.sidebar = Sidebar()

    def test_persistence_footer_structure(self):
        """El footer del Sidebar debe tener título de sección, estado de sincronización y botones."""
        header = self.sidebar.findChild(object, "sidebarStorageHeader")
        status = self.sidebar.findChild(object, "sidebarSyncStatus")
        self.assertIsNotNone(header)
        self.assertIsNotNone(status)
        self.assertIn("PERSISTENCIA", header.text())
        self.assertIn("Sincronizado", status.text())

    def test_persistence_buttons_geometry_and_tooltips(self):
        """Los botones deben tener altura mínima >= 34px y tooltips descriptivos de impacto físico."""
        save_btn = self.sidebar.save_btn
        reload_btn = self.sidebar.reload_btn

        self.assertGreaterEqual(save_btn.minimumHeight(), 34)
        self.assertGreaterEqual(reload_btn.minimumHeight(), 34)

        # Tooltips con explicación de impacto en disco
        self.assertIn("Sobrescribe", save_btn.toolTip())
        self.assertIn("Ctrl+S", save_btn.toolTip())
        self.assertIn("disco", reload_btn.toolTip())
        self.assertIn("F5", reload_btn.toolTip())

    def test_set_unsaved_changes_updates_ui(self):
        """Al marcar cambios pendientes, se actualiza el texto de estado y del botón guardar."""
        self.sidebar.set_unsaved_changes(True)
        self.assertIn("Cambios sin guardar", self.sidebar.lbl_sync_status.text())
        self.assertIn("●", self.sidebar.save_btn.text())
        self.assertEqual(self.sidebar.save_btn.property("unsaved"), "true")

        self.sidebar.set_unsaved_changes(False)
        self.assertIn("Sincronizado", self.sidebar.lbl_sync_status.text())
        self.assertEqual(self.sidebar.save_btn.text(), "Guardar Datos")
        self.assertEqual(self.sidebar.save_btn.property("unsaved"), "false")


class TestMainWindowIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.mgr = EntityManager()
        self.window = MainWindow(self.mgr)
        self.window.resize(1100, 700)
        self.window.show()
        QApplication.processEvents()

    def tearDown(self):
        self.window._has_unsaved_changes = False
        self.window.close()

    def test_breadcrumb_integrated_in_main_window(self):
        """El breadcrumb debe existir en MainWindow y estar sincronizado con la página inicial."""
        self.assertTrue(hasattr(self.window, "breadcrumb"))
        self.assertEqual(self.window.breadcrumb.get_text_path(), "Inicio")

    def test_navigate_updates_breadcrumb_dynamically(self):
        """Navegar a diferentes páginas actualiza reactivamente la ruta del breadcrumb."""
        self.window._navigate("Estudiantes")
        self.assertEqual(self.window.breadcrumb.get_text_path(), "Gestión Académica › Estudiantes")

        self.window._navigate("Nómina")
        self.assertEqual(self.window.breadcrumb.get_text_path(), "Nómina")

        self.window._navigate("Reportes")
        self.assertEqual(self.window.breadcrumb.get_text_path(), "Herramientas › Reportes")

    def test_data_mutation_activates_unsaved_state(self):
        """Cuando una página emite 'changed', se activa el estado no guardado globalmente."""
        self.assertFalse(self.window._has_unsaved_changes)
        
        # Simular cambio en la página de Facultades
        fac_page = self.window._pages["Facultades"]
        fac_page.changed.emit()
        QApplication.processEvents()

        self.assertTrue(self.window._has_unsaved_changes)
        self.assertIn("Cambios sin guardar", self.window.windowTitle())
        self.assertTrue(self.window.breadcrumb.unsaved_badge.isVisible())
        self.assertIn("Cambios sin guardar", self.window.sidebar.lbl_sync_status.text())

    def test_payroll_mutation_activates_unsaved_state(self):
        """Cuando la página de Nómina emite 'changed', se activa el estado no guardado."""
        payroll_page = self.window._pages["Nómina"]
        payroll_page.changed.emit()
        QApplication.processEvents()

        self.assertTrue(self.window._has_unsaved_changes)

    def test_save_state_clears_unsaved_state(self):
        """Al guardar exitosamente con batch_save_state, el estado vuelve a sincronizado/limpio."""
        self.window._set_unsaved_changes(True)
        self.assertTrue(self.window._has_unsaved_changes)

        with patch("gui.main_window.batch_save_state") as mock_save,              patch.object(QMessageBox, "information"):
            self.window._save_state()
            mock_save.assert_called_once()

        self.assertFalse(self.window._has_unsaved_changes)
        self.assertNotIn("• Cambios sin guardar", self.window.windowTitle())
        self.assertFalse(self.window.breadcrumb.unsaved_badge.isVisible())
        self.assertIn("Sincronizado", self.window.sidebar.lbl_sync_status.text())

    def test_reload_state_warns_on_unsaved_changes(self):
        """Recargar datos teniendo cambios pendientes debe mostrar advertencia de pérdida de trabajo."""
        self.window._set_unsaved_changes(True)

        with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.No) as mock_warn:
            self.window._reload_state()
            mock_warn.assert_called_once()
            args, _ = mock_warn.call_args
            self.assertIn("irreversible", args[2].lower())

    def test_close_event_prompts_when_unsaved_changes_exist(self):
        """Al cerrar con cambios pendientes, se consulta si desea guardar o descartar."""
        from PySide6.QtGui import QCloseEvent
        self.window._set_unsaved_changes(True)

        event = QCloseEvent()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Save) as mock_q, \
             patch.object(self.window, "_save_state") as mock_save:
            self.window.closeEvent(event)
            mock_q.assert_called_once()
            mock_save.assert_called_once()
            self.assertTrue(event.isAccepted())


if __name__ == "__main__":
    unittest.main()
