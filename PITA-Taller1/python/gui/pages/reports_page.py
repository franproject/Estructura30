"""Página de Reportes Institucionales avanzados para NexoCampus."""
import csv
import logging
from typing import List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..components.data_table import DataTable
from ..components.icons import icon
from ..components.page_header import PageHeader
from ..components.pagination_bar import PaginationBar
from ..components.search_bar import SearchBar
from ..i18n.labels import get_acronym_tooltip
from .crud_page import _normalize_text


class ReportsPage(QWidget):
    """Centro de Reportes Institucionales de NexoCampus organizado en pestañas."""

    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager

        # Almacenamiento de datos crudos y filtrados por reporte
        self._ebra_all: List[Tuple] = []
        self._ebra_filtered: List[Tuple] = []

        self._workload_all: List[Tuple] = []
        self._workload_filtered: List[Tuple] = []

        self._salary_all: List[Tuple] = []
        self._salary_filtered: List[Tuple] = []

        self._metrics_all: List[Tuple] = []
        self._metrics_filtered: List[Tuple] = []

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(16)

        # Header principal
        header = PageHeader(
            title="Reportes Institucionales",
            subtitle="Métricas estratégicas, seguimiento académico y gestión financiera universitaria",
        )
        root_layout.addWidget(header)

        # QTabWidget de Reportes
        self.tabs = QTabWidget()
        self.tabs.setObjectName("reportsTabWidget")

        # Pestañas
        self.tab_ebra = self._create_ebra_tab()
        self.tab_workload = self._create_workload_tab()
        self.tab_salary = self._create_salary_tab()
        self.tab_metrics = self._create_metrics_tab()

        self.tabs.addTab(self.tab_ebra, icon("warning", "#DC2626", 16), "Riesgo Académico (EBRA)")
        self.tabs.setTabToolTip(0, get_acronym_tooltip("EBRA"))
        self.tabs.addTab(self.tab_workload, icon("book-open", "#2563EB", 16), "Carga Docente")
        self.tabs.addTab(self.tab_salary, icon("briefcase", "#16A34A", 16), "Consolidado Salarial")
        self.tabs.addTab(self.tab_metrics, icon("chart", "#0D9488", 16), "Indicadores Globales")

        root_layout.addWidget(self.tabs, stretch=1)

    # -------------------------------------------------------------------------
    # 1. Pestaña: Estudiantes en Riesgo Académico (EBRA)
    # -------------------------------------------------------------------------
    def _create_ebra_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        self.search_ebra = SearchBar(placeholder="Filtrar por estudiante, programa o semestre...")
        self.search_ebra.search_changed.connect(self._filter_ebra)
        toolbar.addWidget(self.search_ebra)

        self.lbl_ebra_badge = QLabel("0 estudiantes")
        self.lbl_ebra_badge.setToolTip(get_acronym_tooltip("EBRA"))
        self.lbl_ebra_badge.setStyleSheet(
            "background: #FEE2E2; color: #DC2626; font-size: 11px; font-weight: 700; "
            "border-radius: 6px; padding: 5px 10px;"
        )
        toolbar.addWidget(self.lbl_ebra_badge)

        toolbar.addStretch()

        btn_export = QPushButton("Exportar CSV")
        btn_export.setIcon(icon("download", "#16A34A", 14))
        btn_export.setObjectName("secondaryButton")
        btn_export.clicked.connect(self._export_ebra_csv)
        toolbar.addWidget(btn_export)

        layout.addLayout(toolbar)

        # Tabla y Paginador
        columns = ("ID", "Nombre Completo", "Programa Académico", "Semestre", "Promedio Acumulado", "Estado de Riesgo")
        self.table_ebra = DataTable(
            headers=columns,
            stretch_column="Nombre Completo",
            column_types=("id", "text", "text", "center", "numeric", "status"),
        )
        layout.addWidget(self.table_ebra)

        self.pag_ebra = PaginationBar(parent=self)
        self.pag_ebra.connect_table(self.table_ebra)
        layout.addWidget(self.pag_ebra)
        layout.addStretch()

        return widget

    def _filter_ebra(self, query: str):
        norm_q = _normalize_text(query)
        if not norm_q:
            self._ebra_filtered = list(self._ebra_all)
        else:
            self._ebra_filtered = [
                row for row in self._ebra_all
                if any(norm_q in _normalize_text(str(col)) for col in row)
            ]
        self.lbl_ebra_badge.setText(f"{len(self._ebra_filtered)} estudiantes")
        self.table_ebra.populate(self._ebra_filtered)
        self.pag_ebra.update_pagination(
            current_page=self.table_ebra.page,
            total_pages=self.table_ebra.page_count,
            total_rows=self.table_ebra.total_rows,
            page_size=self.table_ebra.page_size,
        )

    def _export_ebra_csv(self):
        headers = ["ID Estudiante", "Nombre Completo", "Programa Académico", "Semestre", "Promedio Acumulado", "Estado de Riesgo"]
        self._export_to_csv("reporte_estudiantes_riesgo_ebra.csv", headers, self._ebra_filtered)

    # -------------------------------------------------------------------------
    # 2. Pestaña: Carga Académica Docente
    # -------------------------------------------------------------------------
    def _create_workload_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        self.search_workload = SearchBar(placeholder="Filtrar por profesor, categoría o dedicación...")
        self.search_workload.search_changed.connect(self._filter_workload)
        toolbar.addWidget(self.search_workload)

        self.lbl_workload_badge = QLabel("0 profesores")
        self.lbl_workload_badge.setStyleSheet(
            "background: #EFF6FF; color: #2563EB; font-size: 11px; font-weight: 700; "
            "border-radius: 6px; padding: 5px 10px;"
        )
        toolbar.addWidget(self.lbl_workload_badge)

        toolbar.addStretch()

        btn_export = QPushButton("Exportar CSV")
        btn_export.setIcon(icon("download", "#16A34A", 14))
        btn_export.setObjectName("secondaryButton")
        btn_export.clicked.connect(self._export_workload_csv)
        toolbar.addWidget(btn_export)

        layout.addLayout(toolbar)

        # Tabla y Paginador
        columns = ("ID", "Nombre del Profesor", "Categoría / Rango", "Cursos Asignados", "Total Créditos a Cargo", "Dedicación")
        self.table_workload = DataTable(
            headers=columns,
            stretch_column="Nombre del Profesor",
            column_types=("id", "text", "text", "numeric", "numeric", "center"),
        )
        layout.addWidget(self.table_workload)

        self.pag_workload = PaginationBar(parent=self)
        self.pag_workload.connect_table(self.table_workload)
        layout.addWidget(self.pag_workload)
        layout.addStretch()

        return widget

    def _filter_workload(self, query: str):
        norm_q = _normalize_text(query)
        if not norm_q:
            self._workload_filtered = list(self._workload_all)
        else:
            self._workload_filtered = [
                row for row in self._workload_all
                if any(norm_q in _normalize_text(str(col)) for col in row)
            ]
        self.lbl_workload_badge.setText(f"{len(self._workload_filtered)} profesores")
        self.table_workload.populate(self._workload_filtered)
        self.pag_workload.update_pagination(
            current_page=self.table_workload.page,
            total_pages=self.table_workload.page_count,
            total_rows=self.table_workload.total_rows,
            page_size=self.table_workload.page_size,
        )

    def _export_workload_csv(self):
        headers = ["ID Profesor", "Nombre del Profesor", "Categoría", "Cursos Asignados", "Total Créditos a Cargo", "Dedicación"]
        self._export_to_csv("reporte_carga_academica_docente.csv", headers, self._workload_filtered)

    # -------------------------------------------------------------------------
    # 3. Pestaña: Consolidado Salarial por Categoría
    # -------------------------------------------------------------------------
    def _create_salary_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        self.search_salary = SearchBar(placeholder="Filtrar por categoría o tipo de personal...")
        self.search_salary.search_changed.connect(self._filter_salary)
        toolbar.addWidget(self.search_salary)

        self.lbl_salary_summary = QLabel("Nómina Base Total: $ 0.00")
        self.lbl_salary_summary.setStyleSheet(
            "background: #FEF3C7; color: #D97706; font-size: 11px; font-weight: 700; "
            "border-radius: 6px; padding: 5px 10px;"
        )
        toolbar.addWidget(self.lbl_salary_summary)

        toolbar.addStretch()

        btn_export = QPushButton("Exportar CSV")
        btn_export.setIcon(icon("download", "#16A34A", 14))
        btn_export.setObjectName("secondaryButton")
        btn_export.clicked.connect(self._export_salary_csv)
        toolbar.addWidget(btn_export)

        layout.addLayout(toolbar)

        # Tabla y Paginador
        columns = ("Categoría / Escalafón", "Tipo de Personal", "Cantidad de Empleados", "Salario Base Promedio", "Total a Pagar")
        self.table_salary = DataTable(
            headers=columns,
            stretch_column="Categoría / Escalafón",
            column_types=("text", "text", "numeric", "money", "money"),
        )
        layout.addWidget(self.table_salary)

        self.pag_salary = PaginationBar(parent=self)
        self.pag_salary.connect_table(self.table_salary)
        layout.addWidget(self.pag_salary)
        layout.addStretch()

        return widget

    def _filter_salary(self, query: str):
        norm_q = _normalize_text(query)
        if not norm_q:
            self._salary_filtered = list(self._salary_all)
        else:
            self._salary_filtered = [
                row for row in self._salary_all
                if any(norm_q in _normalize_text(str(col)) for col in row)
            ]
        self.table_salary.populate(self._salary_filtered)
        self.pag_salary.update_pagination(
            current_page=self.table_salary.page,
            total_pages=self.table_salary.page_count,
            total_rows=self.table_salary.total_rows,
            page_size=self.table_salary.page_size,
        )

    def _export_salary_csv(self):
        headers = ["Categoría / Escalafón", "Tipo de Personal", "Cantidad de Empleados", "Salario Base Promedio", "Total a Pagar"]
        self._export_to_csv("reporte_consolidado_salarial.csv", headers, self._salary_filtered)

    # -------------------------------------------------------------------------
    # 4. Pestaña: Métricas e Indicadores Globales
    # -------------------------------------------------------------------------
    def _create_metrics_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        self.search_metrics = SearchBar(placeholder="Filtrar métricas por área o indicador...")
        self.search_metrics.search_changed.connect(self._filter_metrics)
        toolbar.addWidget(self.search_metrics)

        toolbar.addStretch()

        btn_export = QPushButton("Exportar CSV")
        btn_export.setIcon(icon("download", "#16A34A", 14))
        btn_export.setObjectName("secondaryButton")
        btn_export.clicked.connect(self._export_metrics_csv)
        toolbar.addWidget(btn_export)

        layout.addLayout(toolbar)

        # Tabla y Paginador
        columns = ("Área / Dimensión", "Indicador Institucional", "Valor Actual", "Observaciones y Contexto")
        self.table_metrics = DataTable(
            headers=columns,
            stretch_column="Indicador Institucional",
            column_types=("text", "text", "center", "text"),
        )
        layout.addWidget(self.table_metrics)

        self.pag_metrics = PaginationBar(parent=self)
        self.pag_metrics.connect_table(self.table_metrics)
        layout.addWidget(self.pag_metrics)
        layout.addStretch()

        return widget

    def _filter_metrics(self, query: str):
        norm_q = _normalize_text(query)
        if not norm_q:
            self._metrics_filtered = list(self._metrics_all)
        else:
            self._metrics_filtered = [
                row for row in self._metrics_all
                if any(norm_q in _normalize_text(str(col)) for col in row)
            ]
        self.table_metrics.populate(self._metrics_filtered)
        self.pag_metrics.update_pagination(
            current_page=self.table_metrics.page,
            total_pages=self.table_metrics.page_count,
            total_rows=self.table_metrics.total_rows,
            page_size=self.table_metrics.page_size,
        )

    def _export_metrics_csv(self):
        headers = ["Área / Dimensión", "Indicador Institucional", "Valor Actual", "Observaciones"]
        self._export_to_csv("reporte_indicadores_institucionales.csv", headers, self._metrics_filtered)

    # -------------------------------------------------------------------------
    # Utilidad de Exportación CSV
    # -------------------------------------------------------------------------
    def _export_to_csv(self, default_filename: str, headers: list, rows: list):
        if not rows:
            QMessageBox.warning(self, "Exportación a CSV", "No hay datos disponibles para exportar.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Reporte CSV",
            default_filename,
            "Archivos CSV (*.csv);;Todos los archivos (*.*)",
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)

            QMessageBox.information(
                self,
                "Exportación Exitosa",
                f"El reporte se ha exportado correctamente:\n\n{file_path}\n\nTotal: {len(rows)} fila(s) exportadas.",
            )
        except Exception as exc:
            logging.getLogger(__name__).exception("Error exportando reporte a CSV")
            QMessageBox.critical(
                self,
                "Error al Exportar",
                f"Ocurrió un error al intentar guardar el archivo CSV:\n\n{str(exc)}",
            )

    # -------------------------------------------------------------------------
    # Recálculo y Refresco General
    # -------------------------------------------------------------------------
    def refresh(self):
        """Recalcula todos los conjuntos de datos a partir del EntityManager."""
        try:
            mgr = self.manager
            if mgr is None:
                return

            # Mapas auxiliares para rendimiento
            program_map = {p.program_id: p.name for p in getattr(mgr, "programs", [])}

            # 1. Reporte EBRA
            ebra_rows = []
            for s in getattr(mgr, "students", []):
                ebra_info = mgr.evaluate_ebra_status(s.student_id)
                if ebra_info.get("status") == "EBRA":
                    avg = ebra_info.get("average", getattr(s, "cumulative_average", 0.0))
                    prog_name = program_map.get(s.program_id, f"Programa #{s.program_id}")
                    ebra_rows.append((
                        s.student_id,
                        s.full_name,
                        prog_name,
                        getattr(s, "current_semester", 0),
                        f"{avg:.2f}",
                        "EBRA (Riesgo Crítico)",
                    ))

            # Ordenar por promedio ascendente (priorizar mayor riesgo)
            ebra_rows.sort(key=lambda r: float(r[4]))
            self._ebra_all = ebra_rows
            self._filter_ebra(self.search_ebra.text())

            # 2. Reporte Carga Académica Docente
            active_courses = [c for c in getattr(mgr, "courses", []) if getattr(c, "active", True)]
            workload_rows = []
            for p in getattr(mgr, "professors", []):
                p_courses = [c for c in active_courses if getattr(c, "assigned_professor_id", None) == p.professor_id]
                total_credits = sum(int(getattr(c, "credits", 0) or 0) for c in p_courses)
                workload_rows.append((
                    p.professor_id,
                    p.full_name,
                    getattr(p, "category_rank", "") or "Sin categoría",
                    len(p_courses),
                    total_credits,
                    getattr(p, "dedication", "") or "No especificada",
                ))

            # Ordenar por total de créditos descendente
            workload_rows.sort(key=lambda r: r[4], reverse=True)
            self._workload_all = workload_rows
            self._filter_workload(self.search_workload.text())

            # 3. Reporte Consolidado Salarial por Categoría
            categories = {}
            total_payroll = 0.0

            # Docentes
            for p in getattr(mgr, "professors", []):
                if getattr(p, "active", True):
                    rank = getattr(p, "category_rank", "") or "Sin categoría"
                    cat_name = f"Docente - {rank}"
                    entry = categories.setdefault(cat_name, {"type": "Docente", "count": 0, "total": 0.0})
                    salary = float(getattr(p, "base_monthly_salary", 0.0))
                    entry["count"] += 1
                    entry["total"] += salary
                    total_payroll += salary

            # Administrativos
            for a in getattr(mgr, "administrative_staff", []):
                if getattr(a, "active", True):
                    cat_label = getattr(a, "category", "") or getattr(a, "position", "") or "General"
                    cat_name = f"Administrativo - {cat_label}"
                    entry = categories.setdefault(cat_name, {"type": "Administrativo", "count": 0, "total": 0.0})
                    salary = float(getattr(a, "base_salary", 0.0))
                    entry["count"] += 1
                    entry["total"] += salary
                    total_payroll += salary

            salary_rows = []
            for cat_name, data in sorted(categories.items()):
                count = data["count"]
                total = data["total"]
                avg = total / count if count else 0.0
                salary_rows.append((
                    cat_name,
                    data["type"],
                    count,
                    f"$ {avg:,.2f}",
                    f"$ {total:,.2f}",
                ))

            self._salary_all = salary_rows
            self.lbl_salary_summary.setText(f"Nómina Base Total: $ {total_payroll:,.2f}")
            self._filter_salary(self.search_salary.text())

            # 4. Reporte Métricas e Indicadores Globales
            all_courses = getattr(mgr, "courses", [])
            # CORRECCIÓN ESTRICTA: filtrar cursos activos por course.active == True
            count_active_courses = sum(1 for c in all_courses if getattr(c, "active", False))
            count_total_courses = len(all_courses)

            total_students = len(getattr(mgr, "students", []))
            count_ebra = len(self._ebra_all)
            ebra_rate = (count_ebra / total_students * 100) if total_students > 0 else 0.0

            prof_with_assignment = sum(1 for r in workload_rows if r[3] > 0)
            total_profs = len(getattr(mgr, "professors", []))

            metrics_rows = [
                ("Gestión Académica", "Facultades Registradas", str(len(getattr(mgr, "faculties", []))), "Unidades mayores del campus"),
                ("Gestión Académica", "Programas Académicos", str(len(getattr(mgr, "programs", []))), "Oferta de pregrado y posgrado"),
                (
                    "Gestión Curricular",
                    "Cursos Activos en Oferta",
                    f"{count_active_courses} asignaturas",
                    f"Filtro activo estricto ({count_active_courses} de {count_total_courses} en catálogo)",
                ),
                ("Población Estudiantil", "Estudiantes Matriculados", str(total_students), "Total de estudiantes en la base institucional"),
                ("Riesgo Académico", "Estudiantes en Alerta EBRA", str(count_ebra), f"Tasa de riesgo crítico: {ebra_rate:.1f}% del estudiantado"),
                ("Cuerpo Docente", "Profesores Registrados", str(total_profs), f"{prof_with_assignment} con asignación de cursos activa"),
                ("Personal Administrativo", "Personal en Servicio", str(len(getattr(mgr, "administrative_staff", []))), "Apoyo administrativo y directivo"),
                ("Matrícula y Cursos", "Inscripciones Registradas", str(len(getattr(mgr, "enrollments", []))), "Transacciones académicas en el sistema"),
                ("Gestión Financiera", "Presupuesto Mensual Salarios Base", f"$ {total_payroll:,.2f}", "Total devengado base (docentes + administrativos)"),
            ]

            self._metrics_all = metrics_rows
            self._filter_metrics(self.search_metrics.text())

        except Exception as exc:
            logging.getLogger(__name__).exception("Error al refrescar ReportsPage")
            QMessageBox.warning(self, "Error", f"Error al generar reportes: {str(exc)}")
