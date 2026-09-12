"""Pruebas unitarias para las mejoras del componente DataTable:
- Columna Acciones fija (85px) y columna principal en modo Stretch
- Alineación correcta de datos numéricos, monetarios, IDs y texto
- Ordenamiento interactivo por clic en cabeceras sobre el dataset completo
- Tooltips automáticos en cada celda
- Sincronización de payloads y botones de acción tras ordenar
"""

import os
import unittest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHeaderView

from gui.components.data_table import DataTable, _sort_key


class TestDataTableEnhancements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_actions_column_fixed_width_and_stretch_column(self):
        """Verifica que la columna 'Acciones' tenga 85px fijos y la columna principal sea Stretch."""
        headers = ("ID", "Nombre", "Departamento", "Salario")
        table = DataTable(headers=headers, stretch_column="Nombre")
        table.set_row_actions(True)

        header = table.horizontalHeader()
        self.assertFalse(header.stretchLastSection())

        # Columna principal "Nombre" (índice 1) debe tener modo Stretch
        self.assertEqual(header.sectionResizeMode(1), QHeaderView.ResizeMode.Stretch)

        # Columna "Acciones" (última columna, índice 4) debe tener modo Fixed y ancho 85
        actions_col_idx = table.columnCount() - 1
        self.assertEqual(header.sectionResizeMode(actions_col_idx), QHeaderView.ResizeMode.Fixed)
        self.assertEqual(table.columnWidth(actions_col_idx), 85)

    def test_stretch_column_resolution_by_name_and_index(self):
        """Verifica la resolución de columna de estiramiento por nombre o por índice numérico."""
        headers = ("ID", "Razón Social", "NIT", "Ciudad")
        table1 = DataTable(headers=headers, stretch_column="Razón Social")
        self.assertEqual(table1._stretch_col_idx, 1)

        table2 = DataTable(headers=headers, stretch_column=2)
        self.assertEqual(table2._stretch_col_idx, 2)

        # Fallback a coincidencia de palabras clave si no se especifica
        table3 = DataTable(headers=("ID", "Nombre del Estudiante", "Código"))
        self.assertEqual(table3._stretch_col_idx, 1)

    def test_text_alignment_with_explicit_column_types(self):
        """Verifica alineación contable y semántica usando column_types explícito."""
        headers = ("ID", "Nombre", "Salario", "Fecha", "Activo")
        column_types = ("id", "text", "money", "date", "status")
        table = DataTable(headers=headers, column_types=column_types)

        rows = [
            (101, "Carlos Pérez", "$ 3,500,000.00", "2024-01-15", "Activo"),
        ]
        table.populate(rows)

        # ID -> Center
        item_id = table.item(0, 0)
        self.assertEqual(item_id.textAlignment(), Qt.AlignmentFlag.AlignCenter)

        # Nombre -> Left + VCenter
        item_nombre = table.item(0, 1)
        self.assertEqual(item_nombre.textAlignment(), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Salario -> Right + VCenter
        item_salario = table.item(0, 2)
        self.assertEqual(item_salario.textAlignment(), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Fecha -> Center
        item_fecha = table.item(0, 3)
        self.assertEqual(item_fecha.textAlignment(), Qt.AlignmentFlag.AlignCenter)

        # Estado -> Center
        item_estado = table.item(0, 4)
        self.assertEqual(item_estado.textAlignment(), Qt.AlignmentFlag.AlignCenter)

    def test_text_alignment_heuristics_auto_detection(self):
        """Verifica que sin column_types, los números y monedas se alinean a la derecha y los IDs al centro."""
        headers = ("ID", "Concepto", "Importe", "Porcentaje")
        table = DataTable(headers=headers)

        rows = [
            (50, "Bono de Desempeño", "$ 450.00", "15%"),
        ]
        table.populate(rows)

        # ID -> Center por nombre de cabecera
        self.assertEqual(table.item(0, 0).textAlignment(), Qt.AlignmentFlag.AlignCenter)
        # Concepto -> Left
        self.assertEqual(table.item(0, 1).textAlignment(), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # Importe -> Right por prefijo '$' y palabra clave en cabecera
        self.assertEqual(table.item(0, 2).textAlignment(), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        # Porcentaje -> Right por sufijo '%'
        self.assertEqual(table.item(0, 3).textAlignment(), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def test_tooltips_on_cells(self):
        """Verifica que cada celda cuente con un tooltip con su contenido para evitar truncamiento."""
        headers = ("ID", "Descripción")
        table = DataTable(headers=headers)
        long_text = "Texto muy extenso que podría sobrepasar el ancho visual de la columna"
        table.populate([(1, long_text)])

        self.assertEqual(table.item(0, 0).toolTip(), "1")
        self.assertEqual(table.item(0, 1).toolTip(), long_text)

    def test_interactive_sorting_over_entire_dataset(self):
        """Verifica que hacer clic en el encabezado ordene todo el conjunto de datos, no solo la página."""
        headers = ("ID", "Nombre", "Salario")
        table = DataTable(headers=headers)

        # Crear 25 filas desordenadas (3 páginas con page_size=10)
        import random
        random.seed(42)
        salaries = [random.randint(1000, 9999) for _ in range(25)]
        rows = [(i, f"Persona {i}", f"$ {sal:,.2f}") for i, sal in enumerate(salaries)]
        table.populate(rows)

        # Clic en cabecera de Salario (columna 2) -> Orden ascendente
        table._on_header_clicked(2)
        self.assertEqual(table._sort_column, 2)
        self.assertEqual(table._sort_order, Qt.SortOrder.AscendingOrder)

        # La primera fila de la página 1 debe tener el salario mínimo
        first_row_salary = table.item(0, 2).text()
        min_salary = f"$ {min(salaries):,.2f}"
        self.assertEqual(first_row_salary, min_salary)

        # Segundo clic en cabecera de Salario -> Orden descendente
        table._on_header_clicked(2)
        self.assertEqual(table._sort_order, Qt.SortOrder.DescendingOrder)

        # La primera fila de la página 1 debe tener el salario máximo
        first_row_salary_desc = table.item(0, 2).text()
        max_salary = f"$ {max(salaries):,.2f}"
        self.assertEqual(first_row_salary_desc, max_salary)

    def test_sort_key_robustness(self):
        """Prueba exhaustiva de la función auxiliar _sort_key para tipos heterogéneos."""
        # Comparación numérica directa
        self.assertLess(_sort_key(10), _sort_key(20))
        self.assertLess(_sort_key(5.5), _sort_key(5.6))

        # Comparación monetaria con formato
        self.assertLess(_sort_key("$ 150.00"), _sort_key("$ 1,200.00"))
        self.assertEqual(_sort_key("$ 1,000.00"), _sort_key(1000.0))

        # Comparación de porcentajes
        self.assertLess(_sort_key("5%"), _sort_key("20%"))

        # Comparación textual con tildes (normalización unicode insensible a tildes)
        self.assertEqual(_sort_key("Álvarez")[2], _sort_key("alvarez")[2])
        self.assertLess(_sort_key("Álvarez"), _sort_key("Zapata"))

        # Valores nulos o vacíos van al principio (o se manejan limpiamente sin excepción)
        self.assertLess(_sort_key(None), _sort_key(1))
        self.assertLess(_sort_key(""), _sort_key("A"))

    def test_actions_column_does_not_trigger_sorting(self):
        """Verifica que hacer clic en el encabezado de 'Acciones' no altere el ordenamiento."""
        headers = ("ID", "Nombre")
        table = DataTable(headers=headers)
        table.set_row_actions(True)
        rows = [(2, "B"), (1, "A")]
        table.populate(rows)

        actions_idx = table.columnCount() - 1
        table._on_header_clicked(actions_idx)
        self.assertIsNone(table._sort_column)

    def test_payloads_synchronization_when_sorting(self):
        """Verifica que los objetos de dominio asociados permanezcan sincronizados con las filas al ordenar."""
        headers = ("ID", "Nombre")
        table = DataTable(headers=headers)
        
        class MockEntity:
            def __init__(self, uid, name):
                self.uid = uid
                self.name = name

        entities = [MockEntity(3, "Carlos"), MockEntity(1, "Ana"), MockEntity(2, "Beto")]
        rows = [(e.uid, e.name) for e in entities]

        table.populate(rows, payloads=entities)

        # Ordenar por ID (columna 0)
        table._on_header_clicked(0)
        
        # Debe haber ordenado Ana (1), Beto (2), Carlos (3)
        self.assertEqual(table.item(0, 1).text(), "Ana")
        self.assertEqual(table.get_payload(0).name, "Ana")
        self.assertEqual(table.item(1, 1).text(), "Beto")
        self.assertEqual(table.get_payload(1).name, "Beto")
        self.assertEqual(table.item(2, 1).text(), "Carlos")
        self.assertEqual(table.get_payload(2).name, "Carlos")

        # Verificar current_source_payload
        table.selectRow(1)
        self.assertEqual(table.current_source_payload().name, "Beto")


if __name__ == "__main__":
    unittest.main()

