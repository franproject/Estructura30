"""Diálogo dinámico de creación/edición de entidades basadas en los modelos."""
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)


class EntityDialog(QDialog):
    """Genera un formulario a partir de los metadatos de campos del modelo."""

    def __init__(self, title: str, fields: tuple, entity=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(440)
        self._fields = fields
        self._widgets = {}
        self._build_ui(entity)

    def _build_ui(self, entity):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)

        for name, label, kind in self._fields:
            val = getattr(entity, name, None) if entity else None
            
            if kind == "bool":
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
            elif kind == "choice" and isinstance(label, (list, tuple)):
                # Manejo de listas desplegables
                field_lbl, options = label[0], label[1]
                widget = QComboBox()
                widget.addItems(options)
                if val is not None and str(val) in options:
                    widget.setCurrentText(str(val))
                label = field_lbl
            else:
                widget = QLineEdit()
                if val is not None:
                    widget.setText(str(val))

            # Deshabilitar ID en edición
            if name.endswith("_id") and entity is not None:
                widget.setEnabled(False)

            self._widgets[name] = widget
            form.addRow(label if isinstance(label, str) else str(label), widget)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setObjectName("ghostButton")

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict:
        result = {}
        for name, _, kind in self._fields:
            widget = self._widgets[name]
            if kind == "bool":
                result[name] = widget.isChecked()
            elif kind == "int":
                result[name] = widget.value() if isinstance(widget, QSpinBox) else int(widget.text() or 0)
            elif kind == "float":
                result[name] = widget.value() if isinstance(widget, QDoubleSpinBox) else float(widget.text() or 0.0)
            elif kind == "choice":
                result[name] = widget.currentText()
            else:
                result[name] = widget.text().strip()
        return result
