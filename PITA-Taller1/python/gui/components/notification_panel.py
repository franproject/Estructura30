"""Panel emergente de notificaciones y alertas universitarias para NexoCampus."""
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .icons import icon, pixmap
from ..i18n.labels import get_payroll_status_label, get_acronym_tooltip


class NotificationPanel(QFrame):
    """Panel flotante que despliega alertas en tiempo real del sistema universitario."""

    navigate_requested = Signal(str)

    def __init__(self, manager=None, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("notificationPanel")
        self.manager = manager
        self.setFixedWidth(370)
        self._build_ui()

    def set_manager(self, manager):
        self.manager = manager
        self.refresh_alerts()

    def _build_ui(self):
        self.setStyleSheet(
            "#notificationPanel { "
            "  background-color: #FFFFFF; "
            "  border: 1px solid #CBD5E1; "
            "  border-radius: 12px; "
            "} "
            "#notifHeader { "
            "  border-bottom: 1px solid #F1F5F9; "
            "  padding: 12px 16px; "
            "} "
            "#notifTitle { "
            "  font-size: 13px; "
            "  font-weight: 700; "
            "  color: #0F172A; "
            "} "
            "#notifBadge { "
            "  font-size: 11px; "
            "  font-weight: 700; "
            "  border-radius: 10px; "
            "  padding: 2px 8px; "
            "}"
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Header
        header_widget = QWidget()
        header_widget.setObjectName("notifHeader")
        h_layout = QHBoxLayout(header_widget)
        h_layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("Centro de Alertas")
        title.setObjectName("notifTitle")
        h_layout.addWidget(title)

        h_layout.addStretch()

        self.badge = QLabel("0")
        self.badge.setObjectName("notifBadge")
        h_layout.addWidget(self.badge)
        root_layout.addWidget(header_widget)

        # Contenedor con Scroll
        self.scroll: QScrollArea = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.content_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.content_widget)
        self.cards_layout.setContentsMargins(12, 12, 12, 12)
        self.cards_layout.setSpacing(10)

        self.scroll.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll)

        self.refresh_alerts()

    def get_alerts(self):
        """Calcula y retorna la lista de alertas activas a partir del EntityManager."""
        if self.manager is None:
            return []

        alerts = []
        mgr = self.manager

        # 1. Alerta EBRA
        try:
            ebra_count = 0
            if hasattr(mgr, "count_ebra_students"):
                ebra_count = mgr.count_ebra_students()
            elif hasattr(mgr, "get_ebra_students"):
                ebra_count = len(mgr.get_ebra_students())
            else:
                for s in getattr(mgr, "students", []):
                    res = mgr.evaluate_ebra_status(s.student_id)
                    if res.get("status") == "EBRA":
                        ebra_count += 1

            if ebra_count > 0:
                threshold = getattr(mgr, "ebra_threshold", 3.0)
                alerts.append({
                    "id": "ebra",
                    "title": f"{ebra_count} Estudiantes en Riesgo Académico (EBRA)",
                    "description": f"Promedio inferior a {threshold:.1f}. Requieren acompañamiento o tutoría académica.",
                    "target": "Estudiantes",
                    "action_text": "Ver Estudiantes",
                    "level": "danger",
                    "icon_name": "user",
                    "icon_color": "#DC2626",
                    "bg_color": "#FEF2F2",
                    "border_color": "#FECACA",
                })
        except Exception:
            pass

        # 2. Alerta de Nómina
        try:
            cycle = getattr(mgr, "payroll_cycle_service", None)
            if cycle and hasattr(cycle, "periods"):
                open_periods = []
                for p in cycle.periods:
                    st = getattr(p, "status", "")
                    st_val = getattr(st, "value", str(st))
                    if str(st_val).upper() in {"OPEN", "CALCULATED", "APPROVED"}:
                        open_periods.append((p, st_val))
                if open_periods:
                    first, status_val = open_periods[0]
                    status_es = get_payroll_status_label(status_val)
                    alerts.append({
                        "id": "payroll",
                        "title": f"Período de Nómina: {first.year}-{first.month:02d}",
                        "description": f"En estado '{status_es}'. Requiere cálculo, aprobación o cierre definitivo.",
                        "target": "Nómina",
                        "action_text": "Ir a Nómina",
                        "level": "warning",
                        "icon_name": "money",
                        "icon_color": "#D97706",
                        "bg_color": "#FFFBEB",
                        "border_color": "#FDE68A",
                    })
        except Exception:
            pass

        # 3. Alerta de Cursos sin Docente Asignado
        try:
            courses = getattr(mgr, "courses", [])
            prof_ids = {p.professor_id for p in getattr(mgr, "professors", []) if getattr(p, "active", True)}
            unassigned = [
                c for c in courses
                if getattr(c, "active", True) and (not getattr(c, "assigned_professor_id", None) or c.assigned_professor_id not in prof_ids)
            ]
            if unassigned:
                count = len(unassigned)
                alerts.append({
                    "id": "courses_unassigned",
                    "title": f"{count} Asignaturas sin Docente",
                    "description": f"Hay {count} cursos activos sin profesor titular asignado en el período.",
                    "target": "Cursos",
                    "action_text": "Ver Cursos",
                    "level": "info",
                    "icon_name": "book",
                    "icon_color": "#2563EB",
                    "bg_color": "#EFF6FF",
                    "border_color": "#BFDBFE",
                })
        except Exception:
            pass

        return alerts

    def refresh_alerts(self):
        """Reconstruye visualmente la lista de alertas."""
        # Limpiar elementos anteriores
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item is None:
                break
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        alerts = self.get_alerts()
        total = len(alerts)

        if total > 0:
            self.badge.setText(f"{total} alertas")
            self.badge.setStyleSheet("background: #FEE2E2; color: #DC2626; font-weight: 700; border-radius: 10px; padding: 2px 8px;")
        else:
            self.badge.setText("Al día")
            self.badge.setStyleSheet("background: #DCFCE7; color: #16A34A; font-weight: 700; border-radius: 10px; padding: 2px 8px;")

        if not alerts:
            empty_widget = QWidget()
            e_layout = QVBoxLayout(empty_widget)
            e_layout.setContentsMargins(16, 24, 16, 24)
            e_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            check_lbl = QLabel()
            check_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            check_lbl.setPixmap(pixmap("check", color="#16A34A", size=24))

            msg_title = QLabel("Todo al día")
            msg_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #0F172A;")

            msg_sub = QLabel("No hay alertas críticas ni acciones pendientes en el sistema universitario.")
            msg_sub.setWordWrap(True)
            msg_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg_sub.setStyleSheet("font-size: 11px; color: #64748B; margin-top: 4px;")

            e_layout.addWidget(check_lbl)
            e_layout.addWidget(msg_title)
            e_layout.addWidget(msg_sub)
            self.cards_layout.addWidget(empty_widget)
            self.setFixedHeight(190)
            return

        for alert in alerts:
            card = self._build_alert_card(alert)
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()
        # Ajustar altura máxima
        needed_h = min(420, 60 + len(alerts) * 115)
        self.setFixedHeight(max(180, needed_h))

    def _build_alert_card(self, alert: dict) -> QFrame:
        card = QFrame()
        bg = alert.get("bg_color", "#F8FAFC")
        border = alert.get("border_color", "#E2E8F0")
        card.setStyleSheet(
            f"QFrame {{ "
            f"  background-color: {bg}; "
            f"  border: 1px solid {border}; "
            f"  border-radius: 8px; "
            f"  padding: 8px; "
            f"}}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(6)

        # Header de tarjeta con ícono y título
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(icon(alert.get("icon_name", "bell"), alert.get("icon_color", "#DC2626"), 16).pixmap(16, 16))
        top_row.addWidget(icon_lbl)

        card_title = QLabel(alert.get("title", ""))
        card_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #0F172A;")
        top_row.addWidget(card_title, stretch=1)
        card_layout.addLayout(top_row)

        # Descripción
        desc = QLabel(alert.get("description", ""))
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 11px; color: #475569; line-height: 1.3;")
        card_layout.addWidget(desc)

        # Botón de acción
        action_row = QHBoxLayout()
        action_row.addStretch()

        action_btn = QPushButton(alert.get("action_text", "Ver más"))
        action_btn.setIcon(icon("arrow-right", color="#166534", size=12))
        action_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        action_btn.setStyleSheet(
            "QPushButton { "
            "  background: transparent; "
            "  border: none; "
            "  color: #166534; "
            "  font-size: 11px; "
            "  font-weight: 700; "
            "  padding: 2px 4px; "
            "} "
            "QPushButton:hover { "
            "  color: #15803D; "
            "  text-decoration: underline; "
            "}"
        )
        action_btn.clicked.connect(
            lambda checked=False, target=alert.get("target"): self._handle_action(
                target if isinstance(target, str) else ""
            )
        )
        action_row.addWidget(action_btn)
        card_layout.addLayout(action_row)

        return card

    def _handle_action(self, target_page: str):
        self.close()
        if target_page:
            self.navigate_requested.emit(target_page)

    def show_below(self, anchor_widget: QWidget):
        """Posiciona y muestra el panel inmediatamente debajo del widget ancla."""
        self.refresh_alerts()
        origin = anchor_widget.mapToGlobal(QPoint(0, anchor_widget.height() + 4))
        # Ajustar para alinear borde derecho
        x = origin.x() + anchor_widget.width() - self.width()
        y = origin.y()
        self.move(x, y)
        self.show()
