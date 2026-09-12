"""Módulo centralizado de localización y etiquetas institucionales en español para NexoCampus."""
from types import MappingProxyType
from typing import Any, NamedTuple, Optional


class EntityInfo(NamedTuple):
    """Metadatos lingüísticos y de presentación de una entidad de negocio."""

    key: str
    name: str
    plural: str
    gender: str  # 'f' (femenino) o 'm' (masculino)
    article_def: str  # 'la' / 'el'
    article_indef: str  # 'una' / 'un'
    new_button_label: str  # '+ Nueva Facultad' / '+ Nuevo Curso'
    create_button_label: str  # '+ Crear Facultad' / '+ Crear Curso'
    created_message: str  # 'Facultad creada exitosamente.'
    updated_message: str  # 'Facultad actualizada exitosamente.'
    deleted_message: str  # 'Facultad eliminada exitosamente.'
    empty_hint: str  # 'Presiona el botón '+ Nueva Facultad'...'


_RAW_ENTITIES = {
    "faculty": EntityInfo(
        key="faculty",
        name="Facultad",
        plural="Facultades",
        gender="f",
        article_def="la",
        article_indef="una",
        new_button_label="+ Nueva Facultad",
        create_button_label="+ Crear Facultad",
        created_message="Facultad creada exitosamente.",
        updated_message="Facultad actualizada exitosamente.",
        deleted_message="Facultad eliminada exitosamente.",
        empty_hint="Presiona el botón '+ Nueva Facultad' para añadir tu primer registro de facultad.",
    ),
    "program": EntityInfo(
        key="program",
        name="Programa",
        plural="Programas",
        gender="m",
        article_def="el",
        article_indef="un",
        new_button_label="+ Nuevo Programa",
        create_button_label="+ Crear Programa",
        created_message="Programa creado exitosamente.",
        updated_message="Programa actualizado exitosamente.",
        deleted_message="Programa eliminado exitosamente.",
        empty_hint="Presiona el botón '+ Nuevo Programa' para añadir tu primer registro de programa.",
    ),
    "course": EntityInfo(
        key="course",
        name="Curso",
        plural="Cursos",
        gender="m",
        article_def="el",
        article_indef="un",
        new_button_label="+ Nuevo Curso",
        create_button_label="+ Crear Curso",
        created_message="Curso creado exitosamente.",
        updated_message="Curso actualizado exitosamente.",
        deleted_message="Curso eliminado exitosamente.",
        empty_hint="Presiona el botón '+ Nuevo Curso' para añadir tu primer registro de curso.",
    ),
    "student": EntityInfo(
        key="student",
        name="Estudiante",
        plural="Estudiantes",
        gender="m",
        article_def="el",
        article_indef="un",
        new_button_label="+ Nuevo Estudiante",
        create_button_label="+ Crear Estudiante",
        created_message="Estudiante creado exitosamente.",
        updated_message="Estudiante actualizado exitosamente.",
        deleted_message="Estudiante eliminado exitosamente.",
        empty_hint="Presiona el botón '+ Nuevo Estudiante' para añadir tu primer registro de estudiante.",
    ),
    "professor": EntityInfo(
        key="professor",
        name="Docente",
        plural="Docentes",
        gender="m",
        article_def="el",
        article_indef="un",
        new_button_label="+ Nuevo Docente",
        create_button_label="+ Crear Docente",
        created_message="Docente creado exitosamente.",
        updated_message="Docente actualizado exitosamente.",
        deleted_message="Docente eliminado exitosamente.",
        empty_hint="Presiona el botón '+ Nuevo Docente' para añadir tu primer registro de docente.",
    ),
    "administrative": EntityInfo(
        key="administrative",
        name="Personal Administrativo",
        plural="Personal Administrativo",
        gender="m",
        article_def="el",
        article_indef="un",
        new_button_label="+ Nuevo Personal Administrativo",
        create_button_label="+ Crear Personal Administrativo",
        created_message="Personal Administrativo creado exitosamente.",
        updated_message="Personal Administrativo actualizado exitosamente.",
        deleted_message="Personal Administrativo eliminado exitosamente.",
        empty_hint="Presiona el botón '+ Nuevo Personal Administrativo' para añadir tu primer registro de personal administrativo.",
    ),
    "enrollment": EntityInfo(
        key="enrollment",
        name="Matrícula",
        plural="Matrículas",
        gender="f",
        article_def="la",
        article_indef="una",
        new_button_label="+ Nueva Matrícula",
        create_button_label="+ Crear Matrícula",
        created_message="Matrícula creada exitosamente.",
        updated_message="Matrícula actualizada exitosamente.",
        deleted_message="Matrícula eliminada exitosamente.",
        empty_hint="Presiona el botón '+ Nueva Matrícula' para añadir tu primer registro de matrícula.",
    ),
}

