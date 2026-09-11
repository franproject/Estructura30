"""Helpers to save and load entities from JSON files.

The project already uses explicit model classes and a custom linked list.
This module serializes those objects without replacing the existing architecture.
"""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
import warnings
from pathlib import Path

from models.administrative import Administrative
from models.course import Course
from models.enrollment import Enrollment
from models.faculty import Faculty
from models.linked_list import LinkedList
from models.payroll import Payroll
from models.payroll_audit import PayrollAudit
from models.payroll_novelty import PayrollNovelty
from models.payroll_period import PayrollPeriod
from models.payroll_run import PayrollRun
from models.professor import Professor
from models.program import Program
from models.student import Student

_LOAD_ISSUES: list[str] = []


def get_load_issues() -> list[str]:
    """Devuelve las incidencias de carga acumuladas desde el último reset."""
    return list(_LOAD_ISSUES)


def clear_load_issues() -> None:
    _LOAD_ISSUES.clear()


if getattr(sys, "frozen", False):
    DATA_DIRECTORY = Path(sys.executable).resolve().parent / "data"
else:
    DATA_DIRECTORY = Path(__file__).resolve().parents[2] / "data"

_LABOR_DEFAULTS = {
    "hire_date": "",
    "termination_date": "",
    "linkage_type": "",
    "employment_status": "UNKNOWN",
    "salary_type": "FIXED_MONTHLY",
    "arl_risk_class": "I",
    "social_security_config_id": "DEFAULT",
    "worked_days": 0,
    "hourly_rate": 0.0,
    "continuous_service_days": 0,
    "novelties": [],
    "bonuses": [],
    "salary_concepts": [],
    "non_salary_concepts": [],
}


def _labor_kwargs(data, entity_name):
    """Returns compatible labor data and warns when loading legacy JSON."""
    missing = [field for field in _LABOR_DEFAULTS if field not in data]
    if missing:
        warnings.warn(
            f"{entity_name} JSON lacks labor fields; explicit defaults applied: {', '.join(missing)}",
            RuntimeWarning,
            stacklevel=2,
        )
        _LOAD_ISSUES.append(
            f"{entity_name}: se aplicaron valores de nómina por defecto para campos faltantes "
            f"({', '.join(missing)}). Verifica que sean correctos."
        )
    values = {}
    for field, default in _LABOR_DEFAULTS.items():
        value = data.get(field, default)
        if field in {"novelties", "bonuses", "salary_concepts", "non_salary_concepts"}:
            value = list(value) if isinstance(value, list) else []
        values[field] = value
    return values


def _ensure_parent_directory(file_path):
    """Creates the parent folder for a data file if it does not exist."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)


def _as_list(values):
    """Normalizes a list, tuple, or custom LinkedList into a list of objects."""
    if values is None:
        return []
    if isinstance(values, LinkedList):
        result = []
        current = values.head
        while current is not None:
            result.append(current.data)
            current = current.next
        return result
    if isinstance(values, (list, tuple)):
        return list(values)
    return [values]


def _to_serializable(value):
    """Recursively converts model objects and linked lists into JSON-serializable data."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _to_serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_serializable(item) for item in value]
    if isinstance(value, LinkedList):
        items = []
        current = value.head
        while current is not None:
            items.append(_to_serializable(current.data))
            current = current.next
        return items
    if hasattr(value, "__dict__"):
        return {
            key: _to_serializable(item)
            for key, item in value.__dict__.items()
            if key not in {"next", "head", "size"}
        }
    return str(value)


def _to_linked_list(values):
    """Converts a list-like payload back into the project's custom LinkedList."""
    linked_list = LinkedList()
    for item in _as_list(values):
        linked_list.insert(item)
    return linked_list


def _model_to_dict(value):
    """Converts a model instance to a dictionary using the model's explicit API when available."""
    if value is None:
        return None
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
        if isinstance(payload, dict):
            return payload
    if hasattr(value, "__dict__"):
        return {
            key: _to_serializable(item)
            for key, item in value.__dict__.items()
            if key not in {"next", "head", "size"}
        }
    return _to_serializable(value)


def _normalize_collection(values):
    """Returns a flat list of model objects or dictionaries for JSON serialization."""
    normalized = []
    for item in _as_list(values):
        if hasattr(item, "to_dict"):
            normalized.append(_model_to_dict(item))
        else:
            normalized.append(_to_serializable(item))
    return normalized


