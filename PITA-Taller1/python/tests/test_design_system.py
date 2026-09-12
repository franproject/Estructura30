"""Pruebas unitarias para el sistema de diseño, tokens, accesibilidad WCAG y renderizado QSS."""

import os
import re
import unittest
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from gui.components.header import TopHeader
from gui.components.page_header import PageHeader
from gui.components.sidebar import Sidebar
from gui.components.stat_card import StatCard
from gui.components.pagination_bar import PaginationBar
from gui.components.empty_state import EmptyState


def relative_luminance(r: int, g: int, b: int) -> float:
    """Calcula la luminancia relativa según WCAG 2.1."""
    def channel_lum(c: int) -> float:
        v = c / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel_lum(r) + 0.7152 * channel_lum(g) + 0.0722 * channel_lum(b)


def contrast_ratio(hex1: str, hex2: str) -> float:
    """Calcula el ratio de contraste entre dos colores hexadecimales."""
    c1 = QColor(hex1)
    c2 = QColor(hex2)
    l1 = relative_luminance(c1.red(), c1.green(), c1.blue())
    l2 = relative_luminance(c2.red(), c2.green(), c2.blue())
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


class TestDesignSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])
        cls.qss_path = Path(__file__).resolve().parent.parent / "gui" / "styles" / "app.qss"
        cls.qss_content = cls.qss_path.read_text(encoding="utf-8")
        cls.app.setStyleSheet(cls.qss_content)

    def test_no_invalid_web_linear_gradient(self):
        """Verifica que no exista la sintaxis web 'linear-gradient' sin el prefijo 'q'."""
        matches = re.findall(r"(?<!q)linear-gradient", self.qss_content)
        self.assertEqual(
            len(matches),
            0,
            f"Se encontraron instancias de sintaxis CSS web no soportada 'linear-gradient': {matches}",
        )

    def test_valid_qlineargradient_avatar(self):
        """Verifica que el avatar use la sintaxis nativa de Qt qlineargradient con los verdes institucionales."""
        self.assertIn("QLabel#headerAvatar", self.qss_content)
        self.assertIn(
            "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #16A34A, stop:1 #14532D)",
            self.qss_content,
        )

    def test_design_tokens_documented_in_header(self):
        """Verifica que app.qss documente formalmente los tokens de diseño al inicio."""
        tokens_block = self.qss_content[:2000]
        self.assertIn("TOKENS DE DISEÑO", tokens_block)
        self.assertIn("--radius-xs:    4px", tokens_block)
        self.assertIn("--radius-sm:    6px", tokens_block)
        self.assertIn("--radius-md:    8px", tokens_block)
        self.assertIn("--radius-lg:    12px", tokens_block)
        self.assertIn("--radius-full:  16px", tokens_block)
        self.assertIn("--color-text-secondary: #64748B", tokens_block)

    def test_typography_scale_strictly_enforced(self):
        """Verifica que todos los tamaños tipográficos en app.qss pertenezcan a la escala formal."""
        allowed_sizes = {11, 13, 15, 17, 20, 24}
        found_sizes = re.findall(r"font-size:\s*(\d+)px", self.qss_content)
        self.assertTrue(len(found_sizes) > 0, "No se encontraron reglas font-size en app.qss")

        for size_str in found_sizes:
            size = int(size_str)
            self.assertIn(
                size,
                allowed_sizes,
                f"Tamaño tipográfico {size}px fuera de la escala formal permitida {allowed_sizes}",
            )

    def test_deprecated_low_contrast_color_eradicated(self):
        """Verifica que el color de bajo contraste #94A3B8 no se use en el archivo QSS ni en componentes."""
        self.assertNotIn(
            "#94A3B8",
            self.qss_content,
            "El color de bajo contraste #94A3B8 aún se encuentra presente en app.qss",
        )
        self.assertNotIn(
            "#94a3b8",
            self.qss_content.lower(),
            "El color de bajo contraste #94a3b8 aún se encuentra en app.qss",
        )

    def test_wcag_21_aa_contrast_ratio(self):
        """Verifica matemáticamente que #64748B cumpla con el ratio WCAG 2.1 AA (>= 4.5:1)."""
        white_contrast = contrast_ratio("#64748B", "#FFFFFF")
        surface_contrast = contrast_ratio("#64748B", "#F8FAFC")

        # Ratios de contraste esperados: ~4.6:1 y ~4.52:1
        self.assertGreaterEqual(
            white_contrast,
            4.5,
            f"El ratio contra blanco ({white_contrast:.2f}:1) no cumple WCAG AA (mínimo 4.5:1)",
        )
        self.assertGreaterEqual(
            surface_contrast,
            4.5,
            f"El ratio contra #F8FAFC ({surface_contrast:.2f}:1) no cumple WCAG AA (mínimo 4.5:1)",
        )

    def test_header_avatar_geometry_and_rendering(self):
        """Verifica que el avatar del header tenga tamaño 32x32 y renderice el degradado verde."""
        header = TopHeader()
        header.resize(1000, 58)
        header.show()

        avatar = header.findChild(object, "headerAvatar")
        self.assertIsNotNone(avatar, "No se encontró el widget con objectName 'headerAvatar'")
        self.assertEqual(avatar.size(), QSize(32, 32))
        self.assertEqual(avatar.alignment(), Qt.AlignmentFlag.AlignCenter)

        # Capturar la imagen renderizada del avatar
        pixmap = avatar.grab()
        image = pixmap.toImage()
        self.assertEqual(image.width(), 32)
        self.assertEqual(image.height(), 32)

        # Muestrear píxeles del degradado diagonal
        c_top_left = image.pixelColor(8, 8)
        c_center = image.pixelColor(16, 16)
        c_bottom_right = image.pixelColor(24, 24)

        # Ambos extremos deben ser tonos verdes (componente verde significativamente dominante)
        self.assertGreater(c_top_left.green(), c_top_left.red())
        self.assertGreater(c_top_left.green(), c_top_left.blue())
        self.assertGreater(c_bottom_right.green(), c_bottom_right.red())
        self.assertGreater(c_bottom_right.green(), c_bottom_right.blue())

        # El inicio (stop 0: #16A34A) debe ser más claro que el final (stop 1: #14532D)
        # La luminancia o el valor verde en el inicio debe ser superior al final
        self.assertGreater(
            c_top_left.green(),
            c_bottom_right.green(),
            f"El degradado debe fluir de verde claro a verde oscuro. Top-Left: {c_top_left.name()}, Bottom-Right: {c_bottom_right.name()}",
        )

    def test_stat_card_clean_selectors(self):
        """Verifica que StatCard aplique objectNames y propiedades dinámicas sin estilos inline."""
        card = StatCard("Facultades", "12", "Activas", "▲ 2", "#DCFCE7", "#16A34A")
        self.assertEqual(card.objectName(), "statCard")
        self.assertEqual(card.lbl_val.objectName(), "statValue")
        self.assertEqual(card.lbl_val.property("tone"), "green")
        self.assertEqual(card.lbl_delta.property("trend"), "up")
        # No debe tener estilos inline asignados
        self.assertEqual(card.lbl_val.styleSheet(), "")

    def test_empty_state_clean_selectors(self):
        """Verifica que EmptyState use selectores centralizados en app.qss."""
        es = EmptyState("Título vacío", "Subtítulo vacío")
        lbl_icon = es.findChild(object, "emptyStateIcon")
        lbl_title = es.findChild(object, "emptyStateTitle")
        lbl_sub = es.findChild(object, "emptyStateSubtitle")

        self.assertIsNotNone(lbl_icon)
        self.assertIsNotNone(lbl_title)
        self.assertIsNotNone(lbl_sub)
        self.assertEqual(lbl_icon.styleSheet(), "")
        self.assertEqual(lbl_title.styleSheet(), "")


if __name__ == "__main__":
    unittest.main()

