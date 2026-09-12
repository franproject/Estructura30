"""Pruebas unitarias para la validación de eliminación de profesores y administrativos.

Verifica:
1. delete_professor():
   - Bloquea la eliminación (retorna False) si el profesor tiene asignaturas activas a su cargo.
   - Preserva al profesor en la colección y no altera los cursos.
   - Permite la eliminación (retorna True) si el profesor solo tiene asignaturas inactivas/históricas.
   - Limpia las referencias en cursos inactivos estableciendo assigned_professor_id = 0.
   - Permite la eliminación (retorna True) si el profesor no tiene cursos asignados.
   - Retorna False si el profesor no existe.
2. get_courses_by_professor():
   - Retorna adecuadamente cursos activos y/o inactivos según el parámetro active_only.
3. delete_administrative():
   - Permite la eliminación limpia de administrativos existentes.
   - Retorna False si no existe el administrativo.
4. CrudPage (GUI):
   - Al intentar eliminar un profesor con cursos activos, muestra un QMessageBox con
     la lista detallada de cursos asignados y las instrucciones para reasignarlos.
   - Al eliminar un profesor sin cursos activos, procede normalmente.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QMessageBox

from models.administrative import Administrative
from models.course import Course
from models.faculty import Faculty
from models.professor import Professor
from models.program import Program
from services.entity_manager import EntityManager
from gui.pages.crud_page import CrudPage
from gui.components.confirm_dialog import ConfirmDialog


class TestProfessorDeletionGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.mgr = EntityManager()

        # Configurar facultad y programa
        self.faculty = Faculty(
            faculty_id=1,
            name="Facultad de Ingeniería",
            dean="Dr. Decano",
            creation_date="2020-01-01",
            active=True,
        )
        self.mgr.create_faculty(self.faculty)

        self.program = Program(
            program_id=10,
            name="Ingeniería de Sistemas",
            faculty_id=1,
            program_director="Ing. Director",
            level="Pregrado",
            modality="Presencial",
            active=True,
        )
        self.mgr.create_program(self.program)

        # Crear profesor de prueba
        self.prof = Professor(
            professor_id=100,
            full_name="Dr. Alan Turing",
            document_type="CC",
            document_number="123456",
            email="alan@test.edu",
            phone="5551234",
            faculty_id=1,
            employment_type="Planta",
            category_rank="Titular",
            academic_title="Doctorado",
            active=True,
        )
        self.mgr.create_professor(self.prof)

    # -------------------------------------------------------------------------
    # 1. ENTITY MANAGER - PRUEBAS DE SERVICIO
    # -------------------------------------------------------------------------

    def test_delete_professor_blocked_when_active_course_assigned(self):
        """No debe permitir eliminar un profesor si tiene al menos un curso activo asignado."""
        course = Course(
            course_id=501,
            name="Estructuras de Datos",
            program_id=10,
            credits=4,
            curriculum_semester=3,
            assigned_professor_id=100,
            max_capacity=30,
            active=True,
        )
        self.mgr.create_course(course)

        # Intento de eliminación debe fallar
        result = self.mgr.delete_professor(100)
        self.assertFalse(result)

        # El profesor debe continuar existiendo
        self.assertIsNotNone(self.mgr.get_professor(100))
        # El curso conserva la asignación
        self.assertEqual(self.mgr.get_course(501).assigned_professor_id, 100)

    def test_delete_professor_blocked_when_mixed_courses_assigned(self):
        """Si tiene cursos tanto activos como inactivos, la eliminación sigue bloqueada."""
        active_course = Course(
            course_id=502,
            name="Algoritmos Avanzados",
            program_id=10,
            credits=3,
            curriculum_semester=4,
            assigned_professor_id=100,
            max_capacity=25,
            active=True,
        )
        inactive_course = Course(
            course_id=503,
            name="Programación I",
            program_id=10,
            credits=3,
            curriculum_semester=1,
            assigned_professor_id=100,
            max_capacity=25,
            active=False,
        )
        self.mgr.create_course(active_course)
        self.mgr.create_course(inactive_course)

        result = self.mgr.delete_professor(100)
        self.assertFalse(result)
        self.assertIsNotNone(self.mgr.get_professor(100))
        self.assertEqual(self.mgr.get_course(502).assigned_professor_id, 100)
        self.assertEqual(self.mgr.get_course(503).assigned_professor_id, 100)

    def test_delete_professor_allowed_when_only_inactive_courses_assigned(self):
        """Si el profesor solo tiene cursos inactivos/históricos, permite eliminar y limpia las referencias a 0."""
        inactive_course1 = Course(
            course_id=504,
            name="Sistemas Operativos Antiguo",
            program_id=10,
            credits=3,
            curriculum_semester=5,
            assigned_professor_id=100,
            max_capacity=20,
            active=False,
        )
        inactive_course2 = Course(
            course_id=505,
            name="Compiladores Histórico",
            program_id=10,
            credits=4,
            curriculum_semester=6,
            assigned_professor_id=100,
            max_capacity=20,
            active=False,
        )
        self.mgr.create_course(inactive_course1)
        self.mgr.create_course(inactive_course2)

        # Debe permitir eliminar
        result = self.mgr.delete_professor(100)
        self.assertTrue(result)

        # El profesor ya no debe existir
        self.assertIsNone(self.mgr.get_professor(100))

        # Los cursos históricos ahora deben tener assigned_professor_id = 0
        self.assertEqual(self.mgr.get_course(504).assigned_professor_id, 0)
        self.assertEqual(self.mgr.get_course(505).assigned_professor_id, 0)

    def test_delete_professor_allowed_when_no_courses_assigned(self):
        """Si el profesor no tiene cursos asignados, se elimina limpiamente."""
        result = self.mgr.delete_professor(100)
        self.assertTrue(result)
        self.assertIsNone(self.mgr.get_professor(100))

    def test_delete_professor_nonexistent_returns_false(self):
        """Eliminar un ID inexistente retorna False."""
        self.assertFalse(self.mgr.delete_professor(9999))

    def test_get_courses_by_professor(self):
        """Verifica el filtrado de get_courses_by_professor con active_only."""
        c_active = Course(
            course_id=601,
            name="Curso Activo",
            program_id=10,
            credits=3,
            curriculum_semester=1,
            assigned_professor_id=100,
            active=True,
        )
        c_inactive = Course(
            course_id=602,
            name="Curso Inactivo",
            program_id=10,
            credits=2,
            curriculum_semester=2,
            assigned_professor_id=100,
            active=False,
        )
        c_other = Course(
            course_id=603,
            name="Curso Otro Prof",
            program_id=10,
            credits=4,
            curriculum_semester=3,
            assigned_professor_id=200,
            active=True,
        )
        self.mgr.create_course(c_active)
        self.mgr.create_course(c_inactive)
        self.mgr.create_course(c_other)

        all_prof_courses = self.mgr.get_courses_by_professor(100, active_only=False)
        self.assertEqual(len(all_prof_courses), 2)
        self.assertEqual({c.course_id for c in all_prof_courses}, {601, 602})

        active_prof_courses = self.mgr.get_courses_by_professor(100, active_only=True)
        self.assertEqual(len(active_prof_courses), 1)
        self.assertEqual(active_prof_courses[0].course_id, 601)

    # -------------------------------------------------------------------------
    # 2. ADMINISTRATIVE DELETION
    # -------------------------------------------------------------------------

    def test_delete_administrative_success_and_nonexistent(self):
        """Verifica la eliminación de empleados administrativos."""
        admin = Administrative(
            administrative_id=300,
            full_name="Clara Rodriguez",
            document_type="CC",
            document_number="888999",
            email="clara@test.edu",
            position="Secretaria Académica",
            category="Auxiliar",
            employment_type="Planta",
            base_salary=2500000.0,
            active=True,
        )
        self.mgr.create_administrative(admin)
        self.assertIsNotNone(self.mgr.get_administrative(300))

        # Eliminación limpia
        self.assertTrue(self.mgr.delete_administrative(300))
        self.assertIsNone(self.mgr.get_administrative(300))

        # ID inexistente
        self.assertFalse(self.mgr.delete_administrative(9999))

    # -------------------------------------------------------------------------
    # 3. GUI / CRUDPAGE INTEGRATION
    # -------------------------------------------------------------------------

    def test_crud_page_delete_professor_with_active_courses_shows_detailed_dialog(self):
        """En CrudPage, si se intenta eliminar un profesor con asignaturas activas,
        debe mostrarse un QMessageBox.warning con el detalle de las asignaturas a reasignar."""
        course = Course(
            course_id=701,
            name="Arquitectura de Computadores",
            program_id=10,
            credits=4,
            curriculum_semester=4,
            assigned_professor_id=100,
            active=True,
        )
        self.mgr.create_course(course)

        page = CrudPage(
            title="Profesores",
            subtitle="Gestión de profesores",
            manager=self.mgr,
            collection_name="professors",
            model_cls=Professor,
            id_field="professor_id",
            fields=(
                ("professor_id", "ID", "int"),
                ("full_name", "Nombre", "text"),
            ),
            columns=("ID", "Nombre", "Email", "Categoría"),
            row_builder=lambda p: (p.professor_id, p.full_name, p.email, p.category_rank),
            operation_name="professor",
        )
        page.refresh()

        # Seleccionar la fila del profesor en la tabla
        page.table.selectRow(0)
        selected = page._selected_item()
        self.assertIsNotNone(selected)
        self.assertEqual(selected.professor_id, 100)

        # Simular ConfirmDialog aceptado y capturar QMessageBox.warning
        with patch.object(ConfirmDialog, "exec", return_value=ConfirmDialog.DialogCode.Accepted), \
             patch.object(QMessageBox, "warning") as mock_warning:
            page.delete_item()

            mock_warning.assert_called_once()
            args, _ = mock_warning.call_args
            # args: (parent, title, message)
            title = args[1]
            message = args[2]

            # Verificar que el mensaje contiene los datos institucionales
            self.assertIn("Cursos activos", title)
            self.assertIn("Alan Turing", message)
            self.assertIn("100", message)
            self.assertIn("Arquitectura de Computadores", message)
            self.assertIn("701", message)
            self.assertIn("Semestre 4", message)
            self.assertIn("4 créditos", message)
            self.assertIn("reasigna estos cursos", message)

        # El profesor debe continuar existiendo
        self.assertIsNotNone(self.mgr.get_professor(100))

    def test_crud_page_delete_professor_without_active_courses_succeeds(self):
        """En CrudPage, si el profesor no tiene cursos activos, la eliminación es exitosa."""
        page = CrudPage(
            title="Profesores",
            subtitle="Gestión de profesores",
            manager=self.mgr,
            collection_name="professors",
            model_cls=Professor,
            id_field="professor_id",
            fields=(
                ("professor_id", "ID", "int"),
                ("full_name", "Nombre", "text"),
            ),
            columns=("ID", "Nombre", "Email", "Categoría"),
            row_builder=lambda p: (p.professor_id, p.full_name, p.email, p.category_rank),
            operation_name="professor",
        )
        page.refresh()
        page.table.selectRow(0)

        with patch.object(ConfirmDialog, "exec", return_value=ConfirmDialog.DialogCode.Accepted), \
             patch.object(QMessageBox, "information") as mock_info:
            page.delete_item()

            mock_info.assert_called()
            # Profesor ya no debe existir
            self.assertIsNone(self.mgr.get_professor(100))


if __name__ == "__main__":
    unittest.main()