def _save_json(file_path, payload):
    """Persists a JSON payload to disk."""
    file_path = Path(file_path)
    _ensure_parent_directory(file_path)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=file_path.parent,
            prefix=f".{file_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            tmp_path = Path(file.name)
            json.dump(payload, file, indent=2, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp_path, file_path)
        tmp_path = None
        return True
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _backup_corrupt_file(file_path):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = file_path.with_name(
        f"{file_path.stem}.corrupto-{timestamp}{file_path.suffix}"
    )
    shutil.copy2(file_path, backup_path)
    return backup_path


def _load_json(file_path):
    """Loads a JSON payload from disk. Returns an empty list for empty or missing files."""
    file_path = Path(file_path)
    if not file_path.exists():
        return []

    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError:
        backup_path = _backup_corrupt_file(file_path)
        _LOAD_ISSUES.append(
            f"No se pudo leer {file_path.name}: el archivo estaba corrupto o ilegible. "
            f"Se respaldó como {backup_path.name}."
        )
        return []

    if not raw_text or not raw_text.strip():
        backup_path = _backup_corrupt_file(file_path)
        _LOAD_ISSUES.append(
            f"No se pudo leer {file_path.name}: el archivo estaba corrupto o ilegible. "
            f"Se respaldó como {backup_path.name}."
        )
        return []

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        backup_path = _backup_corrupt_file(file_path)
        _LOAD_ISSUES.append(
            f"No se pudo leer {file_path.name}: el archivo estaba corrupto o ilegible. "
            f"Se respaldó como {backup_path.name}."
        )
        return []

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]

    _LOAD_ISSUES.append(
        f"El archivo {file_path.name} contiene un tipo JSON inesperado: {type(data).__name__}."
    )
    return []


def _faculty_to_dict(faculty):
    return {
        "faculty_id": getattr(faculty, "faculty_id", 0),
        "name": getattr(faculty, "name", ""),
        "dean": getattr(faculty, "dean", ""),
        "creation_date": getattr(faculty, "creation_date", ""),
        "active": getattr(faculty, "active", False),
        "program_list": _to_serializable(getattr(faculty, "program_list", None)),
    }


def _faculty_from_dict(data):
    return Faculty(
        faculty_id=data.get("faculty_id", 0),
        name=data.get("name", ""),
        dean=data.get("dean", ""),
        creation_date=data.get("creation_date", ""),
        active=data.get("active", False),
        program_list=_to_linked_list(data.get("program_list", [])),
    )


def _program_to_dict(program):
    return {
        "program_id": getattr(program, "program_id", 0),
        "name": getattr(program, "name", ""),
        "faculty_id": getattr(program, "faculty_id", 0),
        "program_director": getattr(program, "program_director", ""),
        "level": getattr(program, "level", ""),
        "modality": getattr(program, "modality", ""),
        "program_type": getattr(program, "program_type", "Otro"),
        "active": getattr(program, "active", False),
        "course_list": _to_serializable(getattr(program, "course_list", None)),
        "student_list": _to_serializable(getattr(program, "student_list", None)),
    }


def _program_from_dict(data):
    return Program(
        program_id=data.get("program_id", 0),
        name=data.get("name", ""),
        faculty_id=data.get("faculty_id", 0),
        program_director=data.get("program_director", ""),
        level=data.get("level", ""),
        modality=data.get("modality", ""),
        program_type=data.get("program_type", "Otro"),
        active=data.get("active", False),
        course_list=_to_linked_list(data.get("course_list", [])),
        student_list=_to_linked_list(data.get("student_list", [])),
    )


def _course_to_dict(course):
    return {
        "course_id": getattr(course, "course_id", 0),
        "name": getattr(course, "name", ""),
        "program_id": getattr(course, "program_id", 0),
        "credits": getattr(course, "credits", 0),
        "curriculum_semester": getattr(course, "curriculum_semester", 0),
        "assigned_professor_id": getattr(course, "assigned_professor_id", 0),
        "max_capacity": getattr(course, "max_capacity", 0),
        "active": getattr(course, "active", False),
        "enrollment_list": _to_serializable(getattr(course, "enrollment_list", None)),
    }


