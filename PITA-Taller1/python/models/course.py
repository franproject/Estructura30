"""Course model.

Represents a university course and stores its associated enrollments.
"""

from .linked_list import LinkedList


class Course:
    """Entity that represents an academic course."""

    def __init__(
        self,
        course_id=0,
        name="",
        program_id=0,
        credits=0,
        curriculum_semester=0,
        assigned_professor_id=0,
        max_capacity=0,
        active=False,
        enrollment_list=None,
    ):
        self.course_id = course_id
        self.name = name
        self.program_id = program_id
        self.credits = credits
        self.curriculum_semester = curriculum_semester
        self.assigned_professor_id = assigned_professor_id
        self.max_capacity = max_capacity
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
        self.course_id = self._validate_id("course_id", self.course_id)
        self.program_id = self._validate_id("program_id", self.program_id)
        self.assigned_professor_id = self._validate_id("assigned_professor_id", self.assigned_professor_id)
        if not isinstance(self.name, str):
            raise TypeError("name must be a string")
        if self.course_id > 0 and not self.name.strip():
            raise ValueError("name is required for a valid course")
        if not isinstance(self.credits, int):
            raise TypeError("credits must be an integer")
        if self.credits < 0:
            raise ValueError("credits cannot be negative")
        if not isinstance(self.curriculum_semester, int):
            raise TypeError("curriculum_semester must be an integer")
        if self.curriculum_semester < 0:
            raise ValueError("curriculum_semester cannot be negative")
        if not isinstance(self.max_capacity, int):
            raise TypeError("max_capacity must be an integer")
        if self.max_capacity < 0:
            raise ValueError("max_capacity cannot be negative")
        if not isinstance(self.active, bool):
            raise TypeError("active must be a boolean")
        if self.enrollment_list is None:
            self.enrollment_list = LinkedList()
        if not isinstance(self.enrollment_list, LinkedList):
            raise TypeError("enrollment_list must be a LinkedList")
        return True

    def to_dict(self):
        return {
            "course_id": self.course_id,
            "name": self.name,
            "program_id": self.program_id,
            "credits": self.credits,
            "curriculum_semester": self.curriculum_semester,
            "assigned_professor_id": self.assigned_professor_id,
            "max_capacity": self.max_capacity,
            "active": self.active,
            "enrollment_list": list(self.enrollment_list),
        }

    @classmethod
    def from_dict(cls, data):
        if data is None:
            raise ValueError("Course data cannot be null")
        return cls(
            course_id=data.get("course_id", 0),
            name=data.get("name", ""),
            program_id=data.get("program_id", 0),
            credits=data.get("credits", 0),
            curriculum_semester=data.get("curriculum_semester", 0),
            assigned_professor_id=data.get("assigned_professor_id", 0),
            max_capacity=data.get("max_capacity", 0),
            active=data.get("active", False),
            enrollment_list=LinkedList(data.get("enrollment_list", [])),
        )
