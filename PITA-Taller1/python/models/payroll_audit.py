"""Immutable audit event for the payroll lifecycle."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PayrollAudit:
    audit_id: str
    entity_type: str
    entity_id: str
    action: str
    timestamp: str
    actor: str = ""
    reason: str = ""
    before_data: dict | None = None
    after_data: dict | None = None
    trace_id: str = ""

    def to_dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
