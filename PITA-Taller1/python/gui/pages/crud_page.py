"""Página genérica CRUD profesional para NexoCampus."""
import logging
import unicodedata
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from typing import Optional, Union, List, Tuple

from ..components.confirm_dialog import ConfirmDialog
from ..components.data_table import DataTable
from ..components.empty_state import EmptyState
from ..components.entity_dialog import EntityDialog
from ..components.page_header import PageHeader
from ..components.pagination_bar import PaginationBar
from ..components.search_bar import SearchBar
from ..i18n.labels import get_entity_info


def _normalize_text(text: str) -> str:
    """Normaliza texto eliminando acentos y diacríticos y convirtiendo a minúsculas."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", str(text))
    return normalized.encode("ascii", "ignore").decode("ascii").lower().strip()


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
        operation_name: Optional[str] = None,
        stretch_column: Optional[Union[int, str]] = None,
        column_types: Optional[Union[List[str], Tuple[str, ...]]] = None,
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
        self.entity_info = get_entity_info(self.operation_name)
        self.stretch_column = stretch_column
        self.column_types = column_types
        self._items = []
        self._empty_title = f"No hay {self.title.lower()} registrados"
        self._empty_subtitle = self.entity_info.empty_hint
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
            action_text=self.entity_info.new_button_label,
            on_action=self.create_item,
        )
        layout.addWidget(self.header)

        # Toolbar (Buscador + Acciones)
        toolbar = QHBoxLayout()
        self.search_bar = SearchBar(placeholder=f"Buscar en {self.title.lower()}...")
        self.search_input = self.search_bar
        self.search_bar.search_changed.connect(self.filter_data)
        toolbar.addWidget(self.search_bar)

        toolbar.addStretch()

        self.btn_edit = QPushButton("Editar")
        self.btn_edit.setObjectName("secondaryButton")
        self.btn_edit.setEnabled(False)
        self.btn_edit.setToolTip("Editar el registro seleccionado")
        self.btn_edit.clicked.connect(self.edit_item)

        self.btn_delete = QPushButton("Eliminar")
        self.btn_delete.setObjectName("ghostDeleteButton")
        self.btn_delete.setEnabled(False)
        self.btn_delete.setToolTip("Eliminar el registro seleccionado (Supr / Delete)")
        self.btn_delete.clicked.connect(self.delete_item)

        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        layout.addLayout(toolbar)

        # Tabla de Datos
        self.table = DataTable(
            headers=self.columns,
            stretch_column=self.stretch_column,
            column_types=self.column_types,
        )
        self.table.set_row_actions()
        self.table.itemSelectionChanged.connect(self._update_selection_state)
        self.table.edit_requested.connect(self._edit_source_item)
        self.table.delete_requested.connect(self._delete_source_item)

        # Atajo Delete para la tabla cuando tiene foco y fila seleccionada
        self.shortcut_delete = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.table)
        self.shortcut_delete.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_delete.activated.connect(self._on_table_delete_shortcut)
        layout.addWidget(self.table)
        self.pagination = PaginationBar(parent=self)
        self.pagination.connect_table(self.table)
        self.page_info = self.pagination.page_info
        self.page_buttons = self.pagination.page_buttons
        layout.addWidget(self.pagination)

        # Estado Vacío (se alterna dinámicamente)
        self.empty_state = EmptyState(
            title=self._empty_title,
            subtitle=self._empty_subtitle,
            action_text=self.entity_info.create_button_label,
            on_action=self.create_item,
        )
        layout.addWidget(self.empty_state)
        self.empty_state.hide()
        layout.addStretch()

    def _collection(self):
        return getattr(self.manager, self.collection_name, [])

    def refresh(self, keep_page: bool = False):
        try:
            self.filter_data(self.search_bar.text(), keep_page=keep_page)
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Error al refrescar %s", self.__class__.__name__
            )
            self.table.hide()
            self.empty_state.set_content(
                "No se pudo cargar esta sección.",
                "Intenta recargar los datos desde el menú lateral.",
                show_action=False,
            )
            self.empty_state.show()

    def filter_data(self, query: str = "", keep_page: bool = False):
        norm_query = _normalize_text(query)
        items_all = list(self._collection())

        if not norm_query:
            self._items = items_all
        else:
            self._items = [
                item for item in items_all
                if norm_query in _normalize_text(str(self.row_builder(item)))
            ]

        if not items_all:
            self.empty_state.set_content(
                self._empty_title, self._empty_subtitle, show_action=True
            )
            self.table.hide()
            self.empty_state.show()
            self.table.populate([], payloads=[], keep_page=False)
            self._update_pagination()
        elif not self._items:
            self.empty_state.set_content(
                f'Sin resultados para "{query}"',
                "Intenta con otro término de búsqueda.",
                show_action=False,
            )
            self.table.hide()
            self.empty_state.show()
            self.table.populate([], payloads=[], keep_page=False)
            self._update_pagination()
        else:
            self.empty_state.set_content(
                self._empty_title, self._empty_subtitle, show_action=True
            )
            self.empty_state.hide()
            self.table.show()
            rows_formatted = [self.row_builder(item) for item in self._items]
            self.table.populate(rows_formatted, payloads=self._items, keep_page=keep_page)
            self._update_pagination()
        self._update_selection_state()

    def _selected_item(self):
        if hasattr(self, "table") and self.table.selectionModel() and not self.table.selectionModel().hasSelection():
            return None
        payload = self.table.current_source_payload()
        if payload is not None:
            return payload
        row = self.table.current_source_row()
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def _update_selection_state(self):
        """Habilita o deshabilita dinámicamente los botones de acción contextual según la selección activa."""
        has_selection = self._selected_item() is not None
        if hasattr(self, "btn_edit"):
            self.btn_edit.setEnabled(has_selection)
        if hasattr(self, "btn_delete"):
            self.btn_delete.setEnabled(has_selection)

    def _on_table_delete_shortcut(self):
        """Elimina el registro seleccionado desde teclado si el foco no está en un campo de texto."""
        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox)):
            return
        if hasattr(self, "btn_delete") and self.btn_delete.isEnabled():
            self.delete_item()

    def _edit_source_item(self, source_index: int):
        self.table.selectRow(source_index - (self.table.page - 1) * self.table.page_size)
        self.edit_item()

    def _delete_source_item(self, source_index: int):
        self.table.selectRow(source_index - (self.table.page - 1) * self.table.page_size)
        self.delete_item()

    def _build_pagination(self):
        """Retorna el componente de paginación."""
        return self.pagination

    def _update_pagination(self):
        """Actualiza la barra de paginación compacta con elipsis."""
        self.pagination.update_pagination(
            current_page=self.table.page,
            total_pages=self.table.page_count,
            total_rows=self.table.total_rows,
            page_size=self.table.page_size,
        )

    def create_item(self):
        dialog = EntityDialog(
            f"Nuevo Registro - {self.title}",
            self.fields,
            parent=self,
            primary_key=self.id_field,
        )
        if dialog.exec() != EntityDialog.DialogCode.Accepted:
            return

        try:
            values = dialog.values()
            item = self.model_cls(**values)
            method_name = f"create_{self.operation_name}"
            method = getattr(self.manager, method_name, None)

            if method and not method(item):
                raise ValueError("El registro fue rechazado por las reglas de negocio de EntityManager.")

            self._after_change(self.entity_info.created_message)
        except Exception as exc:
            QMessageBox.critical(self, "Error al crear", str(exc))

    def edit_item(self):
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "Selección requerida", "Por favor selecciona un registro de la tabla para editar.")
            return

        dialog = EntityDialog(
            f"Editar Registro - {self.title}",
            self.fields,
            entity=item,
            parent=self,
            primary_key=self.id_field,
        )
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

            self._after_change("Registro actualizado correctamente.", keep_page=True)
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
                if self.operation_name == "professor" and hasattr(self.manager, "get_courses_by_professor"):
                    active_courses = self.manager.get_courses_by_professor(identifier, active_only=True)
                    if active_courses:
                        prof_name = getattr(item, "full_name", f"Profesor #{identifier}")
                        course_lines = [
                            f"  • [ID {c.course_id}] {c.name} — Semestre {c.curriculum_semester} ({c.credits} créditos)"
                            for c in active_courses
                        ]
                        courses_list = "\n".join(course_lines)
                        msg = (
                            f"No es posible eliminar al docente '{prof_name}' (ID: {identifier}) "
                            f"porque tiene {len(active_courses)} asignatura(s) activa(s) a su cargo:\n\n"
                            f"{courses_list}\n\n"
                            "Por favor, reasigna estos cursos a otro docente en el módulo de Cursos "
                            "o desactívalos antes de proceder con la eliminación."
                        )
                        QMessageBox.warning(self, "Eliminación no permitida: Cursos activos asignados", msg)
                        return

                raise ValueError("No se pudo eliminar el registro. Puede tener relaciones activas o no existir.")

            self._after_change("Registro eliminado correctamente.", keep_page=True)
        except Exception as exc:
            QMessageBox.warning(self, "Error al eliminar", str(exc))

    def _after_change(self, message: str, keep_page: bool = False):
        self.refresh(keep_page=keep_page)
        self.changed.emit()
        QMessageBox.information(self, "NexoCampus", message)