def _course_from_dict(data):
    return Course(
        course_id=data.get("course_id", 0),
        name=data.get("name", ""),
        program_id=data.get("program_id", 0),
        credits=data.get("credits", 0),
        curriculum_semester=data.get("curriculum_semester", 0),
        assigned_professor_id=data.get("assigned_professor_id", 0),
        max_capacity=data.get("max_capacity", 0),
        active=data.get("active", False),
        enrollment_list=_to_linked_list(data.get("enrollment_list", [])),
    )


def _student_to_dict(student):
    return {
        "student_id": getattr(student, "student_id", 0),
        "full_name": getattr(student, "full_name", ""),
        "document_type": getattr(student, "document_type", ""),
        "document_number": getattr(student, "document_number", ""),
        "birth_date": getattr(student, "birth_date", ""),
        "email": getattr(student, "email", ""),
        "phone": getattr(student, "phone", ""),
        "program_id": getattr(student, "program_id", 0),
        "current_semester": getattr(student, "current_semester", 0),
        "status": getattr(student, "status", ""),
        "cumulative_average": getattr(student, "cumulative_average", 0.0),
        "active": getattr(student, "active", False),
        "enrollment_list": _to_serializable(getattr(student, "enrollment_list", None)),
    }


def _student_from_dict(data):
    return Student(
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
        enrollment_list=_to_linked_list(data.get("enrollment_list", [])),
    )


def _professor_to_dict(professor):
    return {
        "professor_id": getattr(professor, "professor_id", 0),
        "full_name": getattr(professor, "full_name", ""),
        "document_type": getattr(professor, "document_type", ""),
        "document_number": getattr(professor, "document_number", ""),
        "email": getattr(professor, "email", ""),
        "phone": getattr(professor, "phone", ""),
        "faculty_id": getattr(professor, "faculty_id", 0),
        "employment_type": getattr(professor, "employment_type", ""),
        "category_rank": getattr(professor, "category_rank", ""),
        "academic_title": getattr(professor, "academic_title", ""),
        "years_of_qualified_experience": getattr(professor, "years_of_qualified_experience", 0),
        "dedication": getattr(professor, "dedication", ""),
        "lecture_hours": getattr(professor, "lecture_hours", 0),
        "managerial_role": getattr(professor, "managerial_role", ""),
        "category_score": getattr(professor, "category_score", 0.0),
        "title_score": getattr(professor, "title_score", 0.0),
        "experience_score": getattr(professor, "experience_score", 0.0),
        "productivity_score": getattr(professor, "productivity_score", 0.0),
        "academic_management_score": getattr(professor, "academic_management_score", 0.0),
        "total_points": getattr(professor, "total_points", 0.0),
        "point_value": getattr(professor, "point_value", 0.0),
        "base_monthly_salary": getattr(professor, "base_monthly_salary", 0.0),
        "health_discount": getattr(professor, "health_discount", 0.0),
        "pension_discount": getattr(professor, "pension_discount", 0.0),
        "severance_provision": getattr(professor, "severance_provision", 0.0),
        "bonus_provision": getattr(professor, "bonus_provision", 0.0),
        "vacation_provision": getattr(professor, "vacation_provision", 0.0),
        "net_salary": getattr(professor, "net_salary", 0.0),
        "active": getattr(professor, "active", False),
        "hire_date": getattr(professor, "hire_date", ""),
        "termination_date": getattr(professor, "termination_date", ""),
        "linkage_type": getattr(professor, "linkage_type", ""),
        "employment_status": getattr(professor, "employment_status", "UNKNOWN"),
        "salary_type": getattr(professor, "salary_type", "FIXED_MONTHLY"),
        "arl_risk_class": getattr(professor, "arl_risk_class", "I"),
        "social_security_config_id": getattr(professor, "social_security_config_id", "DEFAULT"),
        "worked_days": getattr(professor, "worked_days", 0),
        "hourly_rate": getattr(professor, "hourly_rate", 0.0),
        "continuous_service_days": getattr(professor, "continuous_service_days", 0),
        "novelties": getattr(professor, "novelties", []),
        "bonuses": getattr(professor, "bonuses", []),
        "salary_concepts": getattr(professor, "salary_concepts", []),
        "non_salary_concepts": getattr(professor, "non_salary_concepts", []),
    }


