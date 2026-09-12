"""Pruebas unitarias para las mejoras de usabilidad en EntityDialog."""
import unittest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
)

from gui.components.entity_dialog import EntityDialog
from models.administrative import Administrative
from models.professor import Professor

app = QApplication.instance() or QApplication([])


class TestEntityDialogEnhancements(unittest.TestCase):
    """Verifica scroll vertical, agrupación por secciones, asteriscos, validación reactiva y control de guardado."""

    def test_scroll_area_and_resizable_layout(self):
        """Verifica que el diálogo contenga un QScrollArea vertical con widgetResizable."""
        fields = (
            ("faculty_id", "ID Facultad", "int"),
            ("name", "Nombre", "text"),
            ("dean", "Decano", "text"),
            ("active", "Estado Activo", "bool"),
        )
        dialog = EntityDialog("Nueva Facultad", fields)

        # ScrollArea presente y configurado
        self.assertIsInstance(dialog.scroll_area, QScrollArea)
        self.assertTrue(dialog.scroll_area.widgetResizable())
        self.assertEqual(
            dialog.scroll_area.verticalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )
        self.assertEqual(
            dialog.scroll_area.horizontalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )

        # Botón Guardar y nota al pie fijos en el diálogo (fuera del scroll)
        self.assertIsNotNone(dialog.save_button)
        self.assertIsNotNone(dialog.lbl_footnote)
        self.assertIn("obligatorios", dialog.lbl_footnote.text())
        dialog.close()

    def test_section_grouping_for_many_fields(self):
        """Entidades con más de 8 campos deben agrupar sus controles en secciones visuales."""
        admin_fields = (
            ("administrative_id", "ID Administrativo", "int"),
            ("full_name", "Nombre Completo", "text"),
            ("document_type", "Tipo Documento", "text"),
            ("document_number", "Número Documento", "text"),
            ("email", "Correo Electrónico", "text"),
            ("phone", "Teléfono", "text"),
            ("position", "Cargo", "text"),
            ("category", "Categoría", "text"),
            ("employment_type", "Tipo Contrato", "text"),
            ("base_salary", "Salario Base", "float"),
            ("arl_risk_class", "Clase de Riesgo ARL", "choice", ["I", "II", "III", "IV", "V"]),
            ("active", "Estado Activo", "bool"),
        )
        dialog = EntityDialog("Nuevo Administrativo", admin_fields)

        # Debe contener títulos de sección formSectionTitle
        section_titles = [
            lbl.text()
            for lbl in dialog.findChildren(QLabel, "formSectionTitle")
        ]
        self.assertGreaterEqual(len(section_titles), 3)
        self.assertIn("Datos Personales e Identificación", section_titles)
        self.assertIn("Documentación y Contacto", section_titles)
        self.assertIn("Información Académica y Laboral", section_titles)
        self.assertIn("Estado del Registro", section_titles)
        dialog.close()

    def test_compact_entity_single_form_without_multiple_sections(self):
        """Entidades compactas (<= 8 campos) no deben fragmentarse en múltiples secciones."""
        fac_fields = (
            ("faculty_id", "ID Facultad", "int"),
            ("name", "Nombre", "text"),
            ("dean", "Decano", "text"),
            ("active", "Estado Activo", "bool"),
        )
        dialog = EntityDialog("Nueva Facultad", fac_fields)
        section_titles = dialog.findChildren(QLabel, "formSectionTitle")
        self.assertEqual(len(section_titles), 0)
        dialog.close()

    def test_required_asterisk_and_footnote(self):
        """Los campos obligatorios deben lucir un asterisco rojo y los booleanos no."""
        fields = (
            ("id", "ID", "int"),
            ("name", "Nombre", "text"),
            ("email", "Correo Electrónico", "text"),
            ("active", "Estado Activo", "bool"),
        )
        dialog = EntityDialog("Test Asteriscos", fields)

        lbl_name = dialog.findChild(QLabel, "label_name")
        self.assertIsNotNone(lbl_name)
        self.assertIn("*", lbl_name.text())
        self.assertIn("#DC2626", lbl_name.text())

        lbl_email = dialog.findChild(QLabel, "label_email")
        self.assertIsNotNone(lbl_email)
        self.assertIn("*", lbl_email.text())

        lbl_active = dialog.findChild(QLabel, "label_active")
        self.assertIsNotNone(lbl_active)
        self.assertNotIn("*", lbl_active.text())

        self.assertIn("Campos obligatorios", dialog.lbl_footnote.text())
        dialog.close()

    def test_realtime_email_validation(self):
        """Verifica que el correo electrónico valide su formato mientras el usuario escribe."""
        fields = (
            ("full_name", "Nombre", "text"),
            ("email", "Correo Electrónico", "text"),
        )
        dialog = EntityDialog("Nuevo Usuario", fields)
        email_widget = dialog._widgets.get("email")
        err_lbl = dialog._error_labels.get("email")
        self.assertIsInstance(email_widget, QLineEdit)

        # 1. Correo con formato inválido
        email_widget.setText("correo_invalido")
        self.assertTrue(email_widget.property("has_error"))
        self.assertFalse(err_lbl.isHidden())
        self.assertIn("inválido", err_lbl.text().lower())
        self.assertFalse(dialog.save_button.isEnabled())

        # 2. Correo válido
        email_widget.setText("docente@universidad.edu.co")
        self.assertFalse(email_widget.property("has_error"))
        self.assertTrue(err_lbl.isHidden())
        self.assertEqual(err_lbl.text(), "")
        dialog.close()

    def test_realtime_phone_and_document_validation(self):
        """Verifica que teléfono y documento solo admitan dígitos/guiones y validen longitud mínima."""
        fields = (
            ("phone", "Teléfono", "text"),
            ("document_number", "Número Documento", "text"),
        )
        dialog = EntityDialog("Validación Numérica", fields)
        phone_widget = dialog._widgets.get("phone")
        doc_widget = dialog._widgets.get("document_number")

        phone_err = dialog._error_labels.get("phone")
        doc_err = dialog._error_labels.get("document_number")

        # Teléfono con letras
        phone_widget.setText("300-ABC-1234")
        self.assertTrue(phone_widget.property("has_error"))
        self.assertFalse(phone_err.isHidden())
        self.assertIn("dígitos", phone_err.text().lower())

        # Teléfono con longitud insuficiente
        phone_widget.setText("12345")
        self.assertTrue(phone_widget.property("has_error"))
        self.assertIn("al menos 7", phone_err.text().lower())

        # Teléfono válido
        phone_widget.setText("3001234567")
        self.assertFalse(phone_widget.property("has_error"))
        self.assertTrue(phone_err.isHidden())

        # Documento con caracteres prohibidos
        doc_widget.setText("CC#98765")
        self.assertTrue(doc_widget.property("has_error"))
        self.assertFalse(doc_err.isHidden())
        self.assertIn("dígitos", doc_err.text().lower())

        # Documento muy corto
        doc_widget.setText("12")
        self.assertTrue(doc_widget.property("has_error"))
        self.assertIn("al menos 5", doc_err.text().lower())

        # Documento válido
        doc_widget.setText("1098765432")
        self.assertFalse(doc_widget.property("has_error"))
        self.assertTrue(doc_err.isHidden())
        dialog.close()

    def test_numeric_spinboxes_prevent_negative_values(self):
        """Verifica que salarios y campos numéricos utilicen spinboxes con mínimo en 0 impidiendo negativos."""
        fields = (
            ("base_salary", "Salario Base", "float"),
            ("credits", "Créditos", "int"),
            ("max_capacity", "Cupo Máximo", "int"),
        )
        dialog = EntityDialog("Campos Numéricos", fields)
        salary_widget = dialog._widgets.get("base_salary")
        credits_widget = dialog._widgets.get("credits")
        capacity_widget = dialog._widgets.get("max_capacity")

        self.assertIsInstance(salary_widget, QDoubleSpinBox)
        self.assertGreaterEqual(salary_widget.minimum(), 0.0)
        self.assertEqual(salary_widget.prefix(), "$ ")

        self.assertIsInstance(credits_widget, QSpinBox)
        self.assertGreaterEqual(credits_widget.minimum(), 0)

        self.assertIsInstance(capacity_widget, QSpinBox)
        self.assertGreaterEqual(capacity_widget.minimum(), 0)
        dialog.close()

    def test_save_button_reactivity_create_and_edit_modes(self):
        """El botón Guardar debe habilitarse solo cuando todos los campos requeridos estén completos y válidos."""
        fields = (
            ("professor_id", "ID Profesor", "int"),
            ("full_name", "Nombre Completo", "text"),
            ("email", "Correo Electrónico", "text"),
            ("phone", "Teléfono", "text"),
        )

        # 1. Modo Creación: empieza deshabilitado porque faltan datos obligatorios
        dialog = EntityDialog("Nuevo Profesor", fields)
        self.assertFalse(dialog.save_button.isEnabled())

        # Llenar datos válidos secuencialmente
        dialog._widgets["professor_id"].setValue(101)
        dialog._widgets["full_name"].setText("Dra. Marcela García")
        dialog._widgets["email"].setText("m.garcia@universidad.edu.co")
        dialog._widgets["phone"].setText("3109876543")

        # Ahora todos están completos y válidos
        self.assertTrue(dialog.save_button.isEnabled())

        # Si introducimos un error en el correo, se deshabilita de inmediato
        dialog._widgets["email"].setText("correo_roto")
        self.assertFalse(dialog.save_button.isEnabled())

        # Restaurar correo válido
        dialog._widgets["email"].setText("m.garcia@universidad.edu.co")
        self.assertTrue(dialog.save_button.isEnabled())
        dialog.close()

        # 2. Modo Edición: empieza habilitado si los datos de la entidad son válidos
        prof = Professor(
            professor_id=102,
            full_name="Prof. Pedro Pérez",
            email="p.perez@universidad.edu.co",
            phone="3112233445",
        )
        dialog_edit = EntityDialog("Editar Profesor", fields, entity=prof)
        self.assertTrue(dialog_edit.save_button.isEnabled())

        # Borrar el nombre obligatorio deshabilita Guardar y muestra error
        dialog_edit._widgets["full_name"].setText("")
        self.assertFalse(dialog_edit.save_button.isEnabled())
        self.assertFalse(dialog_edit._error_labels["full_name"].isHidden())

        # Restaurar nombre re-habilita Guardar
        dialog_edit._widgets["full_name"].setText("Prof. Pedro Pérez Modificado")
        self.assertTrue(dialog_edit.save_button.isEnabled())
        self.assertTrue(dialog_edit._error_labels["full_name"].isHidden())
        dialog_edit.close()


if __name__ == "__main__":
    unittest.main()
