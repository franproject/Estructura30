"""Diálogo de confirmación para eliminar o realizar acciones críticas."""
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)


class ConfirmDialog(QDialog):
    """Modal sobrio para confirmar acciones como eliminación de registros."""

    def __init__(self, title: str = "Confirmar eliminación", message: str = "¿Estás seguro de que deseas eliminar este registro?", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(380)
        self._build_ui(message)

    def _build_ui(self, message: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        body_layout = QHBoxLayout()
        icon = QLabel("⚠️")
        icon.setStyleSheet("font-size: 24px;")
        
        lbl_message = QLabel(message)
        lbl_message.setWordWrap(True)
        lbl_message.setStyleSheet("font-size: 13px; color: #0F172A;")

        body_layout.addWidget(icon)
        body_layout.addWidget(lbl_message, stretch=1)
        layout.addLayout(body_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No)
        buttons.button(QDialogButtonBox.StandardButton.Yes).setText("Eliminar")
        buttons.button(QDialogButtonBox.StandardButton.Yes).setStyleSheet("background-color: #DC2626; color: white; border: none; border-radius: 6px; padding: 6px 14px; font-weight: 600;")
        buttons.button(QDialogButtonBox.StandardButton.No).setText("Cancelar")
        buttons.button(QDialogButtonBox.StandardButton.No).setStyleSheet("background-color: #F1F5F9; color: #475569; border: none; border-radius: 6px; padding: 6px 14px; font-weight: 600;")
        
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
