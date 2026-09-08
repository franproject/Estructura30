"""Faculty model.

Represents a university faculty and stores the related academic programs.
"""

from .linked_list import LinkedList


class Faculty:
    """Entity that represents a university faculty."""

    def __init__(
        self,
        faculty_id=0,
        name="",
        dean="",
        creation_date="",
        active=False,
        program_list=None,
    ):
        self.faculty_id = faculty_id
        self.name = name
        self.dean = dean
        self.creation_date = creation_date
        self.active = active
        self.program_list = program_list if program_list is not None else LinkedList()
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
        self.faculty_id = self._validate_id("faculty_id", self.faculty_id)
        if not isinstance(self.name, str):
            raise TypeError("name must be a string")
        if self.faculty_id > 0 and not self.name.strip():
            raise ValueError("name is required for a valid faculty")
        if not isinstance(self.dean, str):
            raise TypeError("dean must be a string")
        if not isinstance(self.creation_date, str):
            raise TypeError("creation_date must be a string")
        if not isinstance(self.active, bool):
            raise TypeError("active must be a boolean")
        if self.program_list is None:
            self.program_list = LinkedList()
        if not isinstance(self.program_list, LinkedList):
            raise TypeError("program_list must be a LinkedList")
        return True

    def to_dict(self):
        return {
            "faculty_id": self.faculty_id,
            "name": self.name,
            "dean": self.dean,
            "creation_date": self.creation_date,
            "active": self.active,
            "program_list": list(self.program_list),
        }

    @classmethod
    def from_dict(cls, data):
        if data is None:
            raise ValueError("Faculty data cannot be null")
        return cls(
            faculty_id=data.get("faculty_id", 0),
            name=data.get("name", ""),
            dean=data.get("dean", ""),
            creation_date=data.get("creation_date", ""),
            active=data.get("active", False),
            program_list=LinkedList(data.get("program_list", [])),
        )
