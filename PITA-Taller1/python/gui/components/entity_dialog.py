"""Diálogo dinámico de creación/edición de entidades basadas en los modelos."""
from typing import Any, Callable, Optional, Union

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)


ARL_RISK_CLASSES = (
    ("I", "Clase I - Riesgo Mínimo (0.522%)"),
    ("II", "Clase II - Riesgo Bajo (1.044%)"),
    ("III", "Clase III - Riesgo Medio (2.436%)"),
    ("IV", "Clase IV - Riesgo Alto (4.350%)"),
    ("V", "Clase V - Riesgo Máximo (6.960%)"),
)


def _resolve_relation_options(source: Any) -> list[tuple[Any, str]]:
    """Convierte la fuente de opciones relacionales en una lista de (id, texto_legible).
    
    Admite:
    - Callables / lambdas que retornan listas, LinkedLists o dicts.
    - Listas o LinkedLists de instancias de modelos.
    - Listas de tuplas (id, etiqueta).
    - Diccionarios {id: etiqueta}.
    """
    if callable(source):
        try:
            raw = source()
        except Exception:
            raw = []
    else:
        raw = source

    if raw is None:
        return []

    # Normalizar colecciones personalizadas (LinkedList)
    raw_head = getattr(raw, "head", None)
    if raw_head is not None:
        items = []
        curr = raw_head
        while curr is not None:
            items.append(curr.data)
            curr = curr.next
    elif isinstance(raw, dict):
        return [(k, str(v)) for k, v in raw.items()]
    elif isinstance(raw, (list, tuple, set)):
        items = list(raw)
    else:
        items = [raw]

    options = []
    for item in items:
        # Si ya es una tupla/lista (id, etiqueta)
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            options.append((item[0], str(item[1])))
            continue

        # Detección de identificador
        item_id = None
        for id_attr in (
            "faculty_id",
            "program_id",
            "course_id",
            "student_id",
            "professor_id",
            "administrative_id",
            "id",
        ):
            if hasattr(item, id_attr):
                item_id = getattr(item, id_attr)
                break
        if item_id is None:
            item_id = getattr(item, "id", None) or str(item)

        # Detección de nombre o descripción legible
        display_name = (
            getattr(item, "full_name", None)
            or getattr(item, "name", None)
            or str(item)
        )

        options.append((item_id, f"{display_name} (#{item_id})"))

    return options