# Alias comunes plurales y de backend
_ENTITY_ALIASES = {
    "faculties": "faculty",
    "programs": "program",
    "courses": "course",
    "students": "student",
    "professors": "professor",
    "administrative_staff": "administrative",
    "administrativos": "administrative",
    "enrollments": "enrollment",
    "inscripciones": "enrollment",
    "inscripcion": "enrollment",
}

for _alias, _target in _ENTITY_ALIASES.items():
    _RAW_ENTITIES[_alias] = _RAW_ENTITIES[_target]

ENTITIES = MappingProxyType(_RAW_ENTITIES)

_RAW_PAYROLL_STATUSES = {
    "OPEN": "Abierto",
    "CALCULATED": "Liquidado",
    "APPROVED": "Aprobado",
    "CLOSED": "Cerrado",
    "ABIERTO": "Abierto",
    "LIQUIDADO": "Liquidado",
    "APROBADO": "Aprobado",
    "CERRADO": "Cerrado",
}

PAYROLL_STATUSES = MappingProxyType(_RAW_PAYROLL_STATUSES)

_RAW_EMPLOYEE_TYPES = {
    "Professor": "Docente",
    "Administrative": "Personal Administrativo",
    "Docente": "Docente",
    "Profesor": "Docente",
    "Personal Administrativo": "Personal Administrativo",
    "Administrativo": "Personal Administrativo",
    "ALL": "Todos los tipos",
    "Todos": "Todos los tipos",
}

EMPLOYEE_TYPES = MappingProxyType(_RAW_EMPLOYEE_TYPES)

_RAW_ACRONYMS = {
    "EBRA": "EBRA — Estudiantes en Riesgo Académico (bajo rendimiento)",
    "IBC": "IBC — Ingreso Base de Cotización (base para aportes a seguridad social)",
    "CST": "CST — Código Sustantivo del Trabajo (régimen laboral ordinario)",
}

ACRONYMS = MappingProxyType(_RAW_ACRONYMS)


def get_entity_info(key: str) -> EntityInfo:
    """Retorna la información de localización para una clave de entidad.
    
    Si la clave no se encuentra, genera un EntityInfo genérico en mayúscula
    respetando el formato estándar.
    """
    normalized = str(key).strip().lower()
    if normalized in ENTITIES:
        return ENTITIES[normalized]
    
    # Fallback genérico gramaticalmente seguro
    title = str(key).capitalize()
    return EntityInfo(
        key=normalized,
        name=title,
        plural=f"{title}s",
        gender="m",
        article_def="el",
        article_indef="un",
        new_button_label=f"+ Nuevo {title}",
        create_button_label=f"+ Crear {title}",
        created_message=f"{title} creado exitosamente.",
        updated_message=f"{title} actualizado exitosamente.",
        deleted_message=f"{title} eliminado exitosamente.",
        empty_hint=f"Presiona el botón '+ Nuevo {title}' para añadir tu primer registro de {normalized}.",
    )


def get_entity_label(key: str) -> str:
    """Retorna el nombre institucional legible de la entidad (ej. 'Facultad')."""
    return get_entity_info(key).name


def get_entity_new_label(key: str) -> str:
    """Retorna la etiqueta del botón de creación con género correcto (ej. '+ Nueva Facultad')."""
    return get_entity_info(key).new_button_label


def get_entity_create_label(key: str) -> str:
    """Retorna la etiqueta del botón de crear en estado vacío (ej. '+ Crear Facultad')."""
    return get_entity_info(key).create_button_label


def get_entity_created_message(key: str) -> str:
    """Retorna el mensaje de confirmación de creación (ej. 'Facultad creada exitosamente.')."""
    return get_entity_info(key).created_message


def get_payroll_status_label(status: Any) -> str:
    """Traduce un estado de período o ejecución de nómina al español institucional."""
    if status is None:
        return "Sin período"
    raw = getattr(status, "value", status)
    raw_str = str(raw).strip().upper()
    return PAYROLL_STATUSES.get(raw_str, str(raw))


def get_employee_type_label(emp_type: str) -> str:
    """Traduce el tipo de empleado al español institucional."""
    if not emp_type:
        return ""
    raw_str = str(emp_type).strip()
    return EMPLOYEE_TYPES.get(raw_str, raw_str)


def get_acronym_tooltip(acronym: str) -> str:
    """Retorna la descripción detallada para tooltips de un acrónimo."""
    key = str(acronym).strip().upper()
    return ACRONYMS.get(key, f"{acronym} — Término institucional")

