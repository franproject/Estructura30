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
        hire_date="",
        termination_date="",
        linkage_type="",
        employment_status="UNKNOWN",
        salary_type="FIXED_MONTHLY",
        arl_risk_class="I",
        social_security_config_id="DEFAULT",
        worked_days=0,
        hourly_rate=0.0,
        continuous_service_days=0,
        novelties=None,
        bonuses=None,
        salary_concepts=None,
        non_salary_concepts=None,
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
        self.hire_date = hire_date
        self.termination_date = termination_date
        self.linkage_type = linkage_type
        self.employment_status = employment_status
        self.salary_type = salary_type
        self.arl_risk_class = arl_risk_class
        self.social_security_config_id = social_security_config_id
        self.worked_days = worked_days
        self.hourly_rate = hourly_rate
        self.continuous_service_days = continuous_service_days
        self.novelties = list(novelties or [])
        self.bonuses = list(bonuses or [])
        self.salary_concepts = list(salary_concepts or [])
        self.non_salary_concepts = list(non_salary_concepts or [])
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
        for field_name in ("base_salary", "health_discount", "pension_discount", "severance_provision", "holiday_bonus", "vacation_provision", "net_salary", "hourly_rate"):
            if not isinstance(getattr(self, field_name), (int, float)):
                raise TypeError(f"{field_name} must be numeric")
        if not isinstance(self.active, bool):
            raise TypeError("active must be a boolean")
        for field_name in ("hire_date", "termination_date", "linkage_type", "employment_status", "salary_type", "arl_risk_class", "social_security_config_id"):
            if not isinstance(getattr(self, field_name), str):
                raise TypeError(f"{field_name} must be a string")
        if not isinstance(self.worked_days, int) or not 0 <= self.worked_days <= 360:
            raise ValueError("worked_days must be between 0 and 360")
        if not isinstance(self.continuous_service_days, int) or self.continuous_service_days < 0:
            raise ValueError("continuous_service_days cannot be negative")
        for field_name in ("novelties", "bonuses", "salary_concepts", "non_salary_concepts"):
            if not isinstance(getattr(self, field_name), list):
                raise TypeError(f"{field_name} must be a list")
        return True

    def __eq__(self, other):
        if isinstance(other, Administrative):
            return self.administrative_id == other.administrative_id
        if isinstance(other, int):
            return self.administrative_id == other
        return False

    def __hash__(self):
        return hash(self.administrative_id)

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
            "hire_date": self.hire_date,
            "termination_date": self.termination_date,
            "linkage_type": self.linkage_type,
            "employment_status": self.employment_status,
            "salary_type": self.salary_type,
            "arl_risk_class": self.arl_risk_class,
            "social_security_config_id": self.social_security_config_id,
            "worked_days": self.worked_days,
            "hourly_rate": self.hourly_rate,
            "continuous_service_days": self.continuous_service_days,
            "novelties": self.novelties,
            "bonuses": self.bonuses,
            "salary_concepts": self.salary_concepts,
            "non_salary_concepts": self.non_salary_concepts,
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
            hire_date=data.get("hire_date", ""),
            termination_date=data.get("termination_date", ""),
            linkage_type=data.get("linkage_type", ""),
            employment_status=data.get("employment_status", "UNKNOWN"),
            salary_type=data.get("salary_type", "FIXED_MONTHLY"),
            arl_risk_class=data.get("arl_risk_class", "I"),
            social_security_config_id=data.get("social_security_config_id", "DEFAULT"),
            worked_days=data.get("worked_days", 0),
            hourly_rate=data.get("hourly_rate", 0.0),
            continuous_service_days=data.get("continuous_service_days", 0),
            novelties=data.get("novelties", []),
            bonuses=data.get("bonuses", []),
            salary_concepts=data.get("salary_concepts", []),
            non_salary_concepts=data.get("non_salary_concepts", []),
        )
