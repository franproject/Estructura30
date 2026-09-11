"""Unit tests verifying hierarchical deletion across domain models, EntityManager, and persistence layer.

Verifies:
1. Deleting a program loaded from disk properly unlinks from faculty and allows faculty deletion.
2. Both scalar integer IDs and domain object instances are correctly handled in child lists.
3. Cascading deletion across Faculty -> Program -> Course/Student -> Enrollment works as expected.
4. Serializing entities with child objects writes clean integer ID lists without nested dictionaries.
"""

import json
import os
import tempfile
import unittest

from models.administrative import Administrative
from models.course import Course
from models.enrollment import Enrollment
from models.faculty import Faculty
from models.linked_list import LinkedList
from models.professor import Professor
from models.program import Program
from models.student import Student
from persistence.file_manager import (
    link_hierarchical_entities,
    load_all_entities,
    load_courses,
    load_enrollments,
    load_faculties,
    load_programs,
    load_students,
    save_courses,
    save_enrollments,
    save_faculties,
    save_programs,
    save_students,
)
from services.entity_manager import EntityManager


class HierarchicalDeletionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_disk_loaded_program_deletion_allows_faculty_deletion_scalar_ids(self):
        """Demonstrates that after loading from disk with scalar IDs, deleting a program
        successfully unlinks from faculty.program_list and allows subsequent faculty deletion.
        """
        faculties_file = os.path.join(self.temp_path, "faculties.json")
        programs_file = os.path.join(self.temp_path, "programs.json")

        with open(faculties_file, "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "faculty_id": 1,
                        "name": "Facultad de Ingeniería",
                        "dean": "Decano Uno",
                        "creation_date": "2020-01-01",
                        "active": True,
                        "program_list": [101],
                    }
                ],
                f,
            )

        with open(programs_file, "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "program_id": 101,
                        "name": "Ingeniería de Sistemas",
                        "faculty_id": 1,
                        "program_director": "Director Uno",
                        "level": "Pregrado",
                        "modality": "Presencial",
                        "program_type": "Ingeniería",
                        "active": True,
                        "course_list": [],
                        "student_list": [],
                    }
                ],
                f,
            )

        em = EntityManager()
        em.faculties = LinkedList(load_faculties(faculties_file))
        em.programs = LinkedList(load_programs(programs_file))

        # Faculty has program 101 registered, so deleting faculty must be blocked
        self.assertFalse(em.delete_faculty(1))

        # Deleting program 101 must succeed and unlink from faculty.program_list (which has scalar 101)
        self.assertTrue(em.delete_program(101))
        self.assertIsNone(em.get_program(101))

        # Now faculty 1 has no remaining programs, so deleting faculty must succeed
        self.assertTrue(em.delete_faculty(1))
        self.assertIsNone(em.get_faculty(1))

    def test_disk_loaded_program_deletion_with_hierarchical_linking(self):
        """Demonstrates deletion after loading from disk and running link_hierarchical_entities."""
        faculties_file = os.path.join(self.temp_path, "faculties.json")
        programs_file = os.path.join(self.temp_path, "programs.json")

        with open(faculties_file, "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "faculty_id": 2,
                        "name": "Facultad de Ciencias",
                        "dean": "Decano Dos",
                        "creation_date": "2021-01-01",
                        "active": True,
                        "program_list": [201],
                    }
                ],
                f,
            )

        with open(programs_file, "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "program_id": 201,
                        "name": "Biología",
                        "faculty_id": 2,
                        "program_director": "Director Dos",
                        "level": "Pregrado",
                        "modality": "Presencial",
                        "program_type": "Ciencias",
                        "active": True,
                        "course_list": [],
                        "student_list": [],
                    }
                ],
                f,
            )

        em = EntityManager()
        em.faculties = LinkedList(load_faculties(faculties_file))
        em.programs = LinkedList(load_programs(programs_file))

        # Explicitly link hierarchical references
        em.link_hierarchical_references()

        # Faculty.program_list now contains the Program object instance
        faculty = em.get_faculty(2)
        self.assertIsInstance(faculty.program_list.head.data, Program)

        # Faculty deletion is blocked while program exists
        self.assertFalse(em.delete_faculty(2))

        # Program deletion succeeds and removes the Program instance from faculty.program_list
        self.assertTrue(em.delete_program(201))
        self.assertEqual(faculty.program_list.count_elements(), 0)

        # Faculty deletion now succeeds
        self.assertTrue(em.delete_faculty(2))
        self.assertIsNone(em.get_faculty(2))

    def test_full_hierarchical_cascade_deletion(self):
        """Tests end-to-end cascading deletion:
        Faculty -> Program -> Course / Student -> Enrollment.
        """
        em = EntityManager()

        faculty = Faculty(faculty_id=1, name="Ingeniería", dean="Decano", creation_date="2020", active=True)
        self.assertTrue(em.create_faculty(faculty))

        program = Program(
            program_id=10,
            name="Sistemas",
            faculty_id=1,
            program_director="Director",
            level="Pregrado",
            modality="Presencial",
            active=True,
        )
        self.assertTrue(em.create_program(program))

        course = Course(
            course_id=100,
            name="Algoritmos",
            program_id=10,
            credits=3,
            curriculum_semester=1,
            max_capacity=30,
            active=True,
        )
        self.assertTrue(em.create_course(course))

        student = Student(
            student_id=1000,
            full_name="Carlos Gomez",
            document_type="CC",
            document_number="987654",
            birth_date="2000-01-01",
            email="carlos@test.edu",
            phone="123456",
            program_id=10,
            current_semester=1,
            status="Active",
            active=True,
        )
        self.assertTrue(em.create_student(student))

        self.assertTrue(em.enroll_student(student_id=1000, course_id=100, academic_period="2026-1", enrollment_id=5000))

        # Verify dependency locks
        self.assertFalse(em.delete_course(100))
        self.assertFalse(em.delete_student(1000))
        self.assertFalse(em.delete_program(10))
        self.assertFalse(em.delete_faculty(1))

        # Delete enrollment first
        self.assertTrue(em.delete_enrollment(5000))
        self.assertIsNone(em.get_enrollment(5000))

        # Now course and student can be deleted
        self.assertTrue(em.delete_course(100))
        self.assertIsNone(em.get_course(100))

        self.assertTrue(em.delete_student(1000))
        self.assertIsNone(em.get_student(1000))

        # Now program can be deleted
        self.assertTrue(em.delete_program(10))
        self.assertIsNone(em.get_program(10))

        # Finally faculty can be deleted
        self.assertTrue(em.delete_faculty(1))
        self.assertIsNone(em.get_faculty(1))

    def test_model_symmetric_equality(self):
        """Verifies that __eq__ allows symmetric comparison between model instances and scalar IDs."""
        faculty = Faculty(faculty_id=1, name="Fac", dean="Dean", creation_date="2020", active=True)
        program = Program(program_id=10, name="Prog", faculty_id=1, program_director="Dir", level="Pre", modality="Pres", active=True)
        course = Course(course_id=20, name="Course", program_id=10, credits=3, curriculum_semester=1, active=True)
        student = Student(student_id=30, full_name="Student", document_type="CC", document_number="1", birth_date="2000", email="s@t.com", phone="1", program_id=10, current_semester=1, status="A", active=True)
        enrollment = Enrollment(enrollment_id=40, student_id=30, course_id=20, academic_period="2026-1", final_grade=4.0, status="ACTIVE", enrollment_date="2026-01-01")
        prof = Professor(professor_id=50, full_name="Prof", document_type="CC", document_number="2", email="p@t.com", phone="2", faculty_id=1, employment_type="Planta", category_rank="Titular", academic_title="PhD", active=True)
        admin = Administrative(administrative_id=60, full_name="Admin", document_type="CC", document_number="3", email="a@t.com", phone="3", position="Coord", category="A", employment_type="Planta", base_salary=1000.0, active=True)

        for entity, eid in [
            (faculty, 1),
            (program, 10),
            (course, 20),
            (student, 30),
            (enrollment, 40),
            (prof, 50),
            (admin, 60),
        ]:
            self.assertEqual(entity, eid)
            self.assertEqual(eid, entity)
            self.assertEqual(hash(entity), hash(eid))

            # Test in LinkedList removal
            ll = LinkedList([eid])
            self.assertTrue(ll.remove(entity))
            self.assertEqual(ll.count_elements(), 0)

            ll2 = LinkedList([entity])
            self.assertTrue(ll2.remove(eid))
            self.assertEqual(ll2.count_elements(), 0)

    def test_calculate_student_average_with_scalar_enrollment_ids(self):
        """Verifies calculate_student_average works even when student.enrollment_list contains integer IDs."""
        em = EntityManager()
        course = Course(course_id=1, name="Calculo", program_id=10, credits=4, curriculum_semester=1, active=True)
        student = Student(student_id=100, full_name="Pedro", document_type="CC", document_number="1", birth_date="2000", email="p@t.com", phone="1", program_id=10, current_semester=1, status="Active", active=True)
        enrollment = Enrollment(enrollment_id=500, student_id=100, course_id=1, academic_period="2026-1", final_grade=4.0, status="COMPLETED", enrollment_date="2026-01-01")

        em.courses.insert(course)
        em.students.insert(student)
        em.enrollments.insert(enrollment)

        # Put scalar ID directly into student's enrollment list
        student.enrollment_list = LinkedList([500])

        avg = em.calculate_student_average(100)
        self.assertAlmostEqual(avg, 4.0)

    def test_clean_id_serialization(self):
        """Verifies that saving entities whose child lists contain domain objects
        serializes them as clean lists of integer IDs, not nested dictionaries.
        """
        faculty = Faculty(faculty_id=1, name="Ingenieria", dean="Decano", creation_date="2020", active=True)
        program = Program(program_id=10, name="Sistemas", faculty_id=1, program_director="Dir", level="Pre", modality="Pres", active=True)
        faculty.program_list = LinkedList([program])

        file_path = os.path.join(self.temp_path, "faculties_test.json")
        self.assertTrue(save_faculties([faculty], file_path))

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data[0]["program_list"], [10])

