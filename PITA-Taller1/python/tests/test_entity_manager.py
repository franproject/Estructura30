import unittest

from models.administrative import Administrative
from models.course import Course
from models.enrollment import Enrollment
from models.faculty import Faculty
from models.professor import Professor
from models.program import Program
from models.student import Student
from services.entity_manager import EntityManager


class EntityManagerTests(unittest.TestCase):
    def setUp(self):
        self.manager = EntityManager()

    def test_faculty_crud_and_state_toggles(self):
        faculty = Faculty(faculty_id=1, name="Ingenieria", dean="Dr. Gomez", creation_date="2020-01-01", active=True)
        self.assertTrue(self.manager.create_faculty(faculty))
        self.assertIsNotNone(self.manager.get_faculty(1))
        self.assertEqual(self.manager.list_faculties().count_elements(), 1)
        self.assertTrue(self.manager.update_faculty(1, name="Ingeniería"))
        self.assertEqual(self.manager.get_faculty(1).name, "Ingeniería")
        self.assertTrue(self.manager.deactivate_faculty(1))
        self.assertFalse(self.manager.get_faculty(1).active)
        self.assertTrue(self.manager.reactivate_faculty(1))
        self.assertTrue(self.manager.delete_faculty(1))
        self.assertIsNone(self.manager.get_faculty(1))

    def test_program_validation_and_relationships(self):
        faculty = Faculty(faculty_id=7, name="Ciencias", dean="Dr. Perez", creation_date="2021-01-01", active=True)
        self.manager.create_faculty(faculty)

        invalid_program = Program(program_id=11, name="Sistemas", faculty_id=99, program_director="Dr. Diaz", level="Pregrado", modality="Presencial", active=True)
        self.assertFalse(self.manager.create_program(invalid_program))

        valid_program = Program(program_id=11, name="Sistemas", faculty_id=7, program_director="Dr. Diaz", level="Pregrado", modality="Presencial", active=True)
        self.assertTrue(self.manager.create_program(valid_program))
        self.assertEqual(self.manager.list_programs().count_elements(), 1)
        self.assertFalse(self.manager.create_program(valid_program))

        self.assertTrue(self.manager.deactivate_program(11))
        course = Course(course_id=13, name="Estructuras", program_id=11, credits=4, curriculum_semester=2, assigned_professor_id=3, max_capacity=20, active=True)
        self.assertFalse(self.manager.create_course(course))

    def test_course_student_and_enrollment_rules(self):
        fac = Faculty(faculty_id=2, name="Artes", dean="Dr. Ruiz", creation_date="2022-02-02", active=True)
        self.manager.create_faculty(fac)
        program = Program(program_id=20, name="Diseño", faculty_id=2, program_director="Dr. Lee", level="Pregrado", modality="Virtual", active=True)
        self.manager.create_program(program)

        professor = Professor(professor_id=3, full_name="Ana Mora", document_type="CC", document_number="998", email="ana@test.com", phone="111", faculty_id=2, employment_type="Tiempo completo", category_rank="A", academic_title="Magister", years_of_qualified_experience=6, dedication="Tiempo completo", lecture_hours=20, managerial_role="", category_score=10, title_score=8, experience_score=7, productivity_score=6, academic_management_score=4, total_points=35, point_value=150000, base_monthly_salary=5000000, health_discount=300000, pension_discount=250000, severance_provision=150000, bonus_provision=50000, vacation_provision=120000, net_salary=4200000, active=True)
        self.manager.create_professor(professor)

        invalid_course = Course(course_id=10, name="Dibujo", program_id=99, credits=3, curriculum_semester=1, assigned_professor_id=3, max_capacity=25, active=True)
        self.assertFalse(self.manager.create_course(invalid_course))

        valid_course = Course(course_id=10, name="Dibujo", program_id=20, credits=3, curriculum_semester=1, assigned_professor_id=3, max_capacity=25, active=True)
        self.assertTrue(self.manager.create_course(valid_course))

        invalid_student = Student(student_id=50, full_name="Luis Gómez", document_type="CC", document_number="321", birth_date="2001-03-03", email="luis@test.com", phone="999", program_id=99, current_semester=3, status="Activo", cumulative_average=4.0, active=True)
        self.assertFalse(self.manager.create_student(invalid_student))

        valid_student = Student(student_id=50, full_name="Luis Gómez", document_type="CC", document_number="321", birth_date="2001-03-03", email="luis@test.com", phone="999", program_id=20, current_semester=3, status="Activo", cumulative_average=4.0, active=True)
        self.assertTrue(self.manager.create_student(valid_student))

        enrollment = Enrollment(enrollment_id=1, student_id=50, course_id=10, academic_period="2026-1", final_grade=4.2, status="Aprobado", enrollment_date="2026-01-15")
        self.assertTrue(self.manager.create_enrollment(enrollment))

        self.assertFalse(self.manager.create_enrollment(Enrollment(enrollment_id=2, student_id=50, course_id=10, academic_period="2026-1", final_grade=4.1, status="Aprobado", enrollment_date="2026-01-16")))

        self.assertTrue(self.manager.deactivate_student(50))
        self.assertFalse(self.manager.create_enrollment(Enrollment(enrollment_id=3, student_id=50, course_id=10, academic_period="2026-2", final_grade=3.8, status="Aprobado", enrollment_date="2026-06-01")))

    def test_professor_and_administrative_management(self):
        faculty = Faculty(faculty_id=5, name="Administración", dean="Dra. Soto", creation_date="2018-01-01", active=True)
        self.manager.create_faculty(faculty)

        professor = Professor(professor_id=8, full_name="Pablo Rojas", document_type="CC", document_number="777", email="pablo@test.com", phone="444", faculty_id=5, employment_type="Tiempo completo", category_rank="B", academic_title="Especialista", years_of_qualified_experience=4, dedication="Tiempo completo", lecture_hours=12, managerial_role="Decano", category_score=8, title_score=7, experience_score=6, productivity_score=5, academic_management_score=4, total_points=30, point_value=130000, base_monthly_salary=4500000, health_discount=250000, pension_discount=220000, severance_provision=140000, bonus_provision=40000, vacation_provision=90000, net_salary=3800000, active=True)
        self.assertTrue(self.manager.create_professor(professor))
        self.assertTrue(self.manager.update_professor(8, full_name="Pablo Rojas C."))
        self.assertTrue(self.manager.deactivate_professor(8))
        self.assertFalse(self.manager.get_professor(8).active)
        self.assertTrue(self.manager.reactivate_professor(8))

        admin = Administrative(administrative_id=9, full_name="Carla Mendez", document_type="CC", document_number="888", email="carla@test.com", phone="333", position="Coordinadora", category="A", employment_type="Tiempo completo", base_salary=3000000, health_discount=180000, pension_discount=200000, severance_provision=120000, holiday_bonus=50000, vacation_provision=70000, net_salary=2700000, active=True)
        self.assertTrue(self.manager.create_administrative(admin))
        self.assertTrue(self.manager.delete_administrative(9))

    def test_academic_transactions_and_ebra_rule(self):
        faculty = Faculty(faculty_id=10, name="Ingeniería", dean="Dr. Ruiz", creation_date="2024-01-01", active=True)
        self.manager.create_faculty(faculty)

        program = Program(program_id=30, name="Sistemas", faculty_id=10, program_director="Dr. Vega", level="Pregrado", modality="Presencial", active=True)
        self.manager.create_program(program)

        course = Course(course_id=40, name="Algoritmos", program_id=30, credits=4, curriculum_semester=2, assigned_professor_id=0, max_capacity=2, active=True)
        self.manager.create_course(course)

        student = Student(student_id=100, full_name="Ana García", document_type="CC", document_number="101", birth_date="2002-05-10", email="ana@test.com", phone="300", program_id=30, current_semester=3, status="Active", cumulative_average=0.0, active=True)
        self.manager.create_student(student)

        self.assertTrue(self.manager.enroll_student(student_id=100, course_id=40, academic_period="2026-1", enrollment_id=500))
        self.assertFalse(self.manager.enroll_student(student_id=100, course_id=40, academic_period="2026-1", enrollment_id=501))

        full_course = Course(course_id=41, name="Bases de Datos", program_id=30, credits=3, curriculum_semester=3, assigned_professor_id=0, max_capacity=1, active=True)
        self.manager.create_course(full_course)
        second_student = Student(student_id=101, full_name="Luis Pérez", document_type="CC", document_number="102", birth_date="2001-11-20", email="luis@test.com", phone="301", program_id=30, current_semester=3, status="Active", cumulative_average=0.0, active=True)
        self.manager.create_student(second_student)
        self.assertTrue(self.manager.enroll_student(student_id=101, course_id=41, academic_period="2026-1", enrollment_id=502))
        self.assertFalse(self.manager.enroll_student(student_id=100, course_id=41, academic_period="2026-1", enrollment_id=503))

        self.manager.deactivate_student(100)
        self.assertFalse(self.manager.enroll_student(student_id=100, course_id=40, academic_period="2026-2", enrollment_id=504))
        self.manager.reactivate_student(100)

        self.manager.deactivate_course(41)
        self.assertFalse(self.manager.enroll_student(student_id=101, course_id=41, academic_period="2026-2", enrollment_id=505))
        self.manager.reactivate_course(41)

        self.assertTrue(self.manager.cancel_enrollment(enrollment_id=500))
        self.assertEqual(self.manager.get_enrollment(500).status, "CANCELLED")

        alternative_course = Course(course_id=42, name="Programación", program_id=30, credits=3, curriculum_semester=2, assigned_professor_id=0, max_capacity=5, active=True)
        self.manager.create_course(alternative_course)
        self.assertTrue(self.manager.enroll_student(student_id=100, course_id=42, academic_period="2026-1", enrollment_id=501))

        self.assertTrue(self.manager.register_grade(enrollment_id=500, grade=4.5))
        self.assertEqual(self.manager.get_enrollment(500).final_grade, 4.5)
        self.assertTrue(self.manager.register_grade(enrollment_id=501, grade=3.0))
        self.assertFalse(self.manager.register_grade(enrollment_id=501, grade=6.0))

        self.manager.set_ebra_threshold(3.7)
        self.assertAlmostEqual(self.manager.calculate_student_average(100), 3.857142857142857)
        status = self.manager.evaluate_ebra_status(100)
        self.assertEqual(status["status"], "OK")
        self.assertEqual(status["rule"], "weighted_average < configured_threshold")

        self.manager.register_grade(enrollment_id=501, grade=2.5)
        self.assertAlmostEqual(self.manager.calculate_student_average(100), 3.642857142857143)
        status = self.manager.evaluate_ebra_status(100)
        self.assertEqual(status["status"], "EBRA")


if __name__ == '__main__':
    unittest.main()
