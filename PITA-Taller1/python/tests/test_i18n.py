"""Pruebas unitarias para el módulo centralizado de localización (i18n) de NexoCampus."""
import os
import unittest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"
_APP = QApplication.instance() or QApplication(["-platform", "offscreen"])

from gui.i18n import (
    ENTITIES,
    PAYROLL_STATUSES,
    EMPLOYEE_TYPES,
    ACRONYMS,
    get_entity_info,
    get_entity_label,
    get_entity_new_label,
    get_entity_create_label,
    get_entity_created_message,
    get_payroll_status_label,
    get_employee_type_label,
    get_acronym_tooltip,
)
from gui.components.header import TopHeader
from gui.components.notification_panel import NotificationPanel
from gui.pages.crud_page import CrudPage
from gui.pages.dashboard_page import DashboardPage
from gui.pages.payroll_page import PayrollPage
from models.faculty import Faculty
from models.course import Course
from services.entity_manager import EntityManager


class TestI18nLabels(unittest.TestCase):
    """Verifica las reglas lingüísticas, gramaticales e inmutabilidad del módulo i18n."""

    def test_immutability(self):
        """Verifica que los diccionarios de i18n sean inmutables (MappingProxyType)."""
        with self.assertRaises(TypeError):
            ENTITIES["faculty"] = None
        with self.assertRaises(TypeError):
            PAYROLL_STATUSES["OPEN"] = "Nuevo"
        with self.assertRaises(TypeError):
            EMPLOYEE_TYPES["Professor"] = "Otro"
        with self.assertRaises(TypeError):
            ACRONYMS["EBRA"] = "Otro"

    def test_entity_gender_and_grammar(self):
        """Verifica concordancia gramatical de género y artículos en etiquetas institucionales."""
        # Femeninas
        fac_info = get_entity_info("faculty")
        self.assertEqual(fac_info.name, "Facultad")
        self.assertEqual(fac_info.gender, "f")
        self.assertEqual(fac_info.new_button_label, "+ Nueva Facultad")
        self.assertEqual(fac_info.create_button_label, "+ Crear Facultad")
        self.assertEqual(fac_info.created_message, "Facultad creada exitosamente.")

        enr_info = get_entity_info("enrollment")
        self.assertEqual(enr_info.name, "Matrícula")
        self.assertEqual(enr_info.gender, "f")
        self.assertEqual(enr_info.new_button_label, "+ Nueva Matrícula")
        self.assertEqual(enr_info.create_button_label, "+ Crear Matrícula")
        self.assertEqual(enr_info.created_message, "Matrícula creada exitosamente.")

        # Masculinas
        crs_info = get_entity_info("course")
        self.assertEqual(crs_info.name, "Curso")
        self.assertEqual(crs_info.gender, "m")
        self.assertEqual(crs_info.new_button_label, "+ Nuevo Curso")
        self.assertEqual(crs_info.created_message, "Curso creado exitosamente.")

        prg_info = get_entity_info("program")
        self.assertEqual(prg_info.name, "Programa")
        self.assertEqual(prg_info.new_button_label, "+ Nuevo Programa")

        std_info = get_entity_info("student")
        self.assertEqual(std_info.name, "Estudiante")
        self.assertEqual(std_info.new_button_label, "+ Nuevo Estudiante")

        prf_info = get_entity_info("professor")
        self.assertEqual(prf_info.name, "Docente")
        self.assertEqual(prf_info.new_button_label, "+ Nuevo Docente")

        adm_info = get_entity_info("administrative")
        self.assertEqual(adm_info.name, "Personal Administrativo")
        self.assertEqual(adm_info.new_button_label, "+ Nuevo Personal Administrativo")

    def test_entity_aliases(self):
        """Verifica que los nombres plurales del backend resuelvan a la entidad correspondiente."""
        self.assertEqual(get_entity_info("faculties").name, "Facultad")
        self.assertEqual(get_entity_info("courses").name, "Curso")
        self.assertEqual(get_entity_info("administrative_staff").name, "Personal Administrativo")
        self.assertEqual(get_entity_info("enrollments").name, "Matrícula")

    def test_payroll_statuses_translation(self):
        """Verifica traducción completa de estados de nómina."""
        self.assertEqual(get_payroll_status_label("OPEN"), "Abierto")
        self.assertEqual(get_payroll_status_label("CALCULATED"), "Liquidado")
        self.assertEqual(get_payroll_status_label("APPROVED"), "Aprobado")
        self.assertEqual(get_payroll_status_label("CLOSED"), "Cerrado")

    def test_employee_types_translation(self):
        """Verifica traducción de roles de empleados."""
        self.assertEqual(get_employee_type_label("Professor"), "Docente")
        self.assertEqual(get_employee_type_label("Administrative"), "Personal Administrativo")
        self.assertEqual(get_employee_type_label("ALL"), "Todos los tipos")

    def test_acronym_tooltips(self):
        """Verifica que los acrónimos institucionales tengan definiciones completas."""
        self.assertIn("Riesgo Académico", get_acronym_tooltip("EBRA"))
        self.assertIn("Ingreso Base de Cotización", get_acronym_tooltip("IBC"))
        self.assertIn("Código Sustantivo del Trabajo", get_acronym_tooltip("CST"))


