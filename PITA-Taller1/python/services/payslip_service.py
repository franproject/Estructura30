"""Payslip projection and PDF rendering from an official PayrollRun."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from models.administrative import Administrative
from models.payroll_run import PayrollRunStatus
from models.payslip import Payslip
from models.professor import Professor
from services.payroll_engine import PayrollRules

# Parámetros legales estándar Colombia (CST)
# SMLMV de referencia legal: $1.423.500 (2 SMLMV tope para auxilio de transporte = $2.847.000)
SMLMV_COLOMBIA_DEFAULT = Decimal("1423500")


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

    def _find_detail(self, run, employee_id):
        employee_id = str(employee_id)
        return next((item for item in run.details if str(item.get("employee_id")) == employee_id), None)

    def _period_and_run(self, employee_id, payroll_period_id):
        period = self.cycle_service.get_period(payroll_period_id)
        if period is None:
            raise ValueError("payroll period does not exist")
        run = next(
            (item for item in reversed(self.cycle_service.runs) if item.period_id == payroll_period_id),
            None,
        )
        if run is None or run.status in {PayrollRunStatus.CANCELLED}:
            raise ValueError("no valid PayrollRun exists for this period")
        detail = self._find_detail(run, employee_id)
        if detail is None:
            raise ValueError("employee has no liquidation detail in this period")
        return period, run, detail

    def generate_payslip(self, employee_id=None, payroll_period_id=None, rules=None, professor_id=None):
        emp_id = employee_id if employee_id is not None else professor_id
        if emp_id is None:
            raise ValueError("employee_id is required")
        rules = rules or PayrollRules()
        employee = self._find_employee(emp_id)
        if employee is None:
            raise ValueError("employee does not exist")
        period, run, detail = self._period_and_run(emp_id, payroll_period_id)

        is_professor = (
            isinstance(employee, Professor)
            or (hasattr(employee, "professor_id") and not hasattr(employee, "administrative_id"))
            or detail.get("employee_type") == "Professor"
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

        if is_professor:
            faculty = self.faculties.get(str(employee.faculty_id)) if hasattr(employee, "faculty_id") else None
            academic_total = sum(
                _decimal(getattr(employee, field_name, 0))
                for field_name in (
                    "category_score", "title_score", "experience_score",
                    "productivity_score", "academic_management_score",
                )
            )
            academic_base = {
                "category": getattr(employee, "category_rank", getattr(employee, "category", "")),
                "category_points": _decimal(getattr(employee, "category_score", 0)),
                "title_points": _decimal(getattr(employee, "title_score", 0)),
                "experience_points": _decimal(getattr(employee, "experience_score", 0)),
                "productivity_points": _decimal(getattr(employee, "productivity_score", 0)),
                "academic_management_points": _decimal(getattr(employee, "academic_management_score", 0)),
                "total_points": academic_total,
                "point_value": _decimal(getattr(employee, "point_value", 0)),
                "base_salary": _decimal(detail["base_salary"]),
            }
            employee_info = {
                "full_name": employee.full_name,
                "document_type": employee.document_type,
                "document_number": employee.document_number,
                "internal_id": str(getattr(employee, "professor_id", emp_id)),
                "employee_type": "Professor",
                "regime": "Decreto 1279 de 2002 (Docente Universitario)",
                "linkage_type": employee.linkage_type or getattr(employee, "employment_type", ""),
                "position": getattr(employee, "managerial_role", getattr(employee, "position", "Docente")),
                "faculty": faculty.name if faculty else "",
                "category": getattr(employee, "category_rank", getattr(employee, "category", "")),
                "title": getattr(employee, "academic_title", ""),
                "hire_date": getattr(employee, "hire_date", ""),
                "termination_date": getattr(employee, "termination_date", ""),
            }
        else:
            academic_base = {}
            base_salary = _decimal(detail.get("base_salary", getattr(employee, "base_salary", 0)))
            days_worked = int(detail.get("days_worked", getattr(employee, "worked_days", 30)))

            smlmv = getattr(rules, "smlmv", SMLMV_COLOMBIA_DEFAULT)
            transport_ceiling = smlmv * Decimal("2")
            transport_applies = base_salary <= transport_ceiling

            transport_amount = Decimal("0")
            for line in list(salary_concepts) + list(non_salary_concepts):
                code_str = str(line.get("code", "")).upper()
                desc_str = str(line.get("description", "")).upper()
                if "TRANSPORTE" in code_str or "TRANSPORT" in code_str or "TRANSPORTE" in desc_str:
                    transport_amount += _decimal(line.get("amount", 0))

            if transport_amount > Decimal("0"):
                transport_status = f"Liquidado ({_money(transport_amount)})"
            elif transport_applies:
                transport_status = f"Aplica por tope de ley (Salario base ≤ {_money(transport_ceiling)})"
            else:
                transport_status = f"No aplica (Salario base supera tope de 2 SMLMV: {_money(transport_ceiling)})"

            employee_info = {
                "full_name": employee.full_name,
                "document_type": employee.document_type,
                "document_number": employee.document_number,
                "internal_id": str(getattr(employee, "administrative_id", emp_id)),
                "employee_type": "Administrative",
                "regime": "Código Sustantivo del Trabajo (CST)",
                "position": getattr(employee, "position", "Personal Administrativo"),
                "employment_type": getattr(employee, "employment_type", getattr(employee, "linkage_type", "Término Indefinido")),
                "base_salary": base_salary,
                "days_worked": days_worked,
                "transport_allowance_applies": transport_applies,
                "transport_allowance_amount": transport_amount,
                "transport_allowance_status": transport_status,
                "hire_date": getattr(employee, "hire_date", ""),
                "termination_date": getattr(employee, "termination_date", ""),
            }

        payslip = Payslip(
            payslip_id=f"PS-{uuid4().hex}",
            run_id=run.run_id,
            period_id=period.period_id,
            liquidation_date=run.executed_at,
            institution_name=self.institution["name"],
            institution_id=self.institution["id"],
            employee=employee_info,
            academic_base=academic_base,
            earnings=earnings,
            deductions={
                "health": _decimal(detail["employee_health"]),
                "pension": _decimal(detail["employee_pension"]),
                "other": _decimal(detail["employee_other_deductions"]),
                "total": _decimal(detail["total_employee_deductions"]),
            },
            benefits=benefits,
            employer_contributions=contributions,
            summary=summary,
            days_worked=int(detail["days_worked"]),
            arl_risk_class=employee.arl_risk_class,
            arl_rate=_decimal(rules.arl_rates[employee.arl_risk_class]),
            health_exemption_rate=_decimal(rules.employer_health_exempt_rate if rules.health_exempt else 0),
            trace_id=f"{run.run_id}:{emp_id}",
            metadata={
                "source": "PayrollRun",
                "run_id": run.run_id,
                "period_id": period.period_id,
                "novelty_ids": list(detail.get("novelty_ids", run.novelty_ids if hasattr(run, "novelty_ids") else [])),
                "concept_origins": concept_origins,
                "detail": detail,
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
        styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#475569")))
        styles.add(ParagraphStyle(name="SubHeader", parent=styles["Normal"], fontSize=9, leading=11, textColor=colors.HexColor("#0284C7"), fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="Section", parent=styles["Heading3"], fontSize=10, leading=12, textColor=colors.HexColor("#17365D"), spaceBefore=7, spaceAfter=2))

        document = SimpleDocTemplate(
            str(output_path),
            pagesize=LETTER,
            rightMargin=0.45 * inch,
            leftMargin=0.45 * inch,
            topMargin=0.4 * inch,
            bottomMargin=0.4 * inch,
        )

        is_professor = (
            bool(payslip.academic_base and payslip.academic_base.get("total_points") is not None)
            or payslip.employee.get("employee_type") == "Professor"
        )
        employee = payslip.employee
        service_bonus_paid = _decimal(payslip.benefits.get("service_bonus", 0))

        story: list[Flowable] = [
            Paragraph(f"<b>{payslip.institution_name}</b>", styles["Title"]),
        ]
        if payslip.institution_id:
            story.append(Paragraph(f"NIT / Identificación: {payslip.institution_id}", styles["Small"]))

        if is_professor:
            regime_title = "COMPROBANTE DE PAGO DE NÓMINA · RÉGIMEN DOCENTE UNIVERSITARIO"
            regime_subtitle = "Régimen Salarial y Prestacional del Profesorado Universitario (Decreto 1279 de 2002)"
        else:
            regime_title = "COMPROBANTE DE PAGO DE NÓMINA · PERSONAL ADMINISTRATIVO"
            regime_subtitle = "Régimen Laboral Ordinario (Código Sustantivo del Trabajo - CST)"

        story.append(Paragraph(f"<b>{regime_title}</b>", styles["SubHeader"]))
        story.append(Paragraph(
            f"<b>Período:</b> {payslip.period_id} &nbsp;|&nbsp; "
            f"<b>Liquidación:</b> {payslip.liquidation_date} &nbsp;|&nbsp; "
            f"<b>Comprobante No:</b> {payslip.payslip_id}",
            styles["Small"],
        ))
        story.append(Paragraph(f"<i>{regime_subtitle}</i>", styles["Small"]))

        def section(title, rows, header_bg="#EAF1F5"):
            story.append(Paragraph(title, styles["Section"]))
            table = Table(
                [[str(label), str(value)] for label, value in rows],
                colWidths=[2.65 * inch, 4.65 * inch],
            )
            table.setStyle(
                TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B7C9D6")),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(header_bg)),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ])
            )
            story.append(table)

        if is_professor:
            # 1. Datos del Empleado Docente
            docente_rows = [
                ("Nombre del Docente", employee.get("full_name", "-")),
                ("Documento de Identidad", f"{employee.get('document_type', '')} {employee.get('document_number', '')}".strip() or "-"),
                ("ID Institucional", employee.get("internal_id", "-")),
                ("Facultad", employee.get("faculty", "-")),
                ("Categoría del Escalafón", employee.get("category", "-")),
                ("Título Académico", employee.get("title", "-")),
                ("Tipo de Vinculación", employee.get("linkage_type", "-")),
                ("Fecha de Ingreso", employee.get("hire_date", "-") or "-"),
            ]
            section("1. Datos del Empleado Docente", docente_rows)

            # 2. Base Académica y Puntos Salariales (Decreto 1279 de 2002)
            academic_rows = [
                ("Categoría Escalafón Docente", payslip.academic_base.get("category", "-")),
                ("Puntos de Categoría", str(payslip.academic_base.get("category_points", 0))),
                ("Puntos de Título", str(payslip.academic_base.get("title_points", 0))),
                ("Puntos de Experiencia Calificada", str(payslip.academic_base.get("experience_points", 0))),
                ("Puntos de Productividad Académica", str(payslip.academic_base.get("productivity_points", 0))),
                ("Puntos de Dirección / Gestión Académica", str(payslip.academic_base.get("academic_management_points", 0))),
                ("TOTAL PUNTOS SALARIALES", str(payslip.academic_base.get("total_points", 0))),
                ("Valor Oficial del Punto", _money(payslip.academic_base.get("point_value", 0))),
                ("Salario Base Mensual Liquidado", _money(payslip.academic_base.get("base_salary", 0))),
            ]
            section("2. Base Académica y Puntos Salariales (Decreto 1279 de 2002)", academic_rows)

        else:
            # 1. Datos del Empleado Administrativo (CST)
            admin_rows = [
                ("Nombre del Empleado", employee.get("full_name", "-")),
                ("Documento de Identidad", f"{employee.get('document_type', '')} {employee.get('document_number', '')}".strip() or "-"),
                ("ID de Empleado", employee.get("internal_id", "-")),
                ("Cargo Institucional", employee.get("position", "-")),
                ("Tipo de Contrato", employee.get("employment_type", "-")),
                ("Días Trabajados en el Período", str(payslip.days_worked)),
                ("Salario Base Mensual", _money(employee.get("base_salary", payslip.summary.get("gross_salary", 0)))),
                ("Auxilio de Transporte (Tope legal ≤ 2 SMLMV)", employee.get("transport_allowance_status", "-")),
                ("Fecha de Ingreso", employee.get("hire_date", "-") or "-"),
            ]
            section("1. Datos del Empleado Administrativo (CST)", admin_rows)

        # Devengados
        earnings_rows = [(line.get("code", "Concepto"), _money(line.get("amount", 0))) for line in payslip.earnings]
        if service_bonus_paid > Decimal("0"):
            earnings_rows.append(("Prima de servicios (Liquidada en efectivo)", _money(service_bonus_paid)))
        earnings_rows.extend([
            ("TOTAL DEVENGADO", _money(payslip.summary["gross_salary"])),
            ("Total no salarial", _money(payslip.summary["non_salary_total"])),
        ])
        section("3. Devengados del Período" if is_professor else "2. Devengados del Período", earnings_rows)

        # Deducciones
        deductions_rows = [
            ("Aporte Salud Trabajador (4%)", _money(payslip.deductions["health"])),
            ("Aporte Pensión Trabajador (4%)", _money(payslip.deductions["pension"])),
            ("Otras deducciones de nómina", _money(payslip.deductions["other"])),
            ("TOTAL DEDUCCIONES TRABAJADOR", _money(payslip.deductions["total"])),
        ]
        section("4. Deducciones del Trabajador" if is_professor else "3. Deducciones del Trabajador", deductions_rows)

        # Prestaciones Sociales / Provisiones
        benefits_rows = []
        if service_bonus_paid > Decimal("0"):
            benefits_rows.append(("Prima de servicios (Pagada en este período)", _money(service_bonus_paid)))
        else:
            benefits_rows.append(("Prima de servicios (Efectivo)", "No aplica pago en este período (Solo provisión contable)"))
        benefits_rows.append(("Provisión prima de servicios", _money(payslip.benefits.get("service_bonus_provision", 0))))
        benefits_rows.append(("Provisión cesantías", _money(payslip.benefits.get("severance_provision", 0))))
        benefits_rows.append(("Intereses sobre cesantías", _money(payslip.benefits.get("severance_interest", 0))))
        benefits_rows.append(("Provisión vacaciones", _money(payslip.benefits.get("vacation_provision", 0))))
        if is_professor:
            benefits_rows.append(("Provisión prima de navidad", _money(payslip.benefits.get("christmas_bonus_provision", 0))))
            benefits_rows.append(("Provisión bonificación vacaciones", _money(payslip.benefits.get("vacation_bonus_provision", 0))))
        else:
            if _decimal(payslip.benefits.get("christmas_bonus_provision", 0)) > Decimal("0"):
                benefits_rows.append(("Provisión prima de navidad", _money(payslip.benefits.get("christmas_bonus_provision", 0))))
        section("5. Prestaciones Sociales / Provisiones" if is_professor else "4. Prestaciones Sociales y Provisiones", benefits_rows)

        # Aportes del Empleador
        contributions_rows = [
            (key.replace("_", " ").title(), _money(value))
            for key, value in payslip.employer_contributions.items()
        ]
        section("6. Aportes Patronales (Seguridad Social y Parafiscales)" if is_professor else "5. Aportes Patronales a la Seguridad Social", contributions_rows)

        # Resumen General
        summary_rows = [
            ("Días laborados", str(payslip.days_worked)),
            ("Clase de riesgo ARL", f"Clase {payslip.arl_risk_class} ({payslip.arl_rate * 100}%)"),
            ("Ingreso Base de Cotización (IBC)", _money(payslip.summary["ibc"])),
            ("TOTAL DEVENGADO", _money(payslip.summary["gross_salary"])),
            ("TOTAL DEDUCCIONES", _money(payslip.summary["total_employee_deductions"])),
            ("NETO A PAGAR AL TRABAJADOR", _money(payslip.summary["net_salary"])),
            ("COSTO TOTAL DEL EMPLEADOR", _money(payslip.summary["total_employer_cost"])),
        ]
        section("7. Resumen de Liquidación" if is_professor else "6. Resumen General de Pago", summary_rows, header_bg="#FEF3C7")

        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph(
            f"Trazabilidad: {payslip.trace_id}. "
            "Documento generado a partir del registro oficial de PayrollRun; no recalcula la liquidación.",
            styles["Small"],
        ))
        document.build(story)
        return output_path

    def generate_payslip_pdf(self, employee_id=None, payroll_period_id=None, rules=None, output_path=None, professor_id=None):
        emp_id = employee_id if employee_id is not None else professor_id
        payslip = self.generate_payslip(emp_id, payroll_period_id, rules)
        return self.render_pdf(payslip, output_path)
