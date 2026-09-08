"""Dashboard financiero basado exclusivamente en PayrollRun."""
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from services.payroll_dashboard import PayrollFinancialDashboard


class PayrollDashboardDialog(QDialog):
    """Vista de indicadores oficiales de un período liquidado."""

    METRICS = (
        ("total_employees", "Total empleados"),
        ("total_professors", "Total profesores"),
        ("total_administratives", "Total administrativos"),
        ("base_salary", "Salario básico total"),
        ("gross_salary", "Total devengado"),
        ("total_employee_deductions", "Total deducciones"),
        ("ibc", "Total IBC"),
        ("total_employee_health", "Salud trabajador"),
        ("total_employee_pension", "Pensión trabajador"),
        ("total_benefits", "Total prestaciones"),
        ("total_employer_pension", "Pensión patronal"),
        ("total_employer_health", "Salud patronal"),
        ("total_arl", "ARL"),
        ("total_compensation_fund", "Caja"),
        ("total_sena", "SENA"),
        ("total_icbf", "ICBF"),
        ("total_employer_contributions", "Aportes patronales"),
        ("total_employer_cost", "Costo total empleador"),
        ("total_net_paid", "Total neto pagado"),
    )

    DISTRIBUTIONS = (
        ("professor_type_distribution", "Tipo de profesor"),
        ("faculty_distribution", "Facultad"),
        ("category_distribution", "Categoría"),
        ("linkage_distribution", "Tipo de vinculación"),
    )

    def __init__(self, cycle, employees, faculties, parent=None, administrative_staff=()):
        super().__init__(parent)
        self.cycle = cycle
        self.employees = list(employees or ()) + list(administrative_staff or ())
        self.faculties = faculties
        self.metric_table = QTableWidget(0, 2)
        self.metric_table.setHorizontalHeaderLabels(("Indicador", "Valor"))
        self.metric_table.horizontalHeader().setStretchLastSection(True)
        self.distribution_tables = {}
        self._build_ui()
        self._load_periods()

    def _build_ui(self):
        self.setWindowTitle("Dashboard financiero de nómina")
        self.resize(980, 720)
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("Dashboard financiero de nómina"))
        self.period_selector = QComboBox()
        self.period_selector.currentIndexChanged.connect(self.refresh)
        refresh_button = QPushButton("Actualizar")
        refresh_button.clicked.connect(self.refresh)
        header.addWidget(self.period_selector)
        header.addWidget(refresh_button)
        layout.addLayout(header)
        layout.addWidget(self.metric_table)

        grid = QGridLayout()
        for index, (key, title) in enumerate(self.DISTRIBUTIONS):
            table = QTableWidget(0, 2)
            table.setHorizontalHeaderLabels((title, "Empleados"))
            table.horizontalHeader().setStretchLastSection(True)
            self.distribution_tables[key] = table
            grid.addWidget(QLabel(title), index // 2, (index % 2) * 2)
            grid.addWidget(table, index // 2, (index % 2) * 2 + 1)
        layout.addLayout(grid)

    def _load_periods(self):
        self.period_selector.clear()
        for period in self.cycle.periods:
            run = next(
                (item for item in reversed(self.cycle.runs) if item.period_id == period.period_id),
                None,
            )
            if run is not None:
                self.period_selector.addItem(
                    f"{period.year}-{period.month:02d} · {run.status.value}", period.period_id
                )
        self.refresh()

    @staticmethod
    def _money(value):
        return f"$ {int(value):,}".replace(",", ".")

    def refresh(self):
        period_id = self.period_selector.currentData()
        run = next(
            (item for item in reversed(self.cycle.runs) if item.period_id == period_id),
            None,
        )
        if run is None:
            self.metric_table.setRowCount(0)
            for table in self.distribution_tables.values():
                table.setRowCount(0)
            return
        data = PayrollFinancialDashboard(run, self.employees, self.faculties).snapshot()
        self.metric_table.setRowCount(len(self.METRICS))
        for row, (key, title) in enumerate(self.METRICS):
            self.metric_table.setItem(row, 0, QTableWidgetItem(title))
            value = data[key]
            self.metric_table.setItem(row, 1, QTableWidgetItem(
                str(value) if key in {"total_employees", "total_professors", "total_administratives"}
                else self._money(value)
            ))
        for key, table in self.distribution_tables.items():
            values = data[key]
            table.setRowCount(len(values))
            for row, (label, count) in enumerate(values.items()):
                table.setItem(row, 0, QTableWidgetItem(label))
                table.setItem(row, 1, QTableWidgetItem(str(count)))
