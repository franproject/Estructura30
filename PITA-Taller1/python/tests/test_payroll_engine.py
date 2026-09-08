import unittest
from datetime import date
from decimal import Decimal

from services.payroll_engine import (
    PayrollDomainError,
    PayrollEmployee,
    PayrollNovelty,
    PayrollPeriod,
    PayrollRules,
    calculate_payroll,
)


class PayrollEngineTests(unittest.TestCase):
    def setUp(self):
        self.period = PayrollPeriod("2026-09", date(2026, 9, 1), date(2026, 9, 30), 30)

    def test_professor_uses_academic_points_when_base_is_missing(self):
        employee = PayrollEmployee(
            "P1", "Professor", "planta", point_value=1000,
            category_score=10, title_score=5, experience_score=3,
            productivity_score=4, academic_management_score=2,
        )
        result = calculate_payroll(employee, self.period, PayrollRules())
        self.assertEqual(result.base_salary, Decimal("24000"))
        self.assertEqual(result.service_bonus_provision, Decimal("167"))
        self.assertEqual(result.severance_provision, Decimal("167"))

    def test_non_salary_excess_enters_ibc(self):
        employee = PayrollEmployee("A1", "Administrative", "planta", base_monthly_salary=1000000)
        novelty = PayrollNovelty("BONUS", amount=1000000, is_salary=False, affects_ibc=False)
        result = calculate_payroll(employee, self.period, PayrollRules(), [novelty])
        self.assertEqual(result.gross_salary, Decimal("2000000"))
        self.assertEqual(result.ibc, Decimal("1200000"))
        self.assertEqual(result.employee_health, Decimal("48000"))

    def test_stored_legacy_benefits_are_not_used(self):
        employee = PayrollEmployee("A1", "Administrative", "planta", base_monthly_salary=1000000)
        result = calculate_payroll(employee, self.period, PayrollRules())
        self.assertEqual(result.service_bonus_provision, Decimal("6942"))
        self.assertEqual(result.severance_provision, Decimal("6942"))
        self.assertEqual(result.net_salary, Decimal("920000"))

    def test_service_bonus_uses_configured_threshold_and_rate(self):
        employee = PayrollEmployee(
            "A1", "Administrative", "planta", base_monthly_salary=2000000,
            continuous_service_days=360,
        )
        rules = PayrollRules(service_bonus_top=2500000)
        result = calculate_payroll(employee, self.period, rules)
        self.assertEqual(result.service_bonus, Decimal("1000000"))

    def test_exoneration_and_rounding_are_parameterized(self):
        employee = PayrollEmployee("A1", "Administrative", "planta", base_monthly_salary=1234567)
        rules = PayrollRules(health_exempt=True, sena_exempt=True, icbf_exempt=True)
        result = calculate_payroll(employee, self.period, rules)
        self.assertEqual(result.employee_health, Decimal("0"))
        self.assertEqual(result.employer_health, Decimal("0"))
        self.assertEqual(result.sena, Decimal("0"))
        self.assertEqual(result.icbf, Decimal("0"))
        self.assertEqual(result.employee_pension, Decimal("49383"))

    def test_invalid_period_is_rejected(self):
        period = PayrollPeriod("", date(2026, 9, 2), date(2026, 9, 1), 31)
        with self.assertRaises(PayrollDomainError):
            calculate_payroll(
                PayrollEmployee("A1", "Administrative", "planta", base_monthly_salary=1),
                period,
                PayrollRules(),
            )


if __name__ == "__main__":
    unittest.main()
