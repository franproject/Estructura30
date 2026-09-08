"""Structured individual payroll payslip."""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class Payslip:
    payslip_id: str
    run_id: str
    period_id: str
    liquidation_date: str
    institution_name: str
    institution_id: str
    employee: dict
    academic_base: dict
    earnings: tuple[dict, ...]
    deductions: dict
    benefits: dict
    employer_contributions: dict
    summary: dict
    days_worked: int
    arl_risk_class: str
    arl_rate: Decimal
    health_exemption_rate: Decimal
    trace_id: str
    metadata: dict = field(default_factory=dict)

    def validate(self):
        required = ("payslip_id", "run_id", "period_id", "liquidation_date")
        if any(not str(getattr(self, field_name)).strip() for field_name in required):
            raise ValueError("payslip identifiers and liquidation_date are required")
        if self.days_worked < 0:
            raise ValueError("days_worked cannot be negative")
        if self.summary.get("net_salary") is None:
            raise ValueError("payslip summary must contain net_salary")
        return True

    def to_dict(self):
        result = self.__dict__.copy()
        result["arl_rate"] = str(self.arl_rate)
        result["health_exemption_rate"] = str(self.health_exemption_rate)
        result["earnings"] = list(self.earnings)
        return result

    @classmethod
    def from_dict(cls, data):
        payslip = cls(
            **{**data, "arl_rate": Decimal(str(data["arl_rate"])),
               "health_exemption_rate": Decimal(str(data["health_exemption_rate"])),
               "earnings": tuple(data.get("earnings", ()))},
        )
        payslip.validate()
        return payslip
