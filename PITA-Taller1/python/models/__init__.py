"""Domain models for the PITA academic system.

This package keeps the existing model layer intact and makes the project
structure explicit without introducing a parallel architecture.
"""

from .administrative import Administrative
from .course import Course
from .enrollment import Enrollment
from .faculty import Faculty
from .linked_list import LinkedList
from .payroll import Payroll
from .professor import Professor
from .program import Program
from .student import Student
