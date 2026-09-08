"""Header superior limpio de NexoCampus."""
from PySide6.QtCore import QDateTime, Qt, QSize
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


class TopHeader(QFrame):
    """Barra superior con buscador, fecha, notificaciones y perfil."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topHeader")
        self.setFixedHeight(58)
        self._build_ui()

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

        # Buscador central
        self.search_input = QLineEdit()
        self.search_input.setObjectName("headerSearch")
        self.search_input.setPlaceholderText("Buscar en Nexus...")
        self.search_input.setMaximumWidth(320)
        self.search_input.addAction(icon("search", "#94A3B8", 15), QLineEdit.ActionPosition.LeadingPosition)
        layout.addWidget(self.search_input)

        layout.addStretch()

        # Fecha y Hora
        now = QDateTime.currentDateTime()
        date_str = now.toString("dd 'de' MMMM 'de' yyyy | hh:mm")
        date_label = QLabel(date_str)
        date_label.setStyleSheet("color: #64748B; font-size: 12px;")
        layout.addWidget(date_label)

        # Separador
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: #E2E8F0; background-color: #E2E8F0; max-width: 1px;")
        layout.addWidget(sep2)

        # Notificación
        notif_btn = QPushButton()
        notif_btn.setIcon(icon("bell", "#64748B", 18))
        notif_btn.setIconSize(QSize(18, 18))
        notif_btn.setObjectName("ghostButton")
        notif_btn.setFixedSize(36, 36)
        notif_btn.setToolTip("Notificaciones")
        notif_wrap = QWidget()
        notif_wrap.setFixedSize(36, 36)
        notif_btn.setParent(notif_wrap)
        notif_btn.move(0, 0)
        dot = QLabel(notif_wrap)
        dot.setObjectName("notificationDot")
        dot.setFixedSize(8, 8)
        dot.move(24, 4)
        dot.setStyleSheet("background: #EF4444; border: 2px solid white; border-radius: 4px;")
        layout.addWidget(notif_wrap)

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
        user_role.setStyleSheet("font-size: 10px; color: #94A3B8;")
        user_info.addWidget(user_name)
        user_info.addWidget(user_role)

        user_layout.addWidget(avatar)
        user_layout.addLayout(user_info)
        layout.addLayout(user_layout)
