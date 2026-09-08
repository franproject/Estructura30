from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class EntityDialog(QDialog):
    """Dialogo generico que construye formularios desde campos del modelo."""

    def __init__(self, title, fields, entity=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(430)
        self._fields = fields
        self._widgets = {}
        layout = QVBoxLayout(self)
        form = QFormLayout()
        for name, label, kind in fields:
            if kind == "bool":
                widget = QCheckBox()
                widget.setChecked(bool(getattr(entity, name, True)) if entity else True)
            else:
                widget = QLineEdit()
                if entity is not None:
                    widget.setText(str(getattr(entity, name, "")))
            if name.endswith("_id") and entity is not None:
                widget.setEnabled(False)
            self._widgets[name] = widget
            form.addRow(label, widget)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        result = {}
        for name, _, kind in self._fields:
            widget = self._widgets[name]
            if kind == "bool":
                result[name] = widget.isChecked()
            elif kind == "int":
                result[name] = int(widget.text() or 0)
            elif kind == "float":
                result[name] = float(widget.text() or 0)
            else:
                result[name] = widget.text().strip()
        return result


class CrudPage(QWidget):
    changed = Signal()

    def __init__(self, title, manager, collection_name, model_cls, id_field, fields, columns, row_builder, operation_name=None, parent=None):
        super().__init__(parent)
        self.title = title
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
        layout.setContentsMargins(28, 24, 28, 24)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        title = QLabel(self.title)
        title.setObjectName("pageTitle")
        subtitle = QLabel("Gestiona registros usando las reglas del EntityManager")
        subtitle.setObjectName("pageSubtitle")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        header.addLayout(heading)
        header.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar...")
        self.search.setMaximumWidth(220)
        self.search.textChanged.connect(self.refresh)
        header.addWidget(self.search)
        add = QPushButton("+ Nuevo")
        add.setObjectName("primaryButton")
        add.clicked.connect(self.create_item)
        header.addWidget(add)
        layout.addLayout(header)

        actions = QHBoxLayout()
        self.edit_button = QPushButton("Editar seleccionado")
        self.edit_button.setObjectName("secondaryButton")
        self.edit_button.clicked.connect(self.edit_item)
        self.delete_button = QPushButton("Eliminar seleccionado")
        self.delete_button.setObjectName("secondaryButton")
        self.delete_button.clicked.connect(self.delete_item)
        actions.addWidget(self.edit_button)
        actions.addWidget(self.delete_button)
        actions.addStretch()
        layout.addLayout(actions)

        self.table = QTableWidget(0, len(self.columns))
        self.table.setObjectName("dataTable")
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def _collection(self):
        return getattr(self.manager, self.collection_name)

    def refresh(self):
        query = self.search.text().lower().strip() if hasattr(self, "search") else ""
        self._items = [item for item in self._collection() if not query or query in str(self.row_builder(item)).lower()]
        self.table.setRowCount(len(self._items))
        for row, item in enumerate(self._items):
            for column, value in enumerate(self.row_builder(item)):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()

    def _selected(self):
        row = self.table.currentRow()
        return self._items[row] if 0 <= row < len(self._items) else None

    def create_item(self):
        dialog = EntityDialog(f"Nuevo {self.title}", self.fields, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            item = self.model_cls(**dialog.values())
            method = getattr(self.manager, f"create_{self.operation_name}")
            if not method(item):
                raise ValueError("La entidad fue rechazada por las reglas de negocio")
            self._after_change("Registro creado correctamente")
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo crear", str(exc))

    def edit_item(self):
        item = self._selected()
        if item is None:
            QMessageBox.information(self, "Selecciona un registro", "Selecciona una fila para editar.")
            return
        dialog = EntityDialog(f"Editar {self.title}", self.fields, item, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            values = dialog.values()
            identifier = getattr(item, self.id_field)
            updates = {key: value for key, value in values.items() if key != self.id_field}
            method_name = f"update_{self.operation_name}"
            if self.operation_name == "enrollment":
                updated = self.manager.register_grade(identifier, values["final_grade"])
            else:
                updated = getattr(self.manager, method_name)(identifier, **updates)
            if not updated:
                raise ValueError("La actualización fue rechazada por las reglas de negocio")
            self._after_change("Registro actualizado correctamente")
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo actualizar", str(exc))

    def delete_item(self):
        item = self._selected()
        if item is None:
            QMessageBox.information(self, "Selecciona un registro", "Selecciona una fila para eliminar.")
            return
        answer = QMessageBox.question(self, "Confirmar eliminación", "¿Eliminar el registro seleccionado?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            identifier = getattr(item, self.id_field)
            method_name = f"delete_{self.operation_name}"
            if not getattr(self.manager, method_name)(identifier):
                raise ValueError("El registro tiene relaciones activas o no existe")
            self._after_change("Registro eliminado")
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo eliminar", str(exc))

    def _after_change(self, message):
        self.refresh()
        self.changed.emit()
        QMessageBox.information(self, "NexoCampus", message)
