"""Pruebas unitarias para PayrollPage: verificación de selección pasiva, atajos y diálogos."""

import os
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from models.payroll_period import PayrollPeriod, PayrollPeriodStatus
from models.payroll_run import PayrollRun
from models.professor import Professor
from services.entity_manager import EntityManager
from gui.pages.payroll_page import PayrollPage


class TestPayrollPageSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.manager = EntityManager()
        self.prof = Professor(
            301, "Profesor Prueba", "CC", "12345", "prof@mail.com", "555",
            1, "PLANTA", "ASOCIADO", "PhD", 10, "TIEMPO_COMPLETO", 40, "NINGUNO",
            10.0, 10.0, 10.0, 10.0, 0.0, 40.0, 50000.0, 5000000.0,
            200000.0, 200000.0, 416666.0, 416666.0, 208333.0, 4600000.0, True,
        )
        self.manager.professors.insert(self.prof)

        # Crear período y ejecución de prueba
        period = PayrollPeriod("2026-06", 2026, 6, "2026-06-01", "2026-06-30", PayrollPeriodStatus.CALCULATED)
        run = PayrollRun(
            run_id="RUN-001",
            period_id="2026-06",
            employee_ids=["301"],
            details=[
                {
                    "employee_id": 301,
                    "employee_type": "Professor",
                    "period": "2026-06",
                    "days_worked": 30,
                    "base_salary": 5000000.0,
                    "gross_salary": 5000000.0,
                    "net_salary": 4600000.0,
                    "total_employee_deductions": 400000.0,
                    "total_employer_contributions": 1000000.0,
                    "total_employer_cost": 6000000.0,
                    "ibc": 5000000.0,
                    "service_bonus": 500000.0,
                }
            ],
            totals={
                "gross_salary": 5000000.0,
                "total_employee_deductions": 400000.0,
                "total_employer_contributions": 1000000.0,
                "total_employer_cost": 6000000.0,
            },
            executed_at="2026-06-30T10:00:00",
        )
        self.manager.payroll_cycle_service.periods.append(period)
        self.manager.payroll_cycle_service.runs.append(run)

        self.page = PayrollPage(self.manager)

    def test_passive_selection_does_not_open_dialog(self):
        """Verifica que seleccionar una fila NO dispara QDialog.exec()."""
        with patch.object(QDialog, "exec") as mock_dialog:
            # Seleccionar la fila 0 pasivamente
            self.page.table.selectRow(0)

            # Debe haber selección en la tabla
            self.assertEqual(self.page.table.currentRow(), 0)

            # QDialog.exec() NUNCA debió haberse llamado
            mock_dialog.assert_not_called()

            # Los botones contextuales deben habilitarse
            self.assertTrue(self.page.view_detail_button.isEnabled())
            self.assertTrue(self.page.single_slip_button.isEnabled())

    def test_keyboard_navigation_does_not_open_dialog(self):
        """Verifica que navegar con teclado (cambio de fila) no abre ningún diálogo modal."""
        with patch.object(QDialog, "exec") as mock_dialog:
            self.page.table.setCurrentCell(0, 0)
            self.assertEqual(self.page.table.currentRow(), 0)
            mock_dialog.assert_not_called()

            # Deseleccionar fila
            self.page.table.clearSelection()
            self.page.table.setCurrentCell(-1, -1)
            self.page._on_table_selection_changed()

            # Botones deben deshabilitarse al perder selección
            self.assertFalse(self.page.view_detail_button.isEnabled())
            self.assertFalse(self.page.single_slip_button.isEnabled())
            mock_dialog.assert_not_called()

    def test_double_click_opens_detail_dialog(self):
        """Verifica que el doble clic en una fila sí abre el diálogo de detalle."""
        item = self.page.table.item(0, 0)
        self.assertIsNotNone(item)

        with patch.object(QDialog, "exec") as mock_dialog:
            self.page.table.selectRow(0)
            self.page.table.itemDoubleClicked.emit(item)
            mock_dialog.assert_called_once()

    def test_action_button_opens_detail_dialog_when_selected(self):
        """Verifica que hacer clic en '👁 Ver detalle' abre el diálogo si hay selección."""
        self.page.table.selectRow(0)

        with patch.object(QDialog, "exec") as mock_dialog:
            self.page.view_detail_button.click()
            mock_dialog.assert_called_once()

    def test_action_button_shows_notice_when_no_selection(self):
        """Verifica que '👁 Ver detalle' avisa si no hay fila seleccionada."""
        self.page.table.clearSelection()
        self.page.table.setCurrentCell(-1, -1)

        with patch.object(QMessageBox, "information") as mock_notice, \
             patch.object(QDialog, "exec") as mock_dialog:
            self.page._show_selected_detail()
            mock_notice.assert_called_once()
            mock_dialog.assert_not_called()

    def test_update_summary_with_string_and_mixed_ibc_values(self):
        """Verifica que _update_summary maneja IBC como string sin lanzar TypeError."""
        run = PayrollRun(
            run_id="RUN-STR",
            period_id="2026-06",
            employee_ids=["1", "2", "3"],
            details=[
                {"ibc": "1000000"},
                {"ibc": "2500000"},
                {"ibc": 500000},
                {"ibc": ""},
                {"ibc": None},
            ],
            totals={
                "gross_salary": "4000000",
            },
        )
        self.page._update_summary(run)
        ibc_title, ibc_label = self.page.summary_labels["ibc"]
        self.assertIn("4.000.000", ibc_label.text())


class TestMainWindowLoadStateIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_load_and_reload_state_no_error(self):
        """Verifica que MainWindow cargue y recargue los datos reales sin errores de tipo int + str."""
        from gui.main_window import MainWindow

        with patch.object(QMessageBox, "warning"), \
             patch.object(QMessageBox, "critical") as mock_crit, \
             patch.object(QMessageBox, "information"), \
             patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            window = MainWindow()
            self.assertTrue(window._load_state())
            mock_crit.assert_not_called()

            # Probar también _reload_state
            window._reload_state()
            mock_crit.assert_not_called()


if __name__ == "__main__":
    unittest.main()

