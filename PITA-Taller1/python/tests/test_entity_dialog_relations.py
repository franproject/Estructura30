"""Pruebas unitarias para EntityDialog con soporte de campos relacionales.

Verifica:
1. Soporte de campos tipo 'relation' con QComboBox y datos de clave foránea.
2. Resolución dinámica de opciones (tuplas, modelos, LinkedList, diccionarios, lambdas).
3. Manejo de relaciones vacías: selector deshabilitado con "Sin opciones disponibles", botón Guardar deshabilitado y bloqueo de accept().
4. Modo edición: preselección del valor actual, clave primaria deshabilitada y campo relacional editable.
5. Verificación de las configuraciones de CrudPage en MainWindow para Programas, Cursos, Estudiantes, Profesores e Inscripciones.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QComboBox, QDialogButtonBox, QMessageBox

from models.course import Course
from models.faculty import Faculty
from models.linked_list import LinkedList
from models.professor import Professor
from models.program import Program
from models.student import Student
from services.entity_manager import EntityManager
from gui.components.entity_dialog import EntityDialog, _resolve_relation_options
from gui.main_window import MainWindow


class TestEntityDialogRelations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_resolve_relation_options_with_tuples(self):
        """Verifica la resolución de tuplas directas (id, etiqueta)."""
        source = [(1, "Facultad A"), (2, "Facultad B")]
        options = _resolve_relation_options(source)
        self.assertEqual(options, [(1, "Facultad A"), (2, "Facultad B")])

    def test_resolve_relation_options_with_dict(self):
        """Verifica la resolución de diccionarios {id: etiqueta}."""
        source = {101: "Ingeniería", 102: "Medicina"}
        options = _resolve_relation_options(source)
        self.assertEqual(options, [(101, "Ingeniería"), (102, "Medicina")])

    def test_resolve_relation_options_with_model_objects(self):
        """Verifica la detección automática de IDs y nombres legibles en modelos de dominio."""
        faculties = [
            Faculty(faculty_id=1, name="Ingeniería", active=True),
            Faculty(faculty_id=2, name="Ciencias", active=True),
        ]
        options = _resolve_relation_options(faculties)
        self.assertEqual(options, [(1, "Ingeniería (#1)"), (2, "Ciencias (#2)")])

    def test_resolve_relation_options_with_linked_list(self):
        """Verifica la resolución de opciones contenidas en una LinkedList personalizada."""
        ll = LinkedList()
        ll.insert(Faculty(faculty_id=10, name="Artes", active=True))
        ll.insert(Faculty(faculty_id=20, name="Derecho", active=True))

        options = _resolve_relation_options(ll)
        self.assertEqual(options, [(10, "Artes (#10)"), (20, "Derecho (#20)")])

    def test_resolve_relation_options_with_callable(self):
        """Verifica la resolución mediante callable o lambda."""
        fn = lambda: [(5, "Programa Cinco"), (6, "Programa Seis")]
        options = _resolve_relation_options(fn)
        self.assertEqual(options, [(5, "Programa Cinco"), (6, "Programa Seis")])

    def test_resolve_relation_options_empty_or_none(self):
        """Verifica que fuentes vacías o None retornen una lista vacía."""
        self.assertEqual(_resolve_relation_options([]), [])
        self.assertEqual(_resolve_relation_options(None), [])
        self.assertEqual(_resolve_relation_options(lambda: None), [])

    def test_relation_field_renders_combobox_with_items_and_data(self):
        """Verifica que un campo 'relation' renderiza un QComboBox con etiquetas e IDs internos."""
        fields = (
            ("program_id", "ID Programa", "int"),
            ("name", "Nombre", "text"),
            (
                "faculty_id",
                "Facultad",
                "relation",
                [(1, "Facultad de Ingeniería (#1)"), (2, "Facultad de Medicina (#2)")],
            ),
        )
        dialog = EntityDialog("Nuevo Programa", fields)
        combo = dialog._widgets.get("faculty_id")

        self.assertIsInstance(combo, QComboBox)
        self.assertEqual(combo.count(), 2)
        self.assertEqual(combo.itemText(0), "Facultad de Ingeniería (#1)")
        self.assertEqual(combo.itemData(0), 1)
        self.assertEqual(combo.itemText(1), "Facultad de Medicina (#2)")
        self.assertEqual(combo.itemData(1), 2)

        # Por defecto selecciona el primer elemento
        values = dialog.values()
        self.assertEqual(values["faculty_id"], 1)

        # Al cambiar el índice seleccionado
        combo.setCurrentIndex(1)
        values = dialog.values()
        self.assertEqual(values["faculty_id"], 2)

    def test_empty_relation_options_handling(self):
        """Verifica el comportamiento cuando no hay opciones disponibles para una relación."""
        fields = (
            ("program_id", "ID Programa", "int"),
            ("name", "Nombre", "text"),
            ("faculty_id", "Facultad", "relation", lambda: []),
        )
        dialog = EntityDialog("Nuevo Programa", fields)
        combo = dialog._widgets.get("faculty_id")

        self.assertIsInstance(combo, QComboBox)
        self.assertEqual(combo.count(), 1)
        self.assertEqual(combo.itemText(0), "Sin opciones disponibles")
        self.assertIsNone(combo.itemData(0))
        self.assertFalse(combo.isEnabled())

        # El botón Guardar debe estar deshabilitado
        button_box = dialog.findChild(QDialogButtonBox)
        save_btn = button_box.button(QDialogButtonBox.StandardButton.Save)
        self.assertFalse(save_btn.isEnabled())

        # Si se invoca accept(), se debe bloquear y mostrar advertencia
        with patch.object(QMessageBox, "warning") as mock_warning:
            dialog.accept()
            mock_warning.assert_called_once()
            self.assertEqual(dialog.result(), 0)  # No fue aceptado

    def test_edit_mode_preselection_and_editable_relation(self):
        """Verifica que en edición se preselecciona la relación, se mantiene editable y la PK se deshabilita."""
        existing_program = Program(
            program_id=101,
            name="Ingeniería de Sistemas",
            faculty_id=2,
            active=True,
        )

        options = [
            (1, "Facultad de Ciencias (#1)"),
            (2, "Facultad de Ingeniería (#2)"),
            (3, "Facultad de Medicina (#3)"),
        ]
        fields = (
            ("program_id", "ID Programa", "int"),
            ("name", "Nombre", "text"),
            ("faculty_id", "Facultad", "relation", options),
        )

        dialog = EntityDialog(
            "Editar Programa",
            fields,
            entity=existing_program,
            primary_key="program_id",
        )

        # La clave primaria debe estar deshabilitada
        pk_widget = dialog._widgets.get("program_id")
        self.assertFalse(pk_widget.isEnabled())

        # El campo de relación debe estar habilitado
        combo = dialog._widgets.get("faculty_id")
        self.assertTrue(combo.isEnabled())

        # Debe estar preseleccionada la opción con ID 2
        self.assertEqual(combo.currentIndex(), 1)
        self.assertEqual(combo.currentData(), 2)

        # Permite cambiar la selección a otra facultad
        combo.setCurrentIndex(2)
        values = dialog.values()
        self.assertEqual(values["program_id"], 101)
        self.assertEqual(values["faculty_id"], 3)

    def test_edit_mode_fallback_for_inactive_or_missing_relation(self):
        """Verifica que si la entidad tiene un ID que no está en las opciones activas, se agrega como Actual."""
        existing_program = Program(
            program_id=102,
            name="Programa Histórico",
            faculty_id=99,  # Facultad inactiva o no listada
            active=True,
        )
        options = [
            (1, "Facultad A (#1)"),
            (2, "Facultad B (#2)"),
        ]
        fields = (
            ("program_id", "ID Programa", "int"),
            ("faculty_id", "Facultad", "relation", options),
        )

        dialog = EntityDialog(
            "Editar Programa",
            fields,
            entity=existing_program,
            primary_key="program_id",
        )
        combo = dialog._widgets.get("faculty_id")

        self.assertEqual(combo.itemData(0), 99)
        self.assertIn("ID 99 (Actual)", combo.itemText(0))
        self.assertEqual(combo.currentIndex(), 0)
        self.assertEqual(dialog.values()["faculty_id"], 99)

    def test_main_window_crud_pages_relation_configurations(self):
        """Verifica que MainWindow configure campos de tipo 'relation' para todas las llaves foráneas requeridas."""
        manager = EntityManager()
        # Sembrar datos activos e inactivos
        f_active = Faculty(faculty_id=1, name="Ingeniería", active=True)
        f_inactive = Faculty(faculty_id=2, name="Antigua Facultad", active=False)
        manager.create_faculty(f_active)
        manager.create_faculty(f_inactive)

        p_active = Program(program_id=10, name="Sistemas", faculty_id=1, active=True)
        p_inactive = Program(program_id=20, name="Inactivo", faculty_id=1, active=False)
        manager.create_program(p_active)
        manager.create_program(p_inactive)

        prof_active = Professor(professor_id=100, full_name="Carlos Docente", faculty_id=1, active=True)
        prof_inactive = Professor(professor_id=200, full_name="Juan Retirado", faculty_id=1, active=False)
        manager.create_professor(prof_active)
        manager.create_professor(prof_inactive)

        stud_active = Student(student_id=1000, full_name="Ana Estudiante", program_id=10, active=True)
        stud_inactive = Student(student_id=2000, full_name="Pedro Inactivo", program_id=10, active=False)
        manager.create_student(stud_active)
        manager.create_student(stud_inactive)

        course_active = Course(course_id=500, name="Programación I", program_id=10, assigned_professor_id=100, max_capacity=30, active=True)
        course_inactive = Course(course_id=600, name="Curso Inactivo", program_id=10, assigned_professor_id=100, max_capacity=30, active=False)
        manager.create_course(course_active)
        manager.create_course(course_inactive)

        window = MainWindow(manager=manager)

        # 1. Programas -> faculty_id
        programs_page = window._pages["Programas"]
        prog_fields_dict = {f[0]: f for f in programs_page.fields}
        self.assertIn("faculty_id", prog_fields_dict)
        self.assertEqual(prog_fields_dict["faculty_id"][2], "relation")
        fac_options = _resolve_relation_options(prog_fields_dict["faculty_id"][3])
        self.assertEqual(len(fac_options), 1)
        self.assertEqual(fac_options[0][0], 1)

        # 2. Cursos -> program_id, assigned_professor_id
        courses_page = window._pages["Cursos"]
        courses_fields_dict = {f[0]: f for f in courses_page.fields}
        self.assertIn("program_id", courses_fields_dict)
        self.assertEqual(courses_fields_dict["program_id"][2], "relation")
        prog_options = _resolve_relation_options(courses_fields_dict["program_id"][3])
        self.assertEqual(len(prog_options), 1)
        self.assertEqual(prog_options[0][0], 10)

        self.assertIn("assigned_professor_id", courses_fields_dict)
        self.assertEqual(courses_fields_dict["assigned_professor_id"][2], "relation")
        prof_options = _resolve_relation_options(courses_fields_dict["assigned_professor_id"][3])
        self.assertEqual(len(prof_options), 1)
        self.assertEqual(prof_options[0][0], 100)

        # 3. Estudiantes -> program_id
        students_page = window._pages["Estudiantes"]
        students_fields_dict = {f[0]: f for f in students_page.fields}
        self.assertIn("program_id", students_fields_dict)
        self.assertEqual(students_fields_dict["program_id"][2], "relation")
        stud_prog_options = _resolve_relation_options(students_fields_dict["program_id"][3])
        self.assertEqual(len(stud_prog_options), 1)
        self.assertEqual(stud_prog_options[0][0], 10)

        # 4. Profesores -> faculty_id
        profs_page = window._pages["Profesores"]
        profs_fields_dict = {f[0]: f for f in profs_page.fields}
        self.assertIn("faculty_id", profs_fields_dict)
        self.assertEqual(profs_fields_dict["faculty_id"][2], "relation")
        prof_fac_options = _resolve_relation_options(profs_fields_dict["faculty_id"][3])
        self.assertEqual(len(prof_fac_options), 1)
        self.assertEqual(prof_fac_options[0][0], 1)

        # 5. Inscripciones -> student_id, course_id
        enrollments_page = window._pages["Inscripciones"]
        enrollments_fields_dict = {f[0]: f for f in enrollments_page.fields}
        self.assertIn("student_id", enrollments_fields_dict)
        self.assertEqual(enrollments_fields_dict["student_id"][2], "relation")
        enr_stud_options = _resolve_relation_options(enrollments_fields_dict["student_id"][3])
        self.assertEqual(len(enr_stud_options), 1)
        self.assertEqual(enr_stud_options[0][0], 1000)

        self.assertIn("course_id", enrollments_fields_dict)
        self.assertEqual(enrollments_fields_dict["course_id"][2], "relation")
        enr_course_options = _resolve_relation_options(enrollments_fields_dict["course_id"][3])
        self.assertEqual(len(enr_course_options), 1)
        self.assertEqual(enr_course_options[0][0], 500)


if __name__ == "__main__":
    unittest.main()

