"""Componente para mostrar estados vacíos cuando no hay registros."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from typing import Optional


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

        lbl_icon = QLabel("📋")
        lbl_icon.setStyleSheet("font-size: 36px; color: #CBD5E1;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_icon)

        self._lbl_title = QLabel(title)
        self._lbl_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #0F172A;")
        self._lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl_title)

        self._lbl_sub = QLabel(subtitle)
        self._lbl_sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        self._lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
