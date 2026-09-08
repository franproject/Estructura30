"""Pure payroll calculation domain for Python and C++ parity.

The engine receives immutable-like snapshots and returns a structured result. It
never reads persisted payroll values from Professor or Administrative and has no
GUI, persistence, or printing dependencies.
"""

from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Mapping


class PayrollDomainError(ValueError):
    """Raised when payroll input or configuration violates a domain rule."""


Money = Decimal
ZERO = Decimal("0")
ONE = Decimal("1")
DAYS_IN_YEAR = Decimal("360")


def money(value) -> Money:
    """Converts a numeric value to Decimal without inheriting binary float noise."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round_peso(value) -> Money:
    return money(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _non_negative(value, field_name):
    result = money(value)
    if result < ZERO:
        raise PayrollDomainError(f"{field_name} cannot be negative")
    return result


@dataclass(frozen=True)
class PayrollPeriod:
    period: str
    start_date: date
    end_date: date
    days_worked: int

    def validate(self):
        if not self.period.strip():
            raise PayrollDomainError("period is required")
        if self.end_date < self.start_date:
            raise PayrollDomainError("period end_date cannot precede start_date")
        if not 0 <= self.days_worked <= 360:
            raise PayrollDomainError("days_worked must be between 0 and 360")


@dataclass(frozen=True)
class PayrollEmployee:
    employee_id: str
    employee_type: str
    employment_type: str
    base_monthly_salary: Money = ZERO
    point_value: Money = ZERO
    category_score: Money = ZERO
    title_score: Money = ZERO
    experience_score: Money = ZERO
    productivity_score: Money = ZERO
    academic_management_score: Money = ZERO
    hourly_rate: Money = ZERO
    hours_worked: Money = ZERO
    continuous_service_days: int = 0
    active: bool = True
    hire_date: str = ""
    termination_date: str = ""

    def validate(self):
        if not str(self.employee_id).strip():
            raise PayrollDomainError("employee_id is required")
        if self.employee_type not in {"Professor", "Administrative"}:
            raise PayrollDomainError("unsupported employee_type")
        if self.days_fields_negative():
            raise PayrollDomainError("employee numeric values cannot be negative")
        if self.continuous_service_days < 0:
            raise PayrollDomainError("continuous_service_days cannot be negative")

    def days_fields_negative(self):
        return any(
            money(getattr(self, name)) < ZERO
            for name in (
                "base_monthly_salary", "point_value", "category_score", "title_score",
                "experience_score", "productivity_score", "academic_management_score",
                "hourly_rate", "hours_worked",
            )
        )

    @property
    def total_points(self):
        return sum(
            (money(getattr(self, name)) for name in (
                "category_score", "title_score", "experience_score",
                "productivity_score", "academic_management_score",
            )),
            ZERO,
        )


@dataclass(frozen=True)
class PayrollNovelty:
    code: str
    amount: Money = ZERO
    quantity: Money = ONE
    is_salary: bool = True
    affects_ibc: bool = True
    description: str = ""

    def validate(self):
        if not self.code.strip():
            raise PayrollDomainError("novelty code is required")
        _non_negative(self.amount, "novelty.amount")
        _non_negative(self.quantity, "novelty.quantity")


@dataclass(frozen=True)
class PayrollRules:
    employee_health_rate: Money = Decimal("0.04")
    employee_pension_rate: Money = Decimal("0.04")
    service_bonus_rate: Money = Decimal("0.0833")
    severance_rate: Money = Decimal("0.0833")
    severance_interest_rate: Money = Decimal("0.12")
    christmas_bonus_rate: Money = Decimal("0.0833")
    vacation_rate: Money = Decimal("0.0417")
    vacation_divisor: Money = Decimal("720")
    vacation_bonus_rate: Money = Decimal("0.0556")
    employer_pension_rate: Money = Decimal("0.12")
    employer_health_rate: Money = Decimal("0.085")
    employer_health_exempt_rate: Money = ZERO
    arl_rates: Mapping[str, Money] = field(default_factory=lambda: {"I": Decimal("0.00522")})
    compensation_fund_rate: Money = Decimal("0.04")
    sena_rate: Money = Decimal("0.02")
    sena_exempt_rate: Money = ZERO
    icbf_rate: Money = Decimal("0.03")
    icbf_exempt_rate: Money = ZERO
    non_salary_limit: Money = Decimal("0.40")
    service_bonus_year_days: int = 360
    service_bonus_top: Money = Decimal("0")
    service_bonus_rate_below_top: Money = Decimal("0.50")
    service_bonus_rate_above_top: Money = Decimal("0.35")
    arl_risk_class: str = "I"
    health_exempt: bool = False
    sena_exempt: bool = False
    icbf_exempt: bool = False

    def validate(self):
        rates = (
            "employee_health_rate", "employee_pension_rate",
            "service_bonus_rate", "severance_rate", "severance_interest_rate",
            "christmas_bonus_rate", "vacation_rate", "vacation_bonus_rate",
            "employer_pension_rate", "employer_health_rate", "employer_health_exempt_rate",
            "compensation_fund_rate", "sena_rate", "sena_exempt_rate", "icbf_rate",
            "icbf_exempt_rate", "non_salary_limit", "service_bonus_rate_below_top",
            "service_bonus_rate_above_top",
        )
        for name in rates:
            value = money(getattr(self, name))
            if value < ZERO:
                raise PayrollDomainError(f"{name} cannot be negative")
        if not ZERO <= money(self.non_salary_limit) <= ONE:
            raise PayrollDomainError("non_salary_limit must be between 0 and 1")
        if self.vacation_divisor <= ZERO:
            raise PayrollDomainError("vacation_divisor must be positive")
        if self.service_bonus_year_days <= 0:
            raise PayrollDomainError("service_bonus_year_days must be positive")
        if self.arl_risk_class not in self.arl_rates:
            raise PayrollDomainError("arl risk class has no configured rate")
        if money(self.arl_rates[self.arl_risk_class]) < ZERO:
            raise PayrollDomainError("ARL rate cannot be negative")


@dataclass(frozen=True)
class PayrollLine:
    code: str
    amount: Money
    is_salary: bool
    affects_ibc: bool


@dataclass(frozen=True)
class PayrollResult:
    employee_id: str
    employee_type: str
    period: str
    days_worked: int
    base_salary: Money
    salary_adjustments: Money
    salary_concepts: tuple[PayrollLine, ...]
    non_salary_concepts: tuple[PayrollLine, ...]
    gross_salary: Money
    non_salary_total: Money
    ibc: Money
    employee_health: Money
    employee_pension: Money
    employee_other_deductions: Money
    total_employee_deductions: Money
    service_bonus_provision: Money
    severance_provision: Money
    severance_interest: Money
    christmas_bonus_provision: Money
    vacation_provision: Money
    vacation_bonus_provision: Money
    service_bonus: Money
    employer_pension: Money
    employer_health: Money
    arl: Money
    compensation_fund: Money
    sena: Money
    icbf: Money
    total_employer_contributions: Money
    net_salary: Money
    total_employer_cost: Money

    def to_dict(self):
        result = asdict(self)
        result["salary_concepts"] = [asdict(line) for line in self.salary_concepts]
        result["non_salary_concepts"] = [asdict(line) for line in self.non_salary_concepts]
        return result


def _salary_base(employee: PayrollEmployee) -> Money:
    if employee.employee_type == "Professor":
        if money(employee.base_monthly_salary) > ZERO:
            return money(employee.base_monthly_salary)
        if employee.employment_type.strip().lower() == "catedratico" and money(employee.hourly_rate) > ZERO:
            return money(employee.hourly_rate) * money(employee.hours_worked)
        return employee.total_points * money(employee.point_value)
    return money(employee.base_monthly_salary)


def calculate_payroll(
    employee: PayrollEmployee,
    period: PayrollPeriod,
    rules: PayrollRules,
    novelties: Iterable[PayrollNovelty] = (),
    other_deductions: Money = ZERO,
) -> PayrollResult:
    """Calculates one employee without I/O, mutation, GUI, or persistence."""
    employee.validate()
    period.validate()
    rules.validate()
    novelty_list = tuple(novelties)
    for novelty in novelty_list:
        novelty.validate()
    other_deductions = _non_negative(other_deductions, "other_deductions")

    base_salary = _salary_base(employee)
    salary_adjustments = sum(
        (money(n.amount) * money(n.quantity) for n in novelty_list if n.is_salary), ZERO
    )
    salary_lines = [PayrollLine("SALARY_BASE", base_salary, True, True)]
    non_salary_lines = []
    for novelty in novelty_list:
        amount = money(novelty.amount) * money(novelty.quantity)
        line = PayrollLine(novelty.code, amount, novelty.is_salary, novelty.affects_ibc)
        (salary_lines if novelty.is_salary else non_salary_lines).append(line)
    constitutive_salary = base_salary + salary_adjustments
    non_salary_total = sum((line.amount for line in non_salary_lines), ZERO)
    non_salary_ibc_base = sum(
        (line.amount for line in non_salary_lines if line.affects_ibc), ZERO
    )
    gross_salary = constitutive_salary + non_salary_total

    limit = money(rules.non_salary_limit)
    allowed_non_salary = round_peso(gross_salary * limit)
    excess_non_salary = max(ZERO, non_salary_total - allowed_non_salary)
    ibc = constitutive_salary + non_salary_ibc_base + excess_non_salary

    employee_health_rate = ZERO if rules.health_exempt else money(rules.employee_health_rate)
    employee_pension_rate = money(rules.employee_pension_rate)
    employee_health = round_peso(ibc * employee_health_rate)
    employee_pension = round_peso(ibc * employee_pension_rate)
    total_employee_deductions = employee_health + employee_pension + round_peso(other_deductions)

    adjusted_base = constitutive_salary * money(period.days_worked) / DAYS_IN_YEAR
    service_bonus_provision = round_peso(adjusted_base * money(rules.service_bonus_rate))
    severance_provision = round_peso(adjusted_base * money(rules.severance_rate))
    severance_interest = round_peso(severance_provision * money(period.days_worked) * money(rules.severance_interest_rate) / DAYS_IN_YEAR)
    christmas_bonus_provision = round_peso(adjusted_base * money(rules.christmas_bonus_rate))
    vacation_provision = round_peso(constitutive_salary * money(period.days_worked) * money(rules.vacation_rate) / money(rules.vacation_divisor))
    vacation_bonus_provision = round_peso(adjusted_base * money(rules.vacation_bonus_rate))

    service_bonus = ZERO
    if employee.continuous_service_days >= rules.service_bonus_year_days:
        bonus_rate = (
            money(rules.service_bonus_rate_below_top)
            if money(employee.base_monthly_salary) <= money(rules.service_bonus_top)
            else money(rules.service_bonus_rate_above_top)
        )
        service_bonus = round_peso(money(employee.base_monthly_salary) * bonus_rate)

    arl = round_peso(ibc * money(rules.arl_rates[rules.arl_risk_class]))
    employer_pension = round_peso(ibc * money(rules.employer_pension_rate))
    employer_health = round_peso(ibc * (money(rules.employer_health_exempt_rate) if rules.health_exempt else money(rules.employer_health_rate)))
    compensation_fund = round_peso(ibc * money(rules.compensation_fund_rate))
    sena = round_peso(ibc * (money(rules.sena_exempt_rate) if rules.sena_exempt else money(rules.sena_rate)))
    icbf = round_peso(ibc * (money(rules.icbf_exempt_rate) if rules.icbf_exempt else money(rules.icbf_rate)))
    total_employer_contributions = sum((employer_pension, employer_health, arl, compensation_fund, sena, icbf), ZERO)

    legal_benefits = service_bonus_provision + severance_provision + severance_interest + christmas_bonus_provision + vacation_provision + vacation_bonus_provision
    net_salary = gross_salary + service_bonus - total_employee_deductions
    total_employer_cost = gross_salary + service_bonus + legal_benefits + total_employer_contributions

    return PayrollResult(
        employee_id=str(employee.employee_id), employee_type=employee.employee_type,
        period=period.period, days_worked=period.days_worked, base_salary=round_peso(base_salary),
        salary_adjustments=round_peso(salary_adjustments), salary_concepts=tuple(salary_lines),
        non_salary_concepts=tuple(non_salary_lines), gross_salary=round_peso(gross_salary),
        non_salary_total=round_peso(non_salary_total), ibc=round_peso(ibc),
        employee_health=employee_health, employee_pension=employee_pension,
        employee_other_deductions=round_peso(other_deductions),
        total_employee_deductions=round_peso(total_employee_deductions),
        service_bonus_provision=service_bonus_provision, severance_provision=severance_provision,
        severance_interest=severance_interest, christmas_bonus_provision=christmas_bonus_provision,
        vacation_provision=vacation_provision, vacation_bonus_provision=vacation_bonus_provision,
        service_bonus=service_bonus, employer_pension=employer_pension,
        employer_health=employer_health, arl=arl, compensation_fund=compensation_fund,
        sena=sena, icbf=icbf, total_employer_contributions=total_employer_contributions,
        net_salary=round_peso(net_salary), total_employer_cost=round_peso(total_employer_cost),
    )


def professor_snapshot(professor) -> PayrollEmployee:
    employment_type = professor.employment_type
    if getattr(professor, "salary_type", "").upper() in {"HOURLY", "HOURLY_RATE"}:
        employment_type = "catedratico"
    return PayrollEmployee(
        employee_id=str(professor.professor_id), employee_type="Professor",
        employment_type=employment_type, base_monthly_salary=money(professor.base_monthly_salary),
        point_value=money(professor.point_value), category_score=money(professor.category_score),
        title_score=money(professor.title_score), experience_score=money(professor.experience_score),
        productivity_score=money(professor.productivity_score), academic_management_score=money(professor.academic_management_score),
        hourly_rate=money(getattr(professor, "hourly_rate", 0)),
        hours_worked=money(getattr(professor, "lecture_hours", 0)),
        continuous_service_days=getattr(professor, "continuous_service_days", 0),
        active=professor.active,
    )


def administrative_snapshot(administrative) -> PayrollEmployee:
    return PayrollEmployee(
        employee_id=str(administrative.administrative_id), employee_type="Administrative",
        employment_type=administrative.employment_type, base_monthly_salary=money(administrative.base_salary),
        continuous_service_days=getattr(administrative, "continuous_service_days", 0),
        active=administrative.active,
    )
