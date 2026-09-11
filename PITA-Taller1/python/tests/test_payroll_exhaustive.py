import subprocess
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from models.administrative import Administrative
from models.payroll_novelty import PayrollNovelty, PayrollNoveltyStatus, PayrollNoveltyType
from services.payroll_cycle import PayrollCycleService
from services.payroll_engine import (
    PayrollDomainError,
    PayrollEmployee,
    PayrollNovelty,
    PayrollPeriod,
    PayrollRules,
    calculate_payroll,
)


D = Decimal
PERIOD = PayrollPeriod("2026-09", date(2026, 9, 1), date(2026, 9, 30), 30)


class ExhaustivePayrollTests(unittest.TestCase):
    def employee(self, **overrides):
        values = {
            "employee_id": "E1", "employee_type": "Professor", "employment_type": "planta",
            "base_monthly_salary": D("1000000"), "active": True,
        }
        values.update(overrides)
        return PayrollEmployee(**values)

    def rules(self, **overrides):
        values = {}
        values.update(overrides)
        return PayrollRules(**values)

    def assert_result(self, result, **expected):
        for field, value in expected.items():
            self.assertEqual(getattr(result, field), D(str(value)), field)

    def test_01_profesor_planta(self):
        result = calculate_payroll(self.employee(employment_type="planta"), PERIOD, self.rules())
        self.assertEqual(result.employee_type, "Professor")
        self.assertEqual(result.base_salary, D("1000000"))

    def test_02_profesor_ocasional(self):
        result = calculate_payroll(self.employee(employment_type="ocasional"), PERIOD, self.rules())
        self.assertEqual(result.base_salary, D("1000000"))

    def test_03_profesor_catedratico(self):
        result = calculate_payroll(self.employee(
            employment_type="catedratico", base_monthly_salary=0, hourly_rate=25000, hours_worked=40,
        ), PERIOD, self.rules())
        self.assertEqual(result.base_salary, D("1000000"))

    def test_04_administrativo(self):
        employee = self.employee(employee_type="Administrative", employment_type="planta")
        result = calculate_payroll(employee, PERIOD, self.rules())
        self.assertEqual(result.base_salary, D("1000000"))

    def test_05_profesor_con_salario_base(self):
        result = calculate_payroll(self.employee(base_monthly_salary=2500000), PERIOD, self.rules())
        self.assertEqual(result.base_salary, D("2500000"))

    def test_06_profesor_puntos_por_valor(self):
        result = calculate_payroll(self.employee(
            base_monthly_salary=0, point_value=1000, category_score=10, title_score=5,
            experience_score=3, productivity_score=4, academic_management_score=2,
        ), PERIOD, self.rules())
        self.assertEqual(result.base_salary, D("24000"))

    def test_07_profesor_sin_puntos(self):
        result = calculate_payroll(self.employee(base_monthly_salary=0, point_value=0), PERIOD, self.rules())
        self.assertEqual(result.base_salary, D("0"))
        self.assertEqual(result.net_salary, D("0"))

    def test_08_deducciones(self):
        result = calculate_payroll(self.employee(), PERIOD, self.rules(), other_deductions=D("12345"))
        self.assert_result(result, employee_health=40000, employee_pension=40000,
                           employee_other_deductions=12345, total_employee_deductions=92345)

    def test_09_bonificacion_salarial(self):
        novelty = PayrollNovelty("SALARY_BONUS", D("100000"), D("1"), True, True)
        result = calculate_payroll(self.employee(), PERIOD, self.rules(), [novelty])
        self.assert_result(result, gross_salary=1100000, ibc=1100000)

    def test_10_bonificacion_no_salarial(self):
        novelty = PayrollNovelty("NON_SALARY", D("100000"), D("1"), False, False)
        result = calculate_payroll(self.employee(), PERIOD, self.rules(), [novelty])
        self.assert_result(result, gross_salary=1100000, ibc=1000000)

    def test_11_limite_40_por_ciento(self):
        novelty = PayrollNovelty("NON_SALARY", D("400000"), D("1"), False, False)
        result = calculate_payroll(self.employee(), PERIOD, self.rules(), [novelty])
        self.assert_result(result, gross_salary=1400000, ibc=1000000)

    def test_12_exceso_40_por_ciento(self):
        novelty = PayrollNovelty("NON_SALARY", D("1000000"), D("1"), False, False)
        result = calculate_payroll(self.employee(), PERIOD, self.rules(), [novelty])
        self.assert_result(result, gross_salary=2000000, ibc=1200000)

    def test_13_prima_servicios(self):
        result = calculate_payroll(self.employee(), PERIOD, self.rules())
        self.assertEqual(result.service_bonus_provision, D("6942"))

    def test_14_cesantias(self):
        result = calculate_payroll(self.employee(), PERIOD, self.rules())
        self.assertEqual(result.severance_provision, D("6942"))

    def test_15_intereses_cesantias(self):
        result = calculate_payroll(self.employee(), PERIOD, self.rules())
        self.assertEqual(result.severance_interest, D("69"))

    def test_16_prima_navidad(self):
        result = calculate_payroll(self.employee(), PERIOD, self.rules())
        self.assertEqual(result.christmas_bonus_provision, D("6942"))

    def test_17_vacaciones(self):
        result = calculate_payroll(self.employee(), PERIOD, self.rules())
        self.assertEqual(result.vacation_provision, D("1738"))

    def test_18_prima_vacaciones(self):
        result = calculate_payroll(self.employee(), PERIOD, self.rules())
        self.assertEqual(result.vacation_bonus_provision, D("4633"))

    def test_19_bonificacion_por_servicios(self):
        # In regular months (e.g. September), cash service bonus is 0
        result = calculate_payroll(self.employee(continuous_service_days=360), PERIOD, self.rules(service_bonus_top=2000000))
        self.assertEqual(result.service_bonus, D("0"))

        # In June and December, cash service bonus is liquidated
        period_june = PayrollPeriod("2026-06", date(2026, 6, 1), date(2026, 6, 30), 30)
        result_june = calculate_payroll(self.employee(continuous_service_days=360), period_june, self.rules(service_bonus_top=2000000))
        self.assertEqual(result_june.service_bonus, D("500000"))

        period_dec = PayrollPeriod("2026-12", date(2026, 12, 1), date(2026, 12, 31), 30)
        result_dec = calculate_payroll(self.employee(continuous_service_days=360), period_dec, self.rules(service_bonus_top=2000000))
        self.assertEqual(result_dec.service_bonus, D("500000"))

    def test_20_pension_patronal(self):
        result = calculate_payroll(self.employee(), PERIOD, self.rules())
        self.assertEqual(result.employer_pension, D("120000"))

    def test_21_salud_patronal(self):
        result = calculate_payroll(self.employee(), PERIOD, self.rules())
        self.assertEqual(result.employer_health, D("85000"))

    def test_22_exoneracion(self):
        result = calculate_payroll(self.employee(), PERIOD, self.rules(health_exempt=True, sena_exempt=True, icbf_exempt=True))
        self.assert_result(result, employee_health=0, employer_health=0, sena=0, icbf=0)

    def test_23_arl(self):
        result = calculate_payroll(self.employee(), PERIOD, self.rules())
        self.assertEqual(result.arl, D("5220"))

    def test_24_caja(self):
        result = calculate_payroll(self.employee(), PERIOD, self.rules())
        self.assertEqual(result.compensation_fund, D("40000"))

    def test_25_sena(self):
        result = calculate_payroll(self.employee(), PERIOD, self.rules())
        self.assertEqual(result.sena, D("20000"))

    def test_26_icbf(self):
        result = calculate_payroll(self.employee(), PERIOD, self.rules())
        self.assertEqual(result.icbf, D("30000"))

    def test_27_redondeo_half_up(self):
        result = calculate_payroll(self.employee(base_monthly_salary=1234567), PERIOD, self.rules())
        self.assert_result(result, employee_health=49383, employee_pension=49383,
                           vacation_provision=2145, net_salary=1135801)

    def test_28_dias_laborados_parciales(self):
        result = calculate_payroll(self.employee(), PERIOD.__class__("2026-09", PERIOD.start_date, PERIOD.end_date, 15), self.rules())
        self.assert_result(result, service_bonus_provision=3471, severance_provision=3471,
                           christmas_bonus_provision=3471, vacation_provision=869)

    def test_29_ingreso_durante_periodo(self):
        service, employee, period = self.service_with_employee()
        employee.hire_date = "2026-09-21"
        run = service.calculate_run(period.period_id, [employee], self.rules())
        self.assertEqual(run.details[0]["days_worked"], 10)
        self.assertEqual(run.details[0]["service_bonus_provision"], D("2314"))

    def test_30_retiro_durante_periodo(self):
        service, employee, period = self.service_with_employee()
        employee.termination_date = "2026-09-20"
        run = service.calculate_run(period.period_id, [employee], self.rules())
        self.assertEqual(run.details[0]["days_worked"], 20)
        self.assertEqual(run.details[0]["service_bonus_provision"], D("4628"))

    def service_with_employee(self):
        service = PayrollCycleService()
        employee = Administrative(administrative_id=7, full_name="Ana", base_salary=1000000, active=True, worked_days=30)
        period = service.create_period(2026, 9, "2026-09-01", "2026-09-30")
        return service, employee, period

    def test_31_periodo_cerrado(self):
        service, employee, period = self.service_with_employee()
        run = service.calculate_run(period.period_id, [employee], self.rules())
        service.approve_run(run.run_id)
        service.close_run(run.run_id)
        with self.assertRaises(ValueError):
            service.calculate_run(period.period_id, [employee], self.rules())

    def test_32_duplicacion_liquidacion(self):
        service, employee, period = self.service_with_employee()
        service.calculate_run(period.period_id, [employee], self.rules())
        with self.assertRaises(ValueError):
            service.calculate_run(period.period_id, [employee], self.rules())

    def test_33_empleado_inactivo(self):
        service, employee, period = self.service_with_employee()
        employee.active = False
        with self.assertRaises(ValueError):
            service.calculate_run(period.period_id, [employee], self.rules())

    def test_34_datos_faltantes(self):
        with self.assertRaises(PayrollDomainError):
            calculate_payroll(self.employee(employee_id=""), PERIOD, self.rules())

    def test_35_valores_negativos(self):
        with self.assertRaises(PayrollDomainError):
            calculate_payroll(self.employee(base_monthly_salary=-1), PERIOD, self.rules())
        with self.assertRaises(PayrollDomainError):
            calculate_payroll(self.employee(), PERIOD, self.rules(), [PayrollNovelty("NEG", -1)])

    def test_36_configuracion_invalida(self):
        with self.assertRaises(PayrollDomainError):
            calculate_payroll(self.employee(), PERIOD, self.rules(non_salary_limit=D("1.1")))
        with self.assertRaises(PayrollDomainError):
            calculate_payroll(self.employee(), PERIOD, self.rules(arl_risk_class="V", arl_rates={"I": D("0.00522")}))

    def test_37_exact_total_components(self):
        result = calculate_payroll(self.employee(), PERIOD, self.rules())
        self.assert_result(result, gross_salary=1000000, ibc=1000000,
                           total_employee_deductions=80000, total_employer_contributions=300220,
                           net_salary=920000, total_employer_cost=1327486)

    def test_38_python_cpp_exact_equivalence(self):
        binary = Path(__file__).parents[2] / "cpp" / "build" / "payroll_parity_probe.exe"
        if not binary.exists():
            self.skipTest(f"falta compilar {binary}")
        python_result = calculate_payroll(
            self.employee(employee_id="PARITY", base_monthly_salary=1234567), PERIOD, self.rules(),
            [PayrollNovelty("SALARY_BONUS", D("111111"), D("1"), True, True),
             PayrollNovelty("NON_SALARY", D("222222"), D("1"), False, False)],
        )
        output = subprocess.check_output([str(binary)], text=True).strip()
        cpp_values = [D(value) for value in output.split(",")]
        fields = ("gross_salary", "ibc", "total_employee_deductions", "total_benefits",
                  "total_employer_contributions", "net_salary", "total_employer_cost")
        python_values = [
            python_result.gross_salary, python_result.ibc, python_result.total_employee_deductions,
            python_result.service_bonus_provision + python_result.severance_provision + python_result.severance_interest
            + python_result.christmas_bonus_provision + python_result.vacation_provision + python_result.vacation_bonus_provision,
            python_result.total_employer_contributions, python_result.net_salary, python_result.total_employer_cost,
        ]
        self.assertEqual(len(cpp_values), len(fields))
        for field, expected, actual in zip(fields, python_values, cpp_values):
            self.assertEqual(expected, actual, field)


if __name__ == "__main__":
    unittest.main()
