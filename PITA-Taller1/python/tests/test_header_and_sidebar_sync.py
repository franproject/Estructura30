"""Pruebas unitarias para la sincronización de Sidebar y controles interactivos de TopHeader."""

import os
import unittest

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QPushButton

from gui.main_window import MainWindow
from models.course import Course
from models.student import Student
from services.entity_manager import EntityManager


class TestHeaderAndSidebarSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.manager = EntityManager()
        self.window = MainWindow(manager=self.manager)
        self.window.show()

    def tearDown(self):
        self.window.close()

    def test_navigate_synchronizes_sidebar_active_page(self):
        """Verifica que MainWindow._navigate() actualice el estado visual del Sidebar."""
        sidebar = self.window.sidebar

        # Al iniciar, Dashboard debe estar activo
        self.assertEqual(sidebar._buttons["Dashboard"].property("active"), "true")
        self.assertEqual(sidebar._buttons["Estudiantes"].property("active"), "false")

        # Navegar a Estudiantes
        self.window._navigate("Estudiantes")
        self.assertEqual(sidebar._buttons["Estudiantes"].property("active"), "true")
        self.assertEqual(sidebar._buttons["Dashboard"].property("active"), "false")

        # Navegar a Facultades
        self.window._navigate("Facultades")
        self.assertEqual(sidebar._buttons["Facultades"].property("active"), "true")
        self.assertEqual(sidebar._buttons["Estudiantes"].property("active"), "false")

    def test_sidebar_click_navigates_and_syncs_without_recursion(self):
        """Verifica que hacer clic en un botón del sidebar cambie de página e ilumine el botón."""
        sidebar = self.window.sidebar
        btn_cursos = sidebar._buttons["Cursos"]

        btn_cursos.click()

        self.assertEqual(self.window.stack.currentWidget(), self.window._pages["Cursos"])
        self.assertEqual(btn_cursos.property("active"), "true")
        self.assertEqual(sidebar._buttons["Dashboard"].property("active"), "false")

    def test_dashboard_quick_action_navigates_and_syncs_sidebar(self):
        """Verifica que los botones de acciones rápidas del Dashboard iluminen el botón correspondiente en el Sidebar."""
        sidebar = self.window.sidebar
        dashboard_page = self.window._pages["Dashboard"]

        # Buscar botón de acción rápida para 'Profesores'
        prof_btn = None
        for btn in dashboard_page.findChildren(QPushButton):
            if btn.text() == "Profesores":
                prof_btn = btn
                break

        self.assertIsNotNone(prof_btn, "No se encontró el botón de acción rápida 'Profesores'")
        prof_btn.click()

        self.assertEqual(self.window.stack.currentWidget(), self.window._pages["Profesores"])
        self.assertEqual(sidebar._buttons["Profesores"].property("active"), "true")
        self.assertEqual(sidebar._buttons["Dashboard"].property("active"), "false")

    def test_header_clock_timer_is_active_and_ticking(self):
        """Verifica que el reloj del TopHeader cuente con QTimer activo y formato adecuado."""
        header = self.window.header
        self.assertTrue(hasattr(header, "clock_timer"))
        self.assertIsInstance(header.clock_timer, QTimer)
        self.assertTrue(header.clock_timer.isActive())
        self.assertEqual(header.clock_timer.interval(), 1000)

        # La etiqueta de fecha debe contener separador y año
        text = header.date_label.text()
        self.assertIn("|", text)
        self.assertTrue(len(text) > 10)

        # Invocar actualización manual
        header._update_clock()
        self.assertIn("|", header.date_label.text())

    def test_header_global_search_routes_to_student(self):
        """Verifica que el buscador global encuentre un estudiante, navegue a Estudiantes y active el filtro."""
        student = Student(
            student_id=9876,
            full_name="Valentina Gomez Rios",
            email="vgomez@universidad.edu.co",
            program_id=1,
            current_semester=3,
            status="REGULAR",
            active=True,
        )
        self.manager.students.insert(student)

        # Ejecutar búsqueda global con diacríticos / sin diacríticos
        self.window._handle_global_search("valentina")

        # Debe haber navegado a 'Estudiantes'
        self.assertEqual(self.window.stack.currentWidget(), self.window._pages["Estudiantes"])
        self.assertEqual(self.window.sidebar._buttons["Estudiantes"].property("active"), "true")

        # El buscador de la página debe tener el texto y el filtro aplicado
        est_page = self.window._pages["Estudiantes"]
        self.assertEqual(est_page.search_input.text(), "valentina")
        self.assertEqual(len(est_page._items), 1)
        self.assertEqual(est_page._items[0].student_id, 9876)

    def test_header_global_search_routes_to_course(self):
        """Verifica que el buscador global encuentre un curso y navegue a Cursos."""
        course = Course(
            course_id=777,
            name="Algoritmos y Estructuras II",
            credits=4,
            program_id=1,
            curriculum_semester=4,
            active=True,
        )
        self.manager.courses.insert(course)

        # Búsqueda insensible a acentos
        self.window._handle_global_search("algoritmos")

        self.assertEqual(self.window.stack.currentWidget(), self.window._pages["Cursos"])
        self.assertEqual(self.window.sidebar._buttons["Cursos"].property("active"), "true")
        curso_page = self.window._pages["Cursos"]
        self.assertEqual(curso_page.search_input.text(), "algoritmos")

    def test_header_global_search_no_matches_does_not_crash(self):
        """Verifica que una búsqueda sin coincidencias no cause errores."""
        self.window._handle_global_search("busquedainexistente999")
        # Permanece en la página que estaba sin excepciones
        self.assertIsNotNone(self.window.stack.currentWidget())

    def test_header_notification_panel_and_dot(self):
        """Verifica que el panel de notificaciones y el punto rojo reflejen alertas reales."""
        header = self.window.header
        self.assertTrue(hasattr(header, "notification_panel"))

        # Caso 1: Sin alertas
        header.update_alerts(self.manager)
        # Caso 2: Forzar período de nómina abierto
        period = self.manager.payroll_cycle_service.create_period(
            year=2026, month=10, start_date="2026-10-01", end_date="2026-10-31"
        )
        header.update_alerts(self.manager)
        self.assertFalse(header.dot.isHidden())
        self.assertIn("Centro de Alertas", header.notif_btn.toolTip())

        # Verificar que el panel contiene la alerta
        alerts = header.notification_panel.get_alerts()
        payroll_alerts = [a for a in alerts if a["id"] == "payroll"]
        self.assertTrue(len(payroll_alerts) > 0)
        self.assertEqual(payroll_alerts[0]["target"], "Nómina")

        # Probar navegación desde el panel
        header.notification_panel._handle_action("Nómina")
        self.assertEqual(self.window.stack.currentWidget(), self.window._pages["Nómina"])
        self.assertEqual(self.window.sidebar._buttons["Nómina"].property("active"), "true")


if __name__ == "__main__":
    unittest.main()
