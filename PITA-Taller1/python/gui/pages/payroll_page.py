"""Página de consulta e informe de Nómina académica."""
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
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
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header_view.setMinimumSectionSize(150)
        layout.addWidget(self.table)
        self.pagination = self._build_pagination()
        layout.addWidget(self.pagination)

    def _build_pagination(self):
        footer = QWidget()
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(4, 4, 4, 0)
        self.page_info = QLabel()
        self.page_info.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(self.page_info)
        layout.addStretch()
        self.page_buttons = QHBoxLayout()
        self.page_buttons.setSpacing(4)
        layout.addLayout(self.page_buttons)
        self.table.page_changed.connect(lambda *_: self._update_pagination())
        return footer

    def _update_pagination(self):
        total = self.table.total_rows
        start = 0 if total == 0 else (self.table.page - 1) * self.table.page_size + 1
        end = min(self.table.page * self.table.page_size, total)
        self.page_info.setText(f"Mostrando {start}\u2013{end} de {total} registros")
        while self.page_buttons.count():
            item = self.page_buttons.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for page in range(1, self.table.page_count + 1):
            button = QPushButton(str(page))
            button.setFixedSize(27, 27)
            button.setObjectName("activePageButton" if page == self.table.page else "pageButton")
            button.clicked.connect(lambda checked=False, target=page: self.table.set_page(target))
            self.page_buttons.addWidget(button)
        self.pagination.setVisible(total > self.table.page_size)

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
        self._update_pagination()
        self.lbl_total.setText(f"Total a liquidar: $ {total_payroll:,.2f}")
