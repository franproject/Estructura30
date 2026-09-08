"""Tarjeta de estadística limpia para el Dashboard de NexoCampus."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from .icons import icon


class StatCard(QFrame):
    """Tarjeta individual con valor, título, icono y variación."""

    clicked = Signal()

    def __init__(self, title: str, value: str = "0", detail: str = "", delta: str = "", bg_color: str = "#DCFCE7", text_color: str = "#16A34A", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui(title, value, detail, delta, bg_color, text_color)

    def _build_ui(self, title: str, value: str, detail: str, delta: str, bg_color: str, text_color: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        # Header card (Icon + Label)
        top = QHBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("statLabel")

        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(36, 36)
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_name = {
            "Facultades": "building",
            "Programas": "hat",
            "Cursos": "book",
            "Estudiantes": "users",
            "Profesores": "hat",
            "Administrativos": "briefcase",
            "Inscripciones activas": "clipboard",
            "Alertas EBRA": "bell",
        }.get(title, "chart")
        self.lbl_icon.setPixmap(icon(icon_name, text_color, 20).pixmap(20, 20))
        self.lbl_icon.setStyleSheet(
            f"background-color: {bg_color}; border-radius: 8px;"
        )

        top.addWidget(self.lbl_title)
        top.addStretch()
        top.addWidget(self.lbl_icon)
        layout.addLayout(top)

        # Value
        self.lbl_val = QLabel(str(value))
        self.lbl_val.setObjectName("statValue")
        if text_color != "#16A34A" and text_color != "#0F172A":
            self.lbl_val.setStyleSheet(f"color: {text_color};")
        layout.addWidget(self.lbl_val)

        # Footer (Detail + Delta)
        bottom = QHBoxLayout()
        self.lbl_detail = QLabel(detail)
        self.lbl_detail.setObjectName("statSub")
        
        self.lbl_delta = QLabel(delta)
        if "▲" in delta:
            self.lbl_delta.setStyleSheet("color: #16A34A; font-weight: 700; font-size: 11px;")
        elif "▼" in delta:
            self.lbl_delta.setStyleSheet("color: #DC2626; font-weight: 700; font-size: 11px;")
        else:
            self.lbl_delta.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 11px;")

        bottom.addWidget(self.lbl_detail)
        bottom.addStretch()
        bottom.addWidget(self.lbl_delta)
        layout.addLayout(bottom)

    def set_value(self, value: str or int):
        self.lbl_val.setText(str(value))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
