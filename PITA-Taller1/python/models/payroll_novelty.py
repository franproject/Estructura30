"""Payroll novelty model with explicit formula readiness."""

from dataclasses import dataclass
from enum import Enum


class PayrollNoveltyType(str, Enum):
    INCOME = "INCOME"
    TERMINATION = "TERMINATION"
    INCAPACITY = "INCAPACITY"
    LICENSE = "LICENSE"
    VACATION = "VACATION"
    ABSENCE = "ABSENCE"
    ADDITIONAL_HOURS = "ADDITIONAL_HOURS"
    BONUS = "BONUS"
    DISCOUNT = "DISCOUNT"
    GARNISHMENT = "GARNISHMENT"
    ADVANCE = "ADVANCE"
    SALARY_ADJUSTMENT = "SALARY_ADJUSTMENT"


class PayrollNoveltyStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


# Only these novelty types have an amount-based path defined by the current rules.
AMOUNT_BASED_TYPES = {
    PayrollNoveltyType.BONUS,
    PayrollNoveltyType.DISCOUNT,
    PayrollNoveltyType.GARNISHMENT,
    PayrollNoveltyType.ADVANCE,
    PayrollNoveltyType.SALARY_ADJUSTMENT,
}


@dataclass
class PayrollNovelty:
    novelty_id: str
    period_id: str
    employee_id: str
    novelty_type: PayrollNoveltyType
    start_date: str
    end_date: str = ""
    quantity: str = "1"
    amount: str = ""
    description: str = ""
    status: PayrollNoveltyStatus = PayrollNoveltyStatus.DRAFT
    created_by: str = ""
    approved_by: str = ""
    formula_status: str = "UNDEFINED"
    is_salary: bool = True
    affects_ibc: bool = True

    def validate(self):
        if not self.novelty_id.strip() or not self.period_id.strip() or not self.employee_id.strip():
            raise ValueError("novelty identifiers are required")
        if not self.start_date:
            raise ValueError("novelty start_date is required")
        if not isinstance(self.novelty_type, PayrollNoveltyType):
            self.novelty_type = PayrollNoveltyType(self.novelty_type)
        if not isinstance(self.status, PayrollNoveltyStatus):
            self.status = PayrollNoveltyStatus(self.status)
        if self.quantity == "" or float(self.quantity) < 0:
            raise ValueError("novelty quantity cannot be negative")
        if self.amount != "" and float(self.amount) < 0:
            raise ValueError("novelty amount cannot be negative")
        return True

    def has_defined_formula(self):
        return self.novelty_type in AMOUNT_BASED_TYPES and self.amount != ""

    def to_engine_dict(self):
        if not self.has_defined_formula():
            raise ValueError(
                f"no formula is defined for novelty type {self.novelty_type.value}"
            )
        return {
            "code": self.novelty_id,
            "amount": self.amount,
            "quantity": self.quantity,
            "is_salary": self.is_salary,
            "affects_ibc": self.affects_ibc,
            "description": self.description,
        }

    def to_dict(self):
        result = self.__dict__.copy()
        result["novelty_type"] = self.novelty_type.value
        result["status"] = self.status.value
        return result

    @classmethod
    def from_dict(cls, data):
        novelty = cls(**data)
        novelty.validate()
        return novelty
