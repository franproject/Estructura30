"""Encabezado estándar para las páginas internas de NexoCampus."""
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class PageHeader(QWidget):
    """Barra con título, subtítulo con barra verde vertical y botón de acción principal."""

    def __init__(self, title: str, subtitle: str, action_text: Optional[str] = None, on_action=None, parent=None):
        super().__init__(parent)
        self._build_ui(title, subtitle, action_text, on_action)

    def _build_ui(self, title: str, subtitle: str, action_text: Optional[str], on_action):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Barra verde decorativa
        bar = QWidget()
        bar.setFixedSize(4, 32)
        bar.setStyleSheet("background-color: #16A34A; border-radius: 2px;")
        layout.addWidget(bar)

        # Título y Subtítulo
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A;")

        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet("font-size: 12px; color: #94A3B8;")

        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_sub)
        layout.addLayout(text_layout)

        layout.addStretch()

        # Botón de acción si se especifica
        if action_text and on_action:
            btn = QPushButton(action_text)
            btn.setObjectName("primaryButton")
            btn.clicked.connect(on_action)
            layout.addWidget(btn)
