"""Diálogo dinámico de creación/edición de entidades basadas en los modelos."""
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
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
    """Genera un formulario adaptativo con scroll, agrupación por secciones y validación reactiva en tiempo real."""

    SECTION_ORDER = (
        "Datos Personales e Identificación",
        "Documentación y Contacto",
        "Información Académica y Laboral",
        "Estado del Registro",
    )

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
        self.setMinimumWidth(500)
        self.resize(520, 620)
        self._fields = fields
        self._primary_key = primary_key
        self._entity = entity
        self._parsed_fields: List[Tuple[str, str, str, Any]] = []
        self._widgets: Dict[str, QWidget] = {}
        self._error_labels: Dict[str, QLabel] = {}
        self._field_errors: Dict[str, Optional[str]] = {}
        self._touched: Set[str] = set()
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

    def _classify_field_section(self, name: str, kind: str) -> str:
        """Clasifica semánticamente un campo en una sección para entidades con más de 8 campos."""
        if kind == "relation":
            return "Información Académica y Laboral"
        if name in ("document_type", "document_number", "email", "phone"):
            return "Documentación y Contacto"
        if name in ("active", "status") and kind == "bool":
            return "Estado del Registro"
        if name in ("active",):
            return "Estado del Registro"
        if name in (
            "faculty_id",
            "program_id",
            "course_id",
            "student_id",
            "professor_id",
            "administrative_id",
            "enrollment_id",
            "name",
            "full_name",
            "birth_date",
            "dean",
            "program_director",
            "creation_date",
        ):
            return "Datos Personales e Identificación"
        return "Información Académica y Laboral"

    def _is_field_required(self, name: str, kind: str, extra: Any) -> bool:
        """Determina si un campo es de diligenciamiento obligatorio."""
        if kind == "bool":
            return False
        if isinstance(extra, dict) and "required" in extra:
            return bool(extra["required"])
        return True

    def _build_ui(self, entity):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 18, 20, 16)
        root_layout.setSpacing(10)

        # 1. Scroll Area vertical que garantiza que formularios largos no desborden la ventana
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("entityDialogScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(2, 2, 2, 2)
        self.scroll_layout.setSpacing(12)
        self.scroll_area.setWidget(self.scroll_content)
        root_layout.addWidget(self.scroll_area, stretch=1)

        self._parsed_fields = [self._parse_field_spec(f) for f in self._fields]

        # Inferencia de primary_key si no se especificó explícitamente
        if self._primary_key is None and self._parsed_fields:
            first_name, _, first_kind, _ = self._parsed_fields[0]
            if first_name.endswith("_id") and first_kind != "relation":
                self._primary_key = first_name

        # Creación de los widgets de entrada
        field_widgets_map: Dict[str, QWidget] = {}
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
                widget.setCurrentIndex(idx if idx >= 0 else 0)

            elif kind == "bool":
                widget = QCheckBox()
                widget.setChecked(bool(val) if val is not None else True)

            elif kind == "int":
                widget = QSpinBox()
                widget.setRange(0, 999999)
                if (name == self._primary_key or name.endswith("_id")) and kind != "relation":
                    widget.setRange(0, 999999)
                elif name == "credits":
                    widget.setRange(1, 50)
                elif name in ("curriculum_semester", "current_semester"):
                    widget.setRange(1, 20)
                elif name == "max_capacity":
                    widget.setRange(1, 500)
                if val is not None:
                    try:
                        widget.setValue(int(val))
                    except (ValueError, TypeError):
                        widget.setValue(0)

            elif kind == "float":
                widget = QDoubleSpinBox()
                if name in ("base_salary", "net_salary", "hourly_rate") or "salario" in label.lower():
                    # Rango mínimo 0 que impide directamente salarios negativos
                    widget.setRange(0.0, 100_000_000.0)
                    widget.setDecimals(2)
                    widget.setPrefix("$ ")
                    widget.setSingleStep(50000.0)
                elif name == "final_grade":
                    widget.setRange(0.0, 5.0)
                    widget.setDecimals(1)
                    widget.setSingleStep(0.1)
                else:
                    widget.setRange(0.0, 99999999.0)
                    widget.setDecimals(2)
                    widget.setSingleStep(1.0)
                if val is not None:
                    try:
                        widget.setValue(float(val))
                    except (ValueError, TypeError):
                        widget.setValue(0.0)

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
                            widget.insertItem(0, f"ID {val} (Actual)", val)
                            widget.setCurrentIndex(0)
            else:
                widget = QLineEdit()
                if val is not None:
                    widget.setText(str(val))

            # Deshabilitar clave primaria durante edición
            if entity is not None and name == self._primary_key:
                widget.setEnabled(False)

            self._widgets[name] = widget
            field_widgets_map[name] = widget

            # Conexión reactiva en tiempo real a cambios de valor
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda _, n=name: self._on_field_changed(n))
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                widget.valueChanged.connect(lambda _, n=name: self._on_field_changed(n))
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(lambda _, n=name: self._on_field_changed(n))
            elif isinstance(widget, QCheckBox):
                widget.toggled.connect(lambda _, n=name: self._on_field_changed(n))

        # 2. Renderizado de campos (Agrupados en secciones si > 8 campos, o unificado si <= 8)
        total_fields_count = len(self._parsed_fields)
        if total_fields_count > 8:
            sections_map: Dict[str, List[Tuple[str, str, str, Any]]] = {
                sec: [] for sec in self.SECTION_ORDER
            }
            for spec in self._parsed_fields:
                sec_name = self._classify_field_section(spec[0], spec[2])
                if sec_name in sections_map:
                    sections_map[sec_name].append(spec)
                else:
                    sections_map["Información Académica y Laboral"].append(spec)

            for sec_name in self.SECTION_ORDER:
                specs = sections_map[sec_name]
                if not specs:
                    continue

                section_frame = QFrame()
                section_frame.setObjectName("formSectionFrame")
                sec_layout = QVBoxLayout(section_frame)
                sec_layout.setContentsMargins(14, 12, 14, 12)
                sec_layout.setSpacing(10)

                sec_title = QLabel(sec_name)
                sec_title.setObjectName("formSectionTitle")
                sec_layout.addWidget(sec_title)

                form = QFormLayout()
                form.setSpacing(10)
                form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

                for name, label, kind, extra in specs:
                    w = field_widgets_map[name]
                    is_req = self._is_field_required(name, kind, extra)
                    self._create_field_row(form, name, label, w, is_req)

                sec_layout.addLayout(form)
                self.scroll_layout.addWidget(section_frame)
        else:
            # Formulario unificado para entidades compactas (<= 8 campos)
            section_frame = QFrame()
            section_frame.setObjectName("formSectionFrame")
            sec_layout = QVBoxLayout(section_frame)
            sec_layout.setContentsMargins(14, 12, 14, 12)
            sec_layout.setSpacing(10)

            form = QFormLayout()
            form.setSpacing(10)
            form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

            for name, label, kind, extra in self._parsed_fields:
                w = field_widgets_map[name]
                is_req = self._is_field_required(name, kind, extra)
                self._create_field_row(form, name, label, w, is_req)

            sec_layout.addLayout(form)
            self.scroll_layout.addWidget(section_frame)

        self.scroll_layout.addStretch()

        # 3. Nota al pie de campos obligatorios
        self.lbl_footnote = QLabel("* Campos obligatorios")
        self.lbl_footnote.setObjectName("formFootnote")
        root_layout.addWidget(self.lbl_footnote)

        # 4. Barra de botones fija al pie del diálogo
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setText("Guardar")
        self.save_button.setObjectName("primaryButton")

        self.cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        self.cancel_button.setText("Cancelar")
        self.cancel_button.setObjectName("ghostButton")

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root_layout.addWidget(buttons)

        # En edición, marcar todos los campos como verificados y evaluar validez
        if entity is not None:
            for name, _, _, _ in self._parsed_fields:
                self._touched.add(name)

        self._update_save_button()

        self.setStyleSheet(
            """
            QDialog { background-color: #FFFFFF; color: #0F172A; }
            QLabel { color: #0F172A; background: transparent; }
            QScrollArea { background-color: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background-color: transparent; }
            """
        )

    def _create_field_row(
        self,
        form: QFormLayout,
        name: str,
        label: str,
        widget: QWidget,
        is_required: bool,
    ):
        """Crea una fila de formulario con etiqueta estilizada (con asterisco rojo) y contenedor de error."""
        lbl_text = f"{label} <span style='color: #DC2626; font-weight: bold;'>*</span>" if is_required else label
        lbl_widget = QLabel(lbl_text)
        lbl_widget.setTextFormat(Qt.TextFormat.RichText)
        lbl_widget.setObjectName(f"label_{name}")
        lbl_widget.setStyleSheet("font-size: 13px; font-weight: 500; color: #334155; background: transparent;")

        field_container = QWidget()
        field_layout = QVBoxLayout(field_container)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(3)
        field_layout.addWidget(widget)

        error_lbl = QLabel()
        error_lbl.setObjectName("fieldErrorLabel")
        error_lbl.setStyleSheet("color: #DC2626; font-size: 11px; font-weight: 500; background: transparent;")
        error_lbl.setVisible(False)
        error_lbl.setWordWrap(True)
        field_layout.addWidget(error_lbl)

        self._error_labels[name] = error_lbl
        form.addRow(lbl_widget, field_container)

    def _validate_field(self, name: str) -> Optional[str]:
        """Ejecuta las reglas de validación en tiempo real para un campo específico."""
        widget = self._widgets.get(name)
        if widget is None or not widget.isEnabled():
            return None

        spec = next((f for f in self._parsed_fields if f[0] == name), None)
        if not spec:
            return None
        _, label, kind, extra = spec
        is_required = self._is_field_required(name, kind, extra)

        # 1. Relaciones foráneas
        if kind == "relation":
            if isinstance(widget, QComboBox):
                if widget.currentData() is None:
                    return f"Debe seleccionar una opción válida para '{label}'."
            return None

        # 2. Correo Electrónico
        if name == "email" or "correo" in label.lower() or kind == "email":
            val = widget.text().strip() if isinstance(widget, QLineEdit) else ""
            if not val:
                if is_required:
                    return "El correo electrónico es obligatorio."
                return None
            email_pattern = r"^[^@\s]+@[^@\s]+\.[a-zA-Z0-9-.]+$"
            if not re.match(email_pattern, val) or val.endswith("."):
                return "Formato inválido (ej: usuario@universidad.edu.co)."
            return None

        # 3. Teléfono
        if name == "phone" or "teléfono" in label.lower() or "telefono" in label.lower():
            val = widget.text().strip() if isinstance(widget, QLineEdit) else ""
            if not val:
                if is_required:
                    return "El número de teléfono es obligatorio."
                return None
            if not re.match(r"^[\d\s\-+()]+$", val):
                return "Solo debe contener dígitos, guiones o espacios."
            digits = [c for c in val if c.isdigit()]
            if len(digits) < 7:
                return "El teléfono debe contener al menos 7 dígitos."
            if len(digits) > 15:
                return "El teléfono no debe superar 15 dígitos."
            return None

        # 4. Documento de Identidad
        if name == "document_number" or ("documento" in label.lower() and "tipo" not in label.lower()):
            val = widget.text().strip() if isinstance(widget, QLineEdit) else ""
            if not val:
                if is_required:
                    return "El número de documento es obligatorio."
                return None
            if not re.match(r"^[\d\-]+$", val):
                return "El documento solo debe contener dígitos o guiones."
            digits = [c for c in val if c.isdigit()]
            if len(digits) < 5:
                return "El documento debe contener al menos 5 dígitos."
            if len(digits) > 15:
                return "El documento no debe superar 15 dígitos."
            return None

        # 5. Clave primaria numérica en creación
        if (name == self._primary_key or name.endswith("_id")) and kind == "int" and self._entity is None:
            if isinstance(widget, QSpinBox):
                if widget.value() <= 0:
                    return "El identificador debe ser mayor a 0."
            elif isinstance(widget, QLineEdit):
                txt = widget.text().strip()
                if not txt:
                    return "El identificador es obligatorio."
                if not txt.isdigit() or int(txt) <= 0:
                    return "El identificador debe ser un número entero positivo."
            return None

        # 6. Campos requeridos generales de texto
        if isinstance(widget, QLineEdit):
            txt = widget.text().strip()
            if is_required and not txt:
                return f"El campo '{label}' es obligatorio."
            return None

        # 7. Valores numéricos (SpinBox / DoubleSpinBox)
        if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            if widget.value() < 0:
                return "El valor no puede ser negativo."
            return None

        return None

    def _on_field_changed(self, name: str):
        """Manejador reactivo disparado al modificarse el valor de un campo."""
        self._touched.add(name)
        err = self._validate_field(name)
        self._field_errors[name] = err

        widget = self._widgets.get(name)
        err_lbl = self._error_labels.get(name)

        if widget is not None:
            has_error = bool(err)
            widget.setProperty("has_error", has_error)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        if err_lbl is not None:
            if err:
                err_lbl.setText(err)
                err_lbl.setVisible(True)
            else:
                err_lbl.setText("")
                err_lbl.setVisible(False)

        self._update_save_button()

    def _update_save_button(self):
        """Habilita o deshabilita el botón Guardar según el estado de validez de todos los campos."""
        if not hasattr(self, "save_button") or self.save_button is None:
            return

        # 1. Bloqueo si hay relación inválida
        if self._has_invalid_relation:
            self.save_button.setEnabled(False)
            self.save_button.setToolTip("No se puede guardar: existen campos relacionales sin opciones disponibles.")
            return

        # 2. Validación de todos los campos
        all_valid = True
        for name, _, _, _ in self._parsed_fields:
            widget = self._widgets.get(name)
            if widget is None or not widget.isEnabled():
                continue

            err = self._validate_field(name)
            if err is not None:
                all_valid = False
                break

        if all_valid:
            self.save_button.setEnabled(True)
            self.save_button.setToolTip("Guardar registro")
        else:
            self.save_button.setEnabled(False)
            self.save_button.setToolTip("Complete todos los campos obligatorios sin errores para guardar.")

    def accept(self):
        """Valida exhaustivamente antes de confirmar el diálogo."""
        # Validación de relaciones (preserva comportamiento esperado en pruebas)
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

        # Marcar todos los campos como tocados para visibilizar errores en campos vacíos
        has_errors = False
        for name, _, _, _ in self._parsed_fields:
            self._touched.add(name)
            err = self._validate_field(name)
            widget = self._widgets.get(name)
            err_lbl = self._error_labels.get(name)
            if err:
                has_errors = True
                if widget:
                    widget.setProperty("has_error", True)
                    widget.style().unpolish(widget)
                    widget.style().polish(widget)
                if err_lbl:
                    err_lbl.setText(err)
                    err_lbl.setVisible(True)
            else:
                if widget:
                    widget.setProperty("has_error", False)
                    widget.style().unpolish(widget)
                    widget.style().polish(widget)
                if err_lbl:
                    err_lbl.setText("")
                    err_lbl.setVisible(False)

        self._update_save_button()

        if has_errors or not self.save_button.isEnabled():
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
                result[name] = widget.isChecked() if isinstance(widget, QCheckBox) else False
            elif kind == "int":
                result[name] = (
                    widget.value()
                    if isinstance(widget, QSpinBox)
                    else int(widget.text() or 0)
                    if isinstance(widget, QLineEdit)
                    else 0
                )
            elif kind == "float":
                result[name] = (
                    widget.value()
                    if isinstance(widget, QDoubleSpinBox)
                    else float(widget.text() or 0.0)
                    if isinstance(widget, QLineEdit)
                    else 0.0
                )
            elif kind == "choice":
                if isinstance(widget, QComboBox):
                    result[name] = widget.currentText()
                elif isinstance(widget, QLineEdit):
                    result[name] = widget.text().strip()
                else:
                    result[name] = ""
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
                result[name] = widget.text().strip() if isinstance(widget, QLineEdit) else ""
        return result
