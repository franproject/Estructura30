"""Header superior limpio de NexoCampus con reloj en tiempo real, búsqueda y notificaciones."""
from PySide6.QtCore import QDateTime, QSize, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .icons import icon
from .notification_panel import NotificationPanel


class TopHeader(QFrame):
    """Barra superior con buscador interactivo, reloj en vivo, notificaciones y perfil."""

    search_requested = Signal(str)
    navigate_requested = Signal(str)

    def __init__(self, manager=None, parent=None):
        super().__init__(parent)
        self.setObjectName("topHeader")
        self.setFixedHeight(58)
        self.manager = manager
        self.notification_panel = NotificationPanel(manager=self.manager, parent=self)
        self.notification_panel.navigate_requested.connect(self.navigate_requested.emit)
        self._build_ui()
        self._init_clock()
        if self.manager:
            self.update_alerts(self.manager)

    def set_manager(self, manager):
        self.manager = manager
        if hasattr(self, "notification_panel"):
            self.notification_panel.set_manager(manager)
        self.update_alerts(manager)

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(14)

        # Brand / Logo compacto
        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(1)
        brand_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title = QLabel("NexoCampus")
        title.setObjectName("headerLogo")
        sub = QLabel("Portal Universitario")
        sub.setObjectName("headerSub")

        brand_layout.addWidget(title)
        brand_layout.addWidget(sub)
        layout.addLayout(brand_layout)

        # Separador vertical
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color: #E2E8F0; background-color: #E2E8F0; max-width: 1px;")
        layout.addWidget(sep1)

        # Buscador central interactivo
        self.search_input = QLineEdit()
        self.search_input.setObjectName("headerSearch")
        self.search_input.setPlaceholderText("Buscar en el sistema... (Enter)")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMaximumWidth(320)
        search_action = self.search_input.addAction(
            icon("search", "#94A3B8", 15), QLineEdit.ActionPosition.LeadingPosition
        )
        search_action.triggered.connect(self._on_search_submitted)
        self.search_input.returnPressed.connect(self._on_search_submitted)
        layout.addWidget(self.search_input)

        layout.addStretch()

        # Fecha y Hora en tiempo real con QTimer
        self.date_label = QLabel()
        self.date_label.setObjectName("headerClock")
        self.date_label.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500;")
        layout.addWidget(self.date_label)

        # Separador
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: #E2E8F0; background-color: #E2E8F0; max-width: 1px;")
        layout.addWidget(sep2)

        # Notificación con panel interactivo
        self.notif_wrap = QWidget()
        self.notif_wrap.setFixedSize(36, 36)

        self.notif_btn = QPushButton(self.notif_wrap)
        self.notif_btn.setIcon(icon("bell", "#64748B", 18))
        self.notif_btn.setIconSize(QSize(18, 18))
        self.notif_btn.setObjectName("ghostButton")
        self.notif_btn.setFixedSize(36, 36)
        self.notif_btn.setToolTip("Notificaciones del sistema")
        self.notif_btn.move(0, 0)
        self.notif_btn.clicked.connect(self._toggle_notifications)

        self.dot = QLabel(self.notif_wrap)
        self.dot.setObjectName("notificationDot")
        self.dot.setFixedSize(8, 8)
        self.dot.move(24, 4)
        self.dot.setStyleSheet("background: #EF4444; border: 2px solid white; border-radius: 4px;")
        self.dot.setVisible(False)

        layout.addWidget(self.notif_wrap)

        # Perfil de usuario
        user_layout = QHBoxLayout()
        user_layout.setSpacing(8)

        avatar = QLabel("SA")
        avatar.setStyleSheet(
            "background: linear-gradient(135deg, #16A34A, #14532D);"
            "color: white; font-weight: 700; border-radius: 16px;"
            "padding: 6px 10px; font-size: 11px;"
        )

        user_info = QVBoxLayout()
        user_info.setSpacing(0)
        user_name = QLabel("Administrador")
        user_name.setStyleSheet("font-weight: 700; font-size: 12px; color: #0F172A;")
        user_role = QLabel("Sistema")
        user_role.setStyleSheet("font-size: 11px; color: #94A3B8;")
        user_info.addWidget(user_name)
        user_info.addWidget(user_role)

        user_layout.addWidget(avatar)
        user_layout.addLayout(user_info)
        layout.addLayout(user_layout)

    def _init_clock(self):
        """Inicializa el temporizador de 1 segundo para el reloj en tiempo real."""
        self._update_clock()
        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start()

    def _update_clock(self):
        """Actualiza el texto de la fecha y hora incluyendo segundos."""
        now = QDateTime.currentDateTime()
        date_str = now.toString("dd 'de' MMMM 'de' yyyy | hh:mm:ss")
        self.date_label.setText(date_str)

    def _on_search_submitted(self):
        """Emite la señal de búsqueda con el texto normalizado."""
        query = self.search_input.text().strip()
        if query:
            self.search_requested.emit(query)

    def _toggle_notifications(self):
        """Despliega o cierra el panel de notificaciones flotante."""
        if self.notification_panel.isVisible():
            self.notification_panel.close()
        else:
            self.notification_panel.show_below(self.notif_wrap)

    def update_alerts(self, manager=None):
        """Refresca las alertas del panel y la visibilidad del punto rojo indicador."""
        if manager:
            self.manager = manager
            self.notification_panel.set_manager(manager)

        alerts = self.notification_panel.get_alerts() if hasattr(self, "notification_panel") else []
        count = len(alerts)
        if hasattr(self, "dot"):
            self.dot.setVisible(count > 0)
        if hasattr(self, "notif_btn"):
            if count > 0:
                self.notif_btn.setToolTip(f"Centro de Alertas ({count} activas)")
            else:
                self.notif_btn.setToolTip("Sin alertas pendientes")
