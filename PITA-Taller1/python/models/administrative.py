"""Administrative model.

Represents the university administrative staff.
"""


class Administrative:
    """Entity that represents an administrative worker."""

    def __init__(
        self,
        administrative_id=0,
        full_name="",
        document_type="",
        document_number="",
        email="",
        phone="",
        position="",
        category="",
        employment_type="",
        base_salary=0.0,
        health_discount=0.0,
        pension_discount=0.0,
        severance_provision=0.0,
        holiday_bonus=0.0,
        vacation_provision=0.0,
        net_salary=0.0,
        active=False,
    ):
        self.administrative_id = administrative_id
        self.full_name = full_name
        self.document_type = document_type
        self.document_number = document_number
        self.email = email
        self.phone = phone
        self.position = position
        self.category = category
        self.employment_type = employment_type
        self.base_salary = base_salary
        self.health_discount = health_discount
        self.pension_discount = pension_discount
        self.severance_provision = severance_provision
        self.holiday_bonus = holiday_bonus
        self.vacation_provision = vacation_provision
        self.net_salary = net_salary
        self.active = active
        self.validate()

    @staticmethod
    def _validate_id(field_name, value):
        if value is None:
            raise ValueError(f"{field_name} cannot be null")
        if not isinstance(value, int):
            raise TypeError(f"{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"{field_name} cannot be negative")
        return value

    def validate(self):
        self.administrative_id = self._validate_id("administrative_id", self.administrative_id)
        if not isinstance(self.full_name, str):
            raise TypeError("full_name must be a string")
        if self.administrative_id > 0 and not self.full_name.strip():
            raise ValueError("full_name is required for a valid administrative worker")
        for field_name in ("document_type", "document_number", "email", "phone", "position", "category", "employment_type"):
            if not isinstance(getattr(self, field_name), str):
                raise TypeError(f"{field_name} must be a string")
        for field_name in ("base_salary", "health_discount", "pension_discount", "severance_provision", "holiday_bonus", "vacation_provision", "net_salary"):
            if not isinstance(getattr(self, field_name), (int, float)):
                raise TypeError(f"{field_name} must be numeric")
        if not isinstance(self.active, bool):
            raise TypeError("active must be a boolean")
        return True

    def to_dict(self):
        return {
            "administrative_id": self.administrative_id,
            "full_name": self.full_name,
            "document_type": self.document_type,
            "document_number": self.document_number,
            "email": self.email,
            "phone": self.phone,
            "position": self.position,
            "category": self.category,
            "employment_type": self.employment_type,
            "base_salary": self.base_salary,
            "health_discount": self.health_discount,
            "pension_discount": self.pension_discount,
            "severance_provision": self.severance_provision,
            "holiday_bonus": self.holiday_bonus,
            "vacation_provision": self.vacation_provision,
            "net_salary": self.net_salary,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data):
        if data is None:
            raise ValueError("Administrative data cannot be null")
        return cls(
            administrative_id=data.get("administrative_id", 0),
            full_name=data.get("full_name", ""),
            document_type=data.get("document_type", ""),
            document_number=data.get("document_number", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            position=data.get("position", ""),
            category=data.get("category", ""),
            employment_type=data.get("employment_type", ""),
            base_salary=data.get("base_salary", 0.0),
            health_discount=data.get("health_discount", 0.0),
            pension_discount=data.get("pension_discount", 0.0),
            severance_provision=data.get("severance_provision", 0.0),
            holiday_bonus=data.get("holiday_bonus", 0.0),
            vacation_provision=data.get("vacation_provision", 0.0),
            net_salary=data.get("net_salary", 0.0),
            active=data.get("active", False),
        )
