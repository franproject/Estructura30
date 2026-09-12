"""Página de operación del ciclo formal de nómina."""
from datetime import date
from pathlib import Path
from typing import cast

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from models.payroll_period import PayrollPeriodStatus
from services.payroll_engine import PayrollRules
from services.payslip_service import PayslipService
from ..components.data_table import DataTable
from ..components.icons import icon, pixmap
from ..components.page_header import PageHeader
from ..components.pagination_bar import PaginationBar
from ..i18n.labels import get_payroll_status_label, get_employee_type_label, get_acronym_tooltip
from .payroll_dashboard import PayrollDashboardDialog


class PayrollPage(QWidget):
    """Opera el ciclo de nómina sin duplicar la lógica del motor."""

    changed = Signal()

    COLUMNS = (
        "Empleado", "Tipo", "Período", "Salario base", "Devengado",
        "Deducciones", "IBC", "Neto", "Costo empleador", "Estado",
    )

    DETAIL_SECTIONS = (
        (
            "Identificación",
            (
                ("employee_id", "ID empleado", "text"),
                ("employee_type", "Tipo", "text"),
                ("period", "Período", "text"),
                ("days_worked", "Días trabajados", "text"),
            ),
        ),
        (
            "Devengados",
            (
                ("base_salary", "Salario base", "money"),
                ("salary_adjustments", "Ajustes salariales", "money"),
                ("gross_salary", "Total devengado", "money"),
                ("non_salary_total", "Total no salarial", "money"),
                ("service_bonus", "Prima de servicios pagada", "money"),
                ("ibc", "IBC", "money"),
                ("net_salary", "Neto a pagar", "money"),
            ),
        ),
        (
            "Deducciones del trabajador",
            (
                ("employee_health", "Salud", "money"),
                ("employee_pension", "Pensión", "money"),
                ("employee_other_deductions", "Otras deducciones", "money"),
                ("total_employee_deductions", "Total deducciones", "money"),
            ),
        ),
        (
            "Aportes del empleador",
            (
                ("employer_health", "Salud patronal", "money"),
                ("employer_pension", "Pensión patronal", "money"),
                ("arl", "ARL", "money"),
                ("compensation_fund", "Caja de compensación", "money"),
                ("sena", "SENA", "money"),
                ("icbf", "ICBF", "money"),
                ("total_employer_contributions", "Total aportes", "money"),
                ("total_employer_cost", "Costo total empleador", "money"),
            ),
        ),
        (
            "Provisiones",
            (
                ("service_bonus_provision", "Prima de servicios", "money"),
                ("severance_provision", "Cesantías", "money"),
                ("severance_interest", "Intereses cesantías", "money"),
                ("christmas_bonus_provision", "Prima de navidad", "money"),
                ("vacation_provision", "Vacaciones", "money"),
                ("vacation_bonus_provision", "Prima de vacaciones", "money"),
            ),
        ),
    )

    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.cycle = manager.payroll_cycle_service
        self.rules = PayrollRules()
        self._details = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(PageHeader(
            title="Nómina Académica",
            subtitle="Ciclo de liquidación para personal docente y administrativo",
        ))

        controls = QHBoxLayout()
        self.period_selector = QComboBox()
        self.period_selector.setMinimumWidth(140)
        self.period_selector.currentIndexChanged.connect(self._period_changed)
        self.start_date = self._date_edit()
        self.end_date = self._date_edit()
        create_button = QPushButton("Crear período")
        create_button.setObjectName("primaryButton")
        create_button.clicked.connect(self._create_period)
        controls.addWidget(QLabel("Período"))
        controls.addWidget(self.period_selector)
        controls.addWidget(QLabel("Desde"))
        controls.addWidget(self.start_date)
        controls.addWidget(QLabel("Hasta"))
        controls.addWidget(self.end_date)
        controls.addWidget(create_button)
        controls.addStretch()
        layout.addLayout(controls)

        # Barra de acciones organizada en 3 grupos funcionales claros
        actions = QHBoxLayout()
        actions.setSpacing(8)

        # GRUPO 1 — Ciclo de Liquidación (flujo secuencial de nómina con fondo distintivo sutil)
        self.cycle_group_frame = QFrame()
        self.cycle_group_frame.setObjectName("payrollCycleGroup")
        cycle_layout = QHBoxLayout(self.cycle_group_frame)
        cycle_layout.setContentsMargins(4, 3, 4, 3)
        cycle_layout.setSpacing(4)

        self.calculate_button = self._action_button("Calcular", self._calculate, "payrollPrimaryBtn")
        self.calculate_button.setToolTip("Calcular nómina para el período seleccionado")
        self.recalculate_button = self._action_button("Recalcular", self._recalculate, "payrollSecondaryBtn")
        self.recalculate_button.setToolTip("Recalcular liquidación del ciclo actual")
        self.approve_button = self._action_button("Aprobar", self._approve, "payrollPrimaryBtn")
        self.approve_button.setToolTip("Aprobar ciclo de nómina calculado")
        self.close_button = self._action_button("Cerrar", self._close, "payrollPrimaryBtn")
        self.close_button.setToolTip("Cerrar definitivamente el ciclo de nómina")

        cycle_layout.addWidget(self.calculate_button)
        cycle_layout.addWidget(self.recalculate_button)
        cycle_layout.addWidget(self.approve_button)
        cycle_layout.addWidget(self.close_button)
        actions.addWidget(self.cycle_group_frame)

        # Separador visual sutil entre Grupo 1 y Grupo 2
        self.sep_cycle_selected = QFrame()
        self.sep_cycle_selected.setObjectName("payrollVerticalSep")
        self.sep_cycle_selected.setFrameShape(QFrame.Shape.VLine)
        actions.addWidget(self.sep_cycle_selected)

        # GRUPO 2 — Empleado seleccionado (acciones contextuales de tabla)
        self.view_detail_button = self._action_button("Ver detalle", self._show_selected_detail, "payrollSecondaryBtn")
        self.view_detail_button.setIcon(icon("eye", "#16A34A", 14))
        self.view_detail_button.setToolTip("Ver detalle de liquidación del empleado seleccionado (o doble clic)")
        self.single_slip_button = self._action_button("Desprendible", self._individual_payslip, "payrollSecondaryBtn")
        self.single_slip_button.setToolTip("Desprendible individual: Generar PDF para el empleado seleccionado")

        self.view_detail_button.setEnabled(False)
        self.single_slip_button.setEnabled(False)

        actions.addWidget(self.view_detail_button)
        actions.addWidget(self.single_slip_button)

        # Separador visual sutil entre Grupo 2 y Grupo 3
        self.sep_selected_reports = QFrame()
        self.sep_selected_reports.setObjectName("payrollVerticalSep")
        self.sep_selected_reports.setFrameShape(QFrame.Shape.VLine)
        actions.addWidget(self.sep_selected_reports)

        # GRUPO 3 — Reportería y consultas globales (menú desplegable compacto)
        self.reports_button = QToolButton()
        self.reports_button.setObjectName("payrollMoreBtn")
        self.reports_button.setText("Reportes")
        self.reports_button.setIcon(icon("chart", "#16A34A", 14))
        self.reports_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.reports_button.setToolTip("Reportes globales y consultas de nómina")
        self.reports_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self.reports_menu = QMenu(self.reports_button)
        self.all_slips_action = QAction("Generar todos los desprendibles", self)
        self.all_slips_action.setIcon(icon("file-text", "#16A34A", 14))
        self.all_slips_action.setToolTip("Generar lote completo de desprendibles de pago en PDF")
        self.all_slips_action.triggered.connect(lambda: self._all_payslips())

        self.dashboard_action = QAction("Dashboard financiero", self)
        self.dashboard_action.setIcon(icon("chart", "#16A34A", 14))
        self.dashboard_action.setToolTip("Abrir tablero financiero y analítico de nómina")
        self.dashboard_action.triggered.connect(lambda: self._open_dashboard())

        self.reports_menu.addAction(self.all_slips_action)
        self.reports_menu.addAction(self.dashboard_action)
        self.reports_button.setMenu(self.reports_menu)

        # Aliases para mantener compatibilidad con atributos históricos
        self.all_slips_button = self.all_slips_action
        self.dashboard_button = self.dashboard_action

        actions.addWidget(self.reports_button)
        actions.addStretch()
        layout.addLayout(actions)

        # Banner de advertencia de ARL Clase I por defecto
        self.arl_warning_banner = QFrame()
        self.arl_warning_banner.setObjectName("arlWarningBanner")
        self.arl_warning_banner.setStyleSheet(
            """
            #arlWarningBanner {
                background-color: #FEF3C7;
                border: 1px solid #F59E0B;
                border-radius: 8px;
            }
            """
        )
        banner_layout = QHBoxLayout(self.arl_warning_banner)
        banner_layout.setContentsMargins(14, 8, 14, 8)
        banner_layout.setSpacing(10)
        self.arl_warning_icon = QLabel()
        self.arl_warning_icon.setPixmap(pixmap("warning", "#D97706", 18))
        self.arl_warning_icon.setStyleSheet("background: transparent;")
        self.arl_warning_text = QLabel("Atención: Existen empleados activos asignados a ARL Clase 'I' (Riesgo Mínimo).")
        self.arl_warning_text.setStyleSheet("color: #92400E; font-weight: 600; font-size: 13px; background: transparent;")
        self.arl_warning_text.setWordWrap(True)
        self.arl_review_button = QPushButton("Revisar empleados")
        self.arl_review_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.arl_review_button.setStyleSheet(
            """
            QPushButton {
                background-color: #D97706;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #B45309;
            }
            """
        )
        self.arl_review_button.clicked.connect(self._show_default_arl_dialog)
        banner_layout.addWidget(self.arl_warning_icon)
        banner_layout.addWidget(self.arl_warning_text, stretch=1)
        banner_layout.addWidget(self.arl_review_button)
        self.arl_warning_banner.hide()
        layout.addWidget(self.arl_warning_banner)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar empleado...")
        self.search.textChanged.connect(self._render_run)
        self.type_filter = QComboBox()
        self.type_filter.addItem("Todos los tipos", "ALL")
        self.type_filter.addItem("Docente", "Professor")
        self.type_filter.addItem("Personal Administrativo", "Administrative")
        self.type_filter.currentIndexChanged.connect(self._render_run)
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Todos los estados", "Liquidado", "Con error"])
        self.status_filter.currentIndexChanged.connect(self._render_run)
        filters.addWidget(self.search, stretch=2)
        filters.addWidget(self.type_filter)
        filters.addWidget(self.status_filter)
        layout.addLayout(filters)

        summary = QGridLayout()
        summary.setHorizontalSpacing(16)
        summary.setVerticalSpacing(6)
        self.summary_labels = {}
        summary_items = [
            ("gross_salary", "Total nómina"),
            ("total_employee_deductions", "Total deducciones"),
            ("ibc", "IBC total"),
            ("total_employer_contributions", "Aportes patronales"),
            ("total_employer_cost", "Costo empleador"),
        ]
        for idx, (key, title) in enumerate(summary_items):
            label = QLabel(f"{title}: $ 0")
            label.setStyleSheet("font-size: 13px; font-weight: 700; color: #0F172A;")
            label.setWordWrap(True)
            if key == "ibc":
                label.setToolTip(get_acronym_tooltip("IBC"))
            self.summary_labels[key] = (title, label)
            summary.addWidget(label, idx // 3, idx % 3)
        layout.addLayout(summary)

        self.status_label = QLabel("Estado de liquidación: sin período")
        self.status_label.setStyleSheet("font-weight: 700; color: #64748B;")
        layout.addWidget(self.status_label)

        self.table = DataTable(
            headers=self.COLUMNS,
            stretch_column="Empleado",
            column_types=("text", "center", "center", "money", "money", "money", "money", "money", "money", "status"),
        )
        ibc_col = self.COLUMNS.index("IBC") if "IBC" in self.COLUMNS else -1
        if ibc_col >= 0:
            header_item = self.table.horizontalHeaderItem(ibc_col)
            if header_item:
                header_item.setToolTip(get_acronym_tooltip("IBC"))
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.table.itemDoubleClicked.connect(lambda *_: self._show_selected_detail())
        layout.addWidget(self.table)
        self.pagination = PaginationBar(parent=self)
        self.pagination.connect_table(self.table)
        self.page_info = self.pagination.page_info
        self.page_buttons = self.pagination.page_buttons
        layout.addWidget(self.pagination)

        history_title = QLabel("Historial de liquidaciones")
        history_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #0F172A;")
        layout.addWidget(history_title)
        self.history_table = QTableWidget(0, 4)
        self.history_table.setHorizontalHeaderLabels(("Período", "Estado", "Ejecución", "Empleados"))
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.history_table)
        layout.addStretch()

    @staticmethod
    def _date_edit():
        editor = QDateEdit(QDate.currentDate())
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("yyyy-MM-dd")
        editor.setMinimumWidth(105)
        editor.setMinimumHeight(34)
        # Estilos del popup vía app.qss; no forzar stylesheet aquí
        # porque rompe el botón que abre el calendario en algunos estilos Qt.
        return editor

    @staticmethod
    def _action_button(text, handler, object_name="primaryButton"):
        button = QPushButton(text)
        button.setObjectName(object_name)
        button.clicked.connect(handler)
        return button

    def _build_pagination(self):
        """Retorna el componente de paginación."""
        return self.pagination

    def _employees(self):
        return list(self.manager.professors) + list(self.manager.administrative_staff)

    def _selected_period(self):
        return self.cycle.get_period(self.period_selector.currentData())

    def _create_period(self):
        # PySide6 tipa ``toPython`` como object en algunas versiones, aunque
        # para QDate devuelve un datetime.date en ejecución.
        start = cast(date, self.start_date.date().toPython())
        end = cast(date, self.end_date.date().toPython())
        start_iso = start.isoformat()
        end_iso = end.isoformat()
        try:
            self.cycle.create_period(
                int(start.year), int(start.month), start_iso, end_iso,
            )
        except (TypeError, ValueError) as exc:
            self._error("No se pudo crear el período", exc)
            return
        self._load_periods()
        self.period_selector.setCurrentIndex(self.period_selector.count() - 1)
        self.changed.emit()

    def _calculate(self):
        period = self._selected_period()
        if period is None:
            self._error("No se puede calcular", "Selecciona o crea un período válido.")
            return
        try:
            run = self.cycle.calculate_run(period.period_id, self._employees(), self.rules)
        except (TypeError, ValueError) as exc:
            self._error("No se pudo calcular la nómina", exc)
            return
        self._notice("Nómina calculada", f"Liquidación creada para {len(run.details)} empleados.")
        self.refresh()
        self.changed.emit()

    def _recalculate(self):
        period = self._selected_period()
        run = self._run_for(period)
        if run is None:
            self._calculate()
            return
        try:
            if run.status.value != "CALCULATED":
                raise ValueError("solo se puede recalcular una liquidación calculada y no aprobada")
            self.cycle.create_correction_run(
                period.period_id, self._employees(), self.rules,
                actor="gui", reason=f"recalculo solicitado para {run.run_id}",
            )
        except (TypeError, ValueError) as exc:
            self._error("No se pudo recalcular la nómina", exc)
            return
        self.refresh()
        self.changed.emit()

    def _approve(self):
        run = self._run_for(self._selected_period())
        if run is None:
            self._error("No se puede aprobar", "Primero calcula la nómina del período.")
            return
        try:
            self.cycle.approve_run(run.run_id)
        except ValueError as exc:
            self._error("No se pudo aprobar", exc)
            return
        self.refresh()
        self.changed.emit()

    def _close(self):
        run = self._run_for(self._selected_period())
        if run is None:
            self._error("No se puede cerrar", "Primero calcula y aprueba la nómina.")
            return
        try:
            self.cycle.close_run(run.run_id)
        except ValueError as exc:
            self._error("No se pudo cerrar", exc)
            return
        self.refresh()
        self.changed.emit()

    def _run_for(self, period):
        if period is None:
            return None
        return next(
            (run for run in reversed(self.cycle.runs) if run.period_id == period.period_id),
            None,
        )

    def _period_changed(self):
        self._render_run()
        self._render_history()

    def _load_periods(self):
        selected = self.period_selector.currentData()
        self.period_selector.blockSignals(True)
        self.period_selector.clear()
        for period in self.cycle.periods:
            self.period_selector.addItem(
                f"{period.year}-{period.month:02d} · {get_payroll_status_label(period.status)}", period.period_id
            )
        self.period_selector.blockSignals(False)
        if selected:
            index = self.period_selector.findData(selected)
            if index >= 0:
                self.period_selector.setCurrentIndex(index)

    @staticmethod
    def _money(value):
        if value is None or value in ("-", ""):
            return "$ 0"
        try:
            return f"$ {int(float(value)):,}".replace(",", ".")
        except (ValueError, TypeError):
            return str(value)

    def _render_run(self):
        run = self._run_for(self._selected_period())
        details = list(run.details) if run else []
        self._details = []
        search = self.search.text().strip().lower()
        employee_names = {str(getattr(item, "professor_id", getattr(item, "administrative_id", ""))): item.full_name for item in self._employees()}
        rows = []
        selected_type = self.type_filter.currentData()
        for detail in details:
            employee_id = str(detail.get("employee_id", ""))
            employee = next((item for item in self._employees() if str(getattr(item, "professor_id", getattr(item, "administrative_id", ""))) == employee_id), None)
            name = employee_names.get(employee_id, employee_id)
            if search and search not in name.lower():
                continue
            if selected_type and selected_type != "ALL" and detail.get("employee_type") != selected_type:
                continue
            if self.status_filter.currentText() == "Con error":
                continue
            self._details.append(detail)
            emp_type_label = get_employee_type_label(detail.get("employee_type", ""))
            rows.append((
                name, emp_type_label, detail.get("period", ""),
                self._money(detail.get("base_salary", 0)), self._money(detail.get("gross_salary", 0)),
                self._money(detail.get("total_employee_deductions", 0)), self._money(detail.get("ibc", 0)),
                self._money(detail.get("net_salary", 0)), self._money(detail.get("total_employer_cost", 0)),
                "Liquidado",
            ))
        self.table.populate(rows)
        self._update_pagination()
        self._update_summary(run)
        self._update_actions(run)
        period = self._selected_period()
        status_label_text = get_payroll_status_label(period.status) if period else 'sin período'
        self.status_label.setText(f"Estado de liquidación: {status_label_text}")

    def _update_summary(self, run):
        totals = run.totals if run else {}
        if run:
            totals = dict(totals)
            totals["ibc"] = sum((float(detail.get("ibc", 0) or 0) for detail in run.details), 0.0)
        for key, (title, label) in self.summary_labels.items():
            label.setText(f"{title}: {self._money(totals.get(key, 0))}")

    def _update_actions(self, run):
        status = run.status.value if run else ""
        self.calculate_button.setEnabled(run is None)
        self.recalculate_button.setEnabled(status == "CALCULATED")
        self.approve_button.setEnabled(status == "CALCULATED")
        self.close_button.setEnabled(status == "APPROVED")
        self.all_slips_button.setEnabled(bool(run))
        self._on_table_selection_changed()

    def _on_table_selection_changed(self):
        """Actualiza el estado de los botones contextuales de forma pasiva sin abrir diálogos."""
        source_row = self.table.current_source_row()
        has_selection = 0 <= source_row < len(self._details)
        run = self._run_for(self._selected_period())
        self.view_detail_button.setEnabled(has_selection)
        self.single_slip_button.setEnabled(has_selection and bool(run))

    def _update_pagination(self):
        self.pagination.update_pagination(
            current_page=self.table.page,
            total_pages=self.table.page_count,
            total_rows=self.table.total_rows,
            page_size=self.table.page_size,
        )

    def _show_selected_detail(self):
        source_row = self.table.current_source_row()
        if source_row < 0 or source_row >= len(self._details):
            self._notice("Detalle de liquidación", "Selecciona un empleado de la tabla para ver su detalle.")
            return
        detail = self._details[source_row]
        employee_id = str(detail.get("employee_id", ""))
        employee = next(
            (
                item for item in self._employees()
                if str(getattr(item, "professor_id", getattr(item, "administrative_id", ""))) == employee_id
            ),
            None,
        )
        employee_name = getattr(employee, "full_name", None) or employee_id

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Detalle de liquidación · {employee_name}")
        dialog.resize(640, 620)
        dialog.setMinimumSize(520, 480)
        dialog.setStyleSheet(
            """
            QDialog { background-color: #FFFFFF; color: #0F172A; }
            QLabel#detailTitle { color: #0F172A; font-size: 15px; font-weight: 800; background: transparent; }
            QLabel#detailSubtitle { color: #64748B; font-size: 13px; background: transparent; }
            QLabel#detailSection { color: #14532D; font-size: 13px; font-weight: 800; background: transparent; }
            QLabel#detailKey { color: #64748B; font-size: 13px; background: transparent; }
            QLabel#detailValue { color: #0F172A; font-size: 13px; font-weight: 600; background: transparent; }
            QFrame#detailPanel {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            QScrollArea { background-color: #FFFFFF; border: none; }
            QTableWidget {
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                gridline-color: #F1F5F9;
            }
            QHeaderView::section {
                background-color: #F8FAFC;
                color: #64748B;
                border: none;
                border-bottom: 1px solid #E2E8F0;
                padding: 6px 8px;
                font-size: 11px;
                font-weight: 700;
            }
            """
        )

        root = QVBoxLayout(dialog)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel(employee_name)
        title.setObjectName("detailTitle")
        emp_type_desc = get_employee_type_label(detail.get('employee_type', 'Empleado'))
        subtitle = QLabel(
            f"{emp_type_desc} · Período {detail.get('period', '-')} · "
            f"{detail.get('days_worked', 0)} días trabajados"
        )
        subtitle.setObjectName("detailSubtitle")
        if detail.get('employee_type') == "Administrative":
            subtitle.setToolTip(get_acronym_tooltip("CST"))
        root.addWidget(title)
        root.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        content = QWidget()
        content.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 4, 12, 28)
        content_layout.setSpacing(12)
        content_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)

        for section_title, fields in self.DETAIL_SECTIONS:
            content_layout.addWidget(self._detail_section(section_title, fields, detail))

        salary_concepts = detail.get("salary_concepts") or []
        non_salary_concepts = detail.get("non_salary_concepts") or []
        if salary_concepts:
            content_layout.addWidget(self._detail_concepts("Conceptos salariales", salary_concepts))
        if non_salary_concepts:
            content_layout.addWidget(self._detail_concepts("Conceptos no salariales", non_salary_concepts))

        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        close_button = QPushButton("Cerrar")
        close_button.setObjectName("primaryButton")
        close_button.clicked.connect(dialog.accept)
        root.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
        dialog.exec()

    def _detail_section(self, title, fields, detail):
        panel = QFrame()
        panel.setObjectName("detailPanel")
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        heading = QLabel(title)
        heading.setObjectName("detailSection")
        layout.addWidget(heading)

        form = QFormLayout()
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(6)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        for key, label, kind in fields:
            raw = detail.get(key, "-")
            value = self._money(raw) if kind == "money" else str(raw)
            key_label = QLabel(label)
            key_label.setObjectName("detailKey")
            value_label = QLabel(value)
            value_label.setObjectName("detailValue")
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            form.addRow(key_label, value_label)
        layout.addLayout(form)
        return panel

    def _detail_concepts(self, title, concepts):
        panel = QFrame()
        panel.setObjectName("detailPanel")
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        heading = QLabel(title)
        heading.setObjectName("detailSection")
        layout.addWidget(heading)

        # Filas simples en lugar de QTableWidget: evita scroll anidado
        # que corta el contenido y no deja llegar al final del modal.
        for concept in concepts:
            amount = concept.get("amount", 0)
            try:
                amount_text = self._money(amount)
            except (TypeError, ValueError):
                amount_text = str(amount)
            affects = "Sí" if concept.get("affects_ibc") else "No"
            row = QHBoxLayout()
            code_label = QLabel(str(concept.get("code", "")))
            code_label.setObjectName("detailKey")
            meta_label = QLabel(f"{amount_text}  ·  Afecta IBC: {affects}")
            meta_label.setToolTip(get_acronym_tooltip("IBC"))
            meta_label.setObjectName("detailValue")
            meta_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(code_label)
            row.addStretch()
            row.addWidget(meta_label)
            layout.addLayout(row)
        return panel

    def _individual_payslip(self):
        row = self.table.current_source_row()
        if row < 0 or row >= len(self._details):
            self._error("Desprendible individual", "Selecciona un empleado de la tabla.")
            return
        detail = self._details[row]
        path, _ = QFileDialog.getSaveFileName(self, "Guardar desprendible", "desprendible.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            service = self._payslip_service()
            service.generate_payslip_pdf(detail["employee_id"], self._selected_period().period_id, self.rules, path)
        except (TypeError, ValueError, OSError) as exc:
            self._error("No se pudo generar el desprendible", exc)
            return
        self._notice("Desprendible generado", path)

    def _all_payslips(self):
        period = self._selected_period()
        if period is None:
            return
        folder = QFileDialog.getExistingDirectory(self, "Carpeta de desprendibles")
        if not folder:
            return
        try:
            service = self._payslip_service()
            for payslip in service.generate_period_payslips(period.period_id, self.rules):
                service.render_pdf(payslip, Path(folder) / f"desprendible_{payslip.employee['internal_id']}.pdf")
        except (TypeError, ValueError, OSError) as exc:
            self._error("No se pudieron generar todos los desprendibles", exc)
            return
        self._notice("Desprendibles generados", f"Documentos guardados en {folder}.")

    def _payslip_service(self):
        return PayslipService(
            self.cycle, self.manager.professors, self.manager.faculties,
            administrative_staff=self.manager.administrative_staff,
        )

    def _open_dashboard(self):
        PayrollDashboardDialog(
            self.cycle,
            self.manager.professors,
            self.manager.faculties,
            self,
            administrative_staff=self.manager.administrative_staff,
        ).exec()

    def _render_history(self):
        row_count = len(self.cycle.periods)
        self.history_table.setRowCount(row_count)
        for row, period in enumerate(self.cycle.periods):
            run = self._run_for(period)
            values = (
                f"{period.year}-{period.month:02d}", get_payroll_status_label(period.status),
                run.executed_at if run else "-", str(len(run.details)) if run else "0",
            )
            for column, value in enumerate(values):
                self.history_table.setItem(row, column, QTableWidgetItem(value))

        header_h = self.history_table.horizontalHeader().height() or 33
        rows_h = sum(self.history_table.rowHeight(i) for i in range(row_count))
        if rows_h == 0 and row_count > 0:
            rows_h = row_count * (self.history_table.verticalHeader().defaultSectionSize() or 30)
        elif row_count == 0:
            rows_h = 40
        self.history_table.setFixedHeight(header_h + rows_h + self.history_table.frameWidth() * 2 + 4)
        self.history_table.updateGeometry()

    def _get_default_arl_employees(self):
        default_employees = []
        for emp in self._employees():
            if getattr(emp, "active", True):
                risk_class = getattr(emp, "arl_risk_class", "I")
                if risk_class == "I":
                    default_employees.append(emp)
        return default_employees

    def _update_arl_warning(self):
        default_emps = self._get_default_arl_employees()
        if default_emps:
            count = len(default_emps)
            self.arl_warning_text.setWordWrap(True)
            self.arl_warning_text.setText(
                f"Atención: {count} empleado(s) activo(s) tienen asignada ARL Clase 'I' (Riesgo Mínimo - 0.522%). "
                "Verifique si desempeñan labores de mayor riesgo (laboratorios, talleres, etc.)."
            )
            self.arl_warning_banner.show()
        else:
            self.arl_warning_banner.hide()

    def _show_default_arl_dialog(self):
        default_emps = self._get_default_arl_employees()
        dialog = QDialog(self)
        dialog.setWindowTitle("Empleados con ARL Clase I (Riesgo Mínimo)")
        dialog.resize(600, 420)
        dialog.setMinimumSize(500, 360)
        dialog.setStyleSheet(
            """
            QDialog { background-color: #FFFFFF; color: #0F172A; }
            QLabel#dialogTitle { color: #0F172A; font-size: 15px; font-weight: 800; background: transparent; }
            QLabel#dialogSubtitle { color: #64748B; font-size: 13px; background: transparent; }
            """
        )
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Empleados activos con ARL Clase I por defecto")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Los siguientes empleados activos tienen configurada la Clase I (0.522%).\n"
            "Si algún empleado realiza labores con mayor exposición a riesgos laborales\n"
            "(laboratorios químicos, talleres mecánicos, trabajo de campo, etc.),\n"
            "actualice su clase en la sección de Profesores o Administrativos."
        )
        subtitle.setObjectName("dialogSubtitle")
        layout.addWidget(subtitle)

        table = QTableWidget(len(default_emps), 4)
        table.setHorizontalHeaderLabels(("ID", "Nombre", "Tipo", "Clase ARL"))
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)

        for row, emp in enumerate(default_emps):
            is_prof = hasattr(emp, "professor_id")
            emp_id = str(getattr(emp, "professor_id" if is_prof else "administrative_id", ""))
            emp_type = "Profesor" if is_prof else "Administrativo"
            name = getattr(emp, "full_name", "")
            risk = getattr(emp, "arl_risk_class", "I")

            table.setItem(row, 0, QTableWidgetItem(emp_id))
            table.setItem(row, 1, QTableWidgetItem(name))
            table.setItem(row, 2, QTableWidgetItem(emp_type))
            table.setItem(row, 3, QTableWidgetItem(f"Clase {risk} (0.522%)"))

        layout.addWidget(table)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        close_btn = QPushButton("Cerrar")
        close_btn.setObjectName("primaryButton")
        close_btn.clicked.connect(dialog.accept)
        btn_box.addWidget(close_btn)
        layout.addLayout(btn_box)

        dialog.exec()

    def refresh(self):
        self._load_periods()
        self._update_arl_warning()
        self._render_run()
        self._render_history()

    def _error(self, title, error):
        QMessageBox.critical(self, title, str(error))

    def _notice(self, title, message):
        QMessageBox.information(self, title, message)
