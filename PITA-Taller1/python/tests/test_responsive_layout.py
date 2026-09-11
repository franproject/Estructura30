"""Pruebas unitarias para layout adaptativo, scroll areas y estilos en MainWindow."""

import os
import re
import unittest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QScrollArea, QStackedWidget

from services.entity_manager import EntityManager
from gui.main_window import MainWindow


class TestResponsiveLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.manager = EntityManager()
        self.window = MainWindow(manager=self.manager)

    def tearDown(self):
        self.window.close()

    def test_main_window_minimum_size_is_960x600(self):
        """Verifica que el minimumSize de MainWindow se redujo a 960x600."""
        min_size = self.window.minimumSize()
        self.assertEqual(min_size.width(), 960)
        self.assertEqual(min_size.height(), 600)

    def test_main_content_is_wrapped_in_scroll_area(self):
        """Verifica que QStackedWidget y su contenido están envueltos en un QScrollArea."""
        self.assertTrue(hasattr(self.window, "content_scroll_area"))
        self.assertIsInstance(self.window.content_scroll_area, QScrollArea)
        self.assertTrue(self.window.content_scroll_area.widgetResizable())
        self.assertEqual(self.window.content_scroll_area.widget(), self.window.stack)
        self.assertIsInstance(self.window.stack, QStackedWidget)

    def test_scroll_area_scrollbar_policies(self):
        """Verifica que las políticas de scrollbar estén configuradas como AsNeeded."""
        scroll_area = self.window.content_scroll_area
        self.assertEqual(
            scroll_area.horizontalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )
        self.assertEqual(
            scroll_area.verticalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )

    def test_sidebar_has_adaptive_nav_scroll(self):
        """Verifica que la barra lateral cuenta con área scrollable para sus botones de navegación."""
        sidebar = self.window.sidebar
        nav_scroll = sidebar.findChild(QScrollArea, "sidebarNavScroll")
        self.assertIsNotNone(nav_scroll)
        self.assertTrue(nav_scroll.widgetResizable())

    def test_app_qss_no_universal_color_selector(self):
        """Verifica que no exista el selector universal '* { color: ... }' en app.qss."""
        qss_path = os.path.join(
            os.path.dirname(__file__), "..", "gui", "styles", "app.qss"
        )
        with open(qss_path, encoding="utf-8") as f:
            content = f.read()

        # Buscar si '*' tiene la propiedad color
        universal_rule_match = re.search(r"\*\s*\{([^}]+)\}", content)
        self.assertIsNotNone(universal_rule_match)
        universal_rule_body = universal_rule_match.group(1)
        self.assertNotIn("color:", universal_rule_body)

        # Verificar que widgets específicos sí definen color base
        self.assertIn("QWidget, QLabel, QFrame", content)
        self.assertIn("color: #0F172A;", content)

    def test_app_qss_font_sizes_are_at_least_11px(self):
        """Verifica que ningún tamaño de fuente en app.qss sea menor a 11px."""
        qss_path = os.path.join(
            os.path.dirname(__file__), "..", "gui", "styles", "app.qss"
        )
        with open(qss_path, encoding="utf-8") as f:
            content = f.read()

        font_sizes = [
            int(m.group(1))
            for m in re.finditer(r"font-size:\s*([0-9]+)px", content)
        ]
        sub_11 = [size for size in font_sizes if size < 11]
        self.assertEqual(sub_11, [], f"Fuentes menores a 11px encontradas: {sub_11}")


if __name__ == "__main__":
    unittest.main()

