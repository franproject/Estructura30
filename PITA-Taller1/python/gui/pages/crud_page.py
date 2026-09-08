"""Página genérica CRUD profesional para NexoCampus."""
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..components.confirm_dialog import ConfirmDialog
from ..components.data_table import DataTable
from ..components.empty_state import EmptyState
from ..components.entity_dialog import EntityDialog
from ..components.page_header import PageHeader
from ..components.search_bar import SearchBar


class CrudPage(QWidget):
    """Página de mantenimiento CRUD limpia, conectada con el EntityManager."""

    changed = Signal()

    def __init__(
        self,
        title: str,
        subtitle: str,
        manager,
        collection_name: str,
        model_cls,
        id_field: str,
        fields: tuple,
        columns: tuple,
        row_builder,
        operation_name: str = None,
        parent=None,
    ):
        super().__init__(parent)
        self.title = title
        self.subtitle = subtitle
        self.manager = manager
        self.collection_name = collection_name
        self.model_cls = model_cls
        self.id_field = id_field
        self.fields = fields
        self.columns = columns
        self.row_builder = row_builder
        self.operation_name = operation_name or collection_name.rstrip("s")
        self._items = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header de la página
        self.header = PageHeader(
            title=self.title,
            subtitle=self.subtitle,
            action_text=f"+ Nuevo {self.operation_name.capitalize()}",
            on_action=self.create_item,
        )
        layout.addWidget(self.header)

        # Toolbar (Buscador + Acciones)
        toolbar = QHBoxLayout()
        self.search_bar = SearchBar(placeholder=f"Buscar en {self.title.lower()}...")
        self.search_bar.search_changed.connect(self.filter_data)
        toolbar.addWidget(self.search_bar)

        toolbar.addStretch()

        self.btn_edit = QPushButton("Editar Seleccionado")
        self.btn_edit.setObjectName("secondaryButton")
        self.btn_edit.clicked.connect(self.edit_item)

        self.btn_delete = QPushButton("Eliminar Seleccionado")
        self.btn_delete.setObjectName("ghostButton")
        self.btn_delete.setStyleSheet("color: #DC2626;")
        self.btn_delete.clicked.connect(self.delete_item)

        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        layout.addLayout(toolbar)

        # Tabla de Datos
        self.table = DataTable(headers=self.columns)
        self.table.set_row_actions()
        self.table.edit_requested.connect(self._edit_source_item)
        self.table.delete_requested.connect(self._delete_source_item)
        layout.addWidget(self.table)
        self.pagination = self._build_pagination()
        layout.addWidget(self.pagination)

        # Estado Vacío (se alterna dinámicamente)
        self.empty_state = EmptyState(
            title=f"No hay {self.title.lower()} registrados",
            subtitle=f"Presiona el botón '+ Nuevo' para añadir tu primer registro de {self.operation_name}.",
            action_text=f"+ Crear {self.operation_name.capitalize()}",
            on_action=self.create_item,
        )
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

    def _collection(self):
        return getattr(self.manager, self.collection_name, [])

    def refresh(self):
        self.filter_data(self.search_bar.text())

    def filter_data(self, query: str = ""):
        query = query.lower().strip()
        items_all = list(self._collection())

        if not query:
            self._items = items_all
        else:
            self._items = [
                item for item in items_all
                if query in str(self.row_builder(item)).lower()
            ]

        if not items_all:
            self.table.hide()
            self.empty_state.show()
            self.table.populate([])
            self._update_pagination()
        else:
            self.empty_state.hide()
            self.table.show()
            rows_formatted = [self.row_builder(item) for item in self._items]
            self.table.populate(rows_formatted)
            self._update_pagination()

    def _selected_item(self):
        row = self.table.current_source_row()
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def _edit_source_item(self, source_index: int):
        self.table.selectRow(source_index - (self.table.page - 1) * self.table.page_size)
        self.edit_item()

    def _delete_source_item(self, source_index: int):
        self.table.selectRow(source_index - (self.table.page - 1) * self.table.page_size)
        self.delete_item()

    def _build_pagination(self):
        footer = QWidget()
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(4, 4, 4, 0)
        self.page_info = QLabel()
        self.page_info.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(self.page_info)
        layout.addStretch()
        self.page_buttons = QHBoxLayout()
        self.page_buttons.setSpacing(4)
        layout.addLayout(self.page_buttons)
        self.table.page_changed.connect(lambda *_: self._update_pagination())
        return footer

    def _update_pagination(self):
        total = self.table.total_rows
        start = 0 if total == 0 else (self.table.page - 1) * self.table.page_size + 1
        end = min(self.table.page * self.table.page_size, total)
        self.page_info.setText(f"Mostrando {start}\u2013{end} de {total} registros")
        while self.page_buttons.count():
            item = self.page_buttons.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for page in range(1, self.table.page_count + 1):
            button = QPushButton(str(page))
            button.setFixedSize(27, 27)
            button.setObjectName("activePageButton" if page == self.table.page else "pageButton")
            button.clicked.connect(lambda checked=False, target=page: self.table.set_page(target))
            self.page_buttons.addWidget(button)
        self.pagination.setVisible(total > self.table.page_size)

    def create_item(self):
        dialog = EntityDialog(f"Nuevo Registro - {self.title}", self.fields, parent=self)
        if dialog.exec() != EntityDialog.DialogCode.Accepted:
            return

        try:
            values = dialog.values()
            item = self.model_cls(**values)
            method_name = f"create_{self.operation_name}"
            method = getattr(self.manager, method_name, None)

            if method and not method(item):
                raise ValueError("El registro fue rechazado por las reglas de negocio de EntityManager.")

            self._after_change(f"{self.operation_name.capitalize()} creado exitosamente.")
        except Exception as exc:
            QMessageBox.critical(self, "Error al crear", str(exc))

    def edit_item(self):
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Selección requerida", "Por favor selecciona un registro de la tabla para editar.")
            return

        dialog = EntityDialog(f"Editar Registro - {self.title}", self.fields, entity=item, parent=self)
        if dialog.exec() != EntityDialog.DialogCode.Accepted:
            return

        try:
            values = dialog.values()
            identifier = getattr(item, self.id_field)
            updates = {k: v for k, v in values.items() if k != self.id_field}

            if self.operation_name == "enrollment":
                updated = self.manager.register_grade(identifier, values.get("final_grade", 0.0))
            else:
                method_name = f"update_{self.operation_name}"
                method = getattr(self.manager, method_name, None)
                updated = method(identifier, **updates) if method else False

            if not updated:
                raise ValueError("La actualización fue rechazada por las reglas de negocio.")

            self._after_change("Registro actualizado correctamente.")
        except Exception as exc:
            QMessageBox.critical(self, "Error al editar", str(exc))

    def delete_item(self):
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Selección requerida", "Por favor selecciona un registro de la tabla para eliminar.")
            return

        confirm = ConfirmDialog(
            title="Confirmar eliminación",
            message=f"¿Estás seguro de que deseas eliminar el registro seleccionado ({getattr(item, self.id_field)})?",
            parent=self,
        )
        if confirm.exec() != ConfirmDialog.DialogCode.Accepted:
            return

        try:
            identifier = getattr(item, self.id_field)
            method_name = f"delete_{self.operation_name}"
            method = getattr(self.manager, method_name, None)

            if method and not method(identifier):
                raise ValueError("No se pudo eliminar el registro. Puede tener relaciones activas o no existir.")

            self._after_change("Registro eliminado correctamente.")
        except Exception as exc:
            QMessageBox.warning(self, "Error al eliminar", str(exc))

    def _after_change(self, message: str):
        self.refresh()
        self.changed.emit()
        QMessageBox.information(self, "NexoCampus", message)
