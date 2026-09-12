"""Program model.

Represents an academic program and stores the related courses and students.
"""

from .linked_list import LinkedList


class Program:
    """Entity that represents an academic program."""

    def __init__(
        self,
        program_id=0,
        name="",
        faculty_id=0,
        program_director="",
        level="",
        modality="",
        program_type="Otro",
        active=False,
        course_list=None,
        student_list=None,
    ):
        self.program_id = program_id
        self.name = name
        self.faculty_id = faculty_id
        self.program_director = program_director
        self.level = level
        self.modality = modality
        self.program_type = program_type
        self.active = active
        self.course_list = course_list if course_list is not None else LinkedList()
        self.student_list = student_list if student_list is not None else LinkedList()
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
        self.program_id = self._validate_id("program_id", self.program_id)
        self.faculty_id = self._validate_id("faculty_id", self.faculty_id)
        if not isinstance(self.name, str):
            raise TypeError("name must be a string")
        if self.program_id > 0 and not self.name.strip():
            raise ValueError("name is required for a valid program")
        if not isinstance(self.program_director, str):
            raise TypeError("program_director must be a string")
        if not isinstance(self.level, str):
            raise TypeError("level must be a string")
        if not isinstance(self.modality, str):
            raise TypeError("modality must be a string")
        if not isinstance(self.program_type, str):
            raise TypeError("program_type must be a string")
        if not self.program_type.strip():
            raise ValueError("program_type cannot be empty")
        if not isinstance(self.active, bool):
            raise TypeError("active must be a boolean")
        if self.course_list is None:
            self.course_list = LinkedList()
        if not isinstance(self.course_list, LinkedList):
            raise TypeError("course_list must be a LinkedList")
        if self.student_list is None:
            self.student_list = LinkedList()
        if not isinstance(self.student_list, LinkedList):
            raise TypeError("student_list must be a LinkedList")
        return True

    def __eq__(self, other):
        if isinstance(other, Program):
            return self.program_id == other.program_id
        if isinstance(other, int):
            return self.program_id == other
        return False

    def __hash__(self):
        return hash(self.program_id)

    def to_dict(self):
        return {
            "program_id": self.program_id,
            "name": self.name,
            "faculty_id": self.faculty_id,
            "program_director": self.program_director,
            "level": self.level,
            "modality": self.modality,
            "program_type": self.program_type,
            "active": self.active,
            "course_list": list(self.course_list),
            "student_list": list(self.student_list),
        }

    @classmethod
    def from_dict(cls, data):
        if data is None:
            raise ValueError("Program data cannot be null")
        return cls(
            program_id=data.get("program_id", 0),
            name=data.get("name", ""),
            faculty_id=data.get("faculty_id", 0),
            program_director=data.get("program_director", ""),
            level=data.get("level", ""),
            modality=data.get("modality", ""),
            program_type=data.get("program_type", "Otro"),
            active=data.get("active", False),
            course_list=LinkedList(data.get("course_list", [])),
            student_list=LinkedList(data.get("student_list", [])),
        )
