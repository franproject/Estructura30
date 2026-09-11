"""Tabla de datos estilizada y paginada para las vistas de NexoCampus."""
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from .icons import icon


class DataTable(QTableWidget):
    """QTableWidget con configuración sobria y responsive por columnas."""

    page_changed = Signal(int, int)
    edit_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, headers: tuple | list, parent=None):
        super().__init__(0, len(headers), parent)
        self.setObjectName("dataTable")
        self.setHorizontalHeaderLabels(headers)
        self._headers = list(headers)
        self._rows_data = []
        self._page = 1
        self._page_size = 10
        self._has_actions = False
        self._configure()

    def _configure(self):
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)

    def populate(self, rows_data: list, keep_page: bool = False):
        """Guarda todas las filas y muestra la página correspondiente.
        
        Args:
            rows_data: Lista con los datos de todas las filas.
            keep_page: Si es True, preserva la página actual ajustándola al nuevo rango válido.
                       Si es False (por defecto), reinicia a la página 1.
        """
        self._rows_data = list(rows_data)
        if keep_page:
            self._page = max(1, min(self._page, self.page_count))
        else:
            self._page = 1
        self._render_page()
        self.page_changed.emit(self._page, self.page_count)

    @property
    def page_size(self):
        return self._page_size

    @property
    def page(self):
        return self._page

    @property
    def page_count(self):
        return max(1, (len(self._rows_data) + self._page_size - 1) // self._page_size)

    @property
    def total_rows(self):
        return len(self._rows_data)

    def set_page(self, page: int):
        new_page = max(1, min(page, self.page_count))
        if new_page == self._page:
            return
        self._page = new_page
        self._render_page()
        self.page_changed.emit(self._page, self.page_count)

    def current_source_row(self):
        row = self.currentRow()
        if row < 0:
            return -1
        return (self._page - 1) * self._page_size + row

    def set_row_actions(self, enabled: bool = True):
        """Añade una columna de acciones compactas a la tabla."""
        self._has_actions = enabled
        if enabled and len(self._headers) == self.columnCount():
            self.insertColumn(self.columnCount())
            self._headers.append("Acciones")
            self.setHorizontalHeaderItem(self.columnCount() - 1, QTableWidgetItem("Acciones"))
        self._render_page()

    def _render_page(self):
        start = (self._page - 1) * self._page_size
        visible_rows = self._rows_data[start:start + self._page_size]
        self.setRowCount(len(visible_rows))
        for row_idx, row_data in enumerate(visible_rows):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value) if value is not None else "")
                self.setItem(row_idx, col_idx, item)
            if self._has_actions:
                actions = QWidget()
                actions_layout = QHBoxLayout(actions)
                actions_layout.setContentsMargins(4, 0, 4, 0)
                actions_layout.setSpacing(4)
                source_idx = start + row_idx
                edit = self._action_button("edit", "Editar")
                delete = self._action_button("trash", "Eliminar")
                edit.clicked.connect(lambda checked=False, idx=source_idx: self.edit_requested.emit(idx))
                delete.clicked.connect(lambda checked=False, idx=source_idx: self.delete_requested.emit(idx))
                actions_layout.addWidget(edit)
                actions_layout.addWidget(delete)
                actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setCellWidget(row_idx, len(row_data), actions)

    @staticmethod
    def _action_button(icon_name: str, tooltip: str):
        button = QPushButton()
        button.setFixedSize(26, 26)
        button.setIcon(icon(icon_name, "#64748B", 13))
        button.setIconSize(QSize(13, 13))
        button.setToolTip(tooltip)
        button.setObjectName("tableActionButton")
        return button
