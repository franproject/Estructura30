"""Buscador estilizado reutilizable para las tablas CRUD."""
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QLineEdit

from .icons import icon


class SearchBar(QLineEdit):
    """Campo de búsqueda con evento de cambio dinámico."""

    search_changed = Signal(str)

    def __init__(self, placeholder: str = "Buscar...", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumWidth(260)
        self.setMaximumWidth(400)
        self.setClearButtonEnabled(True)
        self.setToolTip("Buscar registros en la tabla (Ctrl+F)")
        self.addAction(icon("search", "#64748B", 15), QLineEdit.ActionPosition.LeadingPosition)
        self.textChanged.connect(self.search_changed.emit)
