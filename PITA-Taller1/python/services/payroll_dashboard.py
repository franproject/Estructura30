"""Financial projections from official PayrollRun snapshots."""
from collections import Counter
from decimal import Decimal
from typing import Any


MONEY_FIELDS = (
    "base_salary", "gross_salary", "total_employee_deductions", "ibc",
    "employee_health", "employee_pension", "service_bonus_provision",
    "severance_provision", "severance_interest", "christmas_bonus_provision",
    "vacation_provision", "vacation_bonus_provision", "employer_pension",
    "employer_health", "arl", "compensation_fund", "sena", "icbf",
    "total_employer_contributions", "total_employer_cost", "net_salary",
)


class PayrollFinancialDashboard:
    """Builds dashboard data without invoking payroll calculation."""

    def __init__(self, run, employees=(), faculties=()):
        if run is None:
            raise ValueError("an official PayrollRun is required")
        self.run = run
        self.employees = {self._employee_id(employee): employee for employee in employees}
        self.faculties = {str(getattr(faculty, "faculty_id", "")): faculty for faculty in faculties}

    @staticmethod
    def _employee_id(employee):
        return str(getattr(employee, "professor_id", getattr(employee, "administrative_id", "")))

    @staticmethod
    def _sum(details, field):
        return sum((Decimal(str(detail.get(field, 0))) for detail in details), Decimal("0"))

    @staticmethod
    def _label(value, fallback="Sin configurar"):
        value = str(value or "").strip()
        return value or fallback

    def snapshot(self):
        details = list(self.run.details)
        # El snapshot combina valores monetarios, contadores y distribuciones.
        # Any se limita a este DTO de salida para no falsear el tipo de los
        # valores oficiales provenientes de PayrollRun.
        metrics: dict[str, Any] = {
            field: self._sum(details, field) for field in MONEY_FIELDS
        }
        metrics.update({
            "total_employees": len(details),
            "total_professors": sum(detail.get("employee_type") == "Professor" for detail in details),
            "total_administratives": sum(detail.get("employee_type") == "Administrative" for detail in details),
            "total_benefits": sum(
                metrics[field] for field in (
                    "service_bonus_provision", "severance_provision", "severance_interest",
                    "christmas_bonus_provision", "vacation_provision", "vacation_bonus_provision",
                )
            ),
            "total_employee_health": metrics["employee_health"],
            "total_employee_pension": metrics["employee_pension"],
            "total_employer_pension": metrics["employer_pension"],
            "total_employer_health": metrics["employer_health"],
            "total_arl": metrics["arl"],
            "total_compensation_fund": metrics["compensation_fund"],
            "total_sena": metrics["sena"],
            "total_icbf": metrics["icbf"],
            "total_employer_contributions": metrics["total_employer_contributions"],
            "total_employer_cost": metrics["total_employer_cost"],
            "total_net_paid": metrics["net_salary"],
        })
        metrics["professor_type_distribution"] = self._distribution(details, "employment_type", "Professor")
        metrics["faculty_distribution"] = self._faculty_distribution(details)
        metrics["category_distribution"] = self._distribution(details, "category_rank", "Professor")
        metrics["linkage_distribution"] = self._distribution(details, "linkage_type")
        metrics["benefits_cost"] = metrics["total_benefits"]
        metrics["social_security_cost"] = sum(
            metrics[field] for field in (
                "employer_pension", "employer_health", "arl", "compensation_fund", "sena", "icbf",
            )
        )
        return metrics

    def _distribution(self, details, field, employee_type=None):
        values = Counter()
        for detail in details:
            if employee_type and detail.get("employee_type") != employee_type:
                continue
            employee = self.employees.get(str(detail.get("employee_id")))
            values[self._label(getattr(employee, field, "") if employee else detail.get(field, ""))] += 1
        return dict(sorted(values.items()))

    def _faculty_distribution(self, details):
        values = Counter()
        for detail in details:
            if detail.get("employee_type") != "Professor":
                continue
            employee = self.employees.get(str(detail.get("employee_id")))
            faculty = self.faculties.get(str(getattr(employee, "faculty_id", ""))) if employee else None
            values[self._label(getattr(faculty, "name", "") if faculty else "")] += 1
        return dict(sorted(values.items()))
