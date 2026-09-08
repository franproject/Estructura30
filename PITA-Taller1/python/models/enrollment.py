"""Enrollment model.

Represents a student's enrollment in a course during an academic period.
It contains no business logic or calculations and only stores basic information.
"""


class Enrollment:
    """Entity that records a student's enrollment in a course."""

    def __init__(
        self,
        enrollment_id=0,
        student_id=0,
        course_id=0,
        academic_period="",
        final_grade=0.0,
        status="",
        enrollment_date="",
    ):
        self.enrollment_id = enrollment_id
        self.student_id = student_id
        self.course_id = course_id
        self.academic_period = academic_period
        self.final_grade = final_grade
        self.status = status
        self.enrollment_date = enrollment_date
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
        self.enrollment_id = self._validate_id("enrollment_id", self.enrollment_id)
        self.student_id = self._validate_id("student_id", self.student_id)
        self.course_id = self._validate_id("course_id", self.course_id)
        if not isinstance(self.academic_period, str):
            raise TypeError("academic_period must be a string")
        if not isinstance(self.final_grade, (int, float)):
            raise TypeError("final_grade must be numeric")
        if not isinstance(self.status, str):
            raise TypeError("status must be a string")
        if not isinstance(self.enrollment_date, str):
            raise TypeError("enrollment_date must be a string")
        return True

    def to_dict(self):
        return {
            "enrollment_id": self.enrollment_id,
            "student_id": self.student_id,
            "course_id": self.course_id,
            "academic_period": self.academic_period,
            "final_grade": self.final_grade,
            "status": self.status,
            "enrollment_date": self.enrollment_date,
        }

    @classmethod
    def from_dict(cls, data):
        if data is None:
            raise ValueError("Enrollment data cannot be null")
        return cls(
            enrollment_id=data.get("enrollment_id", 0),
            student_id=data.get("student_id", 0),
            course_id=data.get("course_id", 0),
            academic_period=data.get("academic_period", ""),
            final_grade=data.get("final_grade", 0.0),
            status=data.get("status", ""),
            enrollment_date=data.get("enrollment_date", ""),
        )
