"""Pruebas unitarias e integrales para verificar el dimensionamiento compacto de tablas (DataTable)
y la eliminación de espacios en blanco innecesarios en todas las secciones de NexoCampus.
"""

import os
import unittest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from services.entity_manager import EntityManager
from gui.components.data_table import DataTable
from gui.main_window import MainWindow
from gui.pages.reports_page import ReportsPage
from gui.pages.payroll_page import PayrollPage


class TestCompactTables(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.manager = EntityManager()
        self.window = MainWindow(self.manager)
        self.window._load_state()
        self.window.resize(1180, 720)
        self.window.show()
        QApplication.processEvents()

    def tearDown(self):
        self.window.close()

    def test_data_table_height_matches_row_count(self):
        """DataTable debe ajustar su altura exactamente al número de filas visibles."""
        table = DataTable(headers=("ID", "Nombre", "Valor"))
        data = [
            (1, "Elemento 1", "$ 100.00"),
            (2, "Elemento 2", "$ 200.00"),
            (3, "Elemento 3", "$ 300.00"),
            (4, "Elemento 4", "$ 400.00"),
            (5, "Elemento 5", "$ 500.00"),
        ]
        table.populate(data)
        QApplication.processEvents()

        header_h = table.horizontalHeader().height() or 33
        rows_h = sum(table.rowHeight(i) for i in range(5))
        expected_h = header_h + rows_h + table.frameWidth() * 2 + 4

        self.assertEqual(table.rowCount(), 5)
        self.assertEqual(table.height(), expected_h)
        self.assertLess(table.height(), 300)
        self.assertEqual(table.verticalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def test_data_table_resizes_on_filter(self):
        """En una vista CRUD, filtrar registros debe reducir la altura de la tabla en tiempo real."""
        self.window._navigate("Facultades")
        QApplication.processEvents()
        fac = self.window._pages["Facultades"]

        initial_rows = fac.table.rowCount()
        initial_h = fac.table.height()
        self.assertGreater(initial_rows, 1)

        # Filtrar a un único registro
        fac.search_bar.setText("Ingenieria")
        QApplication.processEvents()

        filtered_rows = fac.table.rowCount()
        filtered_h = fac.table.height()
        self.assertEqual(filtered_rows, 1)
        self.assertLess(filtered_h, initial_h)

        # Limpiar filtro
        fac.search_bar.setText("")
        QApplication.processEvents()
        self.assertEqual(fac.table.rowCount(), initial_rows)
        self.assertEqual(fac.table.height(), initial_h)

    def test_reports_tables_compact_heights(self):
        """Las tablas del Centro de Reportes deben tener alturas proporcionales a su cantidad de datos."""
        self.window._navigate("Reportes")
        QApplication.processEvents()
        reports: ReportsPage = self.window._pages["Reportes"]

        # 1. Pestaña Indicadores Globales (la reportada con exceso de blanco)
        reports.tabs.setCurrentIndex(3)
        QApplication.processEvents()
        metrics_tbl = reports.table_metrics
        self.assertGreater(metrics_tbl.rowCount(), 0)
        # 9 filas no deben superar 380px de altura (anteriormente 1171px)
        self.assertLessEqual(metrics_tbl.height(), 380)

        # 2. Pestaña Consolidado Salarial (típicamente ~4-5 categorías)
        reports.tabs.setCurrentIndex(2)
        QApplication.processEvents()
        salary_tbl = reports.table_salary
        self.assertLessEqual(salary_tbl.height(), 250)

        # 3. Pestaña Carga Docente
        reports.tabs.setCurrentIndex(1)
        QApplication.processEvents()
        workload_tbl = reports.table_workload
        self.assertLessEqual(workload_tbl.height(), 400)

        # 4. Pestaña EBRA
        reports.tabs.setCurrentIndex(0)
        QApplication.processEvents()
        ebra_tbl = reports.table_ebra
        self.assertLessEqual(ebra_tbl.height(), 400)

    def test_crud_pages_zero_vertical_scroll_when_fitting(self):
        """En resolución estándar (1180x720), las páginas CRUD con tablas compactas no deben forzar scroll vertical."""
        vbar = self.window.content_scroll_area.verticalScrollBar()
        crud_pages = [
            "Facultades",
            "Programas",
            "Cursos",
            "Estudiantes",
            "Profesores",
            "Administrativos",
            "Inscripciones",
        ]

        for page_name in crud_pages:
            with self.subTest(page=page_name):
                self.window._navigate(page_name)
                QApplication.processEvents()
                page = self.window._pages[page_name]
                # La tabla debe ser compacta
                self.assertLessEqual(page.table.height(), 400)
                # El contenedor no debe forzar scrollbar vertical
                self.assertEqual(
                    vbar.maximum(),
                    0,
                    f"Scrollbar vertical innecesario en '{page_name}': max={vbar.maximum()}"
                )

    def test_dashboard_preserves_scroll_when_needed(self):
        """El Dashboard debe conservar su altura completa y capacidad de desplazamiento vertical."""
        self.window._navigate("Dashboard")
        QApplication.processEvents()

        vbar = self.window.content_scroll_area.verticalScrollBar()
        self.assertGreater(self.window.stack.height(), 1000)
        self.assertGreater(vbar.maximum(), 0)

    def test_payroll_page_compact_table_and_history(self):
        """Nómina debe presentar tabla de empleados e historial con alturas ajustadas."""
        self.window._navigate("Nómina")
        QApplication.processEvents()
        payroll: PayrollPage = self.window._pages["Nómina"]

        # Tabla de empleados
        self.assertLessEqual(payroll.table.height(), 420)
        # Historial de períodos
        self.assertLessEqual(payroll.history_table.height(), 300)


if __name__ == "__main__":
    unittest.main()
