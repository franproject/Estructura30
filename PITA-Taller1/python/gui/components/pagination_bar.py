"""Barra de paginación compacta y accesible para tablas de datos de NexoCampus."""
from typing import Optional, Union
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from .icons import icon


def calculate_page_range(
    current_page: int, total_pages: int, max_numeric: int = 7
) -> list[Union[int, str]]:
    """Calcula la secuencia de números de página y elipsis a mostrar.

    Garantiza que se muestren como máximo `max_numeric` botones numéricos visibles.
    - Si total_pages <= max_numeric: muestra todas las páginas sin elipsis.
    - Si total_pages > max_numeric:
        * Cerca del inicio (current_page <= 4):
          [1, 2, 3, 4, 5, "...", total_pages]
        * Cerca del final (current_page >= total_pages - 3):
          [1, "...", total_pages - 4, total_pages - 3, total_pages - 2, total_pages - 1, total_pages]
        * En el medio:
          [1, "...", current_page - 1, current_page, current_page + 1, "...", total_pages]
    """
    if total_pages <= max_numeric:
        return list(range(1, total_pages + 1))

    if current_page <= 4:
        return [1, 2, 3, 4, 5, "...", total_pages]
    elif current_page >= total_pages - 3:
        return [
            1,
            "...",
            total_pages - 4,
            total_pages - 3,
            total_pages - 2,
            total_pages - 1,
            total_pages,
        ]
    else:
        return [
            1,
            "...",
            current_page - 1,
            current_page,
            current_page + 1,
            "...",
            total_pages,
        ]


class PaginationBar(QWidget):
    """Componente reutilizable de paginación con elipsis y botones Anterior/Siguiente."""

    page_requested = Signal(int)

    def __init__(self, parent=None, max_numeric_buttons: int = 7):
        super().__init__(parent)
        self.max_numeric_buttons = max_numeric_buttons
        self.current_page = 1
        self.total_pages = 1
        self.total_rows = 0
        self.page_size = 10
        self._table = None
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 0)
        layout.setSpacing(4)

        # Información de registros (ej. "Mostrando 1–10 de 100 registros")
        self.page_info = QLabel()
        self.page_info.setObjectName("paginationInfo")
        layout.addWidget(self.page_info)

        layout.addStretch()

        # Botón Anterior
        self.btn_prev = QPushButton("Anterior")
        self.btn_prev.setIcon(icon("chevron-left", color="#475569", size=12))
        self.btn_prev.setObjectName("pageNavButton")
        self.btn_prev.clicked.connect(self._on_prev_clicked)
        layout.addWidget(self.btn_prev)

        # Contenedor de botones numéricos y elipsis
        self.page_buttons = QHBoxLayout()
        self.page_buttons.setSpacing(4)
        layout.addLayout(self.page_buttons)

        # Botón Siguiente
        self.btn_next = QPushButton("Siguiente")
        self.btn_next.setIcon(icon("chevron-right", color="#475569", size=12))
        self.btn_next.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.btn_next.setObjectName("pageNavButton")
        self.btn_next.clicked.connect(self._on_next_clicked)
        layout.addWidget(self.btn_next)

    def connect_table(self, table):
        """Vincula la barra de paginación bidireccionalmente a un DataTable."""
        self._table = table
        self.page_requested.connect(table.set_page)
        table.page_changed.connect(
            lambda page, count: self.update_pagination(
                current_page=page,
                total_pages=count,
                total_rows=table.total_rows,
                page_size=table.page_size,
            )
        )

    def _on_prev_clicked(self):
        if self.current_page > 1:
            target = self.current_page - 1
            if self._table:
                self._table.set_page(target)
            self.page_requested.emit(target)

    def _on_next_clicked(self):
        if self.current_page < self.total_pages:
            target = self.current_page + 1
            if self._table:
                self._table.set_page(target)
            self.page_requested.emit(target)

    def update_pagination(
        self,
        current_page: int,
        total_pages: int,
        total_rows: int,
        page_size: int,
    ):
        self.current_page = max(1, current_page)
        self.total_pages = max(1, total_pages)
        self.total_rows = max(0, total_rows)
        self.page_size = max(1, page_size)

        # Texto descriptivo
        start = 0 if self.total_rows == 0 else (self.current_page - 1) * self.page_size + 1
        end = min(self.current_page * self.page_size, self.total_rows)
        self.page_info.setText(f"Mostrando {start}\u2013{end} de {self.total_rows} registros")

        # Estado de Anterior / Siguiente
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < self.total_pages)

        # Limpiar botones numéricos anteriores
        while self.page_buttons.count():
            item = self.page_buttons.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

        # Calcular items con elipsis
        items = calculate_page_range(
            self.current_page,
            self.total_pages,
            max_numeric=self.max_numeric_buttons,
        )

        for item in items:
            if item == "...":
                lbl_ellipsis = QLabel("...")
                lbl_ellipsis.setObjectName("paginationEllipsis")
                lbl_ellipsis.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.page_buttons.addWidget(lbl_ellipsis)
            else:
                page_num = int(item)
                button = QPushButton(str(page_num))
                button.setFixedSize(27, 27)
                button.setObjectName(
                    "activePageButton" if page_num == self.current_page else "pageButton"
                )
                button.clicked.connect(
                    lambda checked=False, target=page_num: self._on_page_button_clicked(target)
                )
                self.page_buttons.addWidget(button)

        # Visibilidad
        self.setVisible(self.total_rows > self.page_size)

    def _on_page_button_clicked(self, page: int):
        if self._table:
            self._table.set_page(page)
        self.page_requested.emit(page)

