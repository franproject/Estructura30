from PySide6.QtCore import Qt
from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCharts import QChart, QChartView, QPieSeries

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
from .pyside_pages import CrudPage


class StatCard(QFrame):
    def __init__(self, label, icon="•", detail="Total registrado", accent="#00D9FF", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        top = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setObjectName("statIcon")
        icon_label.setStyleSheet(f"color: {accent}; background: {accent}22; border: 1px solid {accent}66; border-radius: 8px; padding: 6px 9px; font-size: 17px;")
        top.addWidget(icon_label)
        top.addStretch()
        layout.addLayout(top)
        self.label = QLabel(label)
        self.label.setObjectName("statLabel")
        self.value = QLabel("0")
        self.value.setObjectName("statValue")
        self.detail = QLabel(detail)
        self.detail.setObjectName("statDetail")
        layout.addWidget(self.label)
        layout.addWidget(self.value)
        layout.addWidget(self.detail)

    def set_value(self, value):
        self.value.setText(str(value))


class DashboardPage(QWidget):
    def __init__(self, manager, open_page, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.open_page = open_page
        self.cards = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        heading = QHBoxLayout()
        heading_text = QVBoxLayout()
        title = QLabel("Dashboard académico")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Vista general del sistema universitario")
        subtitle.setObjectName("pageSubtitle")
        heading_text.addWidget(title)
        heading_text.addWidget(subtitle)
        heading.addLayout(heading_text)
        heading.addStretch()
        layout.addLayout(heading)

        hero = QFrame()
        hero.setObjectName("heroPanel")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 20, 22, 20)
        text = QVBoxLayout()
        title = QLabel("Operación universitaria")
        title.setObjectName("heroTitle")
        subtitle = QLabel("Datos en tiempo real de la sesión actual")
        subtitle.setObjectName("heroSubtitle")
        text.addWidget(title)
        text.addWidget(subtitle)
        hero_layout.addLayout(text)
        hero_layout.addStretch()
        hero_layout.addWidget(QLabel("NexoCampus  /  UPC"), alignment=Qt.AlignRight | Qt.AlignTop)
        layout.addWidget(hero)

        cards_grid = QGridLayout()
        cards_grid.setHorizontalSpacing(12)
        cards_grid.setVerticalSpacing(12)
        card_data = (("Facultades", "▦", "Total registradas", "#00D9FF"), ("Programas", "⌘", "Oferta académica", "#7B4DFF"), ("Cursos", "▤", "Asignaturas", "#00D9A5"), ("Estudiantes", "◉", "Personas activas", "#00B7FF"), ("Profesores", "♙", "Equipo docente", "#A66BFF"), ("Administrativos", "▣", "Personal institucional", "#FFAA2B"), ("Inscripciones activas", "▧", "Matrículas vigentes", "#00D9A5"), ("Alertas EBRA", "!", "Requieren atención", "#FF4264"))
        for index, (label, icon, detail, accent) in enumerate(card_data):
            card = StatCard(label, icon, detail, accent)
            self.cards[label] = card
            cards_grid.addWidget(card, index // 4, index % 4)
        layout.addLayout(cards_grid)

        lower = QHBoxLayout()
        lower.setSpacing(18)
        insight_column = QVBoxLayout()
        insight_column.setSpacing(18)
        insight_column.addWidget(self._build_distribution_panel(), stretch=1)
        insight_column.addWidget(self._build_activity_panel(), stretch=1)
        lower.addLayout(insight_column, stretch=1)
        layout.addLayout(lower, stretch=1)
        layout.addWidget(self._build_quick_actions())
        self.refresh()

    def _build_distribution_panel(self):
        panel = QFrame(); panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        title = QLabel("Distribución de estudiantes")
        title.setObjectName("panelTitle")
        layout.addWidget(title)
        series = QPieSeries()
        self._distribution_series = series
        chart = QChart(); chart.addSeries(series); chart.setBackgroundVisible(False)
        chart.legend().setVisible(True); chart.legend().setAlignment(Qt.AlignBottom)
        view = QChartView(chart); view.setMinimumHeight(150); view.setStyleSheet("background: transparent;")
        self._distribution_chart = chart
        layout.addWidget(view)
        return panel

    def _build_activity_panel(self):
        panel = QFrame(); panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        title = QLabel("Últimos registros")
        title.setObjectName("panelTitle")
        layout.addWidget(title)
        empty = QLabel("No hay registros recientes")
        empty.setObjectName("emptyState")
        empty.setAlignment(Qt.AlignCenter)
        layout.addWidget(empty, stretch=1)
        return panel

    def _build_quick_actions(self):
        panel = QFrame(); panel.setObjectName("quickPanel")
        layout = QVBoxLayout(panel)
        title = QLabel("Acciones rápidas")
        title.setObjectName("panelTitle")
        layout.addWidget(title)
        actions = QHBoxLayout()
        for label, icon, target in (("Facultades", "▦", "Facultades"), ("Programas", "⌘", "Programas"), ("Cursos", "▤", "Cursos"), ("Estudiantes", "◉", "Estudiantes"), ("Profesores", "♙", "Profesores"), ("Nómina", "$", "Nómina")):
            button = QPushButton(f"{icon}\n{label}")
            button.setObjectName("quickButton")
            button.clicked.connect(lambda checked=False, page=target: self.open_page(page))
            actions.addWidget(button)
        layout.addLayout(actions)
        return panel

    def refresh(self):
        manager = self.manager
        active_enrollments = sum(1 for item in manager.enrollments if str(item.status).upper() in {"ACTIVE", "COMPLETED"})
        ebra = sum(1 for student in manager.students if manager.evaluate_ebra_status(student.student_id)["status"] == "EBRA")
        values = {
            "Facultades": len(manager.faculties),
            "Programas": len(manager.programs),
            "Cursos": len(manager.courses),
            "Estudiantes": len(manager.students),
            "Profesores": len(manager.professors),
            "Administrativos": len(manager.administrative_staff),
            "Inscripciones activas": active_enrollments,
            "Alertas EBRA": ebra,
        }
        for label, value in values.items():
            self.cards[label].set_value(value)
        self._distribution_series.clear()
        totals = {}
        for student in manager.students:
            program = manager.get_program(student.program_id)
            name = program.name if program is not None else "Sin programa"
            totals[name] = totals.get(name, 0) + 1
        for name, total in totals.items():
            self._distribution_series.append(name, total)
        self._distribution_chart.legend().setVisible(bool(totals))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NexoCampus | Gestión académica")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)
        self.manager = EntityManager()
        self._load_state()
        self._pages = {}
        self._nav_buttons = {}
        self._load_styles()
        self._build_ui()

    def _load_styles(self):
        path = __file__.replace("main_window_qt.py", "styles.qss")
        try:
            with open(path, encoding="utf-8") as stylesheet:
                self.setStyleSheet(stylesheet.read())
        except OSError:
            pass

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())

        right_side = QWidget()
        right_layout = QVBoxLayout(right_side)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self._build_header())
        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack, stretch=1)
        root.addWidget(right_side, stretch=1)
        self._add_pages()
        self._navigate("Dashboard")

    def _build_header(self):
        header = QFrame(); header.setObjectName("topHeader")
        layout = QHBoxLayout(header); layout.setContentsMargins(26, 14, 28, 14)
        logo = QLabel("NexoCampus")
        logo.setObjectName("headerLogo")
        layout.addWidget(logo)
        separator = QFrame(); separator.setFrameShape(QFrame.Shape.VLine); separator.setObjectName("headerSeparator")
        layout.addWidget(separator)
        context = QLabel("Programa Integrado de\nTransacciones Académicas")
        context.setObjectName("headerContext")
        layout.addWidget(context)
        layout.addStretch()
        now = QDateTime.currentDateTime()
        date_box = QLabel(f"◷  {now.toString('dd/MM/yyyy')}\n    {now.toString('hh:mm')}")
        date_box.setObjectName("headerMeta")
        layout.addWidget(date_box)
        divider = QFrame(); divider.setFrameShape(QFrame.Shape.VLine); divider.setObjectName("headerSeparator")
        layout.addWidget(divider)
        user = QLabel("◉  Administrador\n    Sistema")
        user.setObjectName("headerUser")
        layout.addWidget(user)
        return header

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(245)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 24, 18, 20)
        layout.setSpacing(5)
        brand = QLabel("NexoCampus")
        brand.setObjectName("brand")
        layout.addWidget(brand)
        description = QLabel("Programa Integrado de\nTransacciones Académicas")
        description.setObjectName("muted")
        layout.addWidget(description)
        layout.addSpacing(22)
        menu_title = QLabel("NAVEGACIÓN")
        menu_title.setObjectName("eyebrow")
        layout.addWidget(menu_title)
        icons = {"Dashboard": "⌂", "Facultades": "▦", "Programas": "⌘", "Cursos": "▤", "Estudiantes": "◉", "Profesores": "♙", "Administrativos": "▣", "Inscripciones": "▧", "Nómina": "$", "Reportes": "◒"}
        for label in ("Dashboard", "Facultades", "Programas", "Cursos", "Estudiantes", "Profesores", "Administrativos", "Inscripciones", "Nómina", "Reportes"):
            button = QPushButton(f"{icons[label]}   {label}")
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, name=label: self._navigate(name))
            self._nav_buttons[label] = button
            layout.addWidget(button)
        layout.addStretch()
        settings = QLabel("SISTEMA")
        settings.setObjectName("eyebrow")
        layout.addWidget(settings)
        save = QPushButton("⚙  Guardar datos")
        save.setObjectName("primaryButton")
        save.clicked.connect(self._save_state)
        layout.addWidget(save)
        reload_button = QPushButton("↻  Cargar datos")
        reload_button.setObjectName("secondaryButton")
        reload_button.clicked.connect(self._reload_state)
        layout.addWidget(reload_button)
        return sidebar

    def _add_pages(self):
        dashboard = DashboardPage(self.manager, self._navigate)
        self._register_page("Dashboard", dashboard)
        self._register_page("Facultades", CrudPage("Facultades", self.manager, "faculties", Faculty, "faculty_id", (("faculty_id", "ID", "int"), ("name", "Nombre", "text"), ("dean", "Decano", "text"), ("creation_date", "Fecha", "text"), ("active", "Activo", "bool")), ("ID", "Nombre", "Decano", "Fecha", "Estado"), lambda x: (x.faculty_id, x.name, x.dean, x.creation_date, x.active), "faculty"))
        self._register_page("Programas", CrudPage("Programas", self.manager, "programs", Program, "program_id", (("program_id", "ID", "int"), ("name", "Nombre", "text"), ("faculty_id", "Facultad", "int"), ("program_director", "Director", "text"), ("level", "Nivel", "text"), ("modality", "Modalidad", "text"), ("program_type", "Tipo", "text"), ("active", "Activo", "bool")), ("ID", "Nombre", "Tipo", "Facultad", "Estado"), lambda x: (x.program_id, x.name, x.program_type, x.faculty_id, x.active), "program"))
        self._register_page("Cursos", CrudPage("Cursos", self.manager, "courses", Course, "course_id", (("course_id", "ID", "int"), ("name", "Nombre", "text"), ("program_id", "Programa", "int"), ("credits", "Créditos", "int"), ("curriculum_semester", "Semestre", "int"), ("assigned_professor_id", "Profesor", "int"), ("max_capacity", "Cupo", "int"), ("active", "Activo", "bool")), ("ID", "Nombre", "Programa", "Créditos", "Cupo", "Estado"), lambda x: (x.course_id, x.name, x.program_id, x.credits, x.max_capacity, x.active), "course"))
        self._register_page("Estudiantes", CrudPage("Estudiantes", self.manager, "students", Student, "student_id", (("student_id", "ID", "int"), ("full_name", "Nombre", "text"), ("document_type", "Tipo documento", "text"), ("document_number", "Documento", "text"), ("birth_date", "Nacimiento", "text"), ("email", "Correo", "text"), ("phone", "Teléfono", "text"), ("program_id", "Programa", "int"), ("current_semester", "Semestre", "int"), ("status", "Estado académico", "text"), ("active", "Activo", "bool")), ("ID", "Nombre", "Documento", "Programa", "Estado"), lambda x: (x.student_id, x.full_name, x.document_number, x.program_id, x.active), "student"))
        self._register_page("Profesores", CrudPage("Profesores", self.manager, "professors", Professor, "professor_id", (("professor_id", "ID", "int"), ("full_name", "Nombre", "text"), ("document_type", "Tipo documento", "text"), ("document_number", "Documento", "text"), ("email", "Correo", "text"), ("phone", "Teléfono", "text"), ("faculty_id", "Facultad", "int"), ("employment_type", "Contrato", "text"), ("academic_title", "Título", "text"), ("active", "Activo", "bool")), ("ID", "Nombre", "Facultad", "Contrato", "Estado"), lambda x: (x.professor_id, x.full_name, x.faculty_id, x.employment_type, x.active), "professor"))
        self._register_page("Administrativos", CrudPage("Administrativos", self.manager, "administrative_staff", Administrative, "administrative_id", (("administrative_id", "ID", "int"), ("full_name", "Nombre", "text"), ("document_type", "Tipo documento", "text"), ("document_number", "Documento", "text"), ("email", "Correo", "text"), ("phone", "Teléfono", "text"), ("position", "Cargo", "text"), ("category", "Categoría", "text"), ("employment_type", "Contrato", "text"), ("base_salary", "Salario", "float"), ("active", "Activo", "bool")), ("ID", "Nombre", "Cargo", "Contrato", "Salario", "Estado"), lambda x: (x.administrative_id, x.full_name, x.position, x.employment_type, x.base_salary, x.active), "administrative"))
        self._register_page("Inscripciones", CrudPage("Inscripciones", self.manager, "enrollments", __import__("models.enrollment", fromlist=["Enrollment"]).Enrollment, "enrollment_id", (("enrollment_id", "ID", "int"), ("student_id", "Estudiante", "int"), ("course_id", "Curso", "int"), ("academic_period", "Periodo", "text"), ("final_grade", "Nota", "float"), ("status", "Estado", "text"), ("enrollment_date", "Fecha", "text")), ("ID", "Estudiante", "Curso", "Periodo", "Nota", "Estado"), lambda x: (x.enrollment_id, x.student_id, x.course_id, x.academic_period, x.final_grade, x.status), "enrollment"))
        reports = self._build_reports_page()
        self._register_page("Reportes", reports)
        self._register_page("Nómina", self._build_payroll_page())
        for page in self._pages.values():
            if hasattr(page, "changed"):
                page.changed.connect(self._refresh_dashboard)

    def _register_page(self, name, page):
        self._pages[name] = page
        self.stack.addWidget(page)

    def _build_reports_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Reportes")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(("Reporte", "Resultado"))
        table.horizontalHeader().setStretchLastSection(True)
        for label, value in self._report_rows():
            row = table.rowCount(); table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(label)); table.setItem(row, 1, QTableWidgetItem(str(value)))
        layout.addWidget(table)
        return page

    def _report_rows(self):
        ebra = sum(1 for student in self.manager.students if self.manager.evaluate_ebra_status(student.student_id)["status"] == "EBRA")
        return (("Facultades", len(self.manager.faculties)), ("Programas", len(self.manager.programs)), ("Cursos", len(self.manager.courses)), ("Estudiantes", len(self.manager.students)), ("Alertas EBRA", ebra))

    def _build_payroll_page(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Nómina"); title.setObjectName("pageTitle"); layout.addWidget(title)
        table = QTableWidget(0, 4); table.setHorizontalHeaderLabels(("Empleado", "Tipo", "Base", "Neto")); table.horizontalHeader().setStretchLastSection(True)
        calculator = __import__("models.payroll", fromlist=["Payroll"]).Payroll("Reporte")
        for employee in list(self.manager.professors) + list(self.manager.administrative_staff):
            report = calculator.generate_payroll_report(employee); row = table.rowCount(); table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(str(getattr(employee, "full_name", "")))); table.setItem(row, 1, QTableWidgetItem(report["employee_type"])); table.setItem(row, 2, QTableWidgetItem(f"{report['base_salary']:,.2f}")); table.setItem(row, 3, QTableWidgetItem(f"{report['net_salary']:,.2f}"))
        layout.addWidget(table); return page

    def _navigate(self, name):
        page = self._pages.get(name)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        for label, button in self._nav_buttons.items():
            button.setChecked(label == name)
        if hasattr(page, "refresh"):
            page.refresh()

    def _refresh_dashboard(self):
        dashboard = self._pages.get("Dashboard")
        if dashboard is not None:
            dashboard.refresh()

    def _load_state(self):
        self.manager.faculties = LinkedList(load_faculties())
        self.manager.programs = LinkedList(load_programs())
        self.manager.courses = LinkedList(load_courses())
        self.manager.students = LinkedList(load_students())
        self.manager.professors = LinkedList(load_professors())
        self.manager.administrative_staff = LinkedList(load_administrative_staff())
        self.manager.enrollments = LinkedList(load_enrollments())
        records = load_payroll()
        self.manager.payroll = records[0] if records else None

    def _save_state(self):
        save_faculties(self.manager.faculties)
        save_programs(self.manager.programs)
        save_courses(self.manager.courses)
        save_students(self.manager.students)
        save_professors(self.manager.professors)
        save_administrative_staff(self.manager.administrative_staff)
        save_enrollments(self.manager.enrollments)
        if self.manager.payroll is not None:
            save_payroll([self.manager.payroll])
        QMessageBox.information(self, "NexoCampus", "Datos guardados correctamente.")

    def _reload_state(self):
        answer = QMessageBox.question(self, "Cargar datos", "¿Reemplazar la sesión actual por los datos guardados?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._load_state()
        for page in self._pages.values():
            if hasattr(page, "refresh"):
                page.refresh()
        QMessageBox.information(self, "NexoCampus", "Datos cargados correctamente.")
