"""Tabla de datos estilizada y paginada para las vistas de NexoCampus."""
import unicodedata
from typing import Any, Optional, Union, List, Tuple
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from .icons import icon


def _sort_key(value):
    """Genera una clave de ordenamiento robusta para comparaciones numéricas, monetarias y textuales."""
    if value is None:
        return (0, 0.0, "")

    # Tipo numérico directo
    if isinstance(value, (int, float)):
        return (1, float(value), "")

    val_str = str(value).strip()
    if not val_str:
        return (0, 0.0, "")

    # Detección de moneda: "$ 1,500.00" o "$ 0"
    if val_str.startswith("$"):
        cleaned = val_str.replace("$", "").replace(",", "").replace(" ", "")
        try:
            return (1, float(cleaned), "")
        except ValueError:
            pass

    # Detección de porcentaje: "7%", "15.5%"
    if val_str.endswith("%"):
        cleaned = val_str.replace("%", "").strip()
        try:
            return (1, float(cleaned), "")
        except ValueError:
            pass

    # Detección de string numérico simple
    try:
        return (1, float(val_str), "")
    except ValueError:
        pass

    # Normalización textual para orden alfabético insensible a tildes y mayúsculas
    norm = unicodedata.normalize("NFKD", val_str.lower()).encode("ASCII", "ignore").decode("utf-8")
    return (2, 0.0, norm)


