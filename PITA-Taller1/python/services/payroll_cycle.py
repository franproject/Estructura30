"""Formal payroll period, run, novelty and audit lifecycle."""

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from models.payroll_audit import PayrollAudit
from models.payroll_novelty import PayrollNovelty, PayrollNoveltyStatus
from models.payroll_period import PayrollPeriod, PayrollPeriodStatus
from models.payroll_run import PayrollRun, PayrollRunStatus
from services.payroll_adapters import employee_snapshot, model_novelties
from services.payroll_engine import PayrollPeriod as EnginePeriod
from services.payroll_engine import PayrollNovelty as EngineNovelty
from services.payroll_engine import calculate_payroll


class PayrollCycleService:
    """Coordinates lifecycle transitions without owning calculation formulas."""

    def __init__(self):
        self.periods = []
        self.runs = []
        self.novelties = []
        self.audits = []

    @staticmethod
    def _now():
        return datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def _id(prefix):
        return f"{prefix}-{uuid4().hex}"

    def create_period(self, year, month, start_date, end_date, responsible_user=""):
        period = PayrollPeriod(
            period_id=self._id("PER"), year=year, month=month,
            start_date=start_date, end_date=end_date,
            created_at=self._now(), responsible_user=responsible_user,
        )
        period.validate()
        if any(item.year == year and item.month == month and item.status != PayrollPeriodStatus.CANCELLED for item in self.periods):
            raise ValueError("a non-cancelled payroll period already exists for year and month")
        self.periods.append(period)
        self._audit("PayrollPeriod", period.period_id, "CREATE", None, period.to_dict(), responsible_user)
        return period

    def register_novelty(self, novelty: PayrollNovelty, actor=""):
        novelty.validate()
        period = self.get_period(novelty.period_id)
        if period is None:
            raise ValueError("novelty period does not exist")
        if not period.can_change():
            raise ValueError("closed or cancelled periods cannot receive novelties")
        self.novelties.append(novelty)
        self._audit("PayrollNovelty", novelty.novelty_id, "CREATE", None, novelty.to_dict(), actor)
        return novelty

    def get_period(self, period_id):
        return next((item for item in self.periods if item.period_id == period_id), None)

    def get_run(self, run_id):
        return next((item for item in self.runs if item.run_id == run_id), None)

    def _audit(self, entity_type, entity_id, action, before, after, actor="", reason=""):
        audit = PayrollAudit(
            audit_id=self._id("AUD"), entity_type=entity_type, entity_id=entity_id,
            action=action, timestamp=self._now(), actor=actor, reason=reason,
            before_data=before, after_data=after, trace_id=self._id("TRACE"),
        )
        self.audits.append(audit)
        return audit

    @staticmethod
    def _engine_period(period, days_worked):
        start = date.fromisoformat(period.start_date)
        end = date.fromisoformat(period.end_date)
        return EnginePeriod(period.period_id, start, end, days_worked)

    @staticmethod
    def _effective_days(period, employee):
        start = date.fromisoformat(period.start_date)
        end = date.fromisoformat(period.end_date)
        if getattr(employee, "hire_date", ""):
            start = max(start, date.fromisoformat(employee.hire_date))
        if getattr(employee, "termination_date", ""):
            end = min(end, date.fromisoformat(employee.termination_date))
        calendar_days = max(0, (end - start).days + 1)
        worked_days = getattr(employee, "worked_days", 0) or calendar_days
        return min(worked_days, calendar_days)

    @staticmethod
    def _validate_employee(employee, rules):
        if not getattr(employee, "active", False):
            raise ValueError(f"employee {getattr(employee, 'full_name', '') or 'sin nombre'} is inactive")
        risk_class = str(getattr(employee, "arl_risk_class", "")).strip()
        if not risk_class or risk_class not in rules.arl_rates:
            raise ValueError(f"employee {getattr(employee, 'full_name', '') or 'sin nombre'} has no valid ARL configuration")
        if not str(getattr(employee, "social_security_config_id", "")).strip():
            raise ValueError(f"employee {getattr(employee, 'full_name', '') or 'sin nombre'} has no social security configuration")
        snapshot = employee_snapshot(employee)
        snapshot.validate()
        has_salary = snapshot.base_monthly_salary > 0
        has_salary = has_salary or snapshot.point_value > 0
        has_salary = has_salary or snapshot.hourly_rate > 0 and snapshot.hours_worked > 0
        if not has_salary:
            raise ValueError(f"employee {getattr(employee, 'full_name', '') or 'sin nombre'} has no valid salary")

        for source_name in ("novelties", "bonuses", "salary_concepts", "non_salary_concepts"):
            for value in getattr(employee, source_name, []) or []:
                if not isinstance(value, dict):
                    raise ValueError(f"invalid novelty in {source_name}: expected an object")
                if not str(value.get("code", value.get("concept_code", ""))).strip():
                    raise ValueError(f"invalid novelty in {source_name}: code is required")

    def validate_calculation_inputs(self, period_id, employees, rules):
        period = self.get_period(period_id)
        if period is None:
            raise ValueError("payroll period does not exist")
        period.validate()
        rules.validate()
        employees = list(employees)
        if not employees:
            raise ValueError("there are no employees to liquidate")
        for employee in employees:
            self._validate_employee(employee, rules)
        for novelty in self.novelties:
            if novelty.period_id == period_id:
                novelty.validate()
        return True

    def calculate_run(self, period_id, employees, rules, actor="", allow_existing=False):
        period = self.get_period(period_id)
        if period is None:
            raise ValueError("payroll period does not exist")
        if period.status != PayrollPeriodStatus.OPEN and not allow_existing:
            raise ValueError("only open payroll periods can be calculated")

        self.validate_calculation_inputs(period_id, employees, rules)

        period_novelties = [item for item in self.novelties if item.period_id == period_id]
        by_employee = {}
        for novelty in period_novelties:
            if novelty.status not in {PayrollNoveltyStatus.APPROVED, PayrollNoveltyStatus.DRAFT}:
                continue
            if not novelty.has_defined_formula():
                raise ValueError(
                    f"novelty {novelty.novelty_id} has no defined formula and cannot be liquidated"
                )
            by_employee.setdefault(str(novelty.employee_id), []).append(novelty.to_engine_dict())

        details = []
        employee_ids = []
        for employee in employees:
            if not getattr(employee, "active", False):
                continue
            employee_id = str(getattr(employee, "professor_id", getattr(employee, "administrative_id", "")))
            snapshot = employee_snapshot(employee)
            days_worked = self._effective_days(period, employee)
            engine_period = self._engine_period(period, days_worked)
            employee_rules = replace(rules, arl_risk_class=employee.arl_risk_class)
            period_engine_novelties = tuple(
                EngineNovelty(
                    code=item["code"], amount=item["amount"], quantity=item["quantity"],
                    is_salary=item["is_salary"], affects_ibc=item["affects_ibc"],
                    description=item["description"],
                )
                for item in by_employee.get(employee_id, [])
            )
            employee_novelties = model_novelties(employee) + period_engine_novelties
            result = calculate_payroll(snapshot, engine_period, employee_rules, employee_novelties)
            details.append(result.to_dict())
            employee_ids.append(employee_id)

        def total(field):
            return sum((Decimal(str(item[field])) for item in details), Decimal("0"))

        totals = {
            "gross_salary": total("gross_salary"),
            "total_employee_deductions": total("total_employee_deductions"),
            "total_employer_contributions": total("total_employer_contributions"),
            "net_salary": total("net_salary"),
            "total_employer_cost": total("total_employer_cost"),
        }
        calculated_at = self._now()
        novelty_ids = [item.novelty_id for item in period_novelties
                       if item.status in {PayrollNoveltyStatus.APPROVED, PayrollNoveltyStatus.DRAFT}]
        for detail in details:
            origins = [
                {"code": line["code"], "origin": "PayrollEngine", "source_id": line["code"]}
                for line in detail.get("salary_concepts", ()) + detail.get("non_salary_concepts", ())
            ]
            origins.extend(
                {"code": field, "origin": "PayrollEngine", "source_id": field}
                for field in (
                    "employee_health", "employee_pension", "employee_other_deductions",
                    "service_bonus_provision", "severance_provision", "severance_interest",
                    "christmas_bonus_provision", "vacation_provision", "vacation_bonus_provision",
                    "employer_pension", "employer_health", "arl", "compensation_fund", "sena", "icbf",
                )
            )
            detail["concept_origins"] = origins
            detail["novelty_ids"] = list(novelty_ids)
            detail["calculation_trace"] = {
                "net_salary": ["gross_salary", "service_bonus", "total_employee_deductions"],
                "ibc": ["constitutive_salary", "non_salary_ibc_base", "excess_non_salary_over_40_percent"],
                "total_employer_cost": ["gross_salary", "service_bonus", "legal_benefits", "total_employer_contributions"],
            }
        run = PayrollRun(
            run_id=self._id("RUN"), period_id=period_id, employee_ids=employee_ids,
            details=details, totals=totals,
            employer_cost=int(totals["total_employer_cost"]),
            executed_at=calculated_at, audit_ids=[], created_at=calculated_at,
            calculated_at=calculated_at, calculated_by=actor, novelty_ids=novelty_ids,
        )
        run.validate()
        audit = self._audit("PayrollRun", run.run_id, "CALCULATE", None, run.to_dict(), actor)
        run.audit_ids.append(audit.audit_id)
        period.status = PayrollPeriodStatus.CALCULATED
        for novelty in period_novelties:
            if novelty.has_defined_formula() and novelty.status == PayrollNoveltyStatus.APPROVED:
                novelty.status = PayrollNoveltyStatus.APPLIED
        self.runs.append(run)
        return run

    def create_correction_run(self, period_id, employees, rules, actor="", reason=""):
        """Creates a new revision while retaining the prior run unchanged."""
        period = self.get_period(period_id)
        if period is None:
            raise ValueError("payroll period does not exist")
        previous = next((item for item in reversed(self.runs) if item.period_id == period_id), None)
        if previous is None:
            raise ValueError("there is no prior payroll run to correct")
        original_status = period.status
        period.status = PayrollPeriodStatus.OPEN
        try:
            run = self.calculate_run(period_id, employees, rules, actor, allow_existing=True)
        finally:
            period.status = original_status
        run.revision_of = previous.run_id
        audit = self._audit(
            "PayrollRun", run.run_id, "CORRECT", previous.to_dict(), run.to_dict(), actor, reason
        )
        run.audit_ids.append(audit.audit_id)
        return run

    def approve_run(self, run_id, actor=""):
        run = self.get_run(run_id)
        if run is None:
            raise ValueError("payroll run does not exist")
        run.assert_mutable()
        period = self.get_period(run.period_id)
        if period is None or period.status != PayrollPeriodStatus.CALCULATED:
            raise ValueError("period must be calculated before approval")
        before = run.to_dict()
        run.approve()
        run.approved_at = self._now()
        run.approved_by = actor
        period.status = PayrollPeriodStatus.APPROVED
        audit = self._audit("PayrollRun", run.run_id, "APPROVE", before, run.to_dict(), actor)
        run.audit_ids.append(audit.audit_id)
        return run

    def close_run(self, run_id, actor=""):
        run = self.get_run(run_id)
        if run is None:
            raise ValueError("payroll run does not exist")
        run.assert_mutable()
        period = self.get_period(run.period_id)
        if period is None:
            raise ValueError("payroll period does not exist")
        before = run.to_dict()
        run.close()
        run.closed_at = self._now()
        run.closed_by = actor
        period.close(self._now(), actor)
        audit = self._audit("PayrollRun", run.run_id, "CLOSE", before, run.to_dict(), actor)
        run.audit_ids.append(audit.audit_id)
        return run