def _professor_from_dict(data):
    return Professor(
        professor_id=data.get("professor_id", 0),
        full_name=data.get("full_name", ""),
        document_type=data.get("document_type", ""),
        document_number=data.get("document_number", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        faculty_id=data.get("faculty_id", 0),
        employment_type=data.get("employment_type", ""),
        category_rank=data.get("category_rank", ""),
        academic_title=data.get("academic_title", ""),
        years_of_qualified_experience=data.get("years_of_qualified_experience", 0),
        dedication=data.get("dedication", ""),
        lecture_hours=data.get("lecture_hours", 0),
        managerial_role=data.get("managerial_role", ""),
        category_score=data.get("category_score", 0.0),
        title_score=data.get("title_score", 0.0),
        experience_score=data.get("experience_score", 0.0),
        productivity_score=data.get("productivity_score", 0.0),
        academic_management_score=data.get("academic_management_score", 0.0),
        total_points=data.get("total_points", 0.0),
        point_value=data.get("point_value", 0.0),
        base_monthly_salary=data.get("base_monthly_salary", 0.0),
        health_discount=data.get("health_discount", 0.0),
        pension_discount=data.get("pension_discount", 0.0),
        severance_provision=data.get("severance_provision", 0.0),
        bonus_provision=data.get("bonus_provision", 0.0),
        vacation_provision=data.get("vacation_provision", 0.0),
        net_salary=data.get("net_salary", 0.0),
        active=data.get("active", False),
        **_labor_kwargs(data, "Professor"),
    )


def _administrative_to_dict(administrative):
    return {
        "administrative_id": getattr(administrative, "administrative_id", 0),
        "full_name": getattr(administrative, "full_name", ""),
        "document_type": getattr(administrative, "document_type", ""),
        "document_number": getattr(administrative, "document_number", ""),
        "email": getattr(administrative, "email", ""),
        "phone": getattr(administrative, "phone", ""),
        "position": getattr(administrative, "position", ""),
        "category": getattr(administrative, "category", ""),
        "employment_type": getattr(administrative, "employment_type", ""),
        "base_salary": getattr(administrative, "base_salary", 0.0),
        "health_discount": getattr(administrative, "health_discount", 0.0),
        "pension_discount": getattr(administrative, "pension_discount", 0.0),
        "severance_provision": getattr(administrative, "severance_provision", 0.0),
        "holiday_bonus": getattr(administrative, "holiday_bonus", 0.0),
        "vacation_provision": getattr(administrative, "vacation_provision", 0.0),
        "net_salary": getattr(administrative, "net_salary", 0.0),
        "active": getattr(administrative, "active", False),
        "hire_date": getattr(administrative, "hire_date", ""),
        "termination_date": getattr(administrative, "termination_date", ""),
        "linkage_type": getattr(administrative, "linkage_type", ""),
        "employment_status": getattr(administrative, "employment_status", "UNKNOWN"),
        "salary_type": getattr(administrative, "salary_type", "FIXED_MONTHLY"),
        "arl_risk_class": getattr(administrative, "arl_risk_class", "I"),
        "social_security_config_id": getattr(administrative, "social_security_config_id", "DEFAULT"),
        "worked_days": getattr(administrative, "worked_days", 0),
        "hourly_rate": getattr(administrative, "hourly_rate", 0.0),
        "continuous_service_days": getattr(administrative, "continuous_service_days", 0),
        "novelties": getattr(administrative, "novelties", []),
        "bonuses": getattr(administrative, "bonuses", []),
        "salary_concepts": getattr(administrative, "salary_concepts", []),
        "non_salary_concepts": getattr(administrative, "non_salary_concepts", []),
    }


def _administrative_from_dict(data):
    return Administrative(
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
        **_labor_kwargs(data, "Administrative"),
    )


def _payroll_to_dict(payroll):
    return {
        "description": getattr(payroll, "description", ""),
    }


def _payroll_from_dict(data):
    return Payroll(description=data.get("description", ""))


def _enrollment_to_dict(enrollment):
    return {
        "enrollment_id": getattr(enrollment, "enrollment_id", 0),
        "student_id": getattr(enrollment, "student_id", 0),
        "course_id": getattr(enrollment, "course_id", 0),
        "academic_period": getattr(enrollment, "academic_period", ""),
        "final_grade": getattr(enrollment, "final_grade", 0.0),
        "status": getattr(enrollment, "status", ""),
        "enrollment_date": getattr(enrollment, "enrollment_date", ""),
    }


def _enrollment_from_dict(data):
    return Enrollment(
        enrollment_id=data.get("enrollment_id", 0),
        student_id=data.get("student_id", 0),
        course_id=data.get("course_id", 0),
        academic_period=data.get("academic_period", ""),
        final_grade=data.get("final_grade", 0.0),
        status=data.get("status", ""),
        enrollment_date=data.get("enrollment_date", ""),
    )


def save_faculties(faculties, file_path=DATA_DIRECTORY / "faculties.json"):
    """Guardará las facultades en formato JSON."""
    try:
        return _save_json(file_path, [_faculty_to_dict(item) for item in _as_list(faculties)])
    except (TypeError, ValueError, OSError):
        return False


def load_faculties(file_path=DATA_DIRECTORY / "faculties.json"):
    """Cargará las facultades desde un archivo JSON."""
    try:
        faculties = []
        for item in _load_json(file_path):
            if not isinstance(item, dict):
                continue
            faculties.append(_faculty_from_dict(item))
        return faculties
    except (TypeError, ValueError, OSError):
        return []


def save_programs(programs, file_path=DATA_DIRECTORY / "programs.json"):
    """Guardará los programas en formato JSON."""
    try:
        return _save_json(file_path, [_program_to_dict(item) for item in _as_list(programs)])
    except (TypeError, ValueError, OSError):
        return False


def load_programs(file_path=DATA_DIRECTORY / "programs.json"):
    """Cargará los programas desde un archivo JSON."""
    try:
        programs = []
        for item in _load_json(file_path):
            if not isinstance(item, dict):
                continue
            programs.append(_program_from_dict(item))
        return programs
    except (TypeError, ValueError, OSError):
        return []


def save_courses(courses, file_path=DATA_DIRECTORY / "courses.json"):
    """Guardará los cursos en formato JSON."""
    try:
        return _save_json(file_path, [_course_to_dict(item) for item in _as_list(courses)])
    except (TypeError, ValueError, OSError):
        return False


def load_courses(file_path=DATA_DIRECTORY / "courses.json"):
    """Cargará los cursos desde un archivo JSON."""
    try:
        courses = []
        for item in _load_json(file_path):
            if not isinstance(item, dict):
                continue
            courses.append(_course_from_dict(item))
        return courses
    except (TypeError, ValueError, OSError):
        return []


def save_students(students, file_path=DATA_DIRECTORY / "students.json"):
    """Guardará los estudiantes en formato JSON."""
    try:
        return _save_json(file_path, [_student_to_dict(item) for item in _as_list(students)])
    except (TypeError, ValueError, OSError):
        return False


def load_students(file_path=DATA_DIRECTORY / "students.json"):
    """Cargará los estudiantes desde un archivo JSON."""
    try:
        students = []
        for item in _load_json(file_path):
            if not isinstance(item, dict):
                continue
            students.append(_student_from_dict(item))
        return students
    except (TypeError, ValueError, OSError):
        return []


def save_professors(professors, file_path=DATA_DIRECTORY / "professors.json"):
    """Guardará los profesores en formato JSON."""
    try:
        return _save_json(file_path, [_professor_to_dict(item) for item in _as_list(professors)])
    except (TypeError, ValueError, OSError):
        return False


def load_professors(file_path=DATA_DIRECTORY / "professors.json"):
    """Cargará los profesores desde un archivo JSON."""
    try:
        professors = []
        for item in _load_json(file_path):
            if not isinstance(item, dict):
                continue
            professors.append(_professor_from_dict(item))
        return professors
    except (TypeError, ValueError, OSError):
        return []


def save_administrative_staff(staff, file_path=DATA_DIRECTORY / "administrative_staff.json"):
    """Guardará el personal administrativo en formato JSON."""
    try:
        return _save_json(file_path, [_administrative_to_dict(item) for item in _as_list(staff)])
    except (TypeError, ValueError, OSError):
        return False


def load_administrative_staff(file_path=DATA_DIRECTORY / "administrative_staff.json"):
    """Cargará el personal administrativo desde un archivo JSON."""
    try:
        staff = []
        for item in _load_json(file_path):
            if not isinstance(item, dict):
                continue
            staff.append(_administrative_from_dict(item))
        return staff
    except (TypeError, ValueError, OSError):
        return []


def save_payroll(payroll, file_path=DATA_DIRECTORY / "payroll.json"):
    """Guardará la nómina en formato JSON."""
    try:
        return _save_json(file_path, [_payroll_to_dict(item) for item in _as_list(payroll)])
    except (TypeError, ValueError, OSError):
        return False


def load_payroll(file_path=DATA_DIRECTORY / "payroll.json"):
    """Cargará la nómina desde un archivo JSON."""
    try:
        payroll = []
        for item in _load_json(file_path):
            if not isinstance(item, dict):
                continue
            payroll.append(_payroll_from_dict(item))
        return payroll
    except (TypeError, ValueError, OSError):
        return []


def save_enrollments(enrollments, file_path=DATA_DIRECTORY / "enrollments.json"):
    """Guardará las matrículas en formato JSON."""
    try:
        return _save_json(file_path, [_enrollment_to_dict(item) for item in _as_list(enrollments)])
    except (TypeError, ValueError, OSError):
        return False


def load_enrollments(file_path=DATA_DIRECTORY / "enrollments.json"):
    """Cargará las matrículas desde un archivo JSON."""
    try:
        enrollments = []
        for item in _load_json(file_path):
            if not isinstance(item, dict):
                continue
            enrollments.append(_enrollment_from_dict(item))
        return enrollments
    except (TypeError, ValueError, OSError):
        return []


def _save_payroll_collection(values, file_path):
    return _save_json(file_path, [_to_serializable(item.to_dict() if hasattr(item, "to_dict") else item) for item in _as_list(values)])


def _load_payroll_collection(file_path, model_cls):
    result = []
    for item in _load_json(file_path):
        if isinstance(item, dict):
            result.append(model_cls.from_dict(item))
    return result


def save_payroll_periods(periods, file_path=DATA_DIRECTORY / "payroll_periods.json"):
    try:
        return _save_payroll_collection(periods, file_path)
    except (TypeError, ValueError, OSError):
        return False


def load_payroll_periods(file_path=DATA_DIRECTORY / "payroll_periods.json"):
    try:
        return _load_payroll_collection(file_path, PayrollPeriod)
    except (TypeError, ValueError, OSError):
        return []


def save_payroll_runs(runs, file_path=DATA_DIRECTORY / "payroll_runs.json"):
    try:
        return _save_payroll_collection(runs, file_path)
    except (TypeError, ValueError, OSError):
        return False


def load_payroll_runs(file_path=DATA_DIRECTORY / "payroll_runs.json"):
    try:
        return _load_payroll_collection(file_path, PayrollRun)
    except (TypeError, ValueError, OSError):
        return []


def save_payroll_details(details, file_path=DATA_DIRECTORY / "payroll_details.json"):
    try:
        return _save_json(file_path, [_to_serializable(item) for item in _as_list(details)])
    except (TypeError, ValueError, OSError):
        return False


def load_payroll_details(file_path=DATA_DIRECTORY / "payroll_details.json"):
    try:
        return _load_json(file_path)
    except (TypeError, ValueError, OSError):
        return []


def save_payroll_novelties(novelties, file_path=DATA_DIRECTORY / "payroll_novelties.json"):
    try:
        return _save_payroll_collection(novelties, file_path)
    except (TypeError, ValueError, OSError):
        return False


def load_payroll_novelties(file_path=DATA_DIRECTORY / "payroll_novelties.json"):
    try:
        return _load_payroll_collection(file_path, PayrollNovelty)
    except (TypeError, ValueError, OSError):
        return []


def save_payroll_audit(audits, file_path=DATA_DIRECTORY / "payroll_audit.json"):
    try:
        return _save_payroll_collection(audits, file_path)
    except (TypeError, ValueError, OSError):
        return False


def load_payroll_audit(file_path=DATA_DIRECTORY / "payroll_audit.json"):
    try:
        return _load_payroll_collection(file_path, PayrollAudit)
    except (TypeError, ValueError, OSError):
        return []


def ask_load_existing_data():
    """Pregunta si se deben cargar los archivos existentes al iniciar."""
    answer = input("Do you want to load existing data? (y/n): ")
    return answer.strip().lower() in {"y", "yes"}
