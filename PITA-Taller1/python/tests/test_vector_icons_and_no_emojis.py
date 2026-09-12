"""Pruebas unitarias de iconografía vectorial, multi-DPI, desambiguación semántica y erradicación de emojis."""
import os
import re
import unittest
from unittest.mock import MagicMock

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QPushButton

from gui.components.confirm_dialog import ConfirmDialog
from gui.components.empty_state import EmptyState
from gui.components.icons import _PATHS, icon, pixmap
from gui.components.sidebar import Sidebar
from gui.components.stat_card import StatCard
from gui.pages.payroll_page import PayrollPage
from gui.pages.reports_page import ReportsPage

app = QApplication.instance() or QApplication([])


class TestVectorIconsAndNoEmojis(unittest.TestCase):
    """Verifica que el catálogo de iconos SVG sea completo, soporte multi-DPI y que no queden emojis en la GUI."""

    def test_all_catalog_icons_render_valid_pixmaps_and_icons(self):
        """Todos los identificadores registrados en _PATHS deben generar QPixmap y QIcon no nulos."""
        self.assertGreaterEqual(len(_PATHS), 30, "El catálogo _PATHS debe contener al menos 30 iconos vectoriales")
        for key in _PATHS.keys():
            pm = pixmap(key, "#16A34A", 18)
            self.assertIsInstance(pm, QPixmap)
            self.assertFalse(pm.isNull(), f"El pixmap para '{key}' no debe ser nulo")
            self.assertEqual(pm.width(), 18)
            self.assertEqual(pm.height(), 18)

            ic = icon(key, "#16A34A", 18)
            self.assertIsInstance(ic, QIcon)
            self.assertFalse(ic.isNull(), f"El QIcon para '{key}' no debe ser nulo")

    def test_multi_dpi_scaling_support(self):
        """Verifica que pixmap() genere dimensiones físicas proporcionales a DPR con devicePixelRatio correcto."""
        for dpr in (1.0, 1.25, 1.5, 2.0):
            pm = pixmap("check", "#16A34A", size=20, dpr=dpr)
            expected_px = int(20 * dpr)
            self.assertEqual(pm.width(), expected_px)
            self.assertEqual(pm.height(), expected_px)
            self.assertAlmostEqual(pm.devicePixelRatio(), dpr, places=2)

    def test_sidebar_and_statcard_disambiguation(self):
        """Verifica la desambiguación semántica entre Programas ('layers') y Profesores ('hat')."""
        # 1. Sidebar
        sidebar = Sidebar()
        self.assertEqual(sidebar.NAV_ICON_MAP["Programas"], "layers")
        self.assertEqual(sidebar.NAV_ICON_MAP["Profesores"], "hat")
        self.assertNotEqual(sidebar.NAV_ICON_MAP["Programas"], sidebar.NAV_ICON_MAP["Profesores"])

        btn_prog = sidebar._buttons.get("Programas")
        btn_prof = sidebar._buttons.get("Profesores")
        self.assertIsNotNone(btn_prog)
        self.assertIsNotNone(btn_prof)
        self.assertEqual(btn_prog.property("icon_name"), "layers")
        self.assertEqual(btn_prof.property("icon_name"), "hat")
        self.assertFalse(btn_prog.icon().isNull())
        self.assertFalse(btn_prof.icon().isNull())
        sidebar.close()

        # 2. StatCard
        card_prog = StatCard(title="Programas", value="12")
        self.assertEqual(card_prog.icon_name, "layers")
        card_prog.close()

        card_prof = StatCard(title="Profesores", value="45")
        self.assertEqual(card_prof.icon_name, "hat")
        card_prof.close()

    def test_empty_state_and_confirm_dialog_use_vector_pixmaps(self):
        """Verifica que EmptyState y ConfirmDialog usen QPixmap vectoriales y no texto emoji."""
        # EmptyState
        empty = EmptyState(title="Sin datos", subtitle="No hay registros")
        pm_empty = empty.lbl_icon.pixmap()
        self.assertIsNotNone(pm_empty)
        self.assertFalse(pm_empty.isNull())
        self.assertEqual(empty.lbl_icon.text(), "")
        empty.close()

        # ConfirmDialog
        dlg = ConfirmDialog(title="Confirmar", message="¿Desea continuar?")
        pm_dlg = dlg.icon_lbl.pixmap()
        self.assertIsNotNone(pm_dlg)
        self.assertFalse(pm_dlg.isNull())
        self.assertEqual(dlg.icon_lbl.text(), "")
        dlg.close()

    def test_payroll_page_vector_icons(self):
        """Verifica que la barra de nómina y el banner de ARL utilicen iconos vectoriales."""
        manager = MagicMock()
        page = PayrollPage(manager=manager)

        self.assertFalse(page.view_detail_button.icon().isNull())
        self.assertEqual(page.view_detail_button.text(), "Ver detalle")

        self.assertFalse(page.reports_button.icon().isNull())
        self.assertEqual(page.reports_button.text(), "Reportes")

        self.assertFalse(page.all_slips_action.icon().isNull())
        self.assertEqual(page.all_slips_action.text(), "Generar todos los desprendibles")

        self.assertFalse(page.dashboard_action.icon().isNull())
        self.assertEqual(page.dashboard_action.text(), "Dashboard financiero")

        pm_arl = page.arl_warning_icon.pixmap()
        self.assertIsNotNone(pm_arl)
        self.assertFalse(pm_arl.isNull())
        self.assertEqual(page.arl_warning_icon.text(), "")
        page.close()

    def test_reports_page_vector_icons(self):
        """Verifica que las pestañas de reportes y los botones de exportación CSV usen iconos vectoriales."""
        manager = MagicMock()
        page = ReportsPage(manager=manager)

        # 4 pestañas con iconos vectoriales y títulos limpios
        self.assertEqual(page.tabs.count(), 4)
        for idx in range(4):
            tab_icon = page.tabs.tabIcon(idx)
            self.assertFalse(tab_icon.isNull(), f"La pestaña {idx} debe tener un icono vectorial no nulo")
            tab_text = page.tabs.tabText(idx)
            self.assertNotIn("⚠️", tab_text)
            self.assertNotIn("📚", tab_text)
            self.assertNotIn("💼", tab_text)
            self.assertNotIn("📊", tab_text)

        # Export buttons in tabs
        export_buttons = page.findChildren(QPushButton)
        csv_buttons = [b for b in export_buttons if "Exportar CSV" in b.text()]
        self.assertEqual(len(csv_buttons), 4)
        for btn in csv_buttons:
            self.assertFalse(btn.icon().isNull(), "Cada botón de exportar CSV debe tener icono vectorial")
            self.assertNotIn("📥", btn.text())
        page.close()

    def test_zero_emojis_in_gui_source_files(self):
        """Auditoría estricta: ninguna línea de código en gui/ debe contener caracteres emoji."""
        gui_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "gui"))
        emoji_pattern = re.compile(
            r"[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]"
        )
        forbidden_specific = ["⚠️", "📋", "👁", "💰", "⚡", "📥", "📚", "💼", "📊", "✓", "➔", "🏛"]

        violations = []
        for root, _, files in os.walk(gui_dir):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line_num, line in enumerate(f, 1):
                            emojis = emoji_pattern.findall(line)
                            if emojis:
                                violations.append((file, line_num, emojis, line.strip()))
                            for symbol in forbidden_specific:
                                if symbol in line:
                                    violations.append((file, line_num, [symbol], line.strip()))

        self.assertEqual(
            len(violations),
            0,
            f"Se encontraron emojis o símbolos prohibidos en la GUI:\n"
            + "\n".join(f"{f}:{n}: {e} -> {l}" for f, n, e, l in violations),
        )


if __name__ == "__main__":
    unittest.main()

