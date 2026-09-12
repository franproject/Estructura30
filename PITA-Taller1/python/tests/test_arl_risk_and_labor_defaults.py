"""Pruebas unitarias para la detección, configuración y visualización de campos laborales y riesgo ARL.

Verifica:
1. persistence/file_manager.py:
   - _labor_kwargs no emite RuntimeWarning invisible en consola.
   - Registra una incidencia detallada en _LOAD_ISSUES con nombre del empleado y campos faltantes.
2. gui/main_window.py:
   - _load_state() notifica al usuario vía QMessageBox.warning si hay incidencias laborales.
   - Los formularios CRUD de Profesores y Administrativos incluyen el campo arl_risk_class.
3. gui/components/entity_dialog.py:
   - arl_risk_class se renderiza como QComboBox con las 5 clases colombianas y porcentajes.
   - values() devuelve el código ("I", "II", "III", "IV", "V").
   - Preselecciona correctamente el valor del empleado al editar.
4. gui/pages/payroll_page.py:
   - Muestra banner de advertencia si hay empleados activos en Clase I.
   - Botón de revisión abre diálogo informativo con la tabla de empleados afectados.
"""

import os
import unittest
import warnings
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QMessageBox, QTableWidget

from models.administrative import Administrative
from models.linked_list import LinkedList
from models.professor import Professor
from persistence.file_manager import (
    _LABOR_DEFAULTS,
    _labor_kwargs,
    clear_load_issues,
    get_load_issues,
    _LOAD_ISSUES,
)
from services.entity_manager import EntityManager
from gui.components.entity_dialog import ARL_RISK_CLASSES, EntityDialog
from gui.main_window import MainWindow
from gui.pages.payroll_page import PayrollPage


