"""Pruebas unitarias para la retención y ajuste de paginación en DataTable y CrudPage."""

import os
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QMessageBox

from models.faculty import Faculty
from services.entity_manager import EntityManager
from gui.components.data_table import DataTable
from gui.pages.crud_page import CrudPage


class TestDataTablePagination(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_populate_default_resets_to_page_1(self):
        """Verifica que populate() sin keep_page reinicia siempre a la página 1."""
        table = DataTable(headers=("ID", "Nombre"))
        # 25 filas -> 3 páginas (10 por página)
        rows = [(i, f"Item {i}") for i in range(25)]
        table.populate(rows)
        self.assertEqual(table.page, 1)

        # Cambiamos a la página 2
        table.set_page(2)
        self.assertEqual(table.page, 2)

        # Repoblamos sin keep_page
        table.populate(rows)
        self.assertEqual(table.page, 1)

    def test_populate_keep_page_true_preserves_current_page(self):
        """Verifica que populate(..., keep_page=True) retiene la página actual si es válida."""
        table = DataTable(headers=("ID", "Nombre"))
        rows = [(i, f"Item {i}") for i in range(25)]
        table.populate(rows)

        table.set_page(2)
        self.assertEqual(table.page, 2)

        # Modificamos una fila y repoblamos con keep_page=True
        rows[15] = (15, "Item 15 Modificado")
        table.populate(rows, keep_page=True)
        self.assertEqual(table.page, 2)
        self.assertEqual(table.page_count, 3)

    def test_populate_keep_page_true_adjusts_if_page_out_of_range(self):
        """Verifica que si la página actual excede el nuevo total, se ajusta a la página más cercana."""
        table = DataTable(headers=("ID", "Nombre"))
        # 21 filas -> 3 páginas (página 3 tiene solo 1 item)
        rows = [(i, f"Item {i}") for i in range(21)]
        table.populate(rows)

        table.set_page(3)
        self.assertEqual(table.page, 3)

        # Se elimina el item 21, quedando 20 filas (2 páginas en total)
        rows = rows[:20]
        table.populate(rows, keep_page=True)

        # Debe haberse ajustado automáticamente a la página 2
        self.assertEqual(table.page, 2)
        self.assertEqual(table.page_count, 2)

    def test_populate_empty_list_sets_page_1(self):
        """Verifica que si la lista queda vacía, la página se fija en 1."""
        table = DataTable(headers=("ID", "Nombre"))
        rows = [(i, f"Item {i}") for i in range(15)]
        table.populate(rows)
        table.set_page(2)

        table.populate([], keep_page=True)
        self.assertEqual(table.page, 1)
        self.assertEqual(table.page_count, 1)


class TestCrudPagePaginationContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.manager = EntityManager()
        # Creamos 25 facultades para tener 3 páginas
        for i in range(1, 26):
            self.manager.create_faculty(Faculty(i, f"Facultad {i}", f"Decano {i}"))

        self.page = CrudPage(
            title="Facultades",
            subtitle="Prueba de paginación",
            manager=self.manager,
            collection_name="faculties",
            model_cls=Faculty,
            id_field="faculty_id",
            fields=(
                ("faculty_id", "ID", "int"),
                ("name", "Nombre", "text"),
                ("dean", "Decano", "text"),
            ),
            columns=("ID", "Nombre", "Decano"),
            row_builder=lambda f: (f.faculty_id, f.name, f.dean),
            operation_name="faculty",
        )

    def test_crud_refresh_sidebar_navigation_resets_to_page_1(self):
        """Navegación desde sidebar llama refresh() por defecto y reinicia a la página 1."""
        self.page.table.set_page(2)
        self.assertEqual(self.page.table.page, 2)

        # refresh() por defecto simula la navegación desde MainWindow
        self.page.refresh()
        self.assertEqual(self.page.table.page, 1)

    def test_crud_refresh_keep_page_preserves_page(self):
        """refresh(keep_page=True) mantiene la página actual."""
        self.page.table.set_page(2)
        self.assertEqual(self.page.table.page, 2)

        self.page.refresh(keep_page=True)
        self.assertEqual(self.page.table.page, 2)

    def test_crud_after_change_edit_preserves_page(self):
        """_after_change con keep_page=True retiene la página tras editar."""
        self.page.table.set_page(2)
        self.assertEqual(self.page.table.page, 2)

        with patch.object(QMessageBox, "information"):
            self.page._after_change("Registro editado", keep_page=True)

        self.assertEqual(self.page.table.page, 2)

    def test_crud_after_change_delete_adjusts_page_when_last_item_deleted(self):
        """Eliminar el único registro de la última página ajusta a la página anterior."""
        # Reducir a 21 elementos para que página 3 tenga solo 1
        while len(list(self.manager.faculties)) > 21:
            last = list(self.manager.faculties)[-1]
            self.manager.delete_faculty(last.faculty_id)

        self.page.refresh()
        self.page.table.set_page(3)
        self.assertEqual(self.page.table.page, 3)

        # Eliminar el item 21
        last = list(self.manager.faculties)[-1]
        self.manager.delete_faculty(last.faculty_id)

        with patch.object(QMessageBox, "information"):
            self.page._after_change("Registro eliminado", keep_page=True)

        # Ahora solo hay 20 registros, debe haberse ajustado a la página 2
        self.assertEqual(self.page.table.page, 2)


if __name__ == "__main__":
    unittest.main()

