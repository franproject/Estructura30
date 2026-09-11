"""Dashboard financiero basado exclusivamente en PayrollRun."""
import logging
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QPieSeries, QValueAxis
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox,
    QPushButton, QScrollArea, QSizePolicy, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from services.payroll_dashboard import PayrollFinancialDashboard
from ..components.icons import icon
from ..components.stat_card import StatCard


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
        self.kpi_cards = {}
        self.financial_values = {}
        self.distribution_tables = {}
        self.distribution_counts = {}
        self.chart_views = {}
        self.chart_empty_labels = {}
        self._build_ui()
        self._load_periods()

    def _build_ui(self):
        self.setWindowTitle("Dashboard financiero de nómina")
        self.resize(980, 720)
        self.setMinimumSize(760, 560)
        self.setStyleSheet(
            """
            QDialog { background-color: #F8FAFC; color: #0F172A; }
            QScrollArea { background-color: #F8FAFC; border: none; }
            QScrollArea > QWidget > QWidget { background-color: #F8FAFC; }
            QLabel#payrollDashboardTitle { color: #0F172A; font-size: 20px; font-weight: 800; background: transparent; }
            QLabel#payrollDashboardSubtitle { color: #64748B; font-size: 12px; background: transparent; }
            QLabel#payrollControlLabel { color: #475569; font-size: 11px; font-weight: 700; background: transparent; }
            QLabel#payrollSectionTitle { color: #14532D; font-size: 14px; font-weight: 800; background: transparent; }
            QFrame#payrollPanel {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            QLabel#payrollPanelTitle { color: #0F172A; font-size: 13px; font-weight: 700; background: transparent; }
            QLabel#payrollPanelCount { color: #16A34A; font-size: 11px; font-weight: 700; background: transparent; }
            QLabel#payrollChartEmpty {
                background-color: #F8FAFC;
                border: 1px dashed #CBD5E1;
                border-radius: 8px;
                color: #64748B;
                font-size: 12px;
                font-weight: 600;
            }
            QFrame#payrollMetricItem {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 7px;
            }
            QLabel#payrollMetricLabel { color: #64748B; font-size: 11px; font-weight: 600; background: transparent; }
            QLabel#payrollMetricValue { color: #0F172A; font-size: 13px; font-weight: 800; background: transparent; }
            QTableWidget {
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                gridline-color: #F1F5F9;
                selection-background-color: #DCFCE7;
                selection-color: #14532D;
            }
            QHeaderView::section {
                background-color: #F8FAFC;
                color: #64748B;
                border: none;
                border-bottom: 1px solid #E2E8F0;
                padding: 6px 8px;
                font-size: 11px;
                font-weight: 700;
            }
            QChartView {
                background-color: #FFFFFF;
                border: none;
            }
            QComboBox {
                background-color: #FFFFFF;
                color: #0F172A;
            }
            """
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: #F8FAFC; border: none;")
        content = QWidget()
        content.setObjectName("payrollDashboardContent")
        content.setStyleSheet("background-color: #F8FAFC;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 22, 24, 28)
        layout.setSpacing(18)

        header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(3)
        title = QLabel("Dashboard financiero de nómina")
        title.setObjectName("payrollDashboardTitle")
        subtitle = QLabel("Resumen de costos laborales y distribución del personal")
        subtitle.setObjectName("payrollDashboardSubtitle")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        header.addLayout(heading, stretch=1)
        period_label = QLabel("Período")
        period_label.setObjectName("payrollControlLabel")
        header.addWidget(period_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.period_selector = QComboBox()
        self.period_selector.setMinimumWidth(180)
        self.period_selector.currentIndexChanged.connect(self.refresh)
        header.addWidget(self.period_selector)
        refresh_button = QPushButton("Actualizar")
        refresh_button.setIcon(icon("refresh", "#FFFFFF", 15))
        refresh_button.setObjectName("primaryButton")
        refresh_button.setToolTip("Actualizar indicadores")
        refresh_button.clicked.connect(self.refresh)
        header.addWidget(refresh_button)
        layout.addLayout(header)

        layout.addWidget(self._section_label("Indicadores principales"))
        layout.addLayout(self._build_kpi_grid())
        layout.addWidget(self._section_label("Resumen de nómina"))
        layout.addWidget(self._build_financial_panel())
        layout.addWidget(self._section_label("Distribución del personal"))
        layout.addLayout(self._build_distribution_grid())
        layout.addWidget(self._section_label("Análisis visual"))
        layout.addLayout(self._build_charts_row())
        layout.addStretch()

        scroll.setWidget(content)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroll)

    @staticmethod
    def _section_label(text):
        label = QLabel(text)
        label.setObjectName("payrollSectionTitle")
        return label

    def _build_kpi_grid(self):
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        definitions = (
            ("total_employees", "Total empleados", "Personal liquidado", "#DBEAFE", "#2563EB", "users"),
            ("total_professors", "Total profesores", "Docentes liquidados", "#DCFCE7", "#16A34A", "hat"),
            ("total_administratives", "Total administrativos", "Personal administrativo", "#E0F2FE", "#0284C7", "briefcase"),
            ("total_net_paid", "Total neto pagado", "Neto de la liquidación", "#DCFCE7", "#15803D", "money"),
            ("gross_salary", "Total devengado", "Salario y conceptos", "#E0F2FE", "#0369A1", "chart"),
            ("total_employee_deductions", "Total deducciones", "Descuentos al trabajador", "#F1F5F9", "#475569", "clipboard"),
            ("total_employer_contributions", "Aportes patronales", "Seguridad social", "#DCFCE7", "#16A34A", "building"),
            ("total_employer_cost", "Costo total empleador", "Costo laboral total", "#FEF3C7", "#B45309", "money"),
        )
        for index, (key, title, detail, background, color, icon_name) in enumerate(definitions):
            card = StatCard(title, "0", detail, "", background, color, icon_name=icon_name)
            card.setMinimumHeight(112)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.kpi_cards[key] = card
            grid.addWidget(card, index // 4, index % 4)
        return grid

    def _build_financial_panel(self):
        panel = self._panel()
        layout = QGridLayout(panel)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)
        metrics = (
            ("base_salary", "Salario básico"), ("ibc", "IBC"),
            ("total_employee_health", "Salud trabajador"), ("total_employee_pension", "Pensión trabajador"),
            ("total_employer_health", "Salud patronal"), ("total_employer_pension", "Pensión patronal"),
            ("total_arl", "ARL"), ("total_compensation_fund", "Caja de compensación"),
            ("total_sena", "SENA"), ("total_icbf", "ICBF"), ("total_benefits", "Prestaciones"),
        )
        for index, (key, title) in enumerate(metrics):
            item = QFrame()
            item.setObjectName("payrollMetricItem")
            item_layout = QVBoxLayout(item)
            item_layout.setContentsMargins(10, 8, 10, 8)
            item_layout.setSpacing(2)
            label = QLabel(title)
            label.setObjectName("payrollMetricLabel")
            value = QLabel("$ 0")
            value.setObjectName("payrollMetricValue")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_layout.addWidget(label)
            item_layout.addWidget(value)
            self.financial_values[key] = value
            layout.addWidget(item, index // 4, index % 4)
        return panel

    def _build_distribution_grid(self):
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        column_titles = {
            "professor_type_distribution": "Tipo",
            "faculty_distribution": "Facultad",
            "category_distribution": "Categoría",
            "linkage_distribution": "Vinculación",
        }
        for index, (key, title) in enumerate(self.DISTRIBUTIONS):
            panel = self._panel()
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(14, 12, 14, 12)
            layout.setSpacing(5)
            label = QLabel(title)
            label.setObjectName("payrollPanelTitle")
            count = QLabel("0 empleados")
            count.setObjectName("payrollPanelCount")
            layout.addWidget(label)
            layout.addWidget(count)
            table = self._distribution_table(column_titles[key])
            self.distribution_tables[key] = table
            self.distribution_counts[key] = count
            layout.addWidget(table)
            grid.addWidget(panel, index // 2, index % 2)
        return grid

    @staticmethod
    def _distribution_table(title):
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels((title, "Empleados"))
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.verticalHeader().setDefaultSectionSize(28)
        table.verticalHeader().setMinimumSectionSize(28)
        table.setMinimumHeight(58)
        table.setMaximumHeight(170)
        table.setWordWrap(False)
        table.setTextElideMode(Qt.TextElideMode.ElideNone)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return table

    def _build_charts_row(self):
        row = QHBoxLayout()
        row.setSpacing(12)
        chart_definitions = (
            ("faculty", "Distribución de empleados por facultad"),
            ("linkage", "Empleados por tipo de vinculación"),
            ("category", "Empleados por categoría docente"),
        )
        for key, title in chart_definitions:
            panel = self._panel()
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(14, 12, 14, 12)
            layout.setSpacing(6)
            label = QLabel(title)
            label.setObjectName("payrollPanelTitle")
            layout.addWidget(label)
            empty_label = QLabel("Sin datos para este período")
            empty_label.setObjectName("payrollChartEmpty")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setMinimumHeight(210)
            empty_label.hide()
            layout.addWidget(empty_label)
            chart = QChartView()
            chart.setMinimumHeight(210)
            chart.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            chart.setRenderHint(QPainter.RenderHint.Antialiasing)
            chart.setStyleSheet("background-color: #FFFFFF; border: none;")
            chart.setBackgroundBrush(QColor("#FFFFFF"))
            layout.addWidget(chart)
            self.chart_views[key] = chart
            self.chart_empty_labels[key] = empty_label
            row.addWidget(panel, stretch=1)
        return row

    @staticmethod
    def _panel():
        panel = QFrame()
        panel.setObjectName("payrollPanel")
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return panel

    def _load_periods(self):
        self.period_selector.clear()
        for period in self.cycle.periods:
            run = next((item for item in reversed(self.cycle.runs) if item.period_id == period.period_id), None)
            if run is not None:
                self.period_selector.addItem(f"{period.year}-{period.month:02d} · {run.status.value}", period.period_id)
        self.refresh()

    @staticmethod
    def _money(value):
        return f"$ {int(value):,}".replace(",", ".")

    def _clear_visuals(self):
        for card in self.kpi_cards.values():
            card.set_value("0")
        for value in self.financial_values.values():
            value.setText("$ 0")
        for key, table in self.distribution_tables.items():
            table.setRowCount(0)
            self.distribution_counts[key].setText("0 empleados")
        for chart in self.chart_views.values():
            chart.hide()
        for label in self.chart_empty_labels.values():
            label.show()

    @staticmethod
    def _style_chart(chart):
        chart.setTheme(QChart.ChartTheme.ChartThemeLight)
        chart.setBackgroundBrush(QColor("#FFFFFF"))
        chart.setPlotAreaBackgroundBrush(QColor("#F8FAFC"))
        chart.setPlotAreaBackgroundVisible(True)
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setVisible(False)
        chart.setTitleBrush(QColor("#334155"))

    def _show_chart(self, key):
        self.chart_empty_labels[key].hide()
        self.chart_views[key].show()

    def _show_empty_chart(self, key):
        self.chart_views[key].hide()
        self.chart_empty_labels[key].show()

    def _render_charts(self, data):
        faculty_values = data["faculty_distribution"]
        if faculty_values:
            self._show_chart("faculty")
        else:
            self._show_empty_chart("faculty")
        faculty_series = QPieSeries()
        faculty_colors = ("#16A34A", "#2563EB", "#0EA5E9", "#F59E0B", "#64748B", "#14B8A6")
        for index, (label, count) in enumerate(faculty_values.items()):
            slice_item = faculty_series.append(label, count)
            slice_item.setBrush(QColor(faculty_colors[index % len(faculty_colors)]))
            slice_item.setLabelColor(QColor("#334155"))
        faculty_series.setHoleSize(0.52)
        faculty_chart = QChart()
        self._style_chart(faculty_chart)
        faculty_chart.setTitle("Distribución de empleados por facultad")
        faculty_chart.addSeries(faculty_series)
        self.chart_views["faculty"].setChart(faculty_chart)

        for chart_key, data_key in (("linkage", "linkage_distribution"), ("category", "category_distribution")):
            values = data[data_key]
            if values:
                self._show_chart(chart_key)
            else:
                self._show_empty_chart(chart_key)
            categories = list(values.keys())
            bar_set = QBarSet("Empleados")
            for category in categories:
                bar_set.append(values[category])
            bar_set.setColor(QColor("#2563EB" if chart_key == "linkage" else "#16A34A"))
            series = QBarSeries()
            series.append(bar_set)
            chart = QChart()
            self._style_chart(chart)
            chart.setTitle(
                "Empleados por tipo de vinculación"
                if chart_key == "linkage" else "Empleados por categoría docente"
            )
            chart.addSeries(series)
            axis_x = QBarCategoryAxis()
            axis_x.append(categories)
            axis_x.setLabelsAngle(-25)
            axis_x.setLabelsColor(QColor("#475569"))
            axis_y = QValueAxis()
            axis_y.setMin(0)
            axis_y.setMax(max(values.values(), default=1))
            axis_y.setTickCount(min(max(len(values) + 1, 2), 6))
            axis_y.setLabelsColor(QColor("#475569"))
            axis_y.setGridLineColor(QColor("#E2E8F0"))
            chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)
            self.chart_views[chart_key].setChart(chart)

    def refresh(self):
        try:
            period_id = self.period_selector.currentData()
            run = next((item for item in reversed(self.cycle.runs) if item.period_id == period_id), None)
            if run is None:
                self._clear_visuals()
                return
            data = PayrollFinancialDashboard(run, self.employees, self.faculties).snapshot()
            count_keys = {"total_employees", "total_professors", "total_administratives"}
            for key, card in self.kpi_cards.items():
                value = data[key]
                card.set_value(str(value) if key in count_keys else self._money(value))
            for key, value_label in self.financial_values.items():
                value_label.setText(self._money(data[key]))
            for key, table in self.distribution_tables.items():
                values = data[key]
                table.setRowCount(len(values))
                for row, (label, count) in enumerate(values.items()):
                    table.setItem(row, 0, QTableWidgetItem(label))
                    table.setItem(row, 1, QTableWidgetItem(str(count)))
                self.distribution_counts[key].setText(f"{sum(values.values())} empleados")
                table.resizeRowsToContents()
                row_height = table.horizontalHeader().height() + sum(
                    table.rowHeight(row) for row in range(table.rowCount())
                ) + 4
                table.setMinimumHeight(min(max(row_height, 58), 170))
            self._render_charts(data)
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Error al refrescar %s", self.__class__.__name__
            )
            QMessageBox.warning(self, "Error", str(exc))