"""Componente para mostrar estados vacíos cuando no hay registros."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from typing import Optional
from .icons import pixmap


class EmptyState(QFrame):
    """Visualización sobria cuando una lista/tabla carece de datos."""

    def __init__(self, title: str = "No hay registros disponibles", subtitle: str = "Crea un nuevo registro usando las acciones rápidas", action_text: Optional[str] = None, on_action=None, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self._build_ui(title, subtitle, action_text, on_action)

    def _build_ui(self, title: str, subtitle: str, action_text: Optional[str], on_action):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 50, 40, 50)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        self.lbl_icon = QLabel()
        self.lbl_icon.setObjectName("emptyStateIcon")
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setPixmap(pixmap("clipboard-check", color="#64748B", size=42))
        layout.addWidget(self.lbl_icon)

        self.setMinimumWidth(0)

        self._lbl_title = QLabel(title)
        self._lbl_title.setObjectName("emptyStateTitle")
        self._lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_title.setWordWrap(True)
        layout.addWidget(self._lbl_title)

        self._lbl_sub = QLabel(subtitle)
        self._lbl_sub.setObjectName("emptyStateSubtitle")
        self._lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_sub.setWordWrap(True)
        layout.addWidget(self._lbl_sub)

        self._btn = None
        if action_text and on_action:
            self._btn = QPushButton(action_text)
            self._btn.setObjectName("primaryButton")
            self._btn.clicked.connect(on_action)
            layout.addSpacing(6)
            layout.addWidget(self._btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def set_content(self, title: str, subtitle: str, show_action: bool = True):
        self._lbl_title.setText(title)
        self._lbl_sub.setText(subtitle)
        if self._btn is not None:
            self._btn.setVisible(show_action)
