"""Business-layer entity management for the existing domain models.

The project already uses a custom LinkedList as the primary collection type.
This module keeps the logic in a manager layer, cleanly separated from the GUI.

Academic transaction rule:
- The current EBRA rule is configured as: weighted_average < configured_threshold.
- The threshold is stored in the manager and can be changed without modifying the
  academic logic itself.
"""

from datetime import date

from models.administrative import Administrative
from models.course import Course
from models.enrollment import Enrollment
from models.faculty import Faculty
from models.linked_list import LinkedList
from models.professor import Professor
from models.program import Program
from models.student import Student


class EntityManager:
    """Provides CRUD and lifecycle operations for the main entities."""

    def __init__(self):
        self.faculties = LinkedList()
        self.programs = LinkedList()
        self.courses = LinkedList()
        self.students = LinkedList()
        self.professors = LinkedList()
        self.administrative_staff = LinkedList()
        self.enrollments = LinkedList()
        self.ebra_threshold = 3.0
        self.ebra_rule = "weighted_average < configured_threshold"

    def set_ebra_threshold(self, threshold):
        """Configures the academic EBRA threshold without changing the rule itself."""
        if not isinstance(threshold, (int, float)):
            raise TypeError("threshold must be numeric")
        if threshold < 0:
            raise ValueError("threshold cannot be negative")
        self.ebra_threshold = float(threshold)
        return self.ebra_threshold

    @staticmethod
    def _safe_status(value):
        return str(value).strip().upper() if value is not None else ""

    @staticmethod
    def _next_id(collection, field_name):
        current_max = 0
        current = collection.head
        while current is not None:
            item = current.data
            if hasattr(item, field_name):
                value = getattr(item, field_name)
                if isinstance(value, int) and value > current_max:
                    current_max = value
            current = current.next
        return current_max + 1

    def _active_course_enrollment_count(self, course_id):
        current = self.enrollments.head
        count = 0
        while current is not None:
            item = current.data
            if (
                isinstance(item, Enrollment)
                and item.course_id == course_id
                and self._safe_status(item.status) in {"ACTIVE", "COMPLETED"}
            ):
                count += 1
            current = current.next
        return count

    def _has_active_enrollment_for_student_course(self, student_id, course_id, academic_period=None):
        current = self.enrollments.head
        while current is not None:
            item = current.data
            if not isinstance(item, Enrollment):
                current = current.next
                continue
            if item.student_id != student_id or item.course_id != course_id:
                current = current.next
                continue
            if self._safe_status(item.status) == "CANCELLED":
                current = current.next
                continue
            if academic_period is not None and item.academic_period != academic_period:
                current = current.next
                continue
            if self._safe_status(item.status) in {"ACTIVE", "COMPLETED"}:
                return True
            current = current.next
        return False

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _find_by_id(collection, field_name, entity_id):
        return collection.find_by(field_name, entity_id)

    @staticmethod
    def _has_duplicate(collection, field_name, entity_id, ignore_id=None):
        current = collection.head
        while current is not None:
            item = current.data
            if item is None:
                current = current.next
                continue
            if getattr(item, field_name, None) == entity_id:
                if ignore_id is None or getattr(item, field_name, None) != ignore_id:
                    return True
            current = current.next
        return False

    @staticmethod
    def _entity_exists(collection, field_name, entity_id):
        return EntityManager._find_by_id(collection, field_name, entity_id) is not None

    @staticmethod
    def _exists_enrollment_for_student_course_period(enrollments, student_id, course_id, academic_period):
        current = enrollments.head
        while current is not None:
            item = current.data
            if (
                isinstance(item, Enrollment)
                and item.student_id == student_id
                and item.course_id == course_id
                and item.academic_period == academic_period
            ):
                return True
            current = current.next
        return False

    @staticmethod
    def _validate_active(entity, action):
        if entity is None:
            return False
        if not getattr(entity, "active", False):
            raise ValueError(f"{action} cannot be used on an inactive entity")
        return True

    # ------------------------------------------------------------------
    # Faculty
    # ------------------------------------------------------------------

    def create_faculty(self, faculty):
        if not isinstance(faculty, Faculty):
            raise TypeError("faculty must be a Faculty instance")
        if self._entity_exists(self.faculties, "faculty_id", faculty.faculty_id):
            return False
        faculty.validate()
        self.faculties.insert(faculty)
        return True

    def get_faculty(self, faculty_id):
        return self._find_by_id(self.faculties, "faculty_id", faculty_id)

    def list_faculties(self):
        return self.faculties

    def search_faculty(self, name):
        return self.faculties.find_by("name", name)

    def update_faculty(self, faculty_id, **updates):
        faculty = self.get_faculty(faculty_id)
        if faculty is None:
            return False
        for key, value in updates.items():
            if hasattr(faculty, key):
                setattr(faculty, key, value)
        faculty.validate()
        return True

    def delete_faculty(self, faculty_id):
        faculty = self.get_faculty(faculty_id)
        if faculty is None:
            return False
        if faculty.program_list.count_elements() > 0:
            return False
        return self.faculties.remove(faculty)

    def deactivate_faculty(self, faculty_id):
        faculty = self.get_faculty(faculty_id)
        if faculty is None:
            return False
        faculty.active = False
        faculty.validate()
        return True

    def reactivate_faculty(self, faculty_id):
        faculty = self.get_faculty(faculty_id)
        if faculty is None:
            return False
        faculty.active = True
        faculty.validate()
        return True

    # ------------------------------------------------------------------
    # Program
    # ------------------------------------------------------------------

    def create_program(self, program):
        if not isinstance(program, Program):
            raise TypeError("program must be a Program instance")
        if self._entity_exists(self.programs, "program_id", program.program_id):
            return False
        if not self._entity_exists(self.faculties, "faculty_id", program.faculty_id):
            return False
        faculty = self.get_faculty(program.faculty_id)
        if faculty is None or not faculty.active:
            return False
        program.validate()
        self.programs.insert(program)
        faculty.program_list.insert(program)
        return True

    def get_program(self, program_id):
        return self._find_by_id(self.programs, "program_id", program_id)

    def list_programs(self):
        return self.programs

    def search_program(self, name):
        return self.programs.find_by("name", name)

    def update_program(self, program_id, **updates):
        program = self.get_program(program_id)
        if program is None:
            return False
        for key, value in updates.items():
            if hasattr(program, key):
                setattr(program, key, value)
        if program.faculty_id and not self._entity_exists(self.faculties, "faculty_id", program.faculty_id):
            return False
        program.validate()
        return True

    def delete_program(self, program_id):
        program = self.get_program(program_id)
        if program is None:
            return False
        if program.course_list.count_elements() > 0 or program.student_list.count_elements() > 0:
            return False
        faculty = self.get_faculty(program.faculty_id)
        if faculty is not None:
            faculty.program_list.remove(program)
        return self.programs.remove(program)

    def deactivate_program(self, program_id):
        program = self.get_program(program_id)
        if program is None:
            return False
        program.active = False
        program.validate()
        return True

    def reactivate_program(self, program_id):
        program = self.get_program(program_id)
        if program is None:
            return False
        faculty = self.get_faculty(program.faculty_id)
        if faculty is None or not faculty.active:
            return False
        program.active = True
        program.validate()
        return True

    # ------------------------------------------------------------------
    # Course
    # ------------------------------------------------------------------

    def create_course(self, course):
        if not isinstance(course, Course):
            raise TypeError("course must be a Course instance")
        if self._entity_exists(self.courses, "course_id", course.course_id):
            return False
        if not self._entity_exists(self.programs, "program_id", course.program_id):
            return False
        program = self.get_program(course.program_id)
        if program is None or not program.active:
            return False
        if course.assigned_professor_id and not self._entity_exists(self.professors, "professor_id", course.assigned_professor_id):
            return False
        professor = self.get_professor(course.assigned_professor_id) if course.assigned_professor_id else None
        if professor is not None and not professor.active:
            return False
        course.validate()
        self.courses.insert(course)
        program.course_list.insert(course)
        return True

    def get_course(self, course_id):
        return self._find_by_id(self.courses, "course_id", course_id)

    def list_courses(self):
        return self.courses

    def search_course(self, name):
        return self.courses.find_by("name", name)

    def update_course(self, course_id, **updates):
        course = self.get_course(course_id)
        if course is None:
            return False
        for key, value in updates.items():
            if hasattr(course, key):
                setattr(course, key, value)
        if course.program_id and not self._entity_exists(self.programs, "program_id", course.program_id):
            return False
        course.validate()
        return True

    def delete_course(self, course_id):
        course = self.get_course(course_id)
        if course is None:
            return False
        if course.enrollment_list.count_elements() > 0:
            return False
        program = self.get_program(course.program_id)
        if program is not None:
            program.course_list.remove(course)
        return self.courses.remove(course)

    def deactivate_course(self, course_id):
        course = self.get_course(course_id)
        if course is None:
            return False
        course.active = False
        course.validate()
        return True

    def reactivate_course(self, course_id):
        course = self.get_course(course_id)
        if course is None:
            return False
        program = self.get_program(course.program_id)
        if program is None or not program.active:
            return False
        course.active = True
        course.validate()
        return True

    # ------------------------------------------------------------------
    # Student
    # ------------------------------------------------------------------

    def create_student(self, student):
        if not isinstance(student, Student):
            raise TypeError("student must be a Student instance")
        if self._entity_exists(self.students, "student_id", student.student_id):
            return False
        if not self._entity_exists(self.programs, "program_id", student.program_id):
            return False
        program = self.get_program(student.program_id)
        if program is None or not program.active:
            return False
        student.validate()
        self.students.insert(student)
        program.student_list.insert(student)
        return True

    def get_student(self, student_id):
        return self._find_by_id(self.students, "student_id", student_id)

    def list_students(self):
        return self.students

    def search_student(self, full_name):
        return self.students.find_by("full_name", full_name)

    def update_student(self, student_id, **updates):
        student = self.get_student(student_id)
        if student is None:
            return False
        for key, value in updates.items():
            if hasattr(student, key):
                setattr(student, key, value)
        if student.program_id and not self._entity_exists(self.programs, "program_id", student.program_id):
            return False
        student.validate()
        return True

    def delete_student(self, student_id):
        student = self.get_student(student_id)
        if student is None:
            return False
        if student.enrollment_list.count_elements() > 0:
            return False
        program = self.get_program(student.program_id)
        if program is not None:
            program.student_list.remove(student)
        return self.students.remove(student)

    def deactivate_student(self, student_id):
        student = self.get_student(student_id)
        if student is None:
            return False
        student.active = False
        student.validate()
        return True

    def reactivate_student(self, student_id):
        student = self.get_student(student_id)
        if student is None:
            return False
        program = self.get_program(student.program_id)
        if program is None or not program.active:
            return False
        student.active = True
        student.validate()
        return True

    # ------------------------------------------------------------------
    # Professor
    # ------------------------------------------------------------------

    def create_professor(self, professor):
        if not isinstance(professor, Professor):
            raise TypeError("professor must be a Professor instance")
        if self._entity_exists(self.professors, "professor_id", professor.professor_id):
            return False
        if professor.faculty_id and not self._entity_exists(self.faculties, "faculty_id", professor.faculty_id):
            return False
        faculty = self.get_faculty(professor.faculty_id) if professor.faculty_id else None
        if faculty is not None and not faculty.active:
            return False
        professor.validate()
        self.professors.insert(professor)
        return True

    def get_professor(self, professor_id):
        return self._find_by_id(self.professors, "professor_id", professor_id)

    def list_professors(self):
        return self.professors

    def search_professor(self, full_name):
        return self.professors.find_by("full_name", full_name)

    def update_professor(self, professor_id, **updates):
        professor = self.get_professor(professor_id)
        if professor is None:
            return False
        for key, value in updates.items():
            if hasattr(professor, key):
                setattr(professor, key, value)
        if professor.faculty_id and not self._entity_exists(self.faculties, "faculty_id", professor.faculty_id):
            return False
        professor.validate()
        return True

    def delete_professor(self, professor_id):
        professor = self.get_professor(professor_id)
        if professor is None:
            return False
        return self.professors.remove(professor)

    def deactivate_professor(self, professor_id):
        professor = self.get_professor(professor_id)
        if professor is None:
            return False
        professor.active = False
        professor.validate()
        return True

    def reactivate_professor(self, professor_id):
        professor = self.get_professor(professor_id)
        if professor is None:
            return False
        if professor.faculty_id and not self._entity_exists(self.faculties, "faculty_id", professor.faculty_id):
            return False
        faculty = self.get_faculty(professor.faculty_id) if professor.faculty_id else None
        if faculty is not None and not faculty.active:
            return False
        professor.active = True
        professor.validate()
        return True

    # ------------------------------------------------------------------
    # Administrative
    # ------------------------------------------------------------------

    def create_administrative(self, administrative):
        if not isinstance(administrative, Administrative):
            raise TypeError("administrative must be an Administrative instance")
        if self._entity_exists(self.administrative_staff, "administrative_id", administrative.administrative_id):
            return False
        administrative.validate()
        self.administrative_staff.insert(administrative)
        return True

    def get_administrative(self, administrative_id):
        return self._find_by_id(self.administrative_staff, "administrative_id", administrative_id)

    def list_administrative_staff(self):
        return self.administrative_staff

    def search_administrative(self, full_name):
        return self.administrative_staff.find_by("full_name", full_name)

    def update_administrative(self, administrative_id, **updates):
        administrative = self.get_administrative(administrative_id)
        if administrative is None:
            return False
        for key, value in updates.items():
            if hasattr(administrative, key):
                setattr(administrative, key, value)
        administrative.validate()
        return True

    def delete_administrative(self, administrative_id):
        administrative = self.get_administrative(administrative_id)
        if administrative is None:
            return False
        return self.administrative_staff.remove(administrative)

    def deactivate_administrative(self, administrative_id):
        administrative = self.get_administrative(administrative_id)
        if administrative is None:
            return False
        administrative.active = False
        administrative.validate()
        return True

    def reactivate_administrative(self, administrative_id):
        administrative = self.get_administrative(administrative_id)
        if administrative is None:
            return False
        administrative.active = True
        administrative.validate()
        return True

    # ------------------------------------------------------------------
    # Enrollment
    # ------------------------------------------------------------------

    def enroll_student(self, student_id, course_id, academic_period, enrollment_id=None):
        """Creates a new academic enrollment with validation for state, capacity and duplicates."""
        student = self.get_student(student_id)
        if student is None or not student.active:
            return False

        course = self.get_course(course_id)
        if course is None or not course.active:
            return False

        program = self.get_program(student.program_id)
        if program is None or not program.active:
            return False

        if course.program_id != program.program_id:
            return False

        if course.max_capacity <= 0:
            return False

        if self._active_course_enrollment_count(course_id) >= course.max_capacity:
            return False

        if self._has_active_enrollment_for_student_course(student_id, course_id, academic_period):
            return False

        if enrollment_id is None:
            enrollment_id = self._next_id(self.enrollments, "enrollment_id")

        if self._entity_exists(self.enrollments, "enrollment_id", enrollment_id):
            return False

        enrollment = Enrollment(
            enrollment_id=enrollment_id,
            student_id=student_id,
            course_id=course_id,
            academic_period=academic_period,
            final_grade=0.0,
            status="ACTIVE",
            enrollment_date=date.today().isoformat(),
        )

        self.enrollments.insert(enrollment)
        student.enrollment_list.insert(enrollment)
        course.enrollment_list.insert(enrollment)
        return True

    def create_enrollment(self, enrollment):
        if not isinstance(enrollment, Enrollment):
            raise TypeError("enrollment must be an Enrollment instance")
        return self.enroll_student(
            student_id=enrollment.student_id,
            course_id=enrollment.course_id,
            academic_period=enrollment.academic_period,
            enrollment_id=enrollment.enrollment_id,
        )

    def cancel_enrollment(self, enrollment_id):
        """Cancels an enrollment without deleting historical records."""
        enrollment = self.get_enrollment(enrollment_id)
        if enrollment is None:
            return False
        if self._safe_status(enrollment.status) in {"CANCELLED", "COMPLETED"}:
            return False
        enrollment.status = "CANCELLED"
        enrollment.validate()
        return True

    def get_enrollment(self, enrollment_id):
        return self._find_by_id(self.enrollments, "enrollment_id", enrollment_id)

    def list_enrollments(self):
        return self.enrollments

    def delete_enrollment(self, enrollment_id):
        enrollment = self.get_enrollment(enrollment_id)
        if enrollment is None:
            return False
        student = self.get_student(enrollment.student_id)
        course = self.get_course(enrollment.course_id)
        if student is not None:
            student.enrollment_list.remove(enrollment)
        if course is not None:
            course.enrollment_list.remove(enrollment)
        return self.enrollments.remove(enrollment)

    def deactivate_enrollment(self, enrollment_id):
        enrollment = self.get_enrollment(enrollment_id)
        if enrollment is None:
            return False
        enrollment.status = "INACTIVE"
        enrollment.validate()
        return True

    def reactivate_enrollment(self, enrollment_id):
        enrollment = self.get_enrollment(enrollment_id)
        if enrollment is None:
            return False
        student = self.get_student(enrollment.student_id)
        course = self.get_course(enrollment.course_id)
        if student is None or course is None:
            return False
        enrollment.status = "ACTIVE"
        enrollment.validate()
        return True

    def register_grade(self, enrollment_id, grade):
        """Validates the grade range and records the final academic grade."""
        if not isinstance(grade, (int, float)):
            return False
        if grade < 0.0 or grade > 5.0:
            return False

        enrollment = self.get_enrollment(enrollment_id)
        if enrollment is None:
            return False
        if self._safe_status(enrollment.status) not in {"ACTIVE", "CANCELLED", "COMPLETED"}:
            return False

        enrollment.final_grade = float(grade)
        enrollment.status = "COMPLETED"
        enrollment.validate()
        return True

    def calculate_student_average(self, student_id):
        """Returns the weighted average by course credits for the student."""
        student = self.get_student(student_id)
        if student is None:
            return 0.0

        weighted_total = 0.0
        credit_total = 0.0
        current = student.enrollment_list.head
        while current is not None:
            enrollment = current.data
            if not isinstance(enrollment, Enrollment):
                current = current.next
                continue
            if self._safe_status(enrollment.status) not in {"ACTIVE", "COMPLETED"}:
                current = current.next
                continue
            if not isinstance(enrollment.final_grade, (int, float)):
                current = current.next
                continue
            course = self.get_course(enrollment.course_id)
            if course is None:
                current = current.next
                continue
            weighted_total += float(enrollment.final_grade) * float(course.credits)
            credit_total += float(course.credits)
            current = current.next

        if credit_total == 0:
            return 0.0
        return weighted_total / credit_total

    def evaluate_ebra_status(self, student_id):
        """Current EBRA rule: weighted_average < configured_threshold."""
        student = self.get_student(student_id)
        if student is None:
            return {"student_id": student_id, "average": 0.0, "threshold": self.ebra_threshold, "status": "NO_DATA", "rule": self.ebra_rule}

        average = self.calculate_student_average(student_id)
        status = "EBRA" if average < self.ebra_threshold else "OK"
        return {
            "student_id": student_id,
            "average": average,
            "threshold": self.ebra_threshold,
            "status": status,
            "rule": self.ebra_rule,
        }