class DataTable(QTableWidget):
    """QTableWidget con configuración sobria, responsive por columnas, ordenamiento y alineación contable."""

    page_changed = Signal(int, int)
    edit_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(
        self,
        headers: Union[tuple, list],
        stretch_column: Optional[Union[int, str]] = None,
        column_types: Optional[Union[List[str], Tuple[str, ...]]] = None,
        parent=None,
    ):
        super().__init__(0, len(headers), parent)
        self.setObjectName("dataTable")
        self.setHorizontalHeaderLabels(headers)
        self._headers = list(headers)
        self._column_types = list(column_types) if column_types else None
        self._rows_data = []
        self._payloads = None
        self._page = 1
        self._page_size = 10
        self._has_actions = False

        # Configuración de ordenamiento
        self._sort_column: Optional[int] = None
        self._sort_order: Qt.SortOrder = Qt.SortOrder.AscendingOrder

        # Determinación de columna estirable principal
        self._stretch_col_idx = self._resolve_stretch_column(stretch_column, self._headers)

        self._configure()
        self._update_column_modes()

    def _resolve_stretch_column(self, stretch_column: Optional[Union[int, str]], headers: list) -> int:
        """Determina el índice de la columna que debe estirarse para ocupar el espacio disponible."""
        if isinstance(stretch_column, int):
            if 0 <= stretch_column < len(headers):
                return stretch_column
            return 0

        if isinstance(stretch_column, str):
            for idx, h in enumerate(headers):
                if h.strip().lower() == stretch_column.strip().lower():
                    return idx

        # Fallback inteligente: buscar columnas clave de texto
        keywords = ("nombre completo", "nombre", "curso", "asignatura", "programa", "categoría", "razón social")
        for kw in keywords:
            for idx, h in enumerate(headers):
                if kw in h.strip().lower():
                    return idx

        # Si hay más de una columna, tomar por defecto la columna 1 (generalmente nombre/descripción)
        return 1 if len(headers) > 1 else 0

    def _configure(self):
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSortIndicatorShown(True)
        self.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.verticalHeader().setVisible(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)

    def _update_column_modes(self):
        """Aplica los modos de redimensionado: columna principal Stretch, columnas interactivas y Acciones fija."""
        header = self.horizontalHeader()
        col_count = self.columnCount()
        data_col_count = len(self._headers) - (1 if self._has_actions else 0)

        for i in range(data_col_count):
            if i == self._stretch_col_idx:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                # Establecer anchos iniciales equilibrados según el tipo/texto de cabecera
                h_text = self._headers[i] if i < len(self._headers) else ""
                h_lower = h_text.lower()
                if h_text in ("ID", "Id", "Código") or h_lower.endswith("_id"):
                    self.setColumnWidth(i, 70)
                elif any(k in h_lower for k in ("semestre", "créditos", "horas", "tipo", "modalidad", "estado", "período")):
                    self.setColumnWidth(i, 95)
                elif any(k in h_lower for k in ("salario", "total", "devengado", "deducciones", "neto", "costo", "ibc", "base")):
                    self.setColumnWidth(i, 115)
                else:
                    self.setColumnWidth(i, 140)

        if self._has_actions and col_count > 0:
            actions_col = col_count - 1
            header.setSectionResizeMode(actions_col, QHeaderView.ResizeMode.Fixed)
            self.setColumnWidth(actions_col, 85)

    def set_stretch_column(self, stretch_column: Union[int, str]):
        """Permite reconfigurar dinámicamente la columna principal que debe estirarse."""
        self._stretch_col_idx = self._resolve_stretch_column(stretch_column, self._headers)
        self._update_column_modes()

    def set_column_types(self, column_types: Union[List[str], Tuple[str, ...]]):
        """Asigna los tipos semánticos de cada columna ('text', 'numeric', 'money', 'id', 'date', 'center')."""
        self._column_types = list(column_types)
        self._render_page()

    def populate(self, rows_data: list, payloads: Optional[list] = None, keep_page: bool = False):
        """Guarda todas las filas y muestra la página correspondiente respetando el orden activo.
        
        Args:
            rows_data: Lista con las tuplas/listas de datos de cada fila.
            payloads: Opcional, lista de objetos de dominio/modelo asociados a cada fila.
            keep_page: Si es True, preserva la página actual ajustándola al nuevo rango válido.
                       Si es False (por defecto), reinicia a la página 1.
        """
        if isinstance(payloads, bool):
            keep_page = payloads
            payloads = None

        self._rows_data = list(rows_data)
        self._payloads = list(payloads) if payloads is not None else None
        if self._sort_column is not None:
            self._sort_rows()

        if keep_page:
            self._page = max(1, min(self._page, self.page_count))
        else:
            self._page = 1
        self.clearSelection()
        self.setCurrentCell(-1, -1)
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

    def current_source_payload(self):
        """Retorna el objeto de dominio asociado a la fila seleccionada actualmente."""
        row = self.current_source_row()
        if self._payloads is not None and 0 <= row < len(self._payloads):
            return self._payloads[row]
        return None

    def get_payload(self, source_row: int):
        """Retorna el payload de una fila en el índice de origen."""
        if self._payloads is not None and 0 <= source_row < len(self._payloads):
            return self._payloads[source_row]
        return None

    def set_row_actions(self, enabled: bool = True):
        """Añade o retira una columna de acciones compacta (85px) fija a la derecha."""
        self._has_actions = enabled
        if enabled and len(self._headers) == self.columnCount():
            self.insertColumn(self.columnCount())
            self._headers.append("Acciones")
            self.setHorizontalHeaderItem(self.columnCount() - 1, QTableWidgetItem("Acciones"))
        self._update_column_modes()
        self._render_page()

    def _on_header_clicked(self, logical_index: int):
        """Gestiona el ordenamiento interactivo por clic en el encabezado de columna."""
        # Ignorar clics sobre la columna "Acciones"
        if self._has_actions and logical_index == self.columnCount() - 1:
            return

        if self._sort_column == logical_index:
            # Alternar dirección de ordenamiento
            self._sort_order = (
                Qt.SortOrder.DescendingOrder
                if self._sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self._sort_column = logical_index
            self._sort_order = Qt.SortOrder.AscendingOrder

        if self._sort_column is not None:
            self.horizontalHeader().setSortIndicator(self._sort_column, self._sort_order)
        self._sort_rows()
        self._render_page()

    def _sort_rows(self):
        """Ordena el conjunto completo de datos subyacente según la columna activa."""
        if self._sort_column is None or self._sort_column < 0:
            return
        col = self._sort_column
        reverse = (self._sort_order == Qt.SortOrder.DescendingOrder)
        if self._payloads is not None and len(self._payloads) == len(self._rows_data):
            combined = list(zip(self._rows_data, self._payloads))
            combined.sort(
                key=lambda pair: _sort_key(pair[0][col] if col < len(pair[0]) else None),
                reverse=reverse,
            )
            self._rows_data = [r for r, _ in combined]
            self._payloads = [p for _, p in combined]
        else:
            self._rows_data.sort(
                key=lambda row: _sort_key(row[col] if col < len(row) else None),
                reverse=reverse,
            )

    def _get_alignment(self, col_idx: int, value: Any) -> Qt.AlignmentFlag:
        """Determina la alineación visual de la celda según su tipo semántico o cabecera."""
        col_type = None
        if self._column_types and col_idx < len(self._column_types):
            col_type = self._column_types[col_idx]

        if col_type in ("numeric", "money", "number", "right"):
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        if col_type in ("id", "date", "status", "center", "badge"):
            return Qt.AlignmentFlag.AlignCenter

        # Heurística automática si no se especificó un tipo de columna explícito
        h_text = self._headers[col_idx] if col_idx < len(self._headers) else ""
        h_lower = h_text.lower()

        if h_text in ("ID", "Id", "Código") or h_lower.endswith("_id"):
            return Qt.AlignmentFlag.AlignCenter
        if any(k in h_lower for k in ("estado", "activo", "tipo", "modalidad", "dedicación", "fecha", "período", "semestre")):
            return Qt.AlignmentFlag.AlignCenter

        if isinstance(value, (int, float)):
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        if isinstance(value, str):
            val_s = value.strip()
            if val_s.startswith("$") or val_s.endswith("%"):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            if any(k in h_lower for k in ("salario", "devengado", "deducciones", "neto", "costo", "ibc", "total", "promedio", "nota", "créditos", "cantidad")):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

    def _render_page(self):
        start = (self._page - 1) * self._page_size
        visible_rows = self._rows_data[start:start + self._page_size]
        self.setRowCount(len(visible_rows))

        for row_idx, row_data in enumerate(visible_rows):
            for col_idx, value in enumerate(row_data):
                val_str = str(value) if value is not None else ""
                item = QTableWidgetItem(val_str)
                item.setTextAlignment(self._get_alignment(col_idx, value))
                item.setToolTip(val_str)
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

        self.update_table_height()

    def update_table_height(self):
        """Ajusta la altura del DataTable exactamente a la cantidad de filas visibles,
        eliminando el espacio en blanco innecesario."""
        header_h = self.horizontalHeader().height()
        if header_h <= 0:
            header_h = self.horizontalHeader().sizeHint().height() or 33

        row_count = self.rowCount()
        if row_count > 0:
            rows_h = sum(self.rowHeight(i) for i in range(row_count))
            if rows_h == 0:
                rows_h = row_count * (self.verticalHeader().defaultSectionSize() or 30)
        else:
            rows_h = 40  # Altura mínima cuando no hay registros

        frame_borders = self.frameWidth() * 2
        target_h = header_h + rows_h + frame_borders + 4
        if self.horizontalScrollBar().isVisible():
            target_h += self.horizontalScrollBar().height()

        self.setFixedHeight(target_h)
        self.updateGeometry()

    def adjust_height_to_content(self):
        """Sincroniza explícitamente la altura con el contenido visible."""
        self.update_table_height()

    @staticmethod
    def _action_button(icon_name: str, tooltip: str):
        button = QPushButton()
        button.setFixedSize(26, 26)
        button.setIcon(icon(icon_name, "#64748B", 13))
        button.setIconSize(QSize(13, 13))
        button.setToolTip(tooltip)
        button.setObjectName("tableActionButton")
        return button
