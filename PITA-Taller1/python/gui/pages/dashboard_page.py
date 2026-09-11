"""Dashboard principal de NexoCampus basado en datos reales del EntityManager."""
import logging
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

from ..components.stat_card import StatCard


class DashboardPage(QWidget):
    """Página de inicio con resumen general de la universidad."""

    def __init__(self, manager, navigate_fn, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.navigate_fn = navigate_fn
        self.cards = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Header de Bienvenida
        header_layout = QHBoxLayout()
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title = QLabel("Dashboard académico")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A;")
        sub = QLabel("Vista general del sistema universitario — Período 2026-II")
        sub.setStyleSheet("font-size: 12px; color: #94A3B8;")

        text_layout.addWidget(title)
        text_layout.addWidget(sub)
        header_layout.addLayout(text_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Grilla de 8 StatCards (2 filas de 4)
        cards_grid = QGridLayout()
        cards_grid.setHorizontalSpacing(12)
        cards_grid.setVerticalSpacing(12)

        card_defs = [
            ("Facultades", "Total registradas", "▲ 1", "#DCFCE7", "#16A34A", "Facultades"),
            ("Programas", "Total registrados", "= 0", "#D1FAE5", "#059669", "Programas"),
            ("Cursos", "Total registrados", "▲ 2", "#DBEAFE", "#2563EB", "Cursos"),
            ("Estudiantes", "Total registrados", "▲ 5", "#EDE9FE", "#7C3AED", "Estudiantes"),
            ("Profesores", "Total registrados", "= 0", "#D1FAE5", "#059669", "Profesores"),
            ("Administrativos", "Total registrados", "▲ 1", "#FEF3C7", "#D97706", "Administrativos"),
            ("Inscripciones activas", "En el período actual", "▲ 7%", "#DCFCE7", "#16A34A", "Inscripciones"),
            ("Alertas EBRA", "Estudiantes en riesgo", "▲ 1", "#FEE2E2", "#DC2626", "Estudiantes"),
        ]

        for idx, (lbl, detail, delta, bg, color, nav_target) in enumerate(card_defs):
            card = StatCard(lbl, "0", detail, delta, bg, color)
            card.clicked.connect(lambda target=nav_target: self.navigate_fn(target))
            self.cards[lbl] = card
            cards_grid.addWidget(card, idx // 4, idx % 4)

        layout.addLayout(cards_grid)

        # Sección central: Info General + Distribución + Últimos Registros
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(14)

        middle_layout.addWidget(self._build_info_panel(), stretch=1)
        middle_layout.addWidget(self._build_distribution_panel(), stretch=1)
        middle_layout.addWidget(self._build_activity_panel(), stretch=1)

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

        self.info_rows_layout = QVBoxLayout()
        layout.addLayout(self.info_rows_layout)
        layout.addStretch()

        # Resumen de Nómina
        payroll_box = QFrame()
        payroll_box.setStyleSheet("background: #F8FAFC; border-radius: 8px; padding: 10px; border: 1px solid #E2E8F0;")
        p_layout = QVBoxLayout(payroll_box)
        p_layout.setSpacing(4)

        p_lbl = QLabel("💰  Nómina (Mes actual)")
        p_lbl.setStyleSheet("font-weight: 700; font-size: 12px; color: #0F172A;")

        self.lbl_payroll_total = QLabel("Total a pagar: $0.00")
        self.lbl_payroll_total.setStyleSheet("font-size: 13px; font-weight: 800; color: #16A34A;")

        btn_nomina = QPushButton("Ver detalle")
        btn_nomina.setObjectName("secondaryButton")
        btn_nomina.clicked.connect(lambda: self.navigate_fn("Nómina"))

        p_layout.addWidget(p_lbl)
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
        
        self.chart = chart
        layout.addWidget(chart_view)
        return panel

    def _build_activity_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Últimos Registros")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        empty_lbl = QLabel("No hay registros recientes.\nLas actividades aparecerán aquí cuando estén disponibles.")
        empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; padding: 20px;")
        layout.addWidget(empty_lbl, stretch=1)

        return panel

    def _build_quick_actions(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel("⚡  Acciones Rápidas")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        actions = [
            ("Facultades", "Facultades"),
            ("Programas", "Programas"),
            ("Cursos", "Cursos"),
            ("Estudiantes", "Estudiantes"),
            ("Profesores", "Profesores"),
            ("Nómina", "Nómina"),
        ]

        for label, target in actions:
            btn = QPushButton(label)
            btn.setObjectName("quickActionButton")
            btn.clicked.connect(lambda checked=False, t=target: self.navigate_fn(t))
            actions_layout.addWidget(btn)

        layout.addLayout(actions_layout)
        return panel

    def refresh(self):
        """Actualiza todos los contadores a partir de EntityManager real."""
        try:
            mgr = self.manager

            active_statuses = {
                "ACTIVE", "ACTIVO", "COMPLETED", "APROBADO", "REPROBADO",
                "APPROVED", "FAILED", "PASSED", "FINALIZADO", "MATRICULADO", "ENROLLED"
            }
            active_enrollments = sum(
                1 for item in mgr.enrollments
                if str(getattr(item, "status", "")).upper() in active_statuses
                and str(getattr(item, "status", "")).upper() not in {"CANCELLED", "CANCELADO", "INACTIVE", "INACTIVO"}
            )
            ebra_count = mgr.count_ebra_students() if hasattr(mgr, "count_ebra_students") else sum(
                1 for s in mgr.students if mgr.evaluate_ebra_status(s.student_id).get("status") == "EBRA"
            )

            counts = {
                "Facultades": len(mgr.faculties),
                "Programas": len(mgr.programs),
                "Cursos": len(mgr.courses),
                "Estudiantes": len(mgr.students),
                "Profesores": len(mgr.professors),
                "Administrativos": len(mgr.administrative_staff),
                "Inscripciones activas": active_enrollments,
                "Alertas EBRA": ebra_count,
            }

            for label, val in counts.items():
                if label in self.cards:
                    self.cards[label].set_value(val)

            # Actualizar gráfico donut de programas
            self.pie_series.clear()
            prog_counts = {}
            for s in mgr.students:
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
