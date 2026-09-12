"""Dashboard principal de NexoCampus basado en datos reales del EntityManager."""
import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCharts import QChart, QChartView, QPieSeries

from persistence.file_manager import DATA_DIRECTORY
from ..components.icons import icon, pixmap
from ..components.stat_card import StatCard
from ..i18n.labels import get_acronym_tooltip


class DashboardPage(QWidget):
    """Página de inicio con resumen general, responsive y métricas en tiempo real de la universidad."""

    def __init__(self, manager, navigate_fn, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.navigate_fn = navigate_fn
        self.cards = {}
        self._card_list = []
        self._current_cols = 4
        self._baseline_counts = self._load_baseline_counts()
        self._last_counts = {}

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Header de Bienvenida con período dinámico
        header_layout = QHBoxLayout()
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        self.lbl_title = QLabel("Inicio")
        self.lbl_title.setObjectName("dashboardTitle")
        self.lbl_subtitle = QLabel("Vista general del sistema universitario")
        self.lbl_subtitle.setObjectName("dashboardSubtitle")

        text_layout.addWidget(self.lbl_title)
        text_layout.addWidget(self.lbl_subtitle)
        header_layout.addLayout(text_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Grilla responsive de 8 StatCards
        self.cards_grid = QGridLayout()
        self.cards_grid.setHorizontalSpacing(12)
        self.cards_grid.setVerticalSpacing(12)

        card_defs = [
            ("Facultades", "Total registradas", "#DCFCE7", "#16A34A", "Facultades"),
            ("Programas", "Total registrados", "#D1FAE5", "#059669", "Programas"),
            ("Cursos", "Total registrados", "#DBEAFE", "#2563EB", "Cursos"),
            ("Estudiantes", "Total registrados", "#EDE9FE", "#7C3AED", "Estudiantes"),
            ("Profesores", "Total registrados", "#D1FAE5", "#059669", "Profesores"),
            ("Administrativos", "Total registrados", "#FEF3C7", "#D97706", "Administrativos"),
            ("Inscripciones activas", "En el período actual", "#DCFCE7", "#16A34A", "Inscripciones"),
            ("Alertas EBRA", "Estudiantes en riesgo", "#FEE2E2", "#DC2626", "Estudiantes"),
        ]

        self._card_list.clear()
        for idx, (lbl, detail, bg, color, nav_target) in enumerate(card_defs):
            card = StatCard(lbl, "0", detail, delta="", bg_color=bg, text_color=color)
            if "EBRA" in lbl:
                card.setToolTip(get_acronym_tooltip("EBRA"))
            card.clicked.connect(lambda target=nav_target: self.navigate_fn(target))
            self.cards[lbl] = card
            self._card_list.append(card)
            self.cards_grid.addWidget(card, idx // 4, idx % 4)

        layout.addLayout(self.cards_grid)

        # Sección central responsive: Info General + Distribución (fila 1) y Actividad Reciente (fila 2)
        middle_layout = QGridLayout()
        middle_layout.setHorizontalSpacing(14)
        middle_layout.setVerticalSpacing(14)

        middle_layout.addWidget(self._build_info_panel(), 0, 0)
        middle_layout.addWidget(self._build_distribution_panel(), 0, 1)
        middle_layout.addWidget(self._build_activity_panel(), 1, 0, 1, 2)
        middle_layout.setColumnStretch(0, 1)
        middle_layout.setColumnStretch(1, 1)

        layout.addLayout(middle_layout, stretch=1)

        # Acciones Rápidas
        layout.addWidget(self._build_quick_actions())

    def _build_info_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Información General")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        fac_header = QHBoxLayout()
        fac_header.setSpacing(6)
        fac_icon = QLabel()
        fac_icon.setPixmap(pixmap("building", "#64748B", 14))
        subtitle_faculty = QLabel("Facultades con mayor población")
        subtitle_faculty.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B;")
        subtitle_faculty.setWordWrap(True)
        fac_header.addWidget(fac_icon)
        fac_header.addWidget(subtitle_faculty)
        fac_header.addStretch()
        layout.addLayout(fac_header)

        self.info_rows_layout = QVBoxLayout()
        self.info_rows_layout.setSpacing(6)
        layout.addLayout(self.info_rows_layout)
        layout.addStretch()

        # Resumen de Nómina conectado a PayrollCycleService
        payroll_box = QFrame()
        payroll_box.setObjectName("dashboardPayrollBox")
        p_layout = QVBoxLayout(payroll_box)
        p_layout.setSpacing(4)

        p_header = QHBoxLayout()
        p_header.setSpacing(6)
        p_icon = QLabel()
        p_icon.setPixmap(pixmap("money", "#16A34A", 14))
        p_lbl = QLabel("Nómina (Período más reciente)")
        p_lbl.setObjectName("dashboardPayrollTitle")
        p_lbl.setWordWrap(True)
        p_header.addWidget(p_icon)
        p_header.addWidget(p_lbl)
        p_header.addStretch()
        p_layout.addLayout(p_header)

        self.lbl_payroll_total = QLabel("Total devengado: $ 0.00")
        self.lbl_payroll_total.setObjectName("dashboardPayrollTotal")
        self.lbl_payroll_total.setWordWrap(True)

        btn_nomina = QPushButton("Ver detalle")
        btn_nomina.setIcon(icon("eye", "#16A34A", 14))
        btn_nomina.setObjectName("secondaryButton")
        btn_nomina.clicked.connect(lambda: self.navigate_fn("Nómina"))

        p_layout.addWidget(self.lbl_payroll_total)
        p_layout.addWidget(btn_nomina)

        layout.addWidget(payroll_box)
        return panel

    def _build_distribution_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Distribución por Programa")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        self.pie_series = QPieSeries()
        chart = QChart()
        chart.addSeries(self.pie_series)
        chart.setBackgroundVisible(False)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setStyleSheet("background: transparent;")
        chart_view.setMinimumSize(0, 0)

        self.chart = chart
        layout.addWidget(chart_view)
        return panel

    def _build_activity_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Actividad Reciente del Sistema")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        self.activity_rows_layout = QVBoxLayout()
        self.activity_rows_layout.setSpacing(6)
        layout.addLayout(self.activity_rows_layout)
        layout.addStretch()

        return panel

    def _build_quick_actions(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title_box = QHBoxLayout()
        title_box.setSpacing(6)
        title_icon = QLabel()
        title_icon.setPixmap(pixmap("bolt", "#16A34A", 16))
        title = QLabel("Acciones Rápidas")
        title.setObjectName("panelTitle")
        title_box.addWidget(title_icon)
        title_box.addWidget(title)
        title_box.addStretch()
        layout.addLayout(title_box)

        actions_grid = QGridLayout()
        actions_grid.setHorizontalSpacing(10)
        actions_grid.setVerticalSpacing(8)

        actions = [
            ("Facultades", "Facultades"),
            ("Programas", "Programas"),
            ("Cursos", "Cursos"),
            ("Estudiantes", "Estudiantes"),
            ("Profesores", "Profesores"),
            ("Nómina", "Nómina"),
        ]

        quick_icons = {
            "Facultades": "building",
            "Programas": "layers",
            "Cursos": "book",
            "Estudiantes": "user",
            "Profesores": "hat",
            "Nómina": "money",
        }

        for idx, (label, target) in enumerate(actions):
            btn = QPushButton(label)
            btn.setIcon(icon(quick_icons.get(label, "home"), "#16A34A", 14))
            btn.setObjectName("quickActionButton")
            btn.clicked.connect(lambda checked=False, t=target: self.navigate_fn(t))
            actions_grid.addWidget(btn, idx // 3, idx % 3)

        layout.addLayout(actions_grid)
        return panel

    def _relayout_cards(self, cols: int):
        """Reubica las 8 tarjetas en el QGridLayout según la cantidad deseada de columnas."""
        if cols == self._current_cols or not self._card_list:
            return
        self._current_cols = cols
        for i, card in enumerate(self._card_list):
            self.cards_grid.removeWidget(card)
            row = i // cols
            col = i % cols
            self.cards_grid.addWidget(card, row, col)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = event.size().width() if event is not None else self.width()
        if w > 1200:
            target_cols = 4
        elif w >= 900:
            target_cols = 3
        else:
            target_cols = 2
        self._relayout_cards(target_cols)

    def _get_active_academic_period(self) -> str:
        """Determina el período académico activo a partir de las inscripciones o el calendario."""
        mgr = self.manager
        active_statuses = {
            "ACTIVE", "ACTIVO", "COMPLETED", "APROBADO", "REPROBADO",
            "APPROVED", "FAILED", "PASSED", "FINALIZADO", "MATRICULADO", "ENROLLED"
        }
        periods = [
            str(item.academic_period).strip()
            for item in getattr(mgr, "enrollments", [])
            if hasattr(item, "academic_period") and str(item.academic_period).strip()
            and str(getattr(item, "status", "")).upper() in active_statuses
        ]
        if periods:
            most_common = Counter(periods).most_common(1)
            if most_common:
                return most_common[0][0]

        now = datetime.now()
        sem = 1 if now.month <= 6 else 2
        return f"{now.year}-{sem}"

    @staticmethod
    def _snapshot_file() -> Path:
        return DATA_DIRECTORY / "dashboard_snapshot.json"

    def _load_baseline_counts(self) -> dict | None:
        path = self._snapshot_file()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return None

    def _save_baseline_counts(self, counts: dict):
        path = self._snapshot_file()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(counts, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logging.getLogger(__name__).warning("No se pudo guardar dashboard_snapshot: %s", exc)

    def update_baseline(self, new_counts: dict | None = None):
        """Actualiza la línea base de comparación (por ejemplo, al guardar o cargar la base de datos)."""
        if new_counts:
            self._baseline_counts = dict(new_counts)
        elif self._last_counts:
            self._baseline_counts = dict(self._last_counts)
        if self._baseline_counts:
            self._save_baseline_counts(self._baseline_counts)

    def refresh(self):
        """Actualiza todos los datos del Dashboard a partir de las fuentes de verdad reales."""
        try:
            mgr = self.manager

            # 1. Período Académico Dinámico
            active_period = self._get_active_academic_period()
            self.lbl_subtitle.setText(f"Vista general del sistema universitario — Período {active_period}")

            # 2. Conteo de entidades reales
            active_statuses = {
                "ACTIVE", "ACTIVO", "COMPLETED", "APROBADO", "REPROBADO",
                "APPROVED", "FAILED", "PASSED", "FINALIZADO", "MATRICULADO", "ENROLLED"
            }
            active_enrollments = sum(
                1 for item in getattr(mgr, "enrollments", [])
                if str(getattr(item, "status", "")).upper() in active_statuses
                and str(getattr(item, "status", "")).upper() not in {"CANCELLED", "CANCELADO", "INACTIVE", "INACTIVO"}
            )
            ebra_count = mgr.count_ebra_students() if hasattr(mgr, "count_ebra_students") else sum(
                1 for s in getattr(mgr, "students", []) if mgr.evaluate_ebra_status(s.student_id).get("status") == "EBRA"
            )

            counts = {
                "Facultades": len(getattr(mgr, "faculties", [])),
                "Programas": len(getattr(mgr, "programs", [])),
                "Cursos": len(getattr(mgr, "courses", [])),
                "Estudiantes": len(getattr(mgr, "students", [])),
                "Profesores": len(getattr(mgr, "professors", [])),
                "Administrativos": len(getattr(mgr, "administrative_staff", [])),
                "Inscripciones activas": active_enrollments,
                "Alertas EBRA": ebra_count,
            }
            self._last_counts = dict(counts)

            # Inicializar línea base si aún no existe
            if self._baseline_counts is None:
                self._baseline_counts = dict(counts)
                self._save_baseline_counts(self._baseline_counts)

            # Actualizar valores y deltas verídicos en StatCards
            for label, val in counts.items():
                if label in self.cards:
                    card = self.cards[label]
                    card.set_value(val)
                    baseline_val = self._baseline_counts.get(label, val)
                    diff = val - baseline_val
                    if diff > 0:
                        delta_str = f"▲ +{diff}"
                    elif diff < 0:
                        delta_str = f"▼ {diff}"
                    else:
                        delta_str = "= 0"
                    card.set_delta(delta_str)

            # 3. Total de Nómina conectado a PayrollCycleService
            cycle = getattr(mgr, "payroll_cycle_service", None)
            latest_run = None
            latest_period = None
            if cycle and getattr(cycle, "runs", None):
                valid_statuses = {"CALCULATED", "APPROVED", "CLOSED"}
                for run in reversed(cycle.runs):
                    status_str = getattr(run.status, "value", str(run.status))
                    if status_str in valid_statuses:
                        latest_run = run
                        latest_period = cycle.get_period(run.period_id)
                        break

            if latest_run and latest_run.totals:
                gross = float(latest_run.totals.get("gross_salary", 0.0))
                if latest_period:
                    self.lbl_payroll_total.setText(
                        f"Total devengado ({latest_period.year}-{latest_period.month:02d}): $ {gross:,.2f}"
                    )
                else:
                    self.lbl_payroll_total.setText(f"Total devengado: $ {gross:,.2f}")
            else:
                self.lbl_payroll_total.setText("Total devengado: $ 0.00")

            # 4. Información General: Resumen de Facultades con más estudiantes
            while self.info_rows_layout.count():
                item = self.info_rows_layout.takeAt(0)
                if item is None:
                    continue
                w = item.widget()
                if w:
                    w.deleteLater()

            prog_faculty = {}
            for p in getattr(mgr, "programs", []):
                prog_faculty[p.program_id] = p.faculty_id

            faculty_counts = {}
            for s in getattr(mgr, "students", []):
                fid = prog_faculty.get(s.program_id)
                if fid is not None:
                    faculty_counts[fid] = faculty_counts.get(fid, 0) + 1

            total_students = len(getattr(mgr, "students", []))
            faculty_map = {f.faculty_id: f.name for f in getattr(mgr, "faculties", [])}
            sorted_faculties = sorted(faculty_counts.items(), key=lambda x: x[1], reverse=True)[:3]

            if sorted_faculties and total_students > 0:
                for fid, count in sorted_faculties:
                    fname = faculty_map.get(fid, f"Facultad #{fid}")
                    pct = (count / total_students) * 100
                    row = QWidget()
                    row_layout = QHBoxLayout(row)
                    row_layout.setContentsMargins(0, 3, 0, 3)

                    lbl_name = QLabel(fname)
                    lbl_name.setStyleSheet("font-size: 13px; color: #1E293B; font-weight: 500;")
                    lbl_name.setToolTip(fname)
                    lbl_name.setWordWrap(True)

                    lbl_count = QLabel(f"{count} est. ({pct:.0f}%)")
                    lbl_count.setStyleSheet(
                        "font-size: 11px; font-weight: 700; color: #15803D; "
                        "background: #DCFCE7; border-radius: 4px; padding: 2px 6px;"
                    )
                    lbl_count.setAlignment(Qt.AlignmentFlag.AlignRight)

                    row_layout.addWidget(lbl_name, stretch=1)
                    row_layout.addWidget(lbl_count)
                    self.info_rows_layout.addWidget(row)
            else:
                empty_info = QLabel("Sin estudiantes registrados en facultades.")
                empty_info.setStyleSheet("font-size: 11px; color: #64748B; font-style: italic;")
                empty_info.setWordWrap(True)
                self.info_rows_layout.addWidget(empty_info)

            # 5. Actividad Reciente: Registro Real de Auditoría de Nómina
            while self.activity_rows_layout.count():
                item = self.activity_rows_layout.takeAt(0)
                w = item.widget() if item is not None else None
                if w:
                    w.deleteLater()

            audits = list(getattr(cycle, "audits", [])) if cycle else []
            recent_audits = audits[-4:][::-1]

            if recent_audits:
                action_styles = {
                    "CREATE": ("#DCFCE7", "#15803D", "CREACIÓN"),
                    "CALCULATE": ("#DBEAFE", "#1D4ED8", "CÁLCULO"),
                    "CORRECT": ("#FEF3C7", "#B45309", "CORRECCIÓN"),
                    "APPROVE": ("#EDE9FE", "#6D28D9", "APROBACIÓN"),
                    "CLOSE": ("#F1F5F9", "#475569", "CIERRE"),
                }
                for audit in recent_audits:
                    row = QFrame()
                    row.setStyleSheet(
                        "background: #F8FAFC; border: 1px solid #E2E8F0; "
                        "border-radius: 6px; padding: 4px 6px;"
                    )
                    r_layout = QVBoxLayout(row)
                    r_layout.setContentsMargins(4, 3, 4, 3)
                    r_layout.setSpacing(2)

                    top_line = QHBoxLayout()
                    action = str(getattr(audit, "action", "")).upper()
                    bg, fg, action_name = action_styles.get(action, ("#F1F5F9", "#475569", action))
                    badge = QLabel(action_name)
                    badge.setStyleSheet(
                        f"background: {bg}; color: {fg}; font-size: 10px; "
                        "font-weight: 700; border-radius: 4px; padding: 1px 5px;"
                    )
                    top_line.addWidget(badge)

                    ts = str(getattr(audit, "timestamp", "")).replace("T", " ")[:16]
                    lbl_time = QLabel(ts)
                    lbl_time.setStyleSheet("font-size: 10px; color: #64748B;")
                    top_line.addStretch()
                    top_line.addWidget(lbl_time)
                    r_layout.addLayout(top_line)

                    etype = getattr(audit, "entity_type", "")
                    actor = getattr(audit, "actor", "") or "Sistema"
                    lbl_desc = QLabel(f"{etype} · Autor: {actor}")
                    lbl_desc.setStyleSheet("font-size: 11px; color: #334155;")
                    lbl_desc.setWordWrap(True)
                    r_layout.addWidget(lbl_desc)

                    self.activity_rows_layout.addWidget(row)
            else:
                empty_act = QLabel(
                    "No hay registros de auditoría recientes.\nLas actividades aparecerán aquí al registrar eventos."
                )
                empty_act.setObjectName("dashboardEmptyState")
                empty_act.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_act.setWordWrap(True)
                self.activity_rows_layout.addWidget(empty_act)

            # 6. Actualizar gráfico donut de programas
            self.pie_series.clear()
            prog_counts = {}
            for s in getattr(mgr, "students", []):
                prog = mgr.get_program(s.program_id)
                name = prog.name if prog else "Sin programa"
                prog_counts[name] = prog_counts.get(name, 0) + 1

            for name, count in prog_counts.items():
                self.pie_series.append(name, count)

            self.chart.legend().setVisible(bool(prog_counts))
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Error al refrescar %s", self.__class__.__name__
            )
            QMessageBox.warning(self, "Error", str(exc))
