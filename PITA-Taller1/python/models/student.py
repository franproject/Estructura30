"""Student model.

Represents a university student and stores their academic enrollments.
"""

from .linked_list import LinkedList


class Student:
    """Entity that represents a student."""

    def __init__(
        self,
        student_id=0,
        full_name="",
        document_type="",
        document_number="",
        birth_date="",
        email="",
        phone="",
        program_id=0,
        current_semester=0,
        status="",
        cumulative_average=0.0,
        active=False,
        enrollment_list=None,
    ):
        self.student_id = student_id
        self.full_name = full_name
        self.document_type = document_type
        self.document_number = document_number
        self.birth_date = birth_date
        self.email = email
        self.phone = phone
        self.program_id = program_id
        self.current_semester = current_semester
        self.status = status
        self.cumulative_average = cumulative_average
        self.active = active
        self.enrollment_list = enrollment_list if enrollment_list is not None else LinkedList()
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
        self.student_id = self._validate_id("student_id", self.student_id)
        self.program_id = self._validate_id("program_id", self.program_id)
        if not isinstance(self.full_name, str):
            raise TypeError("full_name must be a string")
        if self.student_id > 0 and not self.full_name.strip():
            raise ValueError("full_name is required for a valid student")
        if not isinstance(self.document_type, str):
            raise TypeError("document_type must be a string")
        if not isinstance(self.document_number, str):
            raise TypeError("document_number must be a string")
        if not isinstance(self.birth_date, str):
            raise TypeError("birth_date must be a string")
        if not isinstance(self.email, str):
            raise TypeError("email must be a string")
        if not isinstance(self.phone, str):
            raise TypeError("phone must be a string")
        if not isinstance(self.current_semester, int):
            raise TypeError("current_semester must be an integer")
        if self.current_semester < 0:
            raise ValueError("current_semester cannot be negative")
        if not isinstance(self.status, str):
            raise TypeError("status must be a string")
        if not isinstance(self.cumulative_average, (int, float)):
            raise TypeError("cumulative_average must be numeric")
        if not isinstance(self.active, bool):
            raise TypeError("active must be a boolean")
        if self.enrollment_list is None:
            self.enrollment_list = LinkedList()
        if not isinstance(self.enrollment_list, LinkedList):
            raise TypeError("enrollment_list must be a LinkedList")
        return True

    def to_dict(self):
        return {
            "student_id": self.student_id,
            "full_name": self.full_name,
            "document_type": self.document_type,
            "document_number": self.document_number,
            "birth_date": self.birth_date,
            "email": self.email,
            "phone": self.phone,
            "program_id": self.program_id,
            "current_semester": self.current_semester,
            "status": self.status,
            "cumulative_average": self.cumulative_average,
            "active": self.active,
            "enrollment_list": list(self.enrollment_list),
        }

    @classmethod
    def from_dict(cls, data):
        if data is None:
            raise ValueError("Student data cannot be null")
        return cls(
            student_id=data.get("student_id", 0),
            full_name=data.get("full_name", ""),
            document_type=data.get("document_type", ""),
            document_number=data.get("document_number", ""),
            birth_date=data.get("birth_date", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            program_id=data.get("program_id", 0),
            current_semester=data.get("current_semester", 0),
            status=data.get("status", ""),
            cumulative_average=data.get("cumulative_average", 0.0),
            active=data.get("active", False),
            enrollment_list=LinkedList(data.get("enrollment_list", [])),
        )
