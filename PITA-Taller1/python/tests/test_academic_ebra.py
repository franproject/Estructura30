"""Unit tests for student average calculation and EBRA academic risk evaluation.

Verifies:
1. calculate_student_average resolves scalar integer IDs in student.enrollment_list against self.enrollments.
2. calculate_student_average works seamlessly with resolved Enrollment instances.
3. Real dataset evaluation: Juan Perez (10001) has an average > 0.0 (~2.04) and is classified as EBRA.
4. Non-EBRA student (e.g. 10021, Luis Perez) has average > 3.0 and is classified as OK.
5. Overall EBRA count matches ground truth (12 out of 120 students).
6. Students with no enrollments or records return status NO_DATA.
"""

import unittest

from models.course import Course
from models.enrollment import Enrollment
from models.linked_list import LinkedList
from models.student import Student
from services.entity_manager import EntityManager


class AcademicEbraTests(unittest.TestCase):
    def setUp(self):
        self.manager = EntityManager()

    def test_calculate_average_with_scalar_ids(self):
        """Verifies calculate_student_average resolves integer IDs against self.enrollments."""
        c1 = Course(course_id=1, name="Matematicas", program_id=10, credits=3, curriculum_semester=1, active=True)
        c2 = Course(course_id=2, name="Fisica", program_id=10, credits=4, curriculum_semester=1, active=True)
        self.manager.courses.insert(c1)
        self.manager.courses.insert(c2)

        e1 = Enrollment(enrollment_id=101, student_id=1, course_id=1, academic_period="2026-1", final_grade=4.0, status="Aprobado", enrollment_date="2026-01-01")
        e2 = Enrollment(enrollment_id=102, student_id=1, course_id=2, academic_period="2026-1", final_grade=2.5, status="Reprobado", enrollment_date="2026-01-01")
        self.manager.enrollments.insert(e1)
        self.manager.enrollments.insert(e2)

        student = Student(
            student_id=1,
            full_name="Carlos Prueba",
            document_type="CC",
            document_number="123",
            birth_date="2000-01-01",
            email="c@test.com",
            phone="123",
            program_id=10,
            current_semester=1,
            status="Activo",
            active=True,
            enrollment_list=LinkedList([101, 102]),  # Scalar IDs
        )
        self.manager.students.insert(student)

        # Expected: (4.0 * 3 + 2.5 * 4) / (3 + 4) = (12.0 + 10.0) / 7 = 22.0 / 7 = 3.142857
        expected_avg = 22.0 / 7.0
        avg = self.manager.calculate_student_average(1)
        self.assertAlmostEqual(avg, expected_avg, places=5)

        ebra = self.manager.evaluate_ebra_status(1)
        self.assertEqual(ebra["status"], "OK")
        self.assertAlmostEqual(ebra["average"], expected_avg, places=5)

    def test_calculate_average_with_domain_objects(self):
        """Verifies calculate_student_average works directly with Enrollment instances."""
        c1 = Course(course_id=1, name="Quimica", program_id=10, credits=2, curriculum_semester=1, active=True)
        self.manager.courses.insert(c1)

        e1 = Enrollment(enrollment_id=201, student_id=2, course_id=1, academic_period="2026-1", final_grade=2.0, status="Reprobado", enrollment_date="2026-01-01")
        self.manager.enrollments.insert(e1)

        student = Student(
            student_id=2,
            full_name="Laura Riesgo",
            document_type="CC",
            document_number="456",
            birth_date="2000-01-01",
            email="l@test.com",
            phone="456",
            program_id=10,
            current_semester=1,
            status="EBRA",
            active=True,
            enrollment_list=LinkedList([e1]),  # Domain object
        )
        self.manager.students.insert(student)

        avg = self.manager.calculate_student_average(2)
        self.assertEqual(avg, 2.0)

        ebra = self.manager.evaluate_ebra_status(2)
        self.assertEqual(ebra["status"], "EBRA")
        self.assertEqual(ebra["average"], 2.0)

    def test_no_data_student_status(self):
        """Verifies student without enrollments is classified as NO_DATA."""
        student = Student(
            student_id=999,
            full_name="Nuevo Ingreso",
            document_type="CC",
            document_number="999",
            birth_date="2000-01-01",
            email="n@test.com",
            phone="999",
            program_id=10,
            current_semester=1,
            status="Activo",
            cumulative_average=0.0,
            active=True,
            enrollment_list=LinkedList(),
        )
        self.manager.students.insert(student)

        self.assertEqual(self.manager.calculate_student_average(999), 0.0)
        ebra = self.manager.evaluate_ebra_status(999)
        self.assertEqual(ebra["status"], "NO_DATA")

    def test_real_data_juan_perez_and_overall_distribution(self):
        """Verifies calculation on actual system disk dataset:

        1. Juan Perez (10001) returns average ~2.04 (> 0.0) and EBRA status.
        2. Luis Perez (10021) returns average ~3.89 and OK status.
        3. Total EBRA count equals 12 across all 120 registered students.
        """
        em = EntityManager()
        self.assertTrue(em.load_from_directory())

        # 1. Juan Perez
        juan = em.get_student(10001)
        self.assertIsNotNone(juan)
        juan_avg = em.calculate_student_average(10001)
        self.assertGreater(juan_avg, 0.0)
        self.assertAlmostEqual(juan_avg, 2.04375, places=4)

        juan_ebra = em.evaluate_ebra_status(10001)
        self.assertEqual(juan_ebra["status"], "EBRA")
        self.assertAlmostEqual(juan_ebra["average"], 2.04375, places=4)

        # 2. Luis Perez (Passing student)
        luis = em.get_student(10021)
        self.assertIsNotNone(luis)
        luis_avg = em.calculate_student_average(10021)
        self.assertGreater(luis_avg, 3.0)
        self.assertAlmostEqual(luis_avg, 3.89375, places=4)

        luis_ebra = em.evaluate_ebra_status(10021)
        self.assertEqual(luis_ebra["status"], "OK")

        # 3. Overall count
        ebra_count = em.count_ebra_students()
        self.assertEqual(ebra_count, 12)

