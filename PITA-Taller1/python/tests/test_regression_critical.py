"""Suite de pruebas de regresión crítica para NexoCampus (PITA).

Valida específicamente los bugs críticos identificados y subsanados en el sistema:
1. TEST AUD-001: Deserialización segura con student_id: null intercalado en JSON.
2. TEST AUD-003: Integridad referencial en delete_program() con datos reales (compatibilidad int vs objeto).
3. TEST AUD-004: Cálculo de promedio ponderado estudiantil y prevención de falso positivo en EBRA.
4. TEST AUD-002: Liquidación de nómina mensual en meses sin prima (net_salary <= gross_salary).
5. TEST AUD-009: Retención de página activa con keep_page=True en DataTable.
6. TEST AUD-014: Búsqueda insensible a diacríticos (búsqueda de "electronica" encuentra "Ingeniería Electrónica").
"""

import json
import os
import tempfile
import unittest
from datetime import date
from decimal import Decimal

from PySide6.QtWidgets import QApplication

from models.administrative import Administrative
from models.course import Course
from models.enrollment import Enrollment
from models.faculty import Faculty
from models.linked_list import LinkedList
from models.payroll_period import PayrollPeriod as ModelPayrollPeriod
from models.professor import Professor
from models.program import Program
from models.student import Student
from persistence.file_manager import (
    clear_load_issues,
    get_load_issues,
    load_courses,
    load_faculties,
    load_programs,
    load_students,
)
from services.entity_manager import EntityManager
from services.payroll_cycle import PayrollCycleService
from services.payroll_engine import (
    PayrollEmployee,
    PayrollPeriod,
    PayrollRules,
    calculate_payroll,
)
from gui.components.data_table import DataTable
from gui.pages.crud_page import CrudPage


