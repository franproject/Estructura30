"""Ventana principal de la aplicación NexoCampus."""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from models.administrative import Administrative
from models.course import Course
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
from services.entity_manager import EntityManager

from .components.header import TopHeader
from .components.sidebar import Sidebar
from .pages.crud_page import CrudPage
from .pages.dashboard_page import DashboardPage
from .pages.payroll_page import PayrollPage
from .pages.reports_page import ReportsPage


class MainWindow(QMainWindow):
    """Ventana principal moderna de NexoCampus (PySide6 + QSS)."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NexoCampus | Gestión Universitaria")
        self.resize(1366, 768)
        self.setMinimumSize(1100, 680)

        self.manager = EntityManager()
        self._load_state()

        self._pages = {}
        self._load_styles()
        self._build_ui()

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

        # Right Panel (Header + Stack)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.header = TopHeader()
        right_layout.addWidget(self.header)

        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack, stretch=1)

        root.addWidget(right_panel, stretch=1)

        # Registrar páginas
        self._add_pages()
        self.sidebar.set_active_page("Dashboard")

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
                    ("faculty_id", "ID Facultad", "int"),
                    ("program_director", "Director", "text"),
                    ("level", "Nivel", "text"),
                    ("modality", "Modalidad", "text"),
                    ("program_type", "Tipo", "text"),
                    ("active", "Estado Activo", "bool"),
                ),
                columns=("ID", "Nombre", "Director", "Facultad", "Modalidad", "Estado"),
                row_builder=lambda x: (x.program_id, x.name, x.program_director, x.faculty_id, x.modality, "Activo" if x.active else "Inactivo"),
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
                    ("program_id", "ID Programa", "int"),
                    ("credits", "Créditos", "int"),
                    ("curriculum_semester", "Semestre", "int"),
                    ("assigned_professor_id", "ID Profesor", "int"),
                    ("max_capacity", "Cupo Máximo", "int"),
                    ("active", "Estado Activo", "bool"),
                ),
                columns=("ID", "Nombre", "Programa", "Créditos", "Semestre", "Cupo", "Estado"),
                row_builder=lambda x: (x.course_id, x.name, x.program_id, x.credits, x.curriculum_semester, x.max_capacity, "Activo" if x.active else "Inactivo"),
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
                    ("program_id", "ID Programa", "int"),
                    ("current_semester", "Semestre Actual", "int"),
                    ("status", "Estado Académico", "text"),
                    ("active", "Estado Activo", "bool"),
                ),
                columns=("ID", "Nombre Completo", "Documento", "Programa", "Semestre", "Estado Académico", "Activo"),
                row_builder=lambda x: (x.student_id, x.full_name, x.document_number, x.program_id, f"{x.current_semester}°", x.status, "Sí" if x.active else "No"),
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
                    ("faculty_id", "ID Facultad", "int"),
                    ("employment_type", "Tipo Contrato", "text"),
                    ("academic_title", "Título Académico", "text"),
                    ("active", "Estado Activo", "bool"),
                ),
                columns=("ID", "Nombre Completo", "Documento", "Facultad", "Contrato", "Título", "Estado"),
                row_builder=lambda x: (x.professor_id, x.full_name, x.document_number, x.faculty_id, x.employment_type, x.academic_title, "Activo" if x.active else "Inactivo"),
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
                    ("active", "Estado Activo", "bool"),
                ),
                columns=("ID", "Nombre Completo", "Cargo", "Contrato", "Salario Base", "Estado"),
                row_builder=lambda x: (x.administrative_id, x.full_name, x.position, x.employment_type, f"$ {x.base_salary:,.2f}", "Activo" if x.active else "Inactivo"),
                operation_name="administrative",
            ),
        )

        # 8. Inscripciones
        enrollment_mod = __import__("models.enrollment", fromlist=["Enrollment"])
        self._register_page(
            "Inscripciones",
            CrudPage(
                title="Inscripciones y Matrículas",
                subtitle="Asignación de asignaturas y registro de notas",
                manager=self.manager,
                collection_name="enrollments",
                model_cls=enrollment_mod.Enrollment,
                id_field="enrollment_id",
                fields=(
                    ("enrollment_id", "ID Inscripción", "int"),
                    ("student_id", "ID Estudiante", "int"),
                    ("course_id", "ID Curso", "int"),
                    ("academic_period", "Período Académico", "text"),
                    ("final_grade", "Nota Definitiva", "float"),
                    ("status", "Estado", "text"),
                    ("enrollment_date", "Fecha Inscripción", "text"),
                ),
                columns=("ID", "Estudiante", "Curso", "Período", "Nota Definitiva", "Estado"),
                row_builder=lambda x: (x.enrollment_id, x.student_id, x.course_id, x.academic_period, f"{x.final_grade:.1f}", x.status),
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
        if page is not None:
            self.stack.setCurrentWidget(page)
            if hasattr(page, "refresh"):
                page.refresh()

    def _refresh_dashboard(self):
        dash = self._pages.get("Dashboard")
        if dash is not None:
            dash.refresh()

    def _load_state(self):
        self.manager.faculties = LinkedList(load_faculties())
        self.manager.programs = LinkedList(load_programs())
        self.manager.courses = LinkedList(load_courses())
        self.manager.students = LinkedList(load_students())
        self.manager.professors = LinkedList(load_professors())
        self.manager.administrative_staff = LinkedList(load_administrative_staff())
        self.manager.enrollments = LinkedList(load_enrollments())
        records = load_payroll()
        setattr(self.manager, "payroll", records[0] if records else None)

    def _save_state(self):
        save_faculties(self.manager.faculties)
        save_programs(self.manager.programs)
        save_courses(self.manager.courses)
        save_students(self.manager.students)
        save_professors(self.manager.professors)
        save_administrative_staff(self.manager.administrative_staff)
        save_enrollments(self.manager.enrollments)
        payroll = getattr(self.manager, "payroll", None)
        if payroll is not None:
            save_payroll([payroll])
        QMessageBox.information(self, "NexoCampus", "Datos guardados correctamente.")

    def _reload_state(self):
        ans = QMessageBox.question(
            self,
            "Cargar datos",
            "¿Deseas reemplazar la sesión actual por los datos guardados en los archivos JSON?",
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self._load_state()
        for page in self._pages.values():
            if hasattr(page, "refresh"):
                page.refresh()
        QMessageBox.information(self, "NexoCampus", "Datos cargados correctamente.")