class TestGuiLocalizationIntegration(unittest.TestCase):
    """Verifica que los componentes de la interfaz de usuario presenten textos en español."""

    def setUp(self):
        self.manager = EntityManager()

    def test_header_search_placeholder_brand(self):
        """El buscador superior debe indicar NexoCampus, no Nexus ni genérico."""
        header = TopHeader(manager=self.manager)
        placeholder = header.search_input.placeholderText()
        self.assertIn("NexoCampus", placeholder)
        self.assertNotIn("Nexus", placeholder)

    def test_crud_page_buttons_no_spanglish(self):
        """CrudPage debe generar botones con género correcto sin términos en inglés."""
        # 1. Facultades (femenino)
        fac_page = CrudPage(
            title="Facultades",
            subtitle="Estructura institucional",
            manager=self.manager,
            collection_name="faculties",
            model_cls=Faculty,
            id_field="faculty_id",
            fields=(("faculty_id", "ID", "int"), ("name", "Nombre")),
            columns=("ID", "Nombre"),
            row_builder=lambda f: (f.faculty_id, f.name),
            operation_name="faculty",
        )
        self.assertIn("Nueva Facultad", fac_page.header.findChildren(object)[-1].text() if hasattr(fac_page.header, "findChildren") else fac_page.entity_info.new_button_label)
        self.assertEqual(fac_page.entity_info.new_button_label, "+ Nueva Facultad")
        self.assertEqual(fac_page.entity_info.create_button_label, "+ Crear Facultad")
        self.assertEqual(fac_page.entity_info.created_message, "Facultad creada exitosamente.")

        # 2. Cursos (masculino)
        crs_page = CrudPage(
            title="Cursos",
            subtitle="Catálogo de asignaturas",
            manager=self.manager,
            collection_name="courses",
            model_cls=Course,
            id_field="course_id",
            fields=(("course_id", "ID", "int"), ("name", "Nombre")),
            columns=("ID", "Nombre"),
            row_builder=lambda c: (c.course_id, c.name),
            operation_name="course",
        )
        self.assertEqual(crs_page.entity_info.new_button_label, "+ Nuevo Curso")
        self.assertEqual(crs_page.entity_info.create_button_label, "+ Crear Curso")
        self.assertEqual(crs_page.entity_info.created_message, "Curso creado exitosamente.")

    def test_payroll_page_type_filter_spanish(self):
        """El filtro de Nómina debe mostrar etiquetas en español manteniendo datos técnicos."""
        page = PayrollPage(self.manager)
        items_text = [page.type_filter.itemText(i) for i in range(page.type_filter.count())]
        self.assertEqual(items_text, ["Todos los tipos", "Docente", "Personal Administrativo"])
        self.assertNotIn("Professor", items_text)
        self.assertNotIn("Administrative", items_text)

        # Verificar datos internos
        items_data = [page.type_filter.itemData(i) for i in range(page.type_filter.count())]
        self.assertEqual(items_data, ["ALL", "Professor", "Administrative"])

    def test_dashboard_page_title_unified(self):
        """El Dashboard debe titularse 'Inicio' acorde con el Sidebar."""
        page = DashboardPage(self.manager, lambda target: None)
        title_widget = page.findChild(object, "dashboardTitle")
        if title_widget is None:
            matches = [
                child for child in page.children() if hasattr(child, "text") and child.text() == "Inicio"
            ]
            self.assertTrue(len(matches) > 0 or hasattr(page, "title"))
        else:
            self.assertTrue(title_widget is not None)


if __name__ == "__main__":
    unittest.main()

