"""Payslip projection and PDF rendering from an official PayrollRun."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from models.payslip import Payslip
from models.payroll_run import PayrollRunStatus
from services.payroll_engine import PayrollRules


def _decimal(value):
    return Decimal(str(value))


def _money(value):
    return f"$ {int(_decimal(value)):,.0f}".replace(",", ".")


def _line(code, amount):
    return {"code": code, "amount": _decimal(amount)}


class PayslipService:
    """Creates individual payslips without recalculating payroll."""

    def __init__(self, cycle_service, professors, faculties=None, institution=None, administrative_staff=None):
        self.cycle_service = cycle_service
        self.professors = list(professors or [])
        self.administrative_staff = list(administrative_staff or [])
        self.faculties = {str(item.faculty_id): item for item in (faculties or [])}
        self.institution = {
            "name": "Universidad Popular del Cesar",
            "id": "",
            **(institution or {}),
        }

    def _find_professor(self, professor_id):
        professor_id = str(professor_id)
        return next((item for item in self.professors if str(item.professor_id) == professor_id), None)

    def _find_employee(self, employee_id):
        professor = self._find_professor(employee_id)
        if professor is not None:
            return professor
        employee_id = str(employee_id)
        return next(
            (item for item in self.administrative_staff
             if str(item.administrative_id) == employee_id), None
        )

    def _find_detail(self, run, professor_id):
        professor_id = str(professor_id)
        return next((item for item in run.details if str(item.get("employee_id")) == professor_id), None)

    def _period_and_run(self, professor_id, payroll_period_id):
        period = self.cycle_service.get_period(payroll_period_id)
        if period is None:
            raise ValueError("payroll period does not exist")
        run = next(
            (item for item in reversed(self.cycle_service.runs) if item.period_id == payroll_period_id),
            None,
        )
        if run is None or run.status in {PayrollRunStatus.CANCELLED}:
            raise ValueError("no valid PayrollRun exists for this period")
        detail = self._find_detail(run, professor_id)
        if detail is None:
            raise ValueError("professor has no liquidation detail in this period")
        return period, run, detail

    def generate_payslip(self, professor_id, payroll_period_id, rules=None):
        rules = rules or PayrollRules()
        employee = self._find_employee(professor_id)
        if employee is None:
            raise ValueError("employee does not exist")
        period, run, detail = self._period_and_run(professor_id, payroll_period_id)
        is_professor = hasattr(employee, "professor_id")
        faculty = self.faculties.get(str(employee.faculty_id)) if is_professor else None
        academic_total = sum(
            _decimal(getattr(employee, field_name, 0))
            for field_name in (
                "category_score", "title_score", "experience_score",
                "productivity_score", "academic_management_score",
            )
        )
        salary_concepts = tuple(detail.get("salary_concepts", ()))
        non_salary_concepts = tuple(detail.get("non_salary_concepts", ()))
        concept_origins = tuple(detail.get("concept_origins", ()))
        earnings = tuple(salary_concepts) + tuple(non_salary_concepts)
        benefits = {
            "service_bonus_provision": _decimal(detail["service_bonus_provision"]),
            "severance_provision": _decimal(detail["severance_provision"]),
            "severance_interest": _decimal(detail["severance_interest"]),
            "christmas_bonus_provision": _decimal(detail["christmas_bonus_provision"]),
            "vacation_provision": _decimal(detail["vacation_provision"]),
            "vacation_bonus_provision": _decimal(detail["vacation_bonus_provision"]),
            "service_bonus": _decimal(detail["service_bonus"]),
        }
        contributions = {
            "employer_pension": _decimal(detail["employer_pension"]),
            "employer_health": _decimal(detail["employer_health"]),
            "arl": _decimal(detail["arl"]),
            "compensation_fund": _decimal(detail["compensation_fund"]),
            "sena": _decimal(detail["sena"]),
            "icbf": _decimal(detail["icbf"]),
        }
        summary = {
            "gross_salary": _decimal(detail["gross_salary"]),
            "non_salary_total": _decimal(detail["non_salary_total"]),
            "ibc": _decimal(detail["ibc"]),
            "total_employee_deductions": _decimal(detail["total_employee_deductions"]),
            "net_salary": _decimal(detail["net_salary"]),
            "total_employer_contributions": _decimal(detail["total_employer_contributions"]),
            "total_employer_cost": _decimal(detail["total_employer_cost"]),
        }
        payslip = Payslip(
            payslip_id=f"PS-{uuid4().hex}", run_id=run.run_id,
            period_id=period.period_id, liquidation_date=run.executed_at,
            institution_name=self.institution["name"], institution_id=self.institution["id"],
            employee={
                "full_name": employee.full_name, "document_type": employee.document_type,
                "document_number": employee.document_number,
                "internal_id": str(getattr(employee, "professor_id", getattr(employee, "administrative_id", ""))),
                "linkage_type": employee.linkage_type or employee.employment_type,
                "position": getattr(employee, "managerial_role", getattr(employee, "position", "")),
                "faculty": faculty.name if faculty else "",
                "category": getattr(employee, "category_rank", getattr(employee, "category", "")),
                "title": getattr(employee, "academic_title", ""),
                "hire_date": employee.hire_date, "termination_date": employee.termination_date,
            },
            academic_base={
                "category": getattr(employee, "category_rank", getattr(employee, "category", "")),
                "category_points": _decimal(getattr(employee, "category_score", 0)),
                "title_points": _decimal(getattr(employee, "title_score", 0)),
                "experience_points": _decimal(getattr(employee, "experience_score", 0)),
                "productivity_points": _decimal(getattr(employee, "productivity_score", 0)),
                "academic_management_points": _decimal(getattr(employee, "academic_management_score", 0)),
                "total_points": academic_total,
                "point_value": _decimal(getattr(employee, "point_value", 0)),
                "base_salary": _decimal(detail["base_salary"]),
            },
            earnings=earnings,
            deductions={
                "health": _decimal(detail["employee_health"]),
                "pension": _decimal(detail["employee_pension"]),
                "other": _decimal(detail["employee_other_deductions"]),
                "total": _decimal(detail["total_employee_deductions"]),
            },
            benefits=benefits, employer_contributions=contributions, summary=summary,
            days_worked=int(detail["days_worked"]),
            arl_risk_class=employee.arl_risk_class,
            arl_rate=_decimal(rules.arl_rates[employee.arl_risk_class]),
            health_exemption_rate=_decimal(rules.employer_health_exempt_rate if rules.health_exempt else 0),
            trace_id=f"{run.run_id}:{professor_id}",
            metadata={
                "source": "PayrollRun", "run_id": run.run_id, "period_id": period.period_id,
                "novelty_ids": list(detail.get("novelty_ids", run.novelty_ids if hasattr(run, "novelty_ids") else [])),
                "concept_origins": concept_origins, "detail": detail,
            },
        )
        payslip.validate()
        return payslip

    def generate_period_payslips(self, payroll_period_id, rules=None):
        rules = rules or PayrollRules()
        run = next(
            (item for item in reversed(self.cycle_service.runs) if item.period_id == payroll_period_id),
            None,
        )
        if run is None:
            raise ValueError("no PayrollRun exists for this period")
        return [self.generate_payslip(employee_id, payroll_period_id, rules) for employee_id in run.employee_ids
            if self._find_employee(employee_id) is not None]

    def render_pdf(self, payslip, output_path):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, leading=10))
        styles.add(ParagraphStyle(name="Section", parent=styles["Heading3"], fontSize=10, leading=12, textColor=colors.HexColor("#17365D"), spaceBefore=8))
        document = SimpleDocTemplate(str(output_path), pagesize=LETTER, rightMargin=0.45 * inch, leftMargin=0.45 * inch, topMargin=0.4 * inch, bottomMargin=0.4 * inch)
        story: list[Flowable] = [Paragraph(f"<b>{payslip.institution_name}</b>", styles["Title"])]
        if payslip.institution_id:
            story.append(Paragraph(f"Identificación: {payslip.institution_id}", styles["Small"]))
        story.append(Paragraph(f"Desprendible de Nómina | Período: {payslip.period_id} | Liquidación: {payslip.liquidation_date} | No. {payslip.payslip_id}", styles["Small"]))

        def section(title, rows):
            story.append(Paragraph(title, styles["Section"]))
            table = Table([[str(label), str(value)] for label, value in rows], colWidths=[2.65 * inch, 4.65 * inch])
            table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B7C9D6")), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF1F5")), ("FONTSIZE", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.append(table)

        employee = payslip.employee
        section("Empleado", [(key.replace("_", " ").title(), value or "-") for key, value in employee.items()])
        section("Base académica", [("Categoría", payslip.academic_base["category"]), ("Puntos de categoría", payslip.academic_base["category_points"]), ("Puntos de título", payslip.academic_base["title_points"]), ("Puntos de experiencia", payslip.academic_base["experience_points"]), ("Puntos de productividad", payslip.academic_base["productivity_points"]), ("Puntos de gestión académica", payslip.academic_base["academic_management_points"]), ("Total de puntos", payslip.academic_base["total_points"]), ("Valor del punto", _money(payslip.academic_base["point_value"])), ("Salario base", _money(payslip.academic_base["base_salary"]))])
        section("Devengados", [(line.get("code", "Concepto"), _money(line.get("amount", 0))) for line in payslip.earnings] + [("Total devengado", _money(payslip.summary["gross_salary"])), ("Total no salarial", _money(payslip.summary["non_salary_total"]))])
        section("Deducciones del trabajador", [("Salud", _money(payslip.deductions["health"])), ("Pensión", _money(payslip.deductions["pension"])), ("Otras deducciones", _money(payslip.deductions["other"])), ("Total deducciones", _money(payslip.deductions["total"]))])
        section("Prestaciones / provisiones", [(key.replace("_", " ").title(), _money(value)) for key, value in payslip.benefits.items()])
        section("Aportes del empleador", [(key.replace("_", " ").title(), _money(value)) for key, value in payslip.employer_contributions.items()])
        section("Resumen", [("Días laborados", payslip.days_worked), ("Clase de riesgo ARL", payslip.arl_risk_class), ("Porcentaje ARL", f"{payslip.arl_rate * 100}%"), ("Exoneración salud patronal", f"{payslip.health_exemption_rate * 100}%"), ("IBC", _money(payslip.summary["ibc"])), ("NETO A PAGAR", _money(payslip.summary["net_salary"])), ("Total aportes patronales", _money(payslip.summary["total_employer_contributions"])), ("COSTO TOTAL DEL EMPLEADOR", _money(payslip.summary["total_employer_cost"]))])
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph(f"Trazabilidad: {payslip.trace_id}. Documento generado desde el detalle oficial de PayrollRun; no recalcula la liquidación.", styles["Small"]))
        document.build(story)
        return output_path

    def generate_payslip_pdf(self, professor_id, payroll_period_id, rules, output_path):
        payslip = self.generate_payslip(professor_id, payroll_period_id, rules)
        return self.render_pdf(payslip, output_path)
