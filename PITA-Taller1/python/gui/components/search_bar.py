"""Buscador estilizado reutilizable para las tablas CRUD."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLineEdit


class SearchBar(QLineEdit):
    """Campo de búsqueda con evento de cambio dinámico."""

    search_changed = Signal(str)

    def __init__(self, placeholder: str = "Buscar...", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMaximumWidth(280)
        self.textChanged.connect(self.search_changed.emit)
