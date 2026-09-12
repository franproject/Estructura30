"""Pruebas unitarias para búsqueda insensible a diacríticos y paginación compacta con elipsis."""

import os
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from models.faculty import Faculty
from services.entity_manager import EntityManager
from gui.components.data_table import DataTable
from gui.components.pagination_bar import PaginationBar, calculate_page_range
from gui.pages.crud_page import CrudPage, _normalize_text


class TestDiacriticSearch(unittest.TestCase):
    """Pruebas para la normalización Unicode y búsqueda insensible a acentos/diacríticos."""

    def test_normalize_text_removes_accents(self):
        """Verifica la eliminación de diacríticos y conversión a minúsculas."""
        self.assertEqual(_normalize_text("Administración"), "administracion")
        self.assertEqual(_normalize_text("Electrónica"), "electronica")
        self.assertEqual(_normalize_text("Ingeniería de Sistemas"), "ingenieria de sistemas")
        self.assertEqual(_normalize_text("Bogotá, D.C."), "bogota, d.c.")
        self.assertEqual(_normalize_text("ÁÉÍÓÚ ñ áéíóú"), "aeiou n aeiou")
        self.assertEqual(_normalize_text(""), "")
        self.assertEqual(_normalize_text(None), "")

    def test_crud_page_search_with_diacritics(self):
        """Verifica que CrudPage.filter_data encuentre registros independientemente de tildes o mayúsculas."""
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        app = QApplication.instance() or QApplication([])

        manager = EntityManager()
        manager.create_faculty(Faculty(1, "Facultad de Ingeniería", "Decano Uno"))
        manager.create_faculty(Faculty(2, "Facultad de Administración", "Decano Dos"))
        manager.create_faculty(Faculty(3, "Facultad de Ciencias y Electrónica", "Decano Tres"))

        page = CrudPage(
            title="Facultades",
            subtitle="Test",
            manager=manager,
            collection_name="faculties",
            model_cls=Faculty,
            id_field="faculty_id",
            fields=(("faculty_id", "ID", "int"), ("name", "Nombre", "text")),
            columns=("ID", "Nombre"),
            row_builder=lambda f: (f.faculty_id, f.name),
            operation_name="faculty",
        )

        # 1. Buscar "administracion" (sin tilde) debe encontrar "Facultad de Administración"
        page.filter_data("administracion")
        self.assertEqual(len(page._items), 1)
        self.assertEqual(page._items[0].faculty_id, 2)

        # 2. Buscar "ADMINISTRACIÓN" (con tilde y mayúscula)
        page.filter_data("ADMINISTRACIÓN")
        self.assertEqual(len(page._items), 1)
        self.assertEqual(page._items[0].faculty_id, 2)

        # 3. Buscar "electronica" (sin tilde) debe encontrar "Facultad de Ciencias y Electrónica"
        page.filter_data("electronica")
        self.assertEqual(len(page._items), 1)
        self.assertEqual(page._items[0].faculty_id, 3)

        # 4. Buscar "ingenieria" (sin tilde) debe encontrar "Facultad de Ingeniería"
        page.filter_data("ingenieria")
        self.assertEqual(len(page._items), 1)
        self.assertEqual(page._items[0].faculty_id, 1)

        # 5. Buscar "sistemas" no está en ninguna facultad
        page.filter_data("sistemas")
        self.assertEqual(len(page._items), 0)


class TestPaginationLogic(unittest.TestCase):
    """Pruebas para el algoritmo de cálculo de rango de páginas con elipsis."""

    def test_calculate_page_range_small_total(self):
        """Con <= 7 páginas, muestra todas las páginas sin elipsis."""
        self.assertEqual(calculate_page_range(1, 5), [1, 2, 3, 4, 5])
        self.assertEqual(calculate_page_range(3, 7), [1, 2, 3, 4, 5, 6, 7])

    def test_calculate_page_range_near_start(self):
        """Cerca del inicio (<= 4), muestra primeras páginas, elipsis y última página."""
        r1 = calculate_page_range(1, 20)
        self.assertEqual(r1, [1, 2, 3, 4, 5, "...", 20])
        # Verificar que la cantidad de números no exceda 7
        numeric_count = sum(1 for x in r1 if isinstance(x, int))
        self.assertLessEqual(numeric_count, 7)

        r3 = calculate_page_range(3, 20)
        self.assertEqual(r3, [1, 2, 3, 4, 5, "...", 20])

        r4 = calculate_page_range(4, 20)
        self.assertEqual(r4, [1, 2, 3, 4, 5, "...", 20])

    def test_calculate_page_range_near_end(self):
        """Cerca del final (>= total - 3), muestra primera página, elipsis y últimas páginas."""
        r18 = calculate_page_range(18, 20)
        self.assertEqual(r18, [1, "...", 16, 17, 18, 19, 20])
        numeric_count = sum(1 for x in r18 if isinstance(x, int))
        self.assertLessEqual(numeric_count, 7)

        r20 = calculate_page_range(20, 20)
        self.assertEqual(r20, [1, "...", 16, 17, 18, 19, 20])

    def test_calculate_page_range_middle(self):
        """En el medio, muestra primera página, elipsis, páginas vecinas, elipsis y última página."""
        r10 = calculate_page_range(10, 20)
        self.assertEqual(r10, [1, "...", 9, 10, 11, "...", 20])
        numeric_count = sum(1 for x in r10 if isinstance(x, int))
        self.assertLessEqual(numeric_count, 7)

    def test_calculate_page_range_never_exceeds_max_numeric_with_100_pages(self):
        """Con 100 páginas (1000 registros), nunca excede el máximo de botones numéricos."""
        for p in range(1, 101):
            r = calculate_page_range(p, 100, max_numeric=7)
            numeric_count = sum(1 for x in r if isinstance(x, int))
            self.assertLessEqual(numeric_count, 7, f"Falló en página {p}: {r}")
            self.assertIn(1, r)
            self.assertIn(100, r)
            self.assertIn(p, r)


