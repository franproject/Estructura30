"""Pruebas unitarias para la página de Reportes Institucionales (ReportsPage)."""

import csv
import os
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QTabWidget

from gui.pages.reports_page import ReportsPage
from models.administrative import Administrative
from models.course import Course
from models.enrollment import Enrollment
from models.professor import Professor
from models.program import Program
from models.student import Student
from services.entity_manager import EntityManager


class TestReportsPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.manager = EntityManager()
        self.page = ReportsPage(self.manager)

    def tearDown(self):
        self.page.close()

    def test_reports_tabs_exist(self):
        """Verifica que el QTabWidget contenga las 4 pestañas institucionales."""
        self.assertIsInstance(self.page.tabs, QTabWidget)
        self.assertEqual(self.page.tabs.count(), 4)
        tab_names = [self.page.tabs.tabText(i) for i in range(4)]
        self.assertTrue(any("EBRA" in t for t in tab_names))
        self.assertTrue(any("Carga Docente" in t for t in tab_names))
        self.assertTrue(any("Consolidado Salarial" in t for t in tab_names))
        self.assertTrue(any("Indicadores Globales" in t for t in tab_names))

    def test_ebra_report_detects_students_and_filters(self):
        """Verifica que el reporte EBRA liste a los estudiantes en riesgo (< 3.0) y soporte filtrado."""
        prog = Program(program_id=10, name="Ingeniería Biomédica", active=True)
        self.manager.programs.insert(prog)

        course = Course(course_id=101, name="Biomateriales", credits=3, active=True)
        self.manager.courses.insert(course)

        # Estudiante 1: en EBRA (nota 2.2)
        s1 = Student(
            student_id=5001,
            full_name="Carlos Mario Restrepo",
            program_id=10,
            current_semester=4,
            active=True,
        )
        enr1 = Enrollment(enrollment_id=1, student_id=5001, course_id=101, final_grade=2.2, status="FINALIZADO")
        s1.enrollment_list.insert(1)
        self.manager.students.insert(s1)
        self.manager.enrollments.insert(enr1)

        # Estudiante 2: Buen rendimiento (nota 4.5)
        s2 = Student(
            student_id=5002,
            full_name="Mariana Ospina Duque",
            program_id=10,
            current_semester=4,
            active=True,
        )
        enr2 = Enrollment(enrollment_id=2, student_id=5002, course_id=101, final_grade=4.5, status="FINALIZADO")
        s2.enrollment_list.insert(2)
        self.manager.students.insert(s2)
        self.manager.enrollments.insert(enr2)

        self.page.refresh()

        # Solo s1 debe aparecer en EBRA
        self.assertEqual(len(self.page._ebra_all), 1)
        self.assertEqual(self.page._ebra_all[0][0], 5001)
        self.assertEqual(self.page._ebra_all[0][1], "Carlos Mario Restrepo")
        self.assertEqual(self.page._ebra_all[0][2], "Ingeniería Biomédica")
        self.assertEqual(self.page._ebra_all[0][4], "2.20")

        # Filtrar por texto coincidente
        self.page._filter_ebra("Restrepo")
        self.assertEqual(len(self.page._ebra_filtered), 1)

        # Filtrar por texto no coincidente
        self.page._filter_ebra("Duque")
        self.assertEqual(len(self.page._ebra_filtered), 0)

    def test_faculty_workload_calculation(self):
        """Verifica el cálculo de asignaturas asignadas y total de créditos lectivos por docente."""
        prof1 = Professor(
            professor_id=101,
            full_name="Profesor Juan Valdez",
            category_rank="Titular",
            dedication="Tiempo completo",
            active=True,
        )
        prof2 = Professor(
            professor_id=102,
            full_name="Profesora Lucia Gomez",
            category_rank="Asistente",
            dedication="Cátedra",
            active=True,
        )
        self.manager.professors.insert(prof1)
        self.manager.professors.insert(prof2)

        # Cursos asignados a prof1: 2 activos (3 + 4 créditos) y 1 inactivo (2 créditos)
        c1 = Course(course_id=1, name="Cálculo I", credits=3, assigned_professor_id=101, active=True)
        c2 = Course(course_id=2, name="Cálculo II", credits=4, assigned_professor_id=101, active=True)
        c3 = Course(course_id=3, name="Cálculo Inactivo", credits=2, assigned_professor_id=101, active=False)

        # Curso asignado a prof2: 1 activo (3 créditos)
        c4 = Course(course_id=4, name="Física", credits=3, assigned_professor_id=102, active=True)

        self.manager.courses.insert(c1)
        self.manager.courses.insert(c2)
        self.manager.courses.insert(c3)
        self.manager.courses.insert(c4)

        self.page.refresh()

        workload_map = {row[0]: row for row in self.page._workload_all}

        # Prof 1: debe tener 2 cursos activos y 7 créditos (el inactivo no cuenta)
        self.assertIn(101, workload_map)
        self.assertEqual(workload_map[101][3], 2)  # Cursos
        self.assertEqual(workload_map[101][4], 7)  # Créditos

        # Prof 2: 1 curso y 3 créditos
        self.assertIn(102, workload_map)
        self.assertEqual(workload_map[102][3], 1)
        self.assertEqual(workload_map[102][4], 3)

    def test_salary_consolidation_by_category(self):
        """Verifica la agregación salarial por categoría de docentes y administrativos."""
        # 2 docentes Titulares de 5M cada uno
        p1 = Professor(professor_id=1, full_name="P1", category_rank="Titular", base_monthly_salary=5000000.0, active=True)
        p2 = Professor(professor_id=2, full_name="P2", category_rank="Titular", base_monthly_salary=5000000.0, active=True)
        # 1 docente Auxiliar de 3M
        p3 = Professor(professor_id=3, full_name="P3", category_rank="Auxiliar", base_monthly_salary=3000000.0, active=True)

        # 2 administrativos Profesionales de 4M cada uno
        a1 = Administrative(administrative_id=1, full_name="A1", category="Profesional", base_salary=4000000.0, active=True)
        a2 = Administrative(administrative_id=2, full_name="A2", category="Profesional", base_salary=4000000.0, active=True)

        self.manager.professors.insert(p1)
        self.manager.professors.insert(p2)
        self.manager.professors.insert(p3)
        self.manager.administrative_staff.insert(a1)
        self.manager.administrative_staff.insert(a2)

        self.page.refresh()

        salary_map = {row[0]: row for row in self.page._salary_all}

        # Docente - Titular: 2 empleados, promedio 5M, total 10M
        self.assertIn("Docente - Titular", salary_map)
        self.assertEqual(salary_map["Docente - Titular"][2], 2)
        self.assertIn("5,000,000.00", salary_map["Docente - Titular"][3])
        self.assertIn("10,000,000.00", salary_map["Docente - Titular"][4])

        # Administrativo - Profesional: 2 empleados, total 8M
        self.assertIn("Administrativo - Profesional", salary_map)
        self.assertEqual(salary_map["Administrativo - Profesional"][2], 2)
        self.assertIn("8,000,000.00", salary_map["Administrativo - Profesional"][4])

        # Total nómina visible en el badge: 10M + 3M + 8M = 21M
        self.assertIn("21,000,000.00", self.page.lbl_salary_summary.text())

    def test_corrected_active_courses_count(self):
        """Verifica que el conteo de cursos activos en el reporte filtre explícitamente por course.active == True."""
        # 3 cursos activos y 2 inactivos
        self.manager.courses.insert(Course(course_id=1, name="C1", active=True))
        self.manager.courses.insert(Course(course_id=2, name="C2", active=True))
        self.manager.courses.insert(Course(course_id=3, name="C3", active=True))
        self.manager.courses.insert(Course(course_id=4, name="C4", active=False))
        self.manager.courses.insert(Course(course_id=5, name="C5", active=False))

        self.page.refresh()

        metrics_map = {row[1]: row for row in self.page._metrics_all}
        self.assertIn("Cursos Activos en Oferta", metrics_map)
        active_metric = metrics_map["Cursos Activos en Oferta"]

        # Debe decir "3 asignaturas", NO 5
        self.assertEqual(active_metric[2], "3 asignaturas")
        self.assertIn("3 de 5", active_metric[3])

    def test_export_to_csv_file_generation(self):
        """Verifica que la función de exportación a CSV escriba encabezados y registros correctamente."""
        headers = ["ID", "Nombre", "Programa"]
        rows = [
            (101, "Estudiante Prueba 1", "Medicina"),
            (102, "Estudiante Prueba 2", "Derecho"),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_file = os.path.join(tmp_dir, "test_export.csv")

            # Simular selección de archivo en QFileDialog
            with patch("PySide6.QtWidgets.QFileDialog.getSaveFileName", return_value=(tmp_file, "Archivos CSV (*.csv)")):
                with patch("PySide6.QtWidgets.QMessageBox.information"):
                    self.page._export_to_csv("test.csv", headers, rows)

            self.assertTrue(os.path.exists(tmp_file))

            with open(tmp_file, "r", encoding="utf-8-sig") as f:
                reader = list(csv.reader(f))
                self.assertEqual(reader[0], headers)
                self.assertEqual(reader[1], ["101", "Estudiante Prueba 1", "Medicina"])
                self.assertEqual(reader[2], ["102", "Estudiante Prueba 2", "Derecho"])


if __name__ == "__main__":
    unittest.main()

