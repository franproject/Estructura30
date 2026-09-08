"""Adapters from legacy employee models to the pure payroll engine.

This module is the compatibility boundary. It may inspect Professor and
Administrative, but calculation remains in payroll_engine.py.
"""

import warnings
from dataclasses import replace

from services.payroll_engine import (
    PayrollEmployee,
    PayrollLine,
    PayrollNovelty,
    PayrollPeriod,
    PayrollRules,
    calculate_payroll,
    money,
)


def _novelty_from_value(value, default_is_salary, default_affects_ibc, source):
    if isinstance(value, PayrollNovelty):
        return value
    if not isinstance(value, dict):
        warnings.warn(f"Ignoring invalid {source} entry; expected an object", RuntimeWarning, stacklevel=2)
        return None
    code = value.get("code", value.get("concept_code", ""))
    if not code:
        warnings.warn(f"Ignoring {source} entry without a code", RuntimeWarning, stacklevel=2)
        return None
    return PayrollNovelty(
        code=str(code),
        amount=money(value.get("amount", value.get("value", 0))),
        quantity=money(value.get("quantity", 1)),
        is_salary=value.get("is_salary", default_is_salary),
        affects_ibc=value.get("affects_ibc", default_affects_ibc),
        description=str(value.get("description", "")),
    )


def model_novelties(employee):
    """Converts model concepts without using legacy derived payroll values."""
    sources = (
        ("novelties", True, True),
        ("bonuses", False, False),
        ("salary_concepts", True, True),
        ("non_salary_concepts", False, False),
    )
    result = []
    for field_name, default_is_salary, default_affects_ibc in sources:
        for value in getattr(employee, field_name, []) or []:
            novelty = _novelty_from_value(
                value, default_is_salary, default_affects_ibc, field_name
            )
            if novelty is not None:
                result.append(novelty)
    return tuple(result)


def employee_snapshot(employee):
    """Builds a payroll snapshot from either current employee model."""
    is_professor = hasattr(employee, "professor_id")
    if not is_professor and not hasattr(employee, "administrative_id"):
        raise TypeError("employee must be Professor or Administrative")

    employee_type = "Professor" if is_professor else "Administrative"
    employee_id = employee.professor_id if is_professor else employee.administrative_id
    base_salary = employee.base_monthly_salary if is_professor else employee.base_salary
    employment_type = employee.employment_type or employee.linkage_type
    if employee.salary_type.upper() in {"HOURLY", "HOURLY_RATE"}:
        employment_type = "catedratico"

    return PayrollEmployee(
        employee_id=str(employee_id),
        employee_type=employee_type,
        employment_type=employment_type,
        base_monthly_salary=money(base_salary),
        point_value=money(getattr(employee, "point_value", 0)),
        category_score=money(getattr(employee, "category_score", 0)),
        title_score=money(getattr(employee, "title_score", 0)),
        experience_score=money(getattr(employee, "experience_score", 0)),
        productivity_score=money(getattr(employee, "productivity_score", 0)),
        academic_management_score=money(getattr(employee, "academic_management_score", 0)),
        hourly_rate=money(getattr(employee, "hourly_rate", 0)),
        hours_worked=money(getattr(employee, "lecture_hours", 0)),
        continuous_service_days=getattr(employee, "continuous_service_days", 0),
        active=employee.active,
        hire_date=getattr(employee, "hire_date", ""),
        termination_date=getattr(employee, "termination_date", ""),
    )


def calculate_model_payroll(employee, period, rules, other_deductions=0):
    """Calculates payroll for an existing model through the pure engine."""
    snapshot = employee_snapshot(employee)
    effective_period = period
    worked_days = getattr(employee, "worked_days", 0)
    if worked_days > 0:
        effective_period = replace(period, days_worked=worked_days)

    risk_class = getattr(employee, "arl_risk_class", "")
    effective_rules = rules
    if risk_class:
        effective_rules = replace(rules, arl_risk_class=risk_class)

    # The engine expects Money (Decimal). Reuse its canonical converter so
    # integers, strings, floats, and Decimal values are handled consistently.
    effective_other_deductions = money(other_deductions)

    return calculate_payroll(
        snapshot,
        effective_period,
        effective_rules,
        model_novelties(employee),
        effective_other_deductions,
    )
