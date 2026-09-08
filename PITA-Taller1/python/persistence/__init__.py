"""Persistence helpers for the PITA academic system.

The project keeps persistence isolated from the domain models and GUI.
This package exposes the existing JSON helpers without introducing a second
storage mechanism or a new service layer.
"""

from .file_manager import (
    ask_load_existing_data,
    load_administrative_staff,
    load_courses,
    load_enrollments,
    load_faculties,
    load_payroll,
    load_professors,
    load_programs,
    load_students,
    save_administrative_staff,
    save_courses,
    save_enrollments,
    save_faculties,
    save_payroll,
    save_professors,
    save_programs,
    save_students,
)