class TestPaginationBarComponent(unittest.TestCase):
    """Pruebas para el componente visual PaginationBar."""

    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_pagination_bar_buttons_with_1000_records(self):
        """Con 1000 registros (100 páginas), no genera 100 botones sino un conjunto compacto."""
        bar = PaginationBar(max_numeric_buttons=7)
        bar.update_pagination(current_page=1, total_pages=100, total_rows=1000, page_size=10)

        # Contar botones numéricos en el layout de botones
        buttons = []
        for i in range(bar.page_buttons.count()):
            w = bar.page_buttons.itemAt(i).widget()
            if isinstance(w, QPushButton):
                buttons.append(w.text())

        # No debe haber 100 botones; debe haber como máximo 7 botones numéricos
        self.assertLessEqual(len(buttons), 7)
        self.assertEqual(buttons, ["1", "2", "3", "4", "5", "100"])

        # En página 1: Anterior debe estar deshabilitado, Siguiente habilitado
        self.assertFalse(bar.btn_prev.isEnabled())
        self.assertTrue(bar.btn_next.isEnabled())

    def test_pagination_bar_prev_next_actions(self):
        """Verifica que Anterior y Siguiente emitan la señal y cambien la página correctamente."""
        table = DataTable(headers=("ID", "Nombre"))
        rows = [(i, f"Item {i}") for i in range(100)]  # 10 páginas
        table.populate(rows)

        bar = PaginationBar()
        bar.connect_table(table)
        bar.update_pagination(current_page=1, total_pages=10, total_rows=100, page_size=10)

        # En página 1, Anterior deshabilitado
        self.assertFalse(bar.btn_prev.isEnabled())
        self.assertTrue(bar.btn_next.isEnabled())

        # Clic en Siguiente -> pasa a página 2
        bar.btn_next.click()
        self.assertEqual(table.page, 2)
        self.assertEqual(bar.current_page, 2)
        self.assertTrue(bar.btn_prev.isEnabled())
        self.assertTrue(bar.btn_next.isEnabled())

        # Clic en Anterior -> vuelve a página 1
        bar.btn_prev.click()
        self.assertEqual(table.page, 1)
        self.assertEqual(bar.current_page, 1)
        self.assertFalse(bar.btn_prev.isEnabled())

        # Navegar a la última página (10)
        table.set_page(10)
        self.assertEqual(bar.current_page, 10)
        self.assertTrue(bar.btn_prev.isEnabled())
        self.assertFalse(bar.btn_next.isEnabled())

    def test_crud_page_integration_with_many_records(self):
        """Verifica que CrudPage maneje 500 registros con paginación compacta y funcional."""
        manager = EntityManager()
        for i in range(1, 501):
            manager.create_faculty(Faculty(i, f"Facultad {i}", f"Decano {i}"))

        page = CrudPage(
            title="Facultades",
            subtitle="Test 500",
            manager=manager,
            collection_name="faculties",
            model_cls=Faculty,
            id_field="faculty_id",
            fields=(("faculty_id", "ID", "int"), ("name", "Nombre", "text")),
            columns=("ID", "Nombre"),
            row_builder=lambda f: (f.faculty_id, f.name),
            operation_name="faculty",
        )

        # Total 500 registros -> 50 páginas
        self.assertEqual(page.table.total_rows, 500)
        self.assertEqual(page.table.page_count, 50)

        # Los botones visibles de la barra no deben desbordar
        buttons = [
            page.page_buttons.itemAt(i).widget().text()
            for i in range(page.page_buttons.count())
            if isinstance(page.page_buttons.itemAt(i).widget(), QPushButton)
        ]
        self.assertLessEqual(len(buttons), 7)

        # Usar botón siguiente
        page.pagination.btn_next.click()
        self.assertEqual(page.table.page, 2)


if __name__ == "__main__":
    unittest.main()

