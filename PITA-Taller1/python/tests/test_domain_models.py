import unittest

from models.administrative import Administrative
from models.course import Course
from models.enrollment import Enrollment
from models.faculty import Faculty
from models.payroll import Payroll
from models.professor import Professor
from models.program import Program
from models.student import Student


class DomainModelTests(unittest.TestCase):
    def test_faculty_model(self):
        faculty = Faculty(faculty_id=1, name="Engineering", dean="Dr. Smith", creation_date="2020-01-01", active=True)
        self.assertEqual(faculty.faculty_id, 1)
        self.assertEqual(faculty.to_dict()["name"], "Engineering")
        self.assertEqual(Faculty.from_dict(faculty.to_dict()).name, "Engineering")

    def test_program_model(self):
        program = Program(program_id=10, name="Systems", faculty_id=1, program_director="Dr. Vega", level="Undergraduate", modality="Presencial", active=True)
        self.assertEqual(program.faculty_id, 1)
        self.assertEqual(program.to_dict()["modality"], "Presencial")
        self.assertEqual(Program.from_dict(program.to_dict()).program_id, 10)

    def test_course_student_enrollment_flow(self):
        course = Course(course_id=20, name="Data Structures", program_id=10, credits=4, curriculum_semester=2, assigned_professor_id=3, max_capacity=40, active=True)
        student = Student(student_id=100, full_name="Ana Perez", document_type="CC", document_number="123", birth_date="2002-01-05", email="ana@test.com", phone="555", program_id=10, current_semester=2, status="Active", cumulative_average=4.2, active=True)
        enrollment = Enrollment(enrollment_id=500, student_id=100, course_id=20, academic_period="2026-1", final_grade=4.5, status="Approved", enrollment_date="2026-01-10")

        course.enrollment_list.insert(enrollment)
        student.enrollment_list.insert(enrollment)

        self.assertEqual(course.enrollment_list.count_elements(), 1)
        self.assertEqual(student.enrollment_list.count_elements(), 1)
        self.assertEqual(Enrollment.from_dict(enrollment.to_dict()).course_id, 20)

    def test_professor_models_and_serialization(self):
        professor = Professor(professor_id=3, full_name="Luis Gomez", document_type="CC", document_number="321", email="luis@test.com", phone="777", faculty_id=1, employment_type="Full-time", category_rank="A", academic_title="PhD", years_of_qualified_experience=8, dedication="Full-time", lecture_hours=10, managerial_role="Coordinator", category_score=10.5, title_score=5.5, experience_score=3.0, productivity_score=4.0, academic_management_score=2.0, total_points=25.0, point_value=1000.0, base_monthly_salary=5000000.0, health_discount=250000.0, pension_discount=300000.0, severance_provision=150000.0, bonus_provision=200000.0, vacation_provision=100000.0, net_salary=4500000.0, active=True)
        self.assertTrue(professor.validate())
        self.assertEqual(Professor.from_dict(professor.to_dict()).full_name, "Luis Gomez")

    def test_administrative_and_payroll_serialization(self):
        administrative = Administrative(administrative_id=7, full_name="Maria Ruiz", document_type="CC", document_number="456", email="maria@test.com", phone="888", position="Coordinator", category="A", employment_type="Full-time", base_salary=3500000.0, health_discount=180000.0, pension_discount=220000.0, severance_provision=100000.0, holiday_bonus=50000.0, vacation_provision=75000.0, net_salary=3100000.0, active=True)
        payroll = Payroll(description="Monthly payroll")

        self.assertEqual(Administrative.from_dict(administrative.to_dict()).position, "Coordinator")
        self.assertEqual(Payroll.from_dict(payroll.to_dict()).description, "Monthly payroll")

    def test_payroll_calculations_for_professor_and_administrative(self):
        professor = Professor(
            professor_id=3,
            full_name="Luis Gomez",
            document_type="CC",
            document_number="321",
            email="luis@test.com",
            phone="777",
            faculty_id=1,
            employment_type="Full-time",
            category_rank="A",
            academic_title="PhD",
            years_of_qualified_experience=8,
            dedication="Full-time",
            lecture_hours=10,
            managerial_role="Coordinator",
            category_score=10.5,
            title_score=5.5,
            experience_score=3.0,
            productivity_score=4.0,
            academic_management_score=2.0,
            total_points=25.0,
            point_value=1000.0,
            base_monthly_salary=5000000.0,
            health_discount=250000.0,
            pension_discount=300000.0,
            severance_provision=150000.0,
            bonus_provision=200000.0,
            vacation_provision=100000.0,
            net_salary=4500000.0,
            active=True,
        )

        payroll = Payroll(description="Monthly payroll")
        professor_report = payroll.generate_payroll_report(professor)
        self.assertAlmostEqual(professor_report["points"], 25.0)
        self.assertAlmostEqual(professor_report["deductions"], 550000.0)
        self.assertAlmostEqual(professor_report["benefits"], 450000.0)
        self.assertAlmostEqual(professor_report["net_salary"], 5000000.0 - 550000.0 + 450000.0)

        administrative = Administrative(
            administrative_id=7,
            full_name="Maria Ruiz",
            document_type="CC",
            document_number="456",
            email="maria@test.com",
            phone="888",
            position="Coordinator",
            category="A",
            employment_type="Full-time",
            base_salary=3500000.0,
            health_discount=180000.0,
            pension_discount=220000.0,
            severance_provision=100000.0,
            holiday_bonus=50000.0,
            vacation_provision=75000.0,
            net_salary=3100000.0,
            active=True,
        )

        admin_report = payroll.generate_payroll_report(administrative)
        self.assertAlmostEqual(admin_report["deductions"], 400000.0)
        self.assertAlmostEqual(admin_report["benefits"], 225000.0)
        self.assertAlmostEqual(admin_report["net_salary"], 3500000.0 - 400000.0 + 225000.0)

    def test_invalid_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            Faculty(faculty_id=-1, name="Bad Faculty")
        with self.assertRaises(ValueError):
            Program(program_id=1, name="Bad Program", faculty_id=-1)
        with self.assertRaises(ValueError):
            Enrollment(enrollment_id=1, student_id=0, course_id=-2)


if __name__ == '__main__':
    unittest.main()
