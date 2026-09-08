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

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #0F172A;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_sub)

        if action_text and on_action:
            btn = QPushButton(action_text)
            btn.setObjectName("primaryButton")
            btn.clicked.connect(on_action)
            layout.addSpacing(6)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