class TestArlRiskAndLaborDefaults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        clear_load_issues()

    def tearDown(self):
        clear_load_issues()

    # -------------------------------------------------------------------------
    # 1. PERSISTENCE / FILE_MANAGER TESTS
    # -------------------------------------------------------------------------
    def test_labor_kwargs_no_runtime_warning_and_records_issue(self):
        """Verifica que _labor_kwargs no emita RuntimeWarning y registre el issue con el nombre del empleado."""
        raw_data = {
            "professor_id": 42,
            "full_name": "Dra. Maria Lopez",
            "document_number": "98765432",
        }

        with warnings.catch_warnings(record=True) as captured_warnings:
            warnings.simplefilter("always")
            result = _labor_kwargs(raw_data, "Professor")

            # Ningún RuntimeWarning debe haber sido emitido
            runtime_warnings = [w for w in captured_warnings if issubclass(w.category, RuntimeWarning)]
            self.assertEqual(len(runtime_warnings), 0, "No debe emitirse RuntimeWarning en _labor_kwargs")

        # Verifica los valores por defecto asignados
        self.assertEqual(result["arl_risk_class"], "I")
        self.assertEqual(result["social_security_config_id"], "DEFAULT")

        # Verifica el registro en _LOAD_ISSUES
        issues = get_load_issues()
        self.assertEqual(len(issues), 1)
        self.assertIn("Dra. Maria Lopez", issues[0])
        self.assertIn("[Professor]", issues[0])
        self.assertIn("campos laborales con valores por defecto", issues[0])
        self.assertIn("Requiere revisión de ARL/Seguridad Social", issues[0])

    def test_labor_kwargs_complete_data_does_not_add_issues(self):
        """Si la entidad contiene todos los campos laborales, no genera incidencias."""
        raw_data = {
            "administrative_id": 10,
            "full_name": "Pedro Perez",
            **_LABOR_DEFAULTS,
            "arl_risk_class": "III",
        }

        with warnings.catch_warnings(record=True) as captured_warnings:
            warnings.simplefilter("always")
            result = _labor_kwargs(raw_data, "Administrative")
            self.assertEqual(len(captured_warnings), 0)

        self.assertEqual(result["arl_risk_class"], "III")
        self.assertEqual(len(get_load_issues()), 0)

    # -------------------------------------------------------------------------
    # 2. ENTITY_DIALOG ARL RISK CLASS SELECTOR TESTS
    # -------------------------------------------------------------------------
    def test_entity_dialog_renders_arl_risk_as_combobox_with_five_classes(self):
        """EntityDialog debe renderizar arl_risk_class como QComboBox con las 5 clases colombianas."""
        fields = (
            ("professor_id", "ID Profesor", "int"),
            ("full_name", "Nombre Completo", "text"),
            ("arl_risk_class", "Clase de Riesgo ARL", "choice", ["I", "II", "III", "IV", "V"]),
        )
        dialog = EntityDialog("Nuevo Profesor", fields)

        widget = dialog._widgets.get("arl_risk_class")
        self.assertIsInstance(widget, QComboBox)
        self.assertEqual(widget.count(), 5)

        # Verificar códigos y descripciones con tasas
        items_data = [widget.itemData(i) for i in range(5)]
        items_text = [widget.itemText(i) for i in range(5)]
        self.assertEqual(items_data, ["I", "II", "III", "IV", "V"])
        self.assertTrue(any("0.522%" in t for t in items_text))
        self.assertTrue(any("6.960%" in t for t in items_text))

        # Valor por defecto inicial debe ser "I"
        values = dialog.values()
        self.assertEqual(values["arl_risk_class"], "I")

        # Seleccionar Clase IV y verificar valores devueltos
        widget.setCurrentIndex(3)  # Índice 3 es Clase IV
        self.assertEqual(dialog.values()["arl_risk_class"], "IV")

    def test_entity_dialog_preselects_existing_arl_risk_class(self):
        """Al editar una entidad existente, el combo box de ARL debe preseleccionar su clase."""
        prof = Professor(
            professor_id=105,
            full_name="Dr. Químico Experimental",
            faculty_id=1,
            arl_risk_class="IV",
        )
        fields = (
            ("professor_id", "ID", "int"),
            ("full_name", "Nombre", "text"),
            ("arl_risk_class", "Clase de Riesgo ARL", "choice", ["I", "II", "III", "IV", "V"]),
        )
        dialog = EntityDialog("Editar Profesor", fields, entity=prof)

        widget = dialog._widgets.get("arl_risk_class")
        self.assertEqual(widget.currentData(), "IV")
        self.assertEqual(dialog.values()["arl_risk_class"], "IV")

    # -------------------------------------------------------------------------
    # 3. MAIN_WINDOW TESTS (FIELDS & LOAD WARNING)
    # -------------------------------------------------------------------------
    def test_main_window_crud_pages_contain_arl_risk_field(self):
        """Verifica que las definiciones CRUD de Profesores y Administrativos en MainWindow incluyan arl_risk_class."""
        manager = EntityManager()
        window = MainWindow(manager=manager)
        try:
            prof_page = window._pages.get("Profesores")
            admin_page = window._pages.get("Administrativos")

            self.assertIsNotNone(prof_page)
            self.assertIsNotNone(admin_page)

            prof_fields = [f[0] for f in prof_page.fields]
            admin_fields = [f[0] for f in admin_page.fields]

            self.assertIn("arl_risk_class", prof_fields)
            self.assertIn("arl_risk_class", admin_fields)
        finally:
            window.close()

    @patch("gui.main_window.load_faculties", return_value=LinkedList())
    @patch("gui.main_window.load_programs", return_value=LinkedList())
    @patch("gui.main_window.load_courses", return_value=LinkedList())
    @patch("gui.main_window.load_students", return_value=LinkedList())
    @patch("gui.main_window.load_professors", return_value=LinkedList())
    @patch("gui.main_window.load_administrative_staff", return_value=LinkedList())
    @patch("gui.main_window.load_enrollments", return_value=LinkedList())
    @patch("gui.main_window.load_payroll_periods", return_value=[])
    @patch("gui.main_window.load_payroll_runs", return_value=[])
    @patch("gui.main_window.load_payroll_novelties", return_value=[])
    @patch("gui.main_window.load_payroll_audit", return_value=[])
    @patch("gui.main_window.QMessageBox.warning")
    @patch("gui.main_window.QMessageBox.critical")
    def test_main_window_load_state_triggers_warning_on_labor_issues(self, mock_crit, mock_warning, *mocks):
        """MainWindow._load_state() debe mostrar QMessageBox.warning si hay issues laborales."""
        manager = EntityManager()
        window = MainWindow(manager=manager)
        try:
            with patch("gui.main_window.get_load_issues") as mock_issues:
                mock_issues.return_value = [
                    "[Professor] Ing. Carlos: se completaron campos laborales con valores por defecto (arl_risk_class). Requiere revisión de ARL/Seguridad Social.",
                ]
                with patch.object(window.manager, "link_hierarchical_references"):
                    window._load_state()

                mock_warning.assert_called_once()
                args, _ = mock_warning.call_args
                # args: (parent, title, text)
                self.assertIn("Configuración Laboral y Riesgo ARL", args[1])
                self.assertIn("Ing. Carlos", args[2])
                self.assertIn("Clase I", args[2])
        finally:
            window.close()

    # -------------------------------------------------------------------------
    # 4. PAYROLL_PAGE ARL WARNING BANNER & INSPECTION DIALOG TESTS
    # -------------------------------------------------------------------------
    def test_payroll_page_warning_banner_visible_when_default_arl(self):
        """PayrollPage muestra el banner de advertencia si hay empleados activos en Clase I."""
        manager = EntityManager()
        prof = Professor(
            professor_id=1,
            full_name="Profesor Riesgo Minimo",
            faculty_id=1,
            base_monthly_salary=3000000.0,
            active=True,
            arl_risk_class="I",
        )
        manager.professors.insert(prof)

        page = PayrollPage(manager)
        try:
            page.refresh()
            self.assertFalse(page.arl_warning_banner.isHidden())
            self.assertIn("1 empleado(s) activo(s)", page.arl_warning_text.text())

            default_emps = page._get_default_arl_employees()
            self.assertEqual(len(default_emps), 1)
            self.assertEqual(default_emps[0].professor_id, 1)

            # Si se actualiza el empleado a Clase II (riesgo bajo o superior)
            prof.arl_risk_class = "II"
            page.refresh()
            self.assertTrue(page.arl_warning_banner.isHidden())
        finally:
            page.close()

    def test_payroll_page_show_default_arl_dialog(self):
        """_show_default_arl_dialog crea y muestra la tabla de empleados afectados."""
        manager = EntityManager()
        prof = Professor(
            professor_id=10,
            full_name="Ana Gomez",
            faculty_id=1,
            active=True,
            arl_risk_class="I",
        )
        admin = Administrative(
            administrative_id=20,
            full_name="Jorge Diaz",
            position="Operario Laboratorio",
            active=True,
            arl_risk_class="I",
        )
        manager.professors.insert(prof)
        manager.administrative_staff.insert(admin)

        page = PayrollPage(manager)
        try:
            with patch.object(QDialog, "exec") as mock_exec:
                page._show_default_arl_dialog()
                mock_exec.assert_called_once()
        finally:
            page.close()


if __name__ == "__main__":
    unittest.main()

