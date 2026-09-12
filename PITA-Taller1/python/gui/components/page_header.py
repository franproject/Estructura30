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

    def __init__(
        self,
        title: str,
        subtitle: str,
        action_text: Optional[str] = None,
        on_action=None,
        breadcrumb: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._build_ui(title, subtitle, action_text, on_action, breadcrumb)

    def _build_ui(self, title: str, subtitle: str, action_text: Optional[str], on_action, breadcrumb: Optional[str]):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Barra verde decorativa
        bar = QWidget()
        bar.setObjectName("pageHeaderAccent")
        bar.setFixedSize(4, 32)
        layout.addWidget(bar)

        # Título y Subtítulo
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        if breadcrumb:
            lbl_crumb = QLabel(breadcrumb)
            lbl_crumb.setObjectName("pageHeaderBreadcrumb")
            text_layout.addWidget(lbl_crumb)

        lbl_title = QLabel(title)
        lbl_title.setObjectName("pageHeaderTitle")

        lbl_sub = QLabel(subtitle)
        lbl_sub.setObjectName("pageHeaderSubtitle")
        lbl_sub.setWordWrap(True)

        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_sub)
        layout.addLayout(text_layout)

        layout.addStretch()

        # Botón de acción si se especifica
        if action_text and on_action:
            btn = QPushButton(action_text)
            btn.setObjectName("primaryButton")
            btn.setToolTip(f"{action_text} (Ctrl+N)")
            btn.clicked.connect(on_action)
            layout.addWidget(btn)
