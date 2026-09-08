import os
import tempfile
import unittest
from datetime import date

from models.faculty import Faculty
from models.professor import Professor
from services.payroll_cycle import PayrollCycleService
from services.payroll_engine import PayrollRules
from services.payslip_service import PayslipService


class PayslipTests(unittest.TestCase):
    def setUp(self):
        self.professor = Professor(
            professor_id=3,
            full_name="Luis Gomez",
            document_type="CC",
            document_number="321",
            faculty_id=1,
            employment_type="Planta",
            linkage_type="PROFESSOR_PLANTA",
            category_rank="Asociado",
            academic_title="PhD",
            hire_date="2020-01-10",
            category_score=10,
            title_score=5,
            experience_score=3,
            productivity_score=4,
            academic_management_score=2,
            point_value=1000,
            base_monthly_salary=5000000,
            worked_days=30,
            active=True,
        )
        self.faculty = Faculty(faculty_id=1, name="Ingenieria", active=True)
        self.cycle = PayrollCycleService()
        self.period = self.cycle.create_period(2026, 9, "2026-09-01", "2026-09-30")
        self.run = self.cycle.calculate_run(self.period.period_id, [self.professor], PayrollRules())
        self.service = PayslipService(
            self.cycle, [self.professor], [self.faculty],
            {"name": "Universidad de Prueba", "id": "900123"},
        )

    def test_structured_payslip_uses_official_run_detail(self):
        payslip = self.service.generate_payslip(3, self.period.period_id, PayrollRules())
        detail = self.run.details[0]
        self.assertEqual(payslip.run_id, self.run.run_id)
        self.assertEqual(payslip.employee["full_name"], "Luis Gomez")
        self.assertEqual(payslip.employee["faculty"], "Ingenieria")
        self.assertEqual(payslip.academic_base["total_points"], 24)
        self.assertEqual(payslip.summary["net_salary"], detail["net_salary"])
        self.assertEqual(payslip.summary["ibc"], detail["ibc"])
        self.assertEqual(payslip.trace_id, f"{self.run.run_id}:3")

    def test_all_period_payslips_are_individual(self):
        payslips = self.service.generate_period_payslips(self.period.period_id, PayrollRules())
        self.assertEqual(len(payslips), 1)
        self.assertNotEqual(payslips[0].payslip_id, self.run.run_id)

    def test_pdf_is_generated_from_payslip(self):
        with tempfile.TemporaryDirectory() as directory:
            output = os.path.join(directory, "payslip.pdf")
            generated = self.service.generate_payslip_pdf(3, self.period.period_id, PayrollRules(), output)
            self.assertEqual(str(generated), output)
            with open(output, "rb") as file:
                self.assertEqual(file.read(4), b"%PDF")

    def test_unknown_professor_is_rejected(self):
        with self.assertRaises(ValueError):
            self.service.generate_payslip(99, self.period.period_id, PayrollRules())


if __name__ == "__main__":
    unittest.main()
