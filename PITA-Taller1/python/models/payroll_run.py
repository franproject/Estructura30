"""Payroll run and immutable result snapshot."""

from dataclasses import dataclass, field
from enum import Enum


class PayrollRunStatus(str, Enum):
    CALCULATED = "CALCULATED"
    APPROVED = "APPROVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


@dataclass
class PayrollRun:
    run_id: str
    period_id: str
    employee_ids: list[str] = field(default_factory=list)
    details: list[dict] = field(default_factory=list)
    totals: dict = field(default_factory=dict)
    employer_cost: int = 0
    status: PayrollRunStatus = PayrollRunStatus.CALCULATED
    executed_at: str = ""
    audit_ids: list[str] = field(default_factory=list)
    created_at: str = ""
    calculated_at: str = ""
    calculated_by: str = ""
    approved_at: str = ""
    approved_by: str = ""
    closed_at: str = ""
    closed_by: str = ""
    novelty_ids: list[str] = field(default_factory=list)
    revision_of: str = ""

    def validate(self):
        if not self.run_id.strip() or not self.period_id.strip():
            raise ValueError("run_id and period_id are required")
        if not isinstance(self.status, PayrollRunStatus):
            self.status = PayrollRunStatus(self.status)
        if self.employer_cost < 0:
            raise ValueError("employer_cost cannot be negative")
        return True

    def approve(self):
        if self.status != PayrollRunStatus.CALCULATED:
            raise ValueError("only calculated runs can be approved")
        self.status = PayrollRunStatus.APPROVED

    def close(self):
        if self.status != PayrollRunStatus.APPROVED:
            raise ValueError("only approved runs can be closed")
        self.status = PayrollRunStatus.CLOSED

    def assert_mutable(self):
        if self.status in {PayrollRunStatus.CLOSED, PayrollRunStatus.CANCELLED}:
            raise ValueError("closed or cancelled payroll runs cannot be modified")

    def to_dict(self):
        result = self.__dict__.copy()
        result["status"] = self.status.value
        return result

    @classmethod
    def from_dict(cls, data):
        run = cls(**data)
        run.validate()
        return run