class TestRegressionCritical(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    # -------------------------------------------------------------------------
    # 1. TEST AUD-001 (Deserialización segura)
    # -------------------------------------------------------------------------
    def test_aud_001_safe_deserialization_with_null_student_id(self):
        """BUG AUD-001: Un registro corrupto con student_id: null provocaba que load_students()
        descartara toda la colección devolviendo una lista vacía o fallara catastróficamente.
        
        VALIDACIÓN:
        load_students() debe ignorar únicamente el registro corrupto, cargar todos los registros
        válidos restantes, y registrar una advertencia descriptiva en get_load_issues().
        """
        clear_load_issues()

        corrupt_data = [
            {
                "student_id": 10001,
                "full_name": "Estudiante Valido Uno",
                "document_type": "CC",
                "document_number": "1001",
                "birth_date": "2001-01-01",
                "email": "uno@test.edu",
                "phone": "3001",
                "program_id": 101,
                "current_semester": 3,
                "status": "Active",
                "cumulative_average": 3.8,
                "active": True,
                "enrollment_list": [],
            },
            {
                "student_id": None,  # REGISTRO CORRUPTO
                "full_name": "Estudiante Corrupto Null ID",
                "document_type": "CC",
                "document_number": "9999",
                "birth_date": "2000-01-01",
                "email": "corrupt@test.edu",
                "phone": "0000",
                "program_id": 101,
                "current_semester": 1,
                "status": "Active",
                "cumulative_average": 0.0,
                "active": True,
                "enrollment_list": [],
            },
            {
                "student_id": 10002,
                "full_name": "Estudiante Valido Dos",
                "document_type": "CC",
                "document_number": "1002",
                "birth_date": "2001-02-02",
                "email": "dos@test.edu",
                "phone": "3002",
                "program_id": 101,
                "current_semester": 4,
                "status": "Active",
                "cumulative_average": 4.1,
                "active": True,
                "enrollment_list": [],
            },
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(corrupt_data, f)
            temp_path = f.name

        try:
            loaded_students = load_students(temp_path)

            # Debe recuperar exactamente los 2 estudiantes válidos (no lista vacía)
            self.assertEqual(len(loaded_students), 2)
            self.assertEqual(loaded_students[0].student_id, 10001)
            self.assertEqual(loaded_students[1].student_id, 10002)

            # Debe existir al menos un mensaje de incidencia registrado en _LOAD_ISSUES
            issues = get_load_issues()
            self.assertGreaterEqual(len(issues), 1)
            self.assertTrue(
                any("error al deserializar" in msg.lower() or "omit" in msg.lower() or "null" in msg.lower() for msg in issues),
                f"Issues reportados: {issues}",
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            clear_load_issues()

    # -------------------------------------------------------------------------
    # 2. TEST AUD-003 (Integridad referencial en delete_program)
    # -------------------------------------------------------------------------
    def test_aud_003_referential_integrity_delete_program_real_data(self):
        """BUG AUD-003: Al cargar datos reales desde disco, las facultades contienen listas
        con enteros escalares (ej. [101, 102]). Al invocar delete_program(101), la comparación
        entre el objeto Program(101) y los enteros provocaba fallos de incompatibilidad de tipos,
        impidiendo la desvinculación y eliminación del programa.

        VALIDACIÓN:
        delete_program() sobre un EntityManager inicializado con datos reales de data/ debe
        retornar True cuando no tiene dependencias activas, desvinculándose de faculty.program_list
        sin errores de tipos.
        """
        em = EntityManager()
        em.faculties = LinkedList(load_faculties())
        em.programs = LinkedList(load_programs())
        em.courses = LinkedList(load_courses())
        em.students = LinkedList(load_students())

        # Seleccionar un programa existente (ej. 101)
        target_program_id = 101
        program = em.get_program(target_program_id)
        self.assertIsNotNone(program, "El programa 101 debe existir en los datos iniciales.")

        faculty_id = program.faculty_id
        faculty = em.get_faculty(faculty_id)
        self.assertIsNotNone(faculty, "La facultad del programa 101 debe existir.")

        # Limpiar dependencias activas en memoria para aislar la prueba de eliminación del programa
        program.course_list = LinkedList()
        program.student_list = LinkedList()
        em.courses = LinkedList([c for c in em.courses if c.program_id != target_program_id])
        em.students = LinkedList([s for s in em.students if s.program_id != target_program_id])

        # Verificar que la facultad contiene el ID o la entidad del programa
        faculty_prog_ids = [getattr(p, "program_id", p) for p in faculty.program_list]
        self.assertIn(target_program_id, faculty_prog_ids)

        # La eliminación debe retornar True y no fallar por comparación int vs Program
        deletion_result = em.delete_program(target_program_id)
        self.assertTrue(deletion_result, "delete_program() debe retornar True al eliminar sin dependencias.")

        # El programa ya no debe existir en EntityManager
        self.assertIsNone(em.get_program(target_program_id))

        # El programa debe haber sido desvinculado de faculty.program_list
        updated_faculty_prog_ids = [getattr(p, "program_id", p) for p in faculty.program_list]
        self.assertNotIn(target_program_id, updated_faculty_prog_ids)

    # -------------------------------------------------------------------------
    # 3. TEST AUD-004 (Promedio estudiantil y prevención de falso EBRA)
    # -------------------------------------------------------------------------
    def test_aud_004_student_average_not_misclassified_as_ebra(self):
        """BUG AUD-004: calculate_student_average() fallaba al resolver notas de inscripciones
        asociadas al estudiante o no cruzaba con los créditos de los cursos en la colección,
        dejando el promedio en 0.0 y marcando incorrectamente al estudiante en alerta crítica (EBRA).

        VALIDACIÓN:
        Un estudiante con materias cursadas y notas aprobatorias (> 3.0) debe registrar un promedio
        ponderado > 0.0 y recibir estado 'OK', no siendo clasificado como EBRA.
        """
        em = EntityManager()

        # Registrar estructura académica
        faculty = Faculty(faculty_id=1, name="Facultad de Ciencias", dean="Decano", creation_date="2020", active=True)
        em.create_faculty(faculty)

        program = Program(program_id=10, name="Física", faculty_id=1, program_director="Director", level="Pregrado", modality="Presencial", active=True)
        em.create_program(program)

        course1 = Course(course_id=101, name="Mecánica Clásica", program_id=10, credits=4, curriculum_semester=2, max_capacity=30, active=True)
        course2 = Course(course_id=102, name="Electromagnetismo", program_id=10, credits=3, curriculum_semester=3, max_capacity=30, active=True)
        em.create_course(course1)
        em.create_course(course2)

        student = Student(
            student_id=500,
            full_name="Isaac Newton",
            document_type="CC",
            document_number="50001",
            birth_date="2002-01-01",
            email="isaac@test.edu",
            phone="3000",
            program_id=10,
            current_semester=3,
            status="Active",
            cumulative_average=0.0,
            active=True,
        )
        em.create_student(student)

        # Matricular al estudiante con notas aprobatorias
        em.enroll_student(student_id=500, course_id=101, academic_period="2026-1", enrollment_id=1)
        em.register_grade(enrollment_id=1, grade=4.5)

        em.enroll_student(student_id=500, course_id=102, academic_period="2026-1", enrollment_id=2)
        em.register_grade(enrollment_id=2, grade=4.0)

        # Promedio ponderado esperado: (4.5*4 + 4.0*3) / 7 = (18.0 + 12.0) / 7 = 30.0 / 7 ≈ 4.2857
        average = em.calculate_student_average(500)
        self.assertGreater(average, 0.0)
        self.assertAlmostEqual(average, 30.0 / 7.0, places=3)

        # Verificación del estado EBRA
        ebra_eval = em.evaluate_ebra_status(500)
        self.assertEqual(ebra_eval["status"], "OK")
        self.assertNotEqual(ebra_eval["status"], "EBRA")

        # No debe aparecer en el listado de estudiantes en riesgo
        ebra_list = em.get_ebra_students()
        self.assertNotIn(student, ebra_list)

    # -------------------------------------------------------------------------
    # 4. TEST AUD-002 (Nómina mensual sin prima)
    # -------------------------------------------------------------------------
    def test_aud_002_monthly_payroll_without_prima_net_salary_lte_gross(self):
        """BUG AUD-002: En meses ordinarios donde la prima de servicios no se paga en efectivo
        (meses diferentes a junio y diciembre), el motor acumulaba indebidamente la provisión
        de prima en las percepciones netas, haciendo que net_salary fuera mayor que gross_salary.

        VALIDACIÓN:
        Para cualquier período mensual ordinario (ej. septiembre 2026), el salario neto (net_salary)
        calculado debe ser estrictamente menor o igual al salario bruto (gross_salary).
        """
        period_september = PayrollPeriod("2026-09", date(2026, 9, 1), date(2026, 9, 30), 30)
        rules = PayrollRules()

        # 1. Validación directa en PayrollEngine para docente y administrativo
        prof_employee = PayrollEmployee(
            employee_id="P-1",
            employee_type="Professor",
            employment_type="planta",
            base_monthly_salary=Decimal("4500000"),
            active=True,
        )
        admin_employee = PayrollEmployee(
            employee_id="A-1",
            employee_type="Administrative",
            employment_type="planta",
            base_monthly_salary=Decimal("3000000"),
            active=True,
        )

        res_prof = calculate_payroll(prof_employee, period_september, rules)
        self.assertLessEqual(
            res_prof.net_salary,
            res_prof.gross_salary,
            f"Neto ({res_prof.net_salary}) supera el bruto ({res_prof.gross_salary}) en septiembre.",
        )

        res_admin = calculate_payroll(admin_employee, period_september, rules)
        self.assertLessEqual(
            res_admin.net_salary,
            res_admin.gross_salary,
            f"Neto ({res_admin.net_salary}) supera el bruto ({res_admin.gross_salary}) en septiembre.",
        )

        # 2. Validación a través del servicio de ciclo de nómina
        cycle_service = PayrollCycleService()
        period_record = cycle_service.create_period(2026, 9, "2026-09-01", "2026-09-30", "test_auditor")
        admin_model = Administrative(
            administrative_id=88,
            full_name="Carlos Contador",
            base_salary=2800000.0,
            active=True,
        )

        run = cycle_service.calculate_run(period_record.period_id, [admin_model], rules, "test_auditor")
        detail = run.details[0]

        gross = Decimal(str(detail["gross_salary"]))
        net = Decimal(str(detail["net_salary"]))
        self.assertLessEqual(net, gross, f"En PayrollCycleService, neto ({net}) no puede ser mayor a bruto ({gross}).")

    # -------------------------------------------------------------------------
    # 5. TEST AUD-009 (Retención de página en DataTable)
    # -------------------------------------------------------------------------
    def test_aud_009_data_table_keep_page_retains_active_page(self):
        """BUG AUD-009: DataTable.populate() asignaba incondicionalmente self._page = 1 en cada
        refresco, reseteando la navegación del operador al editar o borrar en páginas intermedias.

        VALIDACIÓN:
        DataTable.populate(rows, keep_page=True) debe retener la página activa si esta sigue
        siendo válida tras la actualización de los datos.
        """
        table = DataTable(headers=("ID", "Nombre"))

        # Crear 25 elementos (3 páginas en total con page_size=10)
        rows_initial = [(i, f"Item {i}") for i in range(1, 26)]
        table.populate(rows_initial, keep_page=False)
        self.assertEqual(table.page, 1)

        # Navegar a la página 2
        table.set_page(2)
        self.assertEqual(table.page, 2)

        # Actualizar datos con keep_page=True
        rows_updated = list(rows_initial)
        rows_updated[12] = (13, "Item 13 Modificado")
        table.populate(rows_updated, keep_page=True)

        # Debe permanecer exactamente en la página 2
        self.assertEqual(table.page, 2, "populate(keep_page=True) debe retener la página 2.")

        # Verificar que el comportamiento estándar sin keep_page sí resetea a 1
        table.populate(rows_updated, keep_page=False)
        self.assertEqual(table.page, 1, "populate(keep_page=False) debe reiniciar a la página 1.")

    # -------------------------------------------------------------------------
    # 6. TEST AUD-014 (Búsqueda insensible a diacríticos)
    # -------------------------------------------------------------------------
    def test_aud_014_crud_page_search_without_accents_finds_accented_text(self):
        """BUG AUD-014: La búsqueda en CrudPage usaba coincidencia literal 'in', impidiendo que
        términos sin tilde como 'electronica' encontraran registros con tilde como 'Electrónica'.

        VALIDACIÓN:
        La búsqueda de 'electronica' debe localizar 'Ingeniería Electrónica' exitosamente.
        """
        mgr = EntityManager()
        mgr.create_faculty(Faculty(faculty_id=1, name="Facultad de Ingeniería", dean="Decano", creation_date="2020", active=True))
        mgr.create_program(
            Program(
                program_id=101,
                name="Ingeniería de Sistemas",
                faculty_id=1,
                program_director="Dir Sistemas",
                level="Pregrado",
                modality="Presencial",
                active=True,
            )
        )
        mgr.create_program(
            Program(
                program_id=102,
                name="Ingeniería Electrónica",
                faculty_id=1,
                program_director="Dir Electrónica",
                level="Pregrado",
                modality="Presencial",
                active=True,
            )
        )
        mgr.create_program(
            Program(
                program_id=103,
                name="Administración de Empresas",
                faculty_id=1,
                program_director="Dir Administración",
                level="Pregrado",
                modality="Presencial",
                active=True,
            )
        )

        page = CrudPage(
            title="Programas",
            subtitle="Gestión de Programas",
            manager=mgr,
            collection_name="programs",
            model_cls=Program,
            id_field="program_id",
            fields=(
                ("program_id", "ID", "int"),
                ("name", "Nombre", "text"),
            ),
            columns=("ID", "Nombre"),
            row_builder=lambda p: (p.program_id, p.name),
            operation_name="program",
        )

        # 1. Búsqueda en minúsculas sin tilde: "electronica"
        page.filter_data("electronica")
        self.assertEqual(len(page._items), 1)
        self.assertEqual(page._items[0].program_id, 102)
        self.assertEqual(page._items[0].name, "Ingeniería Electrónica")

        # 2. Búsqueda en mayúsculas sin tilde: "ELECTRONICA"
        page.filter_data("ELECTRONICA")
        self.assertEqual(len(page._items), 1)
        self.assertEqual(page._items[0].program_id, 102)

        # 3. Búsqueda sin tilde de "administracion"
        page.filter_data("administracion")
        self.assertEqual(len(page._items), 1)
        self.assertEqual(page._items[0].program_id, 103)

        # 4. Búsqueda general de "ingenieria" encuentra ambos programas de ingeniería
        page.filter_data("ingenieria")
        self.assertEqual(len(page._items), 2)
        found_ids = {p.program_id for p in page._items}
        self.assertEqual(found_ids, {101, 102})


if __name__ == "__main__":
    unittest.main()
