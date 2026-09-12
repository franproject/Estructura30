"""Pruebas unitarias e integrales para verificar el diseño responsivo y la eliminación
completa de barras de desplazamiento horizontal forzado en todas las vistas de NexoCampus.
"""

import os
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QApplication, QMessageBox, QLabel

from services.entity_manager import EntityManager
from gui.components.empty_state import EmptyState
from gui.components.page_header import PageHeader
from gui.components.search_bar import SearchBar
from gui.components.stat_card import StatCard
from gui.main_window import MainWindow, AdaptiveStackedWidget
from gui.pages.dashboard_page import DashboardPage
from gui.pages.payroll_page import PayrollPage


class TestResponsiveLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.manager = EntityManager()
        self.window = MainWindow(self.manager)
        self.window._load_state()
        self.window.resize(960, 600)
        self.window.show()
        QApplication.processEvents()

    def tearDown(self):
        self.window.close()

    def test_adaptive_stacked_widget_follows_current_child(self):
        """Verifica que AdaptiveStackedWidget retorne los size hints de la página activa y permita compresión horizontal."""
        stack = AdaptiveStackedWidget()
        w_small = QLabel("Small")
        w_small.setMinimumSize(300, 200)
        w_large = QLabel("Large")
        w_large.setMinimumSize(900, 600)

        stack.addWidget(w_small)
        stack.addWidget(w_large)

        # Activo: w_small -> minimumSizeHint horizontal debe ser 0 para flexibilidad
        stack.setCurrentWidget(w_small)
        self.assertEqual(stack.minimumSizeHint().width(), 0)
        self.assertEqual(stack.minimumSizeHint().height(), w_small.minimumSizeHint().height())

        # Activo: w_large -> altura de w_large
        stack.setCurrentWidget(w_large)
        self.assertEqual(stack.minimumSizeHint().width(), 0)
        self.assertEqual(stack.minimumSizeHint().height(), w_large.minimumSizeHint().height())

    def test_zero_horizontal_scrollbar_on_all_pages_at_min_resolution(self):
        """A la resolución mínima soportada (960x600), ninguna sección debe presentar scroll horizontal."""
        sa = self.window.content_scroll_area
        h_bar = sa.horizontalScrollBar()

        all_pages = [
            "Dashboard",
            "Facultades",
            "Programas",
            "Cursos",
            "Estudiantes",
            "Profesores",
            "Administrativos",
            "Inscripciones",
            "Nómina",
            "Reportes",
        ]

        for name in all_pages:
            with self.subTest(page=name):
                self.window._navigate(name)
                QApplication.processEvents()

                viewport_w = sa.viewport().width()
                stack_w = self.window.stack.width()
                page = self.window.stack.currentWidget()
                page_w = page.width()

                # La barra horizontal de la ventana debe estar inactiva y no visible
                self.assertFalse(
                    h_bar.isVisible(),
                    f"Barra horizontal visible en página '{name}' (viewport={viewport_w}, stack={stack_w})"
                )
                self.assertEqual(
                    h_bar.maximum(),
                    0,
                    f"Scroll horizontal > 0 en página '{name}'"
                )
                # El ancho del contenedor no debe exceder el ancho visible
                self.assertLessEqual(
                    stack_w,
                    viewport_w,
                    f"Stack excede viewport en '{name}': {stack_w} > {viewport_w}"
                )
                # La página debe ocupar exactamente el ancho disponible sin rebasarlo
                self.assertLessEqual(
                    page_w,
                    viewport_w,
                    f"Página excede viewport en '{name}': {page_w} > {viewport_w}"
                )

    def test_empty_state_responsive_shrinking(self):
        """EmptyState debe admitir ajuste de línea y ancho mínimo flexible."""
        empty = EmptyState("Título de prueba", "Un subtítulo sumamente largo que describe una acción que no debe desbordar la ventana jamás.")
        self.assertTrue(empty._lbl_title.wordWrap())
        self.assertTrue(empty._lbl_sub.wordWrap())
        self.assertEqual(empty.minimumWidth(), 0)

    def test_search_bar_min_width(self):
        """SearchBar debe mantener ancho estándar de 260px que cabe sin desbordar el viewport."""
        search = SearchBar()
        self.assertEqual(search.minimumWidth(), 260)

    def test_page_header_subtitle_word_wrap(self):
        """PageHeader debe permitir envolver subtítulos largos sin forzar el ancho de página."""
        header = PageHeader("Título", "Un subtítulo descriptivo extremadamente largo para probar el ajuste responsivo de líneas.")
        self.assertTrue(header.findChild(QLabel, "pageHeaderSubtitle").wordWrap())

    def test_dashboard_components_responsive_structure(self):
        """DashboardPage debe estructurar sus paneles con ajuste de línea y donut adaptable."""
        dash = self.window._pages["Dashboard"]
        self.assertIsNotNone(dash)
        self.assertTrue(dash.lbl_payroll_total.wordWrap())

    def test_payroll_components_responsive_structure(self):
        """PayrollPage con datos y banner de ARL debe estructurarse con ajuste de línea."""
        payroll = self.window._pages["Nómina"]
        self.assertTrue(payroll.arl_warning_text.wordWrap())
        self.assertLessEqual(payroll.period_selector.minimumWidth(), 150)
        self.assertLessEqual(payroll.start_date.minimumWidth(), 130)

    def test_crud_actions_visible_in_viewport(self):
        """Los botones de acción principales (ej. '+ Nueva Facultad') deben quedar dentro del viewport."""
        self.window._navigate("Facultades")
        QApplication.processEvents()

        page = self.window._pages["Facultades"]
        action_btn = page.header.findChild(object, "primaryButton")
        self.assertIsNotNone(action_btn)

        # Mapear coordenada X global del botón respecto al viewport de la ventana
        sa = self.window.content_scroll_area
        viewport_rect = sa.viewport().rect()
        btn_top_right = action_btn.mapTo(sa.viewport(), action_btn.rect().topRight())

        self.assertLessEqual(
            btn_top_right.x(),
            viewport_rect.width() + 10,
            f"El botón de acción excede el borde derecho del viewport: {btn_top_right.x()} > {viewport_rect.width()}"
        )


if __name__ == "__main__":
    unittest.main()
