from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)


from .icons import pixmap


class ConfirmDialog(QDialog):
    """Modal sobrio para confirmar acciones como eliminación de registros."""

    def __init__(self, title: str = "Confirmar eliminación", message: str = "¿Estás seguro de que deseas eliminar este registro?", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(380)
        self.setStyleSheet(
            """
            QDialog { background-color: #FFFFFF; color: #0F172A; }
            QLabel { color: #0F172A; background: transparent; }
            """
        )
        self._build_ui(message)

    def _build_ui(self, message: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)
        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(pixmap("warning", color="#DC2626", size=28))
        self.icon_lbl.setFixedSize(28, 28)
        
        lbl_message = QLabel(message)
        lbl_message.setWordWrap(True)
        lbl_message.setStyleSheet("font-size: 13px; color: #0F172A;")

        body_layout.addWidget(self.icon_lbl)
        body_layout.addWidget(lbl_message, stretch=1)
        layout.addLayout(body_layout)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No)
        self.btn_delete = self.buttons.button(QDialogButtonBox.StandardButton.Yes)
        self.btn_delete.setText("Eliminar")
        self.btn_delete.setStyleSheet("background-color: #DC2626; color: white; border: none; border-radius: 6px; padding: 6px 14px; font-weight: 600;")
        self.btn_delete.setDefault(False)
        self.btn_delete.setAutoDefault(False)

        self.btn_cancel = self.buttons.button(QDialogButtonBox.StandardButton.No)
        self.btn_cancel.setText("Cancelar")
        self.btn_cancel.setStyleSheet("background-color: #F1F5F9; color: #475569; border: none; border-radius: 6px; padding: 6px 14px; font-weight: 600;")
        self.btn_cancel.setDefault(True)
        self.btn_cancel.setAutoDefault(True)
        self.btn_cancel.setFocus()

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def showEvent(self, event):
        super().showEvent(event)
        self.btn_cancel.setFocus()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.focusWidget() == self.btn_delete:
                self.accept()
            else:
                self.reject()
            event.accept()
            return
        super().keyPressEvent(event)
