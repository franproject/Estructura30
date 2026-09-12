import json
import os
import tempfile
import unittest
import warnings
from datetime import date
from decimal import Decimal

from models.administrative import Administrative
from models.professor import Professor
from persistence.file_manager import (
    clear_load_issues,
    get_load_issues,
    load_administrative_staff,
    load_professors,
    save_administrative_staff,
    save_professors,
)
from services.payroll_adapters import calculate_model_payroll
from services.payroll_engine import PayrollPeriod, PayrollRules


class PayrollIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.period = PayrollPeriod("2026-09", date(2026, 9, 1), date(2026, 9, 30), 30)
        self.rules = PayrollRules()

    def test_new_labor_fields_are_preserved(self):
        professor = Professor(
            professor_id=1,
            full_name="Ana Gomez",
            employment_type="Planta",
            hire_date="2020-01-10",
            salary_type="FIXED_MONTHLY",
            arl_risk_class="I",
            social_security_config_id="2026",
            worked_days=30,
            continuous_service_days=360,
            salary_concepts=[{"code": "SALARY_ADJUSTMENT", "amount": 100000}],
        )
        self.assertEqual(professor.hire_date, "2020-01-10")
        self.assertEqual(professor.salary_concepts[0]["code"], "SALARY_ADJUSTMENT")

    def test_legacy_json_loads_with_safe_defaults_and_warning(self):
        clear_load_issues()
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "professors.json")
            with open(path, "w", encoding="utf-8") as file:
                json.dump([{"professor_id": 3, "full_name": "Legacy", "active": True}], file)
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                loaded = load_professors(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].worked_days, 0)
            self.assertEqual(loaded[0].employment_status, "UNKNOWN")
            issues = get_load_issues()
            self.assertTrue(any("Legacy" in issue and "campos laborales" in issue for issue in issues))

    def test_new_fields_round_trip_for_both_employee_types(self):
        professor = Professor(professor_id=1, full_name="Ana", hire_date="2020-01-10", worked_days=12)
        administrative = Administrative(administrative_id=2, full_name="Luis", termination_date="2026-09-15", worked_days=15)
        with tempfile.TemporaryDirectory() as directory:
            professor_path = os.path.join(directory, "professors.json")
            administrative_path = os.path.join(directory, "administrative.json")
            self.assertTrue(save_professors([professor], professor_path))
            self.assertTrue(save_administrative_staff([administrative], administrative_path))
            self.assertEqual(load_professors(professor_path)[0].hire_date, "2020-01-10")
            self.assertEqual(load_professors(professor_path)[0].worked_days, 12)
            self.assertEqual(load_administrative_staff(administrative_path)[0].termination_date, "2026-09-15")
            self.assertEqual(load_administrative_staff(administrative_path)[0].worked_days, 15)

    def test_model_calculation_ignores_legacy_derived_values(self):
        administrative = Administrative(
            administrative_id=7,
            full_name="Maria Ruiz",
            base_salary=1000000,
            health_discount=999999,
            pension_discount=999999,
            severance_provision=999999,
            net_salary=1,
            worked_days=30,
        )
        result = calculate_model_payroll(administrative, self.period, self.rules)
        self.assertEqual(result.employee_health, Decimal("40000"))
        self.assertEqual(result.employee_pension, Decimal("40000"))
        self.assertEqual(result.net_salary, Decimal("920000"))


if __name__ == "__main__":
    unittest.main()
