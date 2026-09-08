"""Página de consulta e informe de Nómina académica."""
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..components.data_table import DataTable
from ..components.page_header import PageHeader


class PayrollPage(QWidget):
    """Generación e inspección del reporte de Nómina académica."""

    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = PageHeader(
            title="Nómina Académica",
            subtitle="Cálculo de compensaciones para personal docente y administrativo",
        )
        layout.addWidget(header)

        # Resumen general
        summary_layout = QHBoxLayout()
        self.lbl_total = QLabel("Total a liquidar: $0.00")
        self.lbl_total.setStyleSheet("font-size: 16px; font-weight: 800; color: #16A34A;")

        btn_refresh = QPushButton("↻ Recalcular")
        btn_refresh.setObjectName("secondaryButton")
        btn_refresh.clicked.connect(self.refresh)

        summary_layout.addWidget(self.lbl_total)
        summary_layout.addStretch()
        summary_layout.addWidget(btn_refresh)
        layout.addLayout(summary_layout)

        # Tabla de Nómina
        columns = ("Empleado", "Tipo Contrato", "Salario Base", "Neto a Pagar")
        self.table = DataTable(headers=columns)
        layout.addWidget(self.table)

    def refresh(self):
        calculator_mod = __import__("models.payroll", fromlist=["Payroll"])
        calculator = calculator_mod.Payroll("Reporte Actual")

        employees = list(self.manager.professors) + list(self.manager.administrative_staff)
        rows_formatted = []
        total_payroll = 0.0

        for emp in employees:
            report = calculator.generate_payroll_report(emp)
            emp_name = getattr(emp, "full_name", "Desconocido")
            emp_type = report.get("employee_type", "General")
            base = report.get("base_salary", 0.0)
            net = report.get("net_salary", 0.0)

            total_payroll += net
            rows_formatted.append((emp_name, emp_type, f"$ {base:,.2f}", f"$ {net:,.2f}"))

        self.table.populate(rows_formatted)
        self.lbl_total.setText(f"Total a liquidar: $ {total_payroll:,.2f}")
