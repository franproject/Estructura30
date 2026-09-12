"""Persistence helpers for the PITA academic system.

The project keeps persistence isolated from the domain models and GUI.
This package exposes the existing JSON helpers without introducing a second
storage mechanism or a new service layer.
"""

from .file_manager import (
    link_hierarchical_entities,
    load_administrative_staff,
    load_all_entities,
    load_courses,
    load_enrollments,
    load_faculties,
    load_professors,
    load_programs,
    load_students,
    save_administrative_staff,
    save_courses,
    save_enrollments,
    save_faculties,
    save_professors,
    save_programs,
    save_students,
    TransactionalSave,
    batch_save_state,
)
