"""Página de operación del ciclo formal de nómina."""
from datetime import date
from pathlib import Path
from typing import cast

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.payroll_period import PayrollPeriodStatus
from services.payroll_engine import PayrollRules
from services.payslip_service import PayslipService
from ..components.data_table import DataTable
from ..components.page_header import PageHeader
from .payroll_dashboard import PayrollDashboardDialog


class PayrollPage(QWidget):
    """Opera el ciclo de nómina sin duplicar la lógica del motor."""

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
        self.period_selector.setMinimumWidth(220)
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

        actions = QHBoxLayout()
        self.calculate_button = self._action_button("Calcular nómina", self._calculate)
        self.recalculate_button = self._action_button("Recalcular", self._recalculate, "secondaryButton")
        self.approve_button = self._action_button("Aprobar", self._approve)
        self.close_button = self._action_button("Cerrar", self._close)
        self.single_slip_button = self._action_button("Desprendible individual", self._individual_payslip, "secondaryButton")
        self.all_slips_button = self._action_button("Generar todos los desprendibles", self._all_payslips, "secondaryButton")
        self.dashboard_button = self._action_button("Dashboard financiero", self._open_dashboard, "secondaryButton")
        for button in (self.calculate_button, self.recalculate_button, self.approve_button,
                   self.close_button, self.single_slip_button, self.all_slips_button, self.dashboard_button):
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar empleado...")
        self.search.textChanged.connect(self._render_run)
        self.type_filter = QComboBox()
        self.type_filter.addItems(["Todos los tipos", "Professor", "Administrative"])
        self.type_filter.currentIndexChanged.connect(self._render_run)
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Todos los estados", "Liquidado", "Con error"])
        self.status_filter.currentIndexChanged.connect(self._render_run)
        filters.addWidget(self.search, stretch=2)
        filters.addWidget(self.type_filter)
        filters.addWidget(self.status_filter)
        layout.addLayout(filters)

        summary = QHBoxLayout()
        self.summary_labels = {}
        for key, title in (
            ("gross_salary", "Total nómina"),
            ("total_employee_deductions", "Total deducciones"),
            ("total_employer_contributions", "Aportes patronales"),
            ("total_employer_cost", "Costo empleador"),
            ("ibc", "IBC total"),
        ):
            label = QLabel(f"{title}: $ 0")
            label.setStyleSheet("font-size: 12px; font-weight: 700; color: #0F172A;")
            self.summary_labels[key] = (title, label)
            summary.addWidget(label)
        summary.addStretch()
        layout.addLayout(summary)

        self.status_label = QLabel("Estado de liquidación: sin período")
        self.status_label.setStyleSheet("font-weight: 700; color: #64748B;")
        layout.addWidget(self.status_label)

        self.table = DataTable(headers=self.COLUMNS)
        self.table.setMinimumHeight(260)
        self.table.itemSelectionChanged.connect(self._show_selected_detail)
        layout.addWidget(self.table)
        self.pagination = self._build_pagination()
        layout.addWidget(self.pagination)

        history_title = QLabel("Historial de liquidaciones")
        history_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #0F172A;")
        layout.addWidget(history_title)
        self.history_table = QTableWidget(0, 4)
        self.history_table.setHorizontalHeaderLabels(("Período", "Estado", "Ejecución", "Empleados"))
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.history_table)

    @staticmethod
    def _date_edit():
        editor = QDateEdit(QDate.currentDate())
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("yyyy-MM-dd")
        editor.setMinimumWidth(148)
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
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(4, 0, 4, 0)
        self.page_info = QLabel()
        self.page_info.setStyleSheet("color: #94A3B8; font-size: 11px;")
        footer_layout.addWidget(self.page_info)
        footer_layout.addStretch()
        self.page_buttons = QHBoxLayout()
        footer_layout.addLayout(self.page_buttons)
        self.table.page_changed.connect(lambda *_: self._update_pagination())
        return footer

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
                f"{period.year}-{period.month:02d} · {period.status.value}", period.period_id
            )
        self.period_selector.blockSignals(False)
        if selected:
            index = self.period_selector.findData(selected)
            if index >= 0:
                self.period_selector.setCurrentIndex(index)

    @staticmethod
    def _money(value):
        return f"$ {int(value):,}".replace(",", ".")

    def _render_run(self):
        run = self._run_for(self._selected_period())
        details = list(run.details) if run else []
        self._details = []
        search = self.search.text().strip().lower()
        employee_names = {str(getattr(item, "professor_id", getattr(item, "administrative_id", ""))): item.full_name for item in self._employees()}
        rows = []
        for detail in details:
            employee_id = str(detail.get("employee_id", ""))
            employee = next((item for item in self._employees() if str(getattr(item, "professor_id", getattr(item, "administrative_id", ""))) == employee_id), None)
            name = employee_names.get(employee_id, employee_id)
            if search and search not in name.lower():
                continue
            if self.type_filter.currentText() != "Todos los tipos" and detail.get("employee_type") != self.type_filter.currentText():
                continue
            if self.status_filter.currentText() == "Con error":
                continue
            self._details.append(detail)
            rows.append((
                name, detail.get("employee_type", ""), detail.get("period", ""),
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
        self.status_label.setText(f"Estado de liquidación: {period.status.value if period else 'sin período'}")

    def _update_summary(self, run):
        totals = run.totals if run else {}
        if run:
            totals = dict(totals)
            totals["ibc"] = sum((detail.get("ibc", 0) for detail in run.details), 0)
        for key, (title, label) in self.summary_labels.items():
            label.setText(f"{title}: {self._money(totals.get(key, 0))}")

    def _update_actions(self, run):
        status = run.status.value if run else ""
        self.calculate_button.setEnabled(run is None)
        self.recalculate_button.setEnabled(status == "CALCULATED")
        self.approve_button.setEnabled(status == "CALCULATED")
        self.close_button.setEnabled(status == "APPROVED")
        self.single_slip_button.setEnabled(bool(run))
        self.all_slips_button.setEnabled(bool(run))

    def _update_pagination(self):
        total = self.table.total_rows
        start = 0 if total == 0 else (self.table.page - 1) * self.table.page_size + 1
        end = min(self.table.page * self.table.page_size, total)
        self.page_info.setText(f"Mostrando {start}-{end} de {total} registros")
        while self.page_buttons.count():
            item = self.page_buttons.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for page in range(1, self.table.page_count + 1):
            button = QPushButton(str(page))
            button.setFixedSize(27, 27)
            button.clicked.connect(lambda checked=False, target=page: self.table.set_page(target))
            self.page_buttons.addWidget(button)
        self.pagination.setVisible(total > self.table.page_size)

    def _show_selected_detail(self):
        source_row = self.table.current_source_row()
        if source_row < 0 or source_row >= len(self._details):
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
            QLabel#detailTitle { color: #0F172A; font-size: 16px; font-weight: 800; background: transparent; }
            QLabel#detailSubtitle { color: #64748B; font-size: 12px; background: transparent; }
            QLabel#detailSection { color: #14532D; font-size: 12px; font-weight: 800; background: transparent; }
            QLabel#detailKey { color: #64748B; font-size: 12px; background: transparent; }
            QLabel#detailValue { color: #0F172A; font-size: 12px; font-weight: 600; background: transparent; }
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
                font-size: 10px;
                font-weight: 700;
            }
            """
        )

        root = QVBoxLayout(dialog)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel(employee_name)
        title.setObjectName("detailTitle")
        subtitle = QLabel(
            f"{detail.get('employee_type', 'Empleado')} · Período {detail.get('period', '-')} · "
            f"{detail.get('days_worked', 0)} días"
        )
        subtitle.setObjectName("detailSubtitle")
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
        self.history_table.setRowCount(len(self.cycle.periods))
        for row, period in enumerate(self.cycle.periods):
            run = self._run_for(period)
            values = (
                f"{period.year}-{period.month:02d}", period.status.value,
                run.executed_at if run else "-", str(len(run.details)) if run else "0",
            )
            for column, value in enumerate(values):
                self.history_table.setItem(row, column, QTableWidgetItem(value))

    def refresh(self):
        self._load_periods()
        self._render_run()
        self._render_history()

    def _error(self, title, error):
        QMessageBox.critical(self, title, str(error))

    def _notice(self, title, message):
        QMessageBox.information(self, title, message)
