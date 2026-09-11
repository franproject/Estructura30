import json
import os
import tempfile
import unittest

from models.administrative import Administrative
from models.course import Course
from models.enrollment import Enrollment
from models.faculty import Faculty
from models.program import Program
from models.student import Student
from persistence.file_manager import (
    save_administrative_staff,
    save_courses,
    save_enrollments,
    save_faculties,
    save_payroll_periods,
    save_programs,
    save_students,
    load_administrative_staff,
    load_courses,
    load_enrollments,
    load_faculties,
    load_payroll_periods,
    load_programs,
    load_students,
    clear_load_issues,
    get_load_issues,
    _save_json,
)


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = self.temp_dir.name
        clear_load_issues()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_missing_files_and_empty_payloads(self):
        missing_file = os.path.join(self.temp_path, "missing.json")
        self.assertEqual(load_faculties(missing_file), [])
        self.assertEqual(load_students(missing_file), [])

        empty_file = os.path.join(self.temp_path, "empty.json")
        with open(empty_file, "w", encoding="utf-8") as file:
            file.write("")
        self.assertEqual(load_courses(empty_file), [])

    def test_persistence_round_trip(self):
        faculty = Faculty(faculty_id=1, name="Engineering", dean="Dr. Smith", creation_date="2020-01-01", active=True)
        program = Program(program_id=10, name="Systems", faculty_id=1, program_director="Dr. Vega", level="Undergraduate", modality="Presencial", active=True)
        course = Course(course_id=20, name="Data Structures", program_id=10, credits=4, curriculum_semester=2, assigned_professor_id=3, max_capacity=40, active=True)
        student = Student(student_id=100, full_name="Ana Perez", document_type="CC", document_number="123", birth_date="2002-01-05", email="ana@test.com", phone="555", program_id=10, current_semester=2, status="Active", cumulative_average=4.2, active=True)
        enrollment = Enrollment(enrollment_id=500, student_id=100, course_id=20, academic_period="2026-1", final_grade=4.5, status="Approved", enrollment_date="2026-01-10")
        administrative = Administrative(administrative_id=7, full_name="Maria Ruiz", document_type="CC", document_number="456", email="maria@test.com", phone="888", position="Coordinator", category="A", employment_type="Full-time", base_salary=3500000.0, health_discount=180000.0, pension_discount=220000.0, severance_provision=100000.0, holiday_bonus=50000.0, vacation_provision=75000.0, net_salary=3100000.0, active=True)

        faculty.program_list.insert(program)
        program.course_list.insert(course)
        program.student_list.insert(student)
        course.enrollment_list.insert(enrollment)
        student.enrollment_list.insert(enrollment)

        faculty_path = os.path.join(self.temp_path, "faculties.json")
        programs_path = os.path.join(self.temp_path, "programs.json")
        courses_path = os.path.join(self.temp_path, "courses.json")
        students_path = os.path.join(self.temp_path, "students.json")
        enrollments_path = os.path.join(self.temp_path, "enrollments.json")
        staff_path = os.path.join(self.temp_path, "administrative_staff.json")

        self.assertTrue(save_faculties([faculty], faculty_path))
        self.assertTrue(save_programs([program], programs_path))
        self.assertTrue(save_courses([course], courses_path))
        self.assertTrue(save_students([student], students_path))
        self.assertTrue(save_enrollments([enrollment], enrollments_path))
        self.assertTrue(save_administrative_staff([administrative], staff_path))

        loaded_faculties = load_faculties(faculty_path)
        loaded_programs = load_programs(programs_path)
        loaded_courses = load_courses(courses_path)
        loaded_students = load_students(students_path)
        loaded_enrollments = load_enrollments(enrollments_path)
        loaded_staff = load_administrative_staff(staff_path)

        self.assertEqual(len(loaded_faculties), 1)
        self.assertEqual(loaded_faculties[0].faculty_id, 1)
        self.assertEqual(loaded_faculties[0].program_list.count_elements(), 1)

        self.assertEqual(loaded_programs[0].faculty_id, 1)
        self.assertEqual(loaded_programs[0].course_list.count_elements(), 1)
        self.assertEqual(loaded_programs[0].student_list.count_elements(), 1)

        self.assertEqual(loaded_courses[0].course_id, 20)
        self.assertEqual(loaded_courses[0].enrollment_list.count_elements(), 1)

        self.assertEqual(loaded_students[0].student_id, 100)
        self.assertEqual(loaded_students[0].enrollment_list.count_elements(), 1)

        self.assertEqual(loaded_enrollments[0].final_grade, 4.5)
        self.assertEqual(loaded_enrollments[0].status, "Approved")

        self.assertTrue(loaded_staff[0].active)

    def test_invalid_json_is_tolerated(self):
        clear_load_issues()
        invalid_file = os.path.join(self.temp_path, "broken.json")
        with open(invalid_file, "w", encoding="utf-8") as file:
            file.write("{esto no es json")
        self.assertEqual(load_programs(invalid_file), [])
        issues = get_load_issues()
        self.assertTrue(issues)
        self.assertIn("broken.corrupto-", issues[0])
        backups = [name for name in os.listdir(self.temp_path) if name.startswith("broken.corrupto-")]
        self.assertEqual(len(backups), 1)

    def test_save_json_removes_temporary_file_after_success(self):
        target_file = os.path.join(self.temp_path, "atomic.json")

        self.assertTrue(_save_json(target_file, [{"saved": True}]))
        self.assertTrue(os.path.exists(target_file))
        temporary_files = [
            name for name in os.listdir(self.temp_path)
            if name.startswith(".atomic.json.") and name.endswith(".tmp")
        ]
        self.assertEqual(temporary_files, [])

    def test_legacy_labor_defaults_use_independent_lists(self):
        staff_file = os.path.join(self.temp_path, "legacy_staff.json")
        legacy_records = [
            {"administrative_id": 1, "full_name": "Ana", "active": True},
            {"administrative_id": 2, "full_name": "Luis", "active": True},
        ]
        with open(staff_file, "w", encoding="utf-8") as file:
            json.dump(legacy_records, file)

        loaded_staff = load_administrative_staff(staff_file)
        self.assertEqual(len(loaded_staff), 2)
        loaded_staff[0].novelties.append({"code": "BONUS"})
        self.assertEqual(loaded_staff[1].novelties, [])

    def test_unexpected_json_type_is_reported(self):
        scalar_file = os.path.join(self.temp_path, "scalar.json")
        with open(scalar_file, "w", encoding="utf-8") as file:
            file.write("42")
        self.assertEqual(load_programs(scalar_file), [])
        self.assertTrue(get_load_issues())

    def test_partial_invalid_records_are_skipped_and_valid_preserved(self):
        clear_load_issues()
        students_file = os.path.join(self.temp_path, "students.json")
        records = [
            {
                "student_id": 101,
                "full_name": "Valido Uno",
                "document_type": "CC",
                "document_number": "111",
                "birth_date": "2000-01-01",
                "email": "v1@test.com",
                "phone": "111",
                "program_id": 1,
                "current_semester": 1,
                "status": "Active",
                "cumulative_average": 4.0,
                "active": True,
            },
            {
                "student_id": None,  # INVALID: triggers validation error
                "full_name": "Invalido Nulo",
                "document_type": "CC",
                "document_number": "222",
                "birth_date": "2000-01-01",
                "email": "v2@test.com",
                "phone": "222",
                "program_id": 1,
                "current_semester": 1,
                "status": "Active",
                "cumulative_average": 4.0,
                "active": True,
            },
            {
                "student_id": 103,
                "full_name": "Valido Dos",
                "document_type": "CC",
                "document_number": "333",
                "birth_date": "2000-01-01",
                "email": "v3@test.com",
                "phone": "333",
                "program_id": 1,
                "current_semester": 1,
                "status": "Active",
                "cumulative_average": 3.8,
                "active": True,
            },
        ]
        with open(students_file, "w", encoding="utf-8") as file:
            json.dump(records, file)

        loaded = load_students(students_file)
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].student_id, 101)
        self.assertEqual(loaded[1].student_id, 103)

        issues = get_load_issues()
        self.assertTrue(issues)
        self.assertTrue(any("students.json" in issue and "registro #1" in issue and "student_id" in issue for issue in issues))

        # Re-saving must preserve the valid records without erasing them
        self.assertTrue(save_students(loaded, students_file))
        reloaded = load_students(students_file)
        self.assertEqual(len(reloaded), 2)
        self.assertEqual(reloaded[0].student_id, 101)
        self.assertEqual(reloaded[1].student_id, 103)

    def test_non_dict_element_in_collection_is_skipped(self):
        clear_load_issues()
        faculties_file = os.path.join(self.temp_path, "faculties.json")
        records = [
            {"faculty_id": 1, "name": "Ingenieria", "active": True},
            "no_es_un_dict",
            {"faculty_id": 2, "name": "Salud", "active": True},
        ]
        with open(faculties_file, "w", encoding="utf-8") as file:
            json.dump(records, file)

        loaded = load_faculties(faculties_file)
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].faculty_id, 1)
        self.assertEqual(loaded[1].faculty_id, 2)

        issues = get_load_issues()
        self.assertTrue(issues)
        self.assertTrue(any("registro #1" in issue and "tipo de dato" in issue for issue in issues))

    def test_save_json_creates_automatic_bak_backup(self):
        target_file = os.path.join(self.temp_path, "data.json")
        bak_file = target_file + ".bak"

        # First save: file created, no .bak yet
        self.assertTrue(_save_json(target_file, [{"version": 1}]))
        self.assertTrue(os.path.exists(target_file))
        self.assertFalse(os.path.exists(bak_file))

        # Second save: .bak created containing version 1, target contains version 2
        self.assertTrue(_save_json(target_file, [{"version": 2}]))
        self.assertTrue(os.path.exists(bak_file))

        with open(bak_file, "r", encoding="utf-8") as f:
            bak_content = json.load(f)
        with open(target_file, "r", encoding="utf-8") as f:
            target_content = json.load(f)

        self.assertEqual(bak_content, [{"version": 1}])
        self.assertEqual(target_content, [{"version": 2}])

    def test_load_payroll_periods_skips_invalid_period(self):
        clear_load_issues()
        periods_file = os.path.join(self.temp_path, "payroll_periods.json")
        records = [
            {
                "period_id": "2026-01",
                "year": 2026,
                "month": 1,
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "status": "OPEN",
            },
            {
                "period_id": "",  # INVALID: empty period_id
                "year": 2026,
                "month": 2,
                "start_date": "2026-02-01",
                "end_date": "2026-02-28",
                "status": "OPEN",
            },
            {
                "period_id": "2026-03",
                "year": 2026,
                "month": 3,
                "start_date": "2026-03-01",
                "end_date": "2026-03-31",
                "status": "OPEN",
            },
        ]
        with open(periods_file, "w", encoding="utf-8") as file:
            json.dump(records, file)

        loaded = load_payroll_periods(periods_file)
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].period_id, "2026-01")
        self.assertEqual(loaded[1].period_id, "2026-03")

        issues = get_load_issues()
        self.assertTrue(issues)
        self.assertTrue(any("payroll_periods.json" in issue and "registro #1" in issue for issue in issues))


if __name__ == '__main__':
    unittest.main()
