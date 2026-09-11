"""Ventana principal de la aplicación NexoCampus."""
import logging
import os
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QStackedWidget,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from models.administrative import Administrative
from models.course import Course
from models.enrollment import Enrollment
from models.faculty import Faculty
from models.linked_list import LinkedList
from models.professor import Professor
from models.program import Program
from models.student import Student
from persistence.file_manager import (
    load_administrative_staff,
    load_courses,
    load_enrollments,
    load_faculties,
    load_professors,
    load_programs,
    load_students,
    load_payroll_periods,
    load_payroll_runs,
    load_payroll_novelties,
    load_payroll_audit,
    clear_load_issues,
    get_load_issues,
    batch_save_state,
    DATA_DIRECTORY,
)
from services.entity_manager import EntityManager

from typing import Any, Optional

from .components.header import TopHeader
from .components.sidebar import Sidebar
from .pages.crud_page import CrudPage, _normalize_text
from .pages.dashboard_page import DashboardPage
from .pages.payroll_page import PayrollPage
from .pages.reports_page import ReportsPage


class MainWindow(QMainWindow):
    """Ventana principal moderna de NexoCampus (PySide6 + QSS)."""

    def __init__(self, manager: Optional[EntityManager] = None):
        super().__init__()
        self.setWindowTitle("NexoCampus | Gestión Universitaria")
        self.resize(1366, 768)
        self.setMinimumSize(960, 600)

        self.manager = manager if manager is not None else EntityManager()
        self._pages = {}
        self._load_styles()
        self._build_ui()
        if manager is None:
            try:
                self._load_state()
            except Exception as exc:
                QMessageBox.critical(self, "Error al iniciar", str(exc))

    def _load_styles(self):
        qss_path = os.path.join(os.path.dirname(__file__), "styles", "app.qss")
        try:
            with open(qss_path, encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except OSError:
            pass

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.navigate_requested.connect(self._navigate)
        self.sidebar.save_requested.connect(self._save_state)
        self.sidebar.reload_requested.connect(self._reload_state)
        root.addWidget(self.sidebar)

        # Right Panel (Header + Scroll Area con contenido)
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.header = TopHeader(manager=self.manager, parent=self)
        self.header.search_requested.connect(self._handle_global_search)
        self.header.navigate_requested.connect(self._navigate)
        right_layout.addWidget(self.header)

        # Contenedor del área de contenido principal envuelto en QScrollArea
        self.stack = QStackedWidget()
        self.stack.setObjectName("mainStack")

        self.content_scroll_area = QScrollArea()
        self.content_scroll_area.setObjectName("mainContentScrollArea")
        self.content_scroll_area.setWidgetResizable(True)
        self.content_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.content_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.content_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.content_scroll_area.setWidget(self.stack)

        right_layout.addWidget(self.content_scroll_area, stretch=1)

        root.addWidget(right_panel, stretch=1)

        # Registrar páginas
        self._add_pages()
        self.sidebar.set_active_page("Dashboard")
        self.header.update_alerts(self.manager)

    def _add_pages(self):
        # 1. Dashboard
        dashboard = DashboardPage(self.manager, self._navigate)
        self._register_page("Dashboard", dashboard)

        # 2. Facultades
        self._register_page(
            "Facultades",
            CrudPage(
                title="Facultades",
                subtitle="Estructura académica e institucional",
                manager=self.manager,
                collection_name="faculties",
                model_cls=Faculty,
                id_field="faculty_id",
                fields=(
                    ("faculty_id", "ID Facultad", "int"),
                    ("name", "Nombre", "text"),
                    ("dean", "Decano", "text"),
                    ("creation_date", "Fecha Creación", "text"),
                    ("active", "Estado Activo", "bool"),
                ),
                columns=("ID", "Nombre", "Decano", "Fecha Creación", "Estado"),
                row_builder=lambda x: (x.faculty_id, x.name, x.dean, x.creation_date, "Activo" if x.active else "Inactivo"),
                operation_name="faculty",
            ),
        )

        # 3. Programas
        self._register_page(
            "Programas",
            CrudPage(
                title="Programas Académicos",
                subtitle="Oferta académica universitaria",
                manager=self.manager,
                collection_name="programs",
                model_cls=Program,
                id_field="program_id",
                fields=(
                    ("program_id", "ID Programa", "int"),
                    ("name", "Nombre", "text"),
                    (
                        "faculty_id",
                        "Facultad",
                        "relation",
                        lambda: [
                            (f.faculty_id, f"{f.name} (#{f.faculty_id})")
                            for f in self.manager.faculties
                            if getattr(f, "active", True)
                        ],
                    ),
                    ("program_director", "Director", "text"),
                    ("level", "Nivel", "text"),
                    ("modality", "Modalidad", "text"),
                    ("program_type", "Tipo", "text"),
                    ("active", "Estado Activo", "bool"),
                ),
                columns=("ID", "Nombre", "Director", "Facultad", "Modalidad", "Estado"),
                row_builder=lambda x: (
                    x.program_id,
                    x.name,
                    x.program_director,
                    getattr(self.manager.get_faculty(x.faculty_id), "name", x.faculty_id),
                    x.modality,
                    "Activo" if x.active else "Inactivo",
                ),
                operation_name="program",
            ),
        )

        # 4. Cursos
        self._register_page(
            "Cursos",
            CrudPage(
                title="Cursos y Asignaturas",
                subtitle="Gestión del plan de estudios",
                manager=self.manager,
                collection_name="courses",
                model_cls=Course,
                id_field="course_id",
                fields=(
                    ("course_id", "ID Curso", "int"),
                    ("name", "Nombre", "text"),
                    (
                        "program_id",
                        "Programa Académico",
                        "relation",
                        lambda: [
                            (p.program_id, f"{p.name} (#{p.program_id})")
                            for p in self.manager.programs
                            if getattr(p, "active", True)
                        ],
                    ),
                    ("credits", "Créditos", "int"),
                    ("curriculum_semester", "Semestre", "int"),
                    (
                        "assigned_professor_id",
                        "Profesor Asignado",
                        "relation",
                        lambda: [
                            (p.professor_id, f"{p.full_name} (#{p.professor_id})")
                            for p in self.manager.professors
                            if getattr(p, "active", True)
                        ],
                    ),
                    ("max_capacity", "Cupo Máximo", "int"),
                    ("active", "Estado Activo", "bool"),
                ),
                columns=("ID", "Nombre", "Programa", "Créditos", "Semestre", "Cupo", "Estado"),
                row_builder=lambda x: (
                    x.course_id,
                    x.name,
                    getattr(self.manager.get_program(x.program_id), "name", x.program_id),
                    x.credits,
                    x.curriculum_semester,
                    x.max_capacity,
                    "Activo" if x.active else "Inactivo",
                ),
                operation_name="course",
            ),
        )

        # 5. Estudiantes
        self._register_page(
            "Estudiantes",
            CrudPage(
                title="Estudiantes",
                subtitle="Directorio de estudiantes matriculados",
                manager=self.manager,
                collection_name="students",
                model_cls=Student,
                id_field="student_id",
                fields=(
                    ("student_id", "ID Estudiante", "int"),
                    ("full_name", "Nombre Completo", "text"),
                    ("document_type", "Tipo Documento", "text"),
                    ("document_number", "Número Documento", "text"),
                    ("birth_date", "Fecha Nacimiento", "text"),
                    ("email", "Correo Electrónico", "text"),
                    ("phone", "Teléfono", "text"),
                    (
                        "program_id",
                        "Programa Académico",
                        "relation",
                        lambda: [
                            (p.program_id, f"{p.name} (#{p.program_id})")
                            for p in self.manager.programs
                            if getattr(p, "active", True)
                        ],
                    ),
                    ("current_semester", "Semestre Actual", "int"),
                    ("status", "Estado Académico", "text"),
                    ("active", "Estado Activo", "bool"),
                ),
                columns=("ID", "Nombre Completo", "Documento", "Programa", "Semestre", "Estado Académico", "Activo"),
                row_builder=lambda x: (
                    x.student_id,
                    x.full_name,
                    x.document_number,
                    getattr(self.manager.get_program(x.program_id), "name", x.program_id),
                    f"{x.current_semester}°",
                    x.status,
                    "Sí" if x.active else "No",
                ),
                operation_name="student",
            ),
        )

        # 6. Profesores
        self._register_page(
            "Profesores",
            CrudPage(
                title="Cuerpo Docente",
                subtitle="Gestión del equipo de profesores",
                manager=self.manager,
                collection_name="professors",
                model_cls=Professor,
                id_field="professor_id",
                fields=(
                    ("professor_id", "ID Profesor", "int"),
                    ("full_name", "Nombre Completo", "text"),
                    ("document_type", "Tipo Documento", "text"),
                    ("document_number", "Número Documento", "text"),
                    ("email", "Correo Electrónico", "text"),
                    ("phone", "Teléfono", "text"),
                    (
                        "faculty_id",
                        "Facultad",
                        "relation",
                        lambda: [
                            (f.faculty_id, f"{f.name} (#{f.faculty_id})")
                            for f in self.manager.faculties
                            if getattr(f, "active", True)
                        ],
                    ),
                    ("employment_type", "Tipo Contrato", "text"),
                    ("academic_title", "Título Académico", "text"),
                    ("arl_risk_class", "Clase de Riesgo ARL", "choice", ["I", "II", "III", "IV", "V"]),
                    ("active", "Estado Activo", "bool"),
                ),
                columns=("ID", "Nombre Completo", "Documento", "Facultad", "Contrato", "Título", "Estado"),
                row_builder=lambda x: (
                    x.professor_id,
                    x.full_name,
                    x.document_number,
                    getattr(self.manager.get_faculty(x.faculty_id), "name", x.faculty_id),
                    x.employment_type,
                    x.academic_title,
                    "Activo" if x.active else "Inactivo",
                ),
                operation_name="professor",
            ),
        )

        # 7. Administrativos
        self._register_page(
            "Administrativos",
            CrudPage(
                title="Personal Administrativo",
                subtitle="Directorio de empleados institucionales",
                manager=self.manager,
                collection_name="administrative_staff",
                model_cls=Administrative,
                id_field="administrative_id",
                fields=(
                    ("administrative_id", "ID Administrativo", "int"),
                    ("full_name", "Nombre Completo", "text"),
                    ("document_type", "Tipo Documento", "text"),
                    ("document_number", "Número Documento", "text"),
                    ("email", "Correo Electrónico", "text"),
                    ("phone", "Teléfono", "text"),
                    ("position", "Cargo", "text"),
                    ("category", "Categoría", "text"),
                    ("employment_type", "Tipo Contrato", "text"),
                    ("base_salary", "Salario Base", "float"),
                    ("arl_risk_class", "Clase de Riesgo ARL", "choice", ["I", "II", "III", "IV", "V"]),
                    ("active", "Estado Activo", "bool"),
                ),
                columns=("ID", "Nombre Completo", "Cargo", "Contrato", "Salario Base", "Estado"),
                row_builder=lambda x: (x.administrative_id, x.full_name, x.position, x.employment_type, f"$ {x.base_salary:,.2f}", "Activo" if x.active else "Inactivo"),
                operation_name="administrative",
            ),
        )

        # 8. Inscripciones
        self._register_page(
            "Inscripciones",
            CrudPage(
                title="Inscripciones y Matrículas",
                subtitle="Asignación de asignaturas y registro de notas",
                manager=self.manager,
                collection_name="enrollments",
                model_cls=Enrollment,
                id_field="enrollment_id",
                fields=(
                    ("enrollment_id", "ID Inscripción", "int"),
                    (
                        "student_id",
                        "Estudiante",
                        "relation",
                        lambda: [
                            (s.student_id, f"{s.full_name} (#{s.student_id})")
                            for s in self.manager.students
                            if getattr(s, "active", True)
                        ],
                    ),
                    (
                        "course_id",
                        "Curso / Asignatura",
                        "relation",
                        lambda: [
                            (c.course_id, f"{c.name} (#{c.course_id})")
                            for c in self.manager.courses
                            if getattr(c, "active", True)
                        ],
                    ),
                    ("academic_period", "Período Académico", "text"),
                    ("final_grade", "Nota Definitiva", "float"),
                    ("status", "Estado", "text"),
                    ("enrollment_date", "Fecha Inscripción", "text"),
                ),
                columns=("ID", "Estudiante", "Curso", "Período", "Nota Definitiva", "Estado"),
                row_builder=lambda x: (
                    x.enrollment_id,
                    getattr(self.manager.get_student(x.student_id), "full_name", x.student_id),
                    getattr(self.manager.get_course(x.course_id), "name", x.course_id),
                    x.academic_period,
                    f"{x.final_grade:.1f}",
                    x.status,
                ),
                operation_name="enrollment",
            ),
        )

        # 9. Nómina
        self._register_page("Nómina", PayrollPage(self.manager))

        # 10. Reportes
        self._register_page("Reportes", ReportsPage(self.manager))

        # Conectar señal de cambio para refrescar Dashboard
        for page in self._pages.values():
            if hasattr(page, "changed"):
                page.changed.connect(self._refresh_dashboard)

    def _register_page(self, name: str, page: QWidget):
        self._pages[name] = page
        self.stack.addWidget(page)

    def _navigate(self, name: str):
        page = self._pages.get(name)
        if page is None:
            logging.getLogger(__name__).warning(
                "Navegación a página inexistente: %s", name
            )
            return
        self.stack.setCurrentWidget(page)
        if hasattr(page, "refresh"):
            page.refresh()
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.set_active_page(name)

    def _handle_global_search(self, query: str):
        query = query.strip()
        if not query:
            return

        norm_query = _normalize_text(query)
        mgr = self.manager

        # Si el widget actual ya es CrudPage y contiene coincidencias, filtrar allí
        current_widget = self.stack.currentWidget()
        if isinstance(current_widget, CrudPage):
            items = getattr(current_widget, "data", [])
            row_builder = getattr(current_widget, "row_builder", str)
            current_matches = sum(
                1 for item in items if norm_query in _normalize_text(str(row_builder(item)))
            )
            if current_matches > 0:
                current_widget.search_input.setText(query)
                current_widget.filter_data(query)
                return

        # Búsqueda transversal en colecciones del EntityManager
        entity_sources = [
            ("Estudiantes", getattr(mgr, "students", []), lambda s: f"{getattr(s, 'full_name', '')} {getattr(s, 'student_id', '')} {getattr(s, 'email', '')} {getattr(s, 'id_card', '')}"),
            ("Cursos", getattr(mgr, "courses", []), lambda c: f"{getattr(c, 'name', '')} {getattr(c, 'course_id', '')}"),
            ("Profesores", getattr(mgr, "professors", []), lambda p: f"{getattr(p, 'full_name', '')} {getattr(p, 'professor_id', '')} {getattr(p, 'email', '')} {getattr(p, 'department', '')}"),
            ("Programas", getattr(mgr, "programs", []), lambda p: f"{getattr(p, 'name', '')} {getattr(p, 'program_id', '')} {getattr(p, 'program_director', '')}"),
            ("Facultades", getattr(mgr, "faculties", []), lambda f: f"{getattr(f, 'name', '')} {getattr(f, 'faculty_id', '')} {getattr(f, 'dean_name', '')}"),
            ("Administrativos", getattr(mgr, "administrative_staff", []), lambda a: f"{getattr(a, 'full_name', '')} {getattr(a, 'administrative_id', '')} {getattr(a, 'position', '')}"),
            ("Inscripciones", getattr(mgr, "enrollments", []), lambda e: f"{getattr(e, 'enrollment_id', '')} {getattr(e, 'academic_period', '')}"),
        ]

        best_page = None
        max_matches = 0

        for page_name, collection, repr_fn in entity_sources:
            matches = 0
            for item in collection:
                if norm_query in _normalize_text(repr_fn(item)):
                    matches += 1
            if matches > max_matches:
                max_matches = matches
                best_page = page_name

        if best_page:
            self._navigate(best_page)
            target = self._pages.get(best_page)
            if target and hasattr(target, "search_input") and hasattr(target, "filter_data"):
                target.search_input.setText(query)
                target.filter_data(query)
        else:
            if hasattr(self, "header") and hasattr(self.header, "search_input"):
                inp = self.header.search_input
                QToolTip.showText(
                    inp.mapToGlobal(QPoint(0, inp.height() + 4)),
                    f"Sin coincidencias para: '{query}'",
                    inp,
                    QRect(),
                    3000,
                )

    def _refresh_dashboard(self):
        dash = self._pages.get("Dashboard")
        if dash is not None:
            dash.refresh()
        if hasattr(self, "header") and self.header:
            self.header.update_alerts(self.manager)

    def _load_state(self):
        clear_load_issues()
        try:
            loaded_state: dict[str, Any] = {
                "faculties": LinkedList(load_faculties()),
                "programs": LinkedList(load_programs()),
                "courses": LinkedList(load_courses()),
                "students": LinkedList(load_students()),
                "professors": LinkedList(load_professors()),
                "administrative_staff": LinkedList(load_administrative_staff()),
                "enrollments": LinkedList(load_enrollments()),
            }
            loaded_state["periods"] = load_payroll_periods()
            loaded_state["runs"] = load_payroll_runs()
            loaded_state["novelties"] = load_payroll_novelties()
            loaded_state["audits"] = load_payroll_audit()

            self.manager.faculties = loaded_state["faculties"]
            self.manager.programs = loaded_state["programs"]
            self.manager.courses = loaded_state["courses"]
            self.manager.students = loaded_state["students"]
            self.manager.professors = loaded_state["professors"]
            self.manager.administrative_staff = loaded_state["administrative_staff"]
            self.manager.enrollments = loaded_state["enrollments"]
            self.manager.link_hierarchical_references()
            cycle = self.manager.payroll_cycle_service
            cycle.periods = loaded_state["periods"]
            cycle.runs = loaded_state["runs"]
            cycle.novelties = loaded_state["novelties"]
            cycle.audits = loaded_state["audits"]

            issues = get_load_issues()
            if issues:
                labor_issues = [
                    i for i in issues
                    if "campos laborales" in i or "valores de nómina por defecto" in i or "ARL" in i
                ]
                other_issues = [i for i in issues if i not in labor_issues]

                if labor_issues:
                    count_labor = len(labor_issues)
                    labor_text = (
                        f"Se detectaron {count_labor} empleado(s) con campos laborales y clase de riesgo ARL "
                        "no configurados en los datos de origen.\n\n"
                        "El sistema asignó Clase I (Riesgo Mínimo - 0.522%) por defecto para permitir la operación. "
                        "Esto puede ocasionar aportes patronales deficitarios si los empleados realizan labores de mayor riesgo "
                        "(laboratorios, talleres, mantenimiento, etc.).\n\n"
                        "Empleados afectados:\n"
                    )
                    if count_labor > 10:
                        labor_text += "\n".join(f"• {item}" for item in labor_issues[:10])
                        labor_text += f"\n\n... y {count_labor - 10} empleado(s) más."
                    else:
                        labor_text += "\n".join(f"• {item}" for item in labor_issues)
                    labor_text += (
                        "\n\nRecomendación: Ingrese a la gestión de Profesores y Administrativos "
                        "para revisar y actualizar la Clase de Riesgo ARL correspondiente a cada empleado."
                    )
                    QMessageBox.warning(
                        self,
                        "Advertencia: Configuración Laboral y Riesgo ARL",
                        labor_text,
                    )

                if other_issues:
                    count = len(other_issues)
                    header = (
                        f"Se encontraron {count} advertencia(s) al cargar los datos.\n"
                        "Los registros con errores fueron omitidos individualmente para proteger "
                        "los registros válidos y evitar pérdidas de datos:\n\n"
                    )
                    if count > 12:
                        body = "\n".join(f"• {item}" for item in other_issues[:12]) + f"\n\n... y {count - 12} registro(s) más (ver detalles)."
                    else:
                        body = "\n".join(f"• {item}" for item in other_issues)

                    msg_box = QMessageBox(self)
                    msg_box.setIcon(QMessageBox.Icon.Warning)
                    msg_box.setWindowTitle("Aviso de Carga de Datos")
                    msg_box.setText(header + body)
                    if count > 12:
                        msg_box.setDetailedText("\n\n".join(other_issues))
                    msg_box.exec()
            for page in self._pages.values():
                if hasattr(page, "refresh"):
                    page.refresh()
            if hasattr(self, "header") and self.header:
                self.header.update_alerts(self.manager)
            return True
        except Exception as exc:
            self.manager.faculties = LinkedList()
            self.manager.programs = LinkedList()
            self.manager.courses = LinkedList()
            self.manager.students = LinkedList()
            self.manager.professors = LinkedList()
            self.manager.administrative_staff = LinkedList()
            self.manager.enrollments = LinkedList()
            cycle = self.manager.payroll_cycle_service
            cycle.periods = []
            cycle.runs = []
            cycle.novelties = []
            cycle.audits = []
            QMessageBox.critical(self, "Error al cargar datos", str(exc))
            return False

    def _save_state(self):
        try:
            batch_save_state(self.manager, DATA_DIRECTORY)
            QMessageBox.information(
                self,
                "NexoCampus",
                "Todos los datos fueron guardados correctamente de forma atómica.",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error al guardar datos",
                "No se guardó ningún cambio para preservar la consistencia de la base de datos.\n\n"
                f"Detalle del error: {exc}",
            )

    def _reload_state(self):
        ans = QMessageBox.question(
            self,
            "Cargar datos",
            "¿Deseas reemplazar la sesión actual por los datos guardados en los archivos JSON?",
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            if not self._load_state():
                return
            for page in self._pages.values():
                if hasattr(page, "refresh"):
                    page.refresh()
            if not get_load_issues():
                QMessageBox.information(self, "NexoCampus", "Datos cargados correctamente.")
        except Exception as exc:
            QMessageBox.critical(self, "Error al cargar datos", str(exc))
