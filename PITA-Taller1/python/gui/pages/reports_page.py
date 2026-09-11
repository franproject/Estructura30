"""Página de Reportes académicos e indicadores clave."""
import logging
from PySide6.QtWidgets import (
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ..components.data_table import DataTable
from ..components.page_header import PageHeader


class ReportsPage(QWidget):
    """Estadísticas resumidas e indicadores del sistema institucional."""

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
            title="Reportes Académicos",
            subtitle="Consolidado de métricas institucionales y alertas de rendimiento",
        )
        layout.addWidget(header)

        columns = ("Indicador Académico", "Valor Consolidado")
        self.table = DataTable(headers=columns)
        layout.addWidget(self.table)

    def refresh(self):
        try:
            mgr = self.manager
            ebra_count = sum(
                1 for s in mgr.students if mgr.evaluate_ebra_status(s.student_id).get("status") == "EBRA"
            )

            data = [
                ("Total Facultades Registradas", len(mgr.faculties)),
                ("Total Programas Académicos", len(mgr.programs)),
                ("Total Cursos Activos", len(mgr.courses)),
                ("Estudiantes Matriculados", len(mgr.students)),
                ("Cuerpo Docente / Profesores", len(mgr.professors)),
                ("Personal Administrativo", len(mgr.administrative_staff)),
                ("Inscripciones Registradas", len(mgr.enrollments)),
                ("Estudiantes en Alerta EBRA", ebra_count),
            ]
            self.table.populate(data)
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Error al refrescar %s", self.__class__.__name__
            )
            QMessageBox.warning(self, "Error", str(exc))
