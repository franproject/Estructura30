"""Tabla de datos estilizada para las vistas CRUD de NexoCampus."""
from PySide6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)


class DataTable(QTableWidget):
    """QTableWidget con configuración sobria y responsive por columnas."""

    def __init__(self, headers: tuple or list, parent=None):
        super().__init__(0, len(headers), parent)
        self.setObjectName("dataTable")
        self.setHorizontalHeaderLabels(headers)
        self._configure()

    def _configure(self):
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)

    def populate(self, rows_data: list):
        """Llena la tabla con una lista de filas (tuplas o listas)."""
        self.setRowCount(len(rows_data))
        for row_idx, row_data in enumerate(rows_data):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value) if value is not None else "")
                self.setItem(row_idx, col_idx, item)
