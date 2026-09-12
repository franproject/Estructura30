import unittest
from decimal import Decimal
import os
import tempfile

from models.faculty import Faculty
from models.professor import Professor
from services.payroll_cycle import PayrollCycleService
from services.payroll_dashboard import PayrollFinancialDashboard
from services.payroll_engine import PayrollRules
from services.payslip_service import PayslipService


class PayrollFinancialDashboardTests(unittest.TestCase):
    def setUp(self):
        self.professor = Professor(
            professor_id=10,
            full_name="Profesor Titular",
            document_type="CC",
            document_number="12345",
            faculty_id=1,
            employment_type="Planta",
            linkage_type="PROFESSOR_PLANTA",
            category_rank="Titular",
            academic_title="Doctorado",
            hire_date="2018-01-01",
            base_monthly_salary=10000000,
            continuous_service_days=720,  # More than 360 days
            worked_days=30,
            active=True,
        )
        self.faculty = Faculty(faculty_id=1, name="Ingenierías", active=True)
        self.cycle = PayrollCycleService()

    def test_regular_month_net_salary_does_not_exceed_gross(self):
        # In September (month 9), service_bonus in cash must be 0
        period = self.cycle.create_period(2026, 9, "2026-09-01", "2026-09-30")
        run = self.cycle.calculate_run(period.period_id, [self.professor], PayrollRules())

        dashboard = PayrollFinancialDashboard(run, [self.professor], [self.faculty])
        snapshot = dashboard.snapshot()

        # Gross salary should be 10,000,000
        self.assertEqual(snapshot["gross_salary"], Decimal("10000000"))
        # Total deductions: Health 4% (400,000) + Pension 4% (400,000) = 800,000
        self.assertEqual(snapshot["total_employee_deductions"], Decimal("800000"))
        # Service bonus in cash MUST be 0 in September
        self.assertEqual(snapshot["total_service_bonus_paid"], Decimal("0"))
        # Provision must be accrued for the employer liability
        self.assertGreater(snapshot["total_service_bonus_provision"], Decimal("0"))
        # Net salary MUST equal gross - deductions = 9,200,000
        self.assertEqual(snapshot["total_net_paid"], Decimal("9200000"))
        # Total net paid MUST be less than gross salary
        self.assertLess(snapshot["total_net_paid"], snapshot["gross_salary"])

    def test_june_month_service_bonus_is_paid(self):
        # In June (month 6), service_bonus in cash is liquidated
        period = self.cycle.create_period(2026, 6, "2026-06-01", "2026-06-30")
        run = self.cycle.calculate_run(period.period_id, [self.professor], PayrollRules())

        dashboard = PayrollFinancialDashboard(run, [self.professor], [self.faculty])
        snapshot = dashboard.snapshot()

        self.assertEqual(snapshot["gross_salary"], Decimal("10000000"))
        # Service bonus paid in June: 35% of 10,000,000 = 3,500,000
        self.assertEqual(snapshot["total_service_bonus_paid"], Decimal("3500000"))
        # Net salary: 10,000,000 gross + 3,500,000 bonus - 800,000 deductions = 12,700,000
        self.assertEqual(snapshot["total_net_paid"], Decimal("12700000"))

    def test_december_month_service_bonus_is_paid(self):
        # In December (month 12), service_bonus in cash is liquidated
        period = self.cycle.create_period(2026, 12, "2026-12-01", "2026-12-31")
        run = self.cycle.calculate_run(period.period_id, [self.professor], PayrollRules())

        dashboard = PayrollFinancialDashboard(run, [self.professor], [self.faculty])
        snapshot = dashboard.snapshot()

        self.assertEqual(snapshot["total_service_bonus_paid"], Decimal("3500000"))
        self.assertEqual(snapshot["total_net_paid"], Decimal("12700000"))

    def test_payslip_renders_bonus_distinction_correctly(self):
        period_sept = self.cycle.create_period(2026, 9, "2026-09-01", "2026-09-30")
        run_sept = self.cycle.calculate_run(period_sept.period_id, [self.professor], PayrollRules())

        payslip_service = PayslipService(self.cycle, [self.professor], [self.faculty])
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = os.path.join(tmp_dir, "payslip_sept.pdf")
            payslip_service.generate_payslip_pdf(10, period_sept.period_id, PayrollRules(), pdf_path)
            self.assertTrue(os.path.exists(pdf_path))
            self.assertGreater(os.path.getsize(pdf_path), 0)

        period_june = self.cycle.create_period(2026, 6, "2026-06-01", "2026-06-30")
        run_june = self.cycle.calculate_run(period_june.period_id, [self.professor], PayrollRules())
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path_june = os.path.join(tmp_dir, "payslip_june.pdf")
            payslip_service.generate_payslip_pdf(10, period_june.period_id, PayrollRules(), pdf_path_june)
            self.assertTrue(os.path.exists(pdf_path_june))
            self.assertGreater(os.path.getsize(pdf_path_june), 0)


if __name__ == "__main__":
    unittest.main()