class EntityDialog(QDialog):
    """Genera un formulario a partir de los metadatos de campos del modelo."""

    def __init__(
        self,
        title: str,
        fields: tuple,
        entity=None,
        parent=None,
        primary_key: Optional[str] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(460)
        self._fields = fields
        self._primary_key = primary_key
        self._parsed_fields = []
        self._widgets = {}
        self._has_invalid_relation = False
        self._build_ui(entity)

    def _parse_field_spec(self, field_spec: tuple) -> tuple[str, str, str, Any]:
        """Estandariza especificaciones de campo de 2, 3 o 4 elementos."""
        if len(field_spec) == 4:
            name, label, kind, extra = field_spec
            return str(name), str(label), str(kind), extra
        elif len(field_spec) == 3:
            name, label, kind = field_spec
            extra = None
            if isinstance(label, (list, tuple)) and kind in ("choice", "relation"):
                lbl, extra = label[0], label[1]
                return str(name), str(lbl), str(kind), extra
            return str(name), str(label), str(kind), extra
        elif len(field_spec) == 2:
            name, label = field_spec
            return str(name), str(label), "text", None
        raise ValueError(f"Especificación de campo inválida: {field_spec}")

    def _build_ui(self, entity):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)

        self._parsed_fields = [self._parse_field_spec(f) for f in self._fields]

        # Si no se indicó primary_key explícita, se infiere del primer campo ID no relacional
        if self._primary_key is None and self._parsed_fields:
            first_name, _, first_kind, _ = self._parsed_fields[0]
            if first_name.endswith("_id") and first_kind != "relation":
                self._primary_key = first_name

        for name, label, kind, extra in self._parsed_fields:
            val = getattr(entity, name, None) if entity else None

            if name == "arl_risk_class" or kind == "arl_risk":
                widget = QComboBox()
                for code, desc in ARL_RISK_CLASSES:
                    widget.addItem(desc, code)
                val_str = str(val) if val is not None else "I"
                idx = -1
                for i in range(widget.count()):
                    if widget.itemData(i) == val_str:
                        idx = i
                        break
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                else:
                    widget.setCurrentIndex(0)

            elif kind == "bool":
                widget = QCheckBox()
                widget.setChecked(bool(val) if val is not None else True)

            elif kind == "int":
                widget = QSpinBox()
                widget.setRange(0, 999999)
                if val is not None:
                    widget.setValue(int(val))

            elif kind == "float":
                widget = QDoubleSpinBox()
                widget.setRange(0.0, 99999999.0)
                widget.setDecimals(2)
                if val is not None:
                    widget.setValue(float(val))

            elif kind == "choice":
                options = extra if isinstance(extra, (list, tuple)) else []
                widget = QComboBox()
                widget.addItems([str(opt) for opt in options])
                if val is not None and str(val) in [str(opt) for opt in options]:
                    widget.setCurrentText(str(val))

            elif kind == "relation":
                options = _resolve_relation_options(extra)
                widget = QComboBox()
                widget.setProperty("is_relation", True)

                if not options:
                    widget.addItem("Sin opciones disponibles", None)
                    widget.setEnabled(False)
                    self._has_invalid_relation = True
                else:
                    for opt_id, opt_label in options:
                        widget.addItem(opt_label, opt_id)

                    if val is not None:
                        idx = -1
                        for i in range(widget.count()):
                            item_data = widget.itemData(i)
                            if item_data == val or str(item_data) == str(val):
                                idx = i
                                break
                        if idx >= 0:
                            widget.setCurrentIndex(idx)
                        else:
                            # Opción preexistente que no está en la lista activa (ej. entidad inactiva)
                            widget.insertItem(0, f"ID {val} (Actual)", val)
                            widget.setCurrentIndex(0)
            else:
                widget = QLineEdit()
                if val is not None:
                    widget.setText(str(val))

            # Deshabilitar solo la clave primaria durante la edición (las relaciones foráneas sí se pueden editar)
            if entity is not None and name == self._primary_key:
                widget.setEnabled(False)

            self._widgets[name] = widget
            form.addRow(label, widget)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        save_button.setText("Guardar")
        save_button.setObjectName("primaryButton")

        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setText("Cancelar")
        cancel_button.setObjectName("ghostButton")

        if self._has_invalid_relation:
            save_button.setEnabled(False)
            save_button.setToolTip("No se puede guardar: existen campos relacionales sin opciones disponibles.")

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(
            """
            QDialog { background-color: #FFFFFF; color: #0F172A; }
            QLabel { color: #0F172A; background: transparent; }
            """
        )

    def accept(self):
        # Validación de negocio: no permitir guardar si alguna relación requerida no tiene opción válida
        for name, label, kind, _ in self._parsed_fields:
            if kind == "relation":
                widget = self._widgets.get(name)
                if isinstance(widget, QComboBox):
                    data = widget.currentData()
                    if data is None:
                        QMessageBox.warning(
                            self,
                            "Relación requerida",
                            f"No se puede guardar: el campo '{label}' no tiene una opción válida seleccionada.",
                        )
                        return
        super().accept()

    def values(self) -> dict:
        result = {}
        for name, _, kind, _ in self._parsed_fields:
            widget = self._widgets[name]
            if name == "arl_risk_class" or kind == "arl_risk":
                data = widget.currentData() if isinstance(widget, QComboBox) else None
                result[name] = str(data) if data is not None else (widget.currentText() if isinstance(widget, QComboBox) else "I")
            elif kind == "bool":
                result[name] = widget.isChecked()
            elif kind == "int":
                result[name] = widget.value() if isinstance(widget, QSpinBox) else int(widget.text() or 0)
            elif kind == "float":
                result[name] = widget.value() if isinstance(widget, QDoubleSpinBox) else float(widget.text() or 0.0)
            elif kind == "choice":
                result[name] = widget.currentText()
            elif kind == "relation":
                data = widget.currentData() if isinstance(widget, QComboBox) else None
                if data is not None:
                    try:
                        result[name] = int(data)
                    except (ValueError, TypeError):
                        result[name] = data
                else:
                    result[name] = None
            else:
                result[name] = widget.text().strip()
        return result
