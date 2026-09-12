"""Tarjeta de estadística limpia para el Dashboard de NexoCampus."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from .icons import icon, pixmap


class StatCard(QFrame):
    """Tarjeta individual con valor, título, icono y variación."""

    clicked = Signal()

    ICON_MAP = {
        "Facultades": "building",
        "Programas": "layers",
        "Cursos": "book",
        "Estudiantes": "users",
        "Profesores": "hat",
        "Administrativos": "briefcase",
        "Inscripciones activas": "clipboard",
        "Alertas EBRA": "bell",
    }

    def __init__(self, title: str, value: str = "0", detail: str = "", delta: str = "", bg_color: str = "#DCFCE7", text_color: str = "#16A34A", parent=None, icon_name: str | None = None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._build_ui(title, value, detail, delta, bg_color, text_color, icon_name)

    def _build_ui(self, title: str, value: str, detail: str, delta: str, bg_color: str, text_color: str, icon_name: str | None):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        # Header card (Icon + Label)
        top = QHBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("statLabel")
        self.lbl_title.setWordWrap(True)

        self.lbl_icon = QLabel()
        self.lbl_icon.setObjectName("statIcon")
        self.lbl_icon.setProperty(
            "tone",
            {
                "#DCFCE7": "green",
                "#D1FAE5": "green",
                "#DBEAFE": "blue",
                "#EDE9FE": "purple",
                "#FEF3C7": "amber",
                "#FEE2E2": "red",
                "#E0F2FE": "cyan",
                "#F1F5F9": "slate",
            }.get(bg_color, "neutral"),
        )
        self.lbl_icon.setFixedSize(36, 36)
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_name = icon_name or self.ICON_MAP.get(title, "chart")
        self.lbl_icon.setPixmap(pixmap(self.icon_name, text_color, 20))

        top.addWidget(self.lbl_title)
        top.addStretch()
        top.addWidget(self.lbl_icon)
        layout.addLayout(top)

        # Value
        self.lbl_val = QLabel(str(value))
        self.lbl_val.setObjectName("statValue")
        tone_map = {
            "#16A34A": "green",
            "#15803D": "green",
            "#059669": "green",
            "#2563EB": "blue",
            "#7C3AED": "purple",
            "#D97706": "amber",
            "#B45309": "amber",
            "#DC2626": "red",
            "#0284C7": "cyan",
            "#0369A1": "cyan",
            "#475569": "slate",
        }
        val_tone = tone_map.get(text_color)
        if val_tone:
            self.lbl_val.setProperty("tone", val_tone)
        layout.addWidget(self.lbl_val)

        # Footer (Detail + Delta)
        bottom = QHBoxLayout()
        self.lbl_detail = QLabel(detail)
        self.lbl_detail.setObjectName("statSub")
        self.lbl_detail.setWordWrap(True)
        
        self.lbl_delta = QLabel()
        self.lbl_delta.setObjectName("statDelta")
        self.set_delta(delta)

        bottom.addWidget(self.lbl_detail)
        bottom.addStretch()
        bottom.addWidget(self.lbl_delta)
        layout.addLayout(bottom)

    def set_value(self, value: str | int):
        self.lbl_val.setText(str(value))

    def set_delta(self, delta: str | None):
        """Actualiza el texto y la tendencia visual del delta, o lo oculta si es None o vacío."""
        if not delta:
            self.lbl_delta.setText("")
            self.lbl_delta.setVisible(False)
            return

        self.lbl_delta.setVisible(True)
        self.lbl_delta.setText(str(delta))
        if "▲" in delta or delta.startswith("+"):
            self.lbl_delta.setProperty("trend", "up")
        elif "▼" in delta or delta.startswith("-"):
            self.lbl_delta.setProperty("trend", "down")
        else:
            self.lbl_delta.setProperty("trend", "neutral")

        # Refrescar estilo dinámico de Qt para la propiedad 'trend'
        self.lbl_delta.style().unpolish(self.lbl_delta)
        self.lbl_delta.style().polish(self.lbl_delta)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
            event.accept()
            return
        super().keyPressEvent(event)
