import os
import tempfile
import unittest
from datetime import date

from decimal import Decimal

from models.administrative import Administrative
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
        self.administrative = Administrative(
            administrative_id=20,
            full_name="Carlos Ruiz",
            document_type="CC",
            document_number="88812345",
            position="Secretario General",
            employment_type="Término Indefinido",
            base_salary=2200000.0,
            worked_days=30,
            active=True,
            hire_date="2021-05-15",
            arl_risk_class="I",
        )
        self.administrative_high_salary = Administrative(
            administrative_id=21,
            full_name="Directora Financiera",
            document_type="CC",
            document_number="99988776",
            position="Directora de Planeación",
            employment_type="Término Indefinido",
            base_salary=6500000.0,
            worked_days=30,
            active=True,
            hire_date="2019-01-10",
            arl_risk_class="I",
        )
        self.faculty = Faculty(faculty_id=1, name="Ingenieria", active=True)
        self.cycle = PayrollCycleService()
        self.period = self.cycle.create_period(2026, 9, "2026-09-01", "2026-09-30")
        self.run = self.cycle.calculate_run(
            self.period.period_id,
            [self.professor, self.administrative, self.administrative_high_salary],
            PayrollRules(),
        )
        self.service = PayslipService(
            self.cycle,
            [self.professor],
            [self.faculty],
            {"name": "Universidad de Prueba", "id": "900123"},
            administrative_staff=[self.administrative, self.administrative_high_salary],
        )

    def test_structured_payslip_uses_official_run_detail(self):
        payslip = self.service.generate_payslip(3, self.period.period_id, PayrollRules())
        detail = next(d for d in self.run.details if d["employee_id"] == "3")
        self.assertEqual(payslip.run_id, self.run.run_id)
        self.assertEqual(payslip.employee["full_name"], "Luis Gomez")
        self.assertEqual(payslip.employee["faculty"], "Ingenieria")
        self.assertEqual(payslip.academic_base["total_points"], 24)
        self.assertEqual(payslip.summary["net_salary"], detail["net_salary"])
        self.assertEqual(payslip.summary["ibc"], detail["ibc"])
        self.assertEqual(payslip.trace_id, f"{self.run.run_id}:3")

    def test_all_period_payslips_are_individual(self):
        payslips = self.service.generate_period_payslips(self.period.period_id, PayrollRules())
        self.assertEqual(len(payslips), 3)
        self.assertNotEqual(payslips[0].payslip_id, self.run.run_id)

    def test_pdf_is_generated_from_payslip(self):
        with tempfile.TemporaryDirectory() as directory:
            output = os.path.join(directory, "payslip_prof.pdf")
            generated = self.service.generate_payslip_pdf(3, self.period.period_id, PayrollRules(), output)
            self.assertEqual(str(generated), output)
            with open(output, "rb") as file:
                self.assertEqual(file.read(4), b"%PDF")

    def test_unknown_professor_is_rejected(self):
        with self.assertRaises(ValueError):
            self.service.generate_payslip(99, self.period.period_id, PayrollRules())

    def test_administrative_payslip_has_no_academic_points_and_includes_cst_fields(self):
        """Verifica que el desprendible de administrativo no contenga puntos académicos e incluya campos CST."""
        payslip = self.service.generate_payslip(20, self.period.period_id, PayrollRules())
        detail = next(d for d in self.run.details if d["employee_id"] == "20")

        # 1. No debe tener puntos académicos
        self.assertEqual(payslip.academic_base, {}, "Administrativo no debe tener base académica de puntos")

        # 2. Información del empleado bajo CST
        emp = payslip.employee
        self.assertEqual(emp["employee_type"], "Administrative")
        self.assertEqual(emp["full_name"], "Carlos Ruiz")
        self.assertEqual(emp["position"], "Secretario General")
        self.assertEqual(emp["employment_type"], "Término Indefinido")
        self.assertEqual(emp["days_worked"], 30)
        self.assertEqual(emp["base_salary"], Decimal("2200000"))

        # 3. Auxilio de transporte (salario 2.2M <= 2 SMLMV)
        self.assertTrue(emp["transport_allowance_applies"])
        self.assertIn("Aplica", emp["transport_allowance_status"])

        # 4. Campos comunes
        self.assertEqual(payslip.period_id, self.period.period_id)
        self.assertEqual(payslip.summary["gross_salary"], detail["gross_salary"])
        self.assertEqual(payslip.summary["total_employee_deductions"], detail["total_employee_deductions"])
        self.assertEqual(payslip.summary["net_salary"], detail["net_salary"])
        self.assertTrue(payslip.summary["net_salary"] > Decimal("0"))

    def test_administrative_above_two_smlmv_transport_allowance_not_applies(self):
        """Si el salario supera 2 SMLMV, el auxilio de transporte reporta que no aplica."""
        payslip = self.service.generate_payslip(21, self.period.period_id, PayrollRules())
        emp = payslip.employee
        self.assertFalse(emp["transport_allowance_applies"])
        self.assertIn("No aplica", emp["transport_allowance_status"])

    def test_administrative_pdf_generation_success(self):
        """Verifica la generación de PDF para empleados administrativos bajo el esquema CST."""
        with tempfile.TemporaryDirectory() as directory:
            output = os.path.join(directory, "payslip_admin.pdf")
            generated = self.service.generate_payslip_pdf(20, self.period.period_id, PayrollRules(), output)
            self.assertEqual(str(generated), output)
            with open(output, "rb") as file:
                self.assertEqual(file.read(4), b"%PDF")
                self.assertTrue(os.path.getsize(output) > 1000)


if __name__ == "__main__":
    unittest.main()
