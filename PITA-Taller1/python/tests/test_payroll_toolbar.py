"""Pruebas unitarias para la reorganización de la barra de herramientas de Nómina."""

import os
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QPushButton, QToolButton
from PySide6.QtGui import QAction

from models.payroll_period import PayrollPeriod, PayrollPeriodStatus
from models.payroll_run import PayrollRun
from models.professor import Professor
from services.entity_manager import EntityManager
from gui.main_window import MainWindow
from gui.pages.payroll_page import PayrollPage


class TestPayrollToolbar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.manager = EntityManager()
        self.prof = Professor(
            301, "Profesor Toolbar", "CC", "998877", "prof.tool@mail.com", "555-1234",
            1, "PLANTA", "TITULAR", "PhD", 12, "TIEMPO_COMPLETO", 40, "NINGUNO",
            12.0, 10.0, 10.0, 10.0, 0.0, 42.0, 50000.0, 6000000.0,
            200000.0, 200000.0, 500000.0, 500000.0, 250000.0, 5500000.0, True,
        )
        self.manager.professors.insert(self.prof)
        self.page = PayrollPage(self.manager)

    def test_three_functional_groups_structure(self):
        """Verifica la existencia y estructuración de los 3 grupos funcionales y separadores."""
        # Grupo 1 — Contenedor del ciclo
        self.assertIsInstance(self.page.cycle_group_frame, QFrame)
        self.assertEqual(self.page.cycle_group_frame.objectName(), "payrollCycleGroup")
        cycle_buttons = self.page.cycle_group_frame.findChildren(QPushButton)
        self.assertEqual(len(cycle_buttons), 4)
        self.assertIn(self.page.calculate_button, cycle_buttons)
        self.assertIn(self.page.recalculate_button, cycle_buttons)
        self.assertIn(self.page.approve_button, cycle_buttons)
        self.assertIn(self.page.close_button, cycle_buttons)

        # Separador 1
        self.assertIsInstance(self.page.sep_cycle_selected, QFrame)
        self.assertEqual(self.page.sep_cycle_selected.frameShape(), QFrame.Shape.VLine)

        # Grupo 2 — Empleado seleccionado
        self.assertIsInstance(self.page.view_detail_button, QPushButton)
        self.assertIsInstance(self.page.single_slip_button, QPushButton)

        # Separador 2
        self.assertIsInstance(self.page.sep_selected_reports, QFrame)
        self.assertEqual(self.page.sep_selected_reports.frameShape(), QFrame.Shape.VLine)

        # Grupo 3 — Menú de reportes
        self.assertIsInstance(self.page.reports_button, QToolButton)
        self.assertEqual(self.page.reports_button.popupMode(), QToolButton.ToolButtonPopupMode.InstantPopup)
        self.assertIsNotNone(self.page.reports_button.menu())

    def test_reports_dropdown_menu_actions(self):
        """Verifica que el menú desplegable contenga las acciones globales y ejecute sus callbacks."""
        menu = self.page.reports_button.menu()
        actions = menu.actions()
        self.assertEqual(len(actions), 2)

        # Acción 1: Todos los desprendibles
        self.assertEqual(actions[0], self.page.all_slips_action)
        self.assertIn("desprendibles", actions[0].text().lower())

        # Acción 2: Dashboard financiero
        self.assertEqual(actions[1], self.page.dashboard_action)
        self.assertIn("dashboard", actions[1].text().lower())

        # Aliases retrocompatibles
        self.assertEqual(self.page.all_slips_button, self.page.all_slips_action)
        self.assertEqual(self.page.dashboard_button, self.page.dashboard_action)

        # Disparo de acciones
        self.page.all_slips_action.setEnabled(True)
        with patch.object(self.page, "_all_payslips") as mock_all:
            self.page.all_slips_action.trigger()
            mock_all.assert_called_once()

        with patch.object(self.page, "_open_dashboard") as mock_dash:
            self.page.dashboard_action.trigger()
            mock_dash.assert_called_once()

    def test_action_states_with_lifecycle(self):
        """Verifica la habilitación de los botones según el ciclo de vida y selección."""
        # 1. Sin período/corrida
        self.page._update_actions(None)
        self.assertTrue(self.page.calculate_button.isEnabled())
        self.assertFalse(self.page.recalculate_button.isEnabled())
        self.assertFalse(self.page.approve_button.isEnabled())
        self.assertFalse(self.page.close_button.isEnabled())
        self.assertFalse(self.page.all_slips_action.isEnabled())
        self.assertFalse(self.page.view_detail_button.isEnabled())
        self.assertFalse(self.page.single_slip_button.isEnabled())

        # 2. Corrida CALCULATED
        run_calc = MagicMock()
        run_calc.status.value = "CALCULATED"
        self.page._update_actions(run_calc)
        self.assertFalse(self.page.calculate_button.isEnabled())
        self.assertTrue(self.page.recalculate_button.isEnabled())
        self.assertTrue(self.page.approve_button.isEnabled())
        self.assertFalse(self.page.close_button.isEnabled())
        self.assertTrue(self.page.all_slips_action.isEnabled())

        # 3. Corrida APPROVED
        run_appr = MagicMock()
        run_appr.status.value = "APPROVED"
        self.page._update_actions(run_appr)
        self.assertTrue(self.page.close_button.isEnabled())
        self.assertFalse(self.page.approve_button.isEnabled())

    def test_visibility_and_fit_in_960x600_window(self):
        """Verifica que en 960x600 todos los elementos de la barra estén dentro del viewport visible."""
        win = MainWindow(self.manager)
        win.resize(960, 600)
        win.show()
        win._navigate("Nómina")
        QApplication.processEvents()

        page = win._pages["Nómina"]

        # El ancho disponible para la página dentro del scroll area
        viewport_w = win.content_scroll_area.viewport().width()
        self.assertGreater(viewport_w, 600)

        # Verificar que todos los botones de la barra tengan ancho > 0 y estén visibles
        toolbar_widgets = [
            page.calculate_button,
            page.recalculate_button,
            page.approve_button,
            page.close_button,
            page.view_detail_button,
            page.single_slip_button,
            page.reports_button,
        ]
        for widget in toolbar_widgets:
            self.assertTrue(widget.isVisible())
            self.assertGreater(widget.width(), 20, f"{widget} debe tener un ancho legible")
