"""Formal payroll period lifecycle."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PayrollPeriodStatus(str, Enum):
    OPEN = "OPEN"
    CALCULATED = "CALCULATED"
    APPROVED = "APPROVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


@dataclass
class PayrollPeriod:
    period_id: str
    year: int
    month: int
    start_date: str
    end_date: str
    status: PayrollPeriodStatus = PayrollPeriodStatus.OPEN
    created_at: str = ""
    closed_at: str = ""
    responsible_user: str = ""

    def validate(self):
        if not self.period_id.strip():
            raise ValueError("period_id is required")
        if self.year < 2000 or not 1 <= self.month <= 12:
            raise ValueError("invalid payroll year or month")
        start = datetime.fromisoformat(self.start_date)
        end = datetime.fromisoformat(self.end_date)
        if end < start:
            raise ValueError("end_date cannot precede start_date")
        if not isinstance(self.status, PayrollPeriodStatus):
            self.status = PayrollPeriodStatus(self.status)
        if self.status == PayrollPeriodStatus.CLOSED and not self.closed_at:
            raise ValueError("closed periods require closed_at")
        return True

    def can_change(self):
        return self.status not in {PayrollPeriodStatus.CLOSED, PayrollPeriodStatus.CANCELLED}

    def close(self, closed_at, responsible_user=""):
        if self.status != PayrollPeriodStatus.APPROVED:
            raise ValueError("only approved periods can be closed")
        self.status = PayrollPeriodStatus.CLOSED
        self.closed_at = closed_at
        if responsible_user:
            self.responsible_user = responsible_user
        self.validate()

    def to_dict(self):
        result = self.__dict__.copy()
        result["status"] = self.status.value
        return result

    @classmethod
    def from_dict(cls, data):
        period = cls(**data)
        period.validate()
        return period
