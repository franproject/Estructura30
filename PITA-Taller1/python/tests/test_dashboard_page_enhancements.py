"""Pruebas unitarias para las mejoras integrales del DashboardPage:
1. Deltas de variación verídicos basados en snapshots (sin datos hardcodeados).
2. Conexión del total de nómina a PayrollCycleService (período calculado/aprobado más reciente).
3. Población de info_rows_layout (facultades con más estudiantes) y actividad reciente (auditorías reales).
4. Período académico dinámico derivado de inscripciones y calendario.
5. Grilla responsive de StatCards (4, 3 y 2 columnas según ancho).
"""

import os
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication

from models.faculty import Faculty
from models.program import Program
from models.student import Student
from models.enrollment import Enrollment
from models.payroll_period import PayrollPeriod, PayrollPeriodStatus
from models.payroll_run import PayrollRun, PayrollRunStatus
from models.payroll_audit import PayrollAudit
from services.entity_manager import EntityManager
from gui.pages.dashboard_page import DashboardPage


class TestDashboardPageEnhancements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.manager = EntityManager()
        # Crear datos de prueba mínimos
        self.fac1 = Faculty(1, "Facultad de Ingeniería", "Decano A", active=True)
        self.fac2 = Faculty(2, "Facultad de Salud", "Decana B", active=True)
        self.manager.create_faculty(self.fac1)
        self.manager.create_faculty(self.fac2)

        self.prog1 = Program(10, "Ingeniería de Sistemas", 1, "Dir 1", "Pregrado", "Presencial", "Universitario", active=True)
        self.prog2 = Program(20, "Medicina", 2, "Dir 2", "Pregrado", "Presencial", "Universitario", active=True)
        self.manager.create_program(self.prog1)
        self.manager.create_program(self.prog2)

        from models.course import Course
        course1 = Course(1001, "Cálculo I", 10, 4, 1, 0, 30, active=True)
        self.manager.create_course(course1)

        # 3 estudiantes en Sistemas, 1 en Medicina
        for i in range(1, 4):
            self.manager.create_student(Student(
                student_id=100 + i, full_name=f"Estudiante {i}", document_type="CC",
                document_number=f"100{i}", email="est@mail.com", program_id=10,
                current_semester=1, active=True,
            ))
        self.manager.create_student(Student(
            student_id=104, full_name="Estudiante 4", document_type="CC",
            document_number="1004", email="est4@mail.com", program_id=20,
            current_semester=1, active=True,
        ))

        # Inscripción activa con período
        self.manager.create_enrollment(
            Enrollment(1, 101, 1001, academic_period="2026-2", final_grade=4.0, status="ACTIVE", enrollment_date="2026-08-01")
        )

        # Mock de persistencia de snapshot en memoria para aislar la prueba del disco
        self.snapshot_storage = {}
        patcher_load = patch.object(
            DashboardPage, "_load_baseline_counts", side_effect=lambda *a, **kw: self.snapshot_storage.copy() or None
        )
        patcher_save = patch.object(
            DashboardPage, "_save_baseline_counts", side_effect=lambda *a, **kw: self.snapshot_storage.update(a[-1] if a else kw.get("counts", {}))
        )
        self.addCleanup(patcher_load.stop)
        self.addCleanup(patcher_save.stop)
        patcher_load.start()
        patcher_save.start()

        self.nav_mock = MagicMock()
        self.page = DashboardPage(self.manager, self.nav_mock)

    def test_real_deltas_and_no_hardcoded_fake_values(self):
        """Verifica que no existan deltas inventados y que reflejen cambios reales."""
        # Inicialmente el baseline se fija a los conteos actuales -> deltas en '= 0'
        card_fac = self.page.cards["Facultades"]
        self.assertEqual(card_fac.lbl_delta.text(), "= 0")
        self.assertEqual(card_fac.lbl_val.text(), "2")

        # Agregar una nueva facultad
        fac3 = Faculty(3, "Facultad de Artes", "Decano C", active=True)
        self.manager.create_faculty(fac3)
        self.page.refresh()

        # El delta debe reflejar exactamente ▲ +1
        self.assertEqual(card_fac.lbl_val.text(), "3")
        self.assertEqual(card_fac.lbl_delta.text(), "▲ +1")
        self.assertEqual(card_fac.lbl_delta.property("trend"), "up")

        # Actualizar línea base con 3 facultades
        self.page.update_baseline()
        self.page.refresh()
        self.assertEqual(card_fac.lbl_delta.text(), "= 0")

        # Eliminar la facultad recién creada (sin dependencias)
        self.manager.delete_faculty(3)
        self.page.refresh()

        # El delta debe reflejar ▼ -1 respecto a la línea base (baseline 3, ahora 2)
        self.assertEqual(card_fac.lbl_val.text(), "2")
        self.assertEqual(card_fac.lbl_delta.text(), "▼ -1")
        self.assertEqual(card_fac.lbl_delta.property("trend"), "down")

        # Al estabilizar el baseline de nuevo, regresa a '= 0'
        self.page.update_baseline()
        self.page.refresh()
        self.assertEqual(card_fac.lbl_delta.text(), "= 0")

    def test_payroll_total_connected_to_cycle_service(self):
        """Verifica que el total de nómina consulte el último período y cálculo de PayrollCycleService."""
        # Inicialmente sin períodos liquidados
        self.page.refresh()
        self.assertIn("$ 0.00", self.page.lbl_payroll_total.text())

        # Agregar período y corrida liquidada en PayrollCycleService
        cycle = self.manager.payroll_cycle_service
        period = PayrollPeriod(
            period_id="PER-2026-09", year=2026, month=9,
            start_date="2026-09-01", end_date="2026-09-30",
            status=PayrollPeriodStatus.CALCULATED,
        )
        cycle.periods.append(period)

        run = PayrollRun(
            run_id="RUN-001", period_id="PER-2026-09", employee_ids=["101"],
            details=[], totals={"gross_salary": Decimal("48500000.50"), "net_salary": Decimal("42000000.00")},
            employer_cost=60000000, executed_at="2026-09-11T10:00:00", audit_ids=[],
            created_at="2026-09-11T10:00:00", calculated_at="2026-09-11T10:00:00", calculated_by="admin",
            novelty_ids=[], status=PayrollRunStatus.CALCULATED,
        )
        cycle.runs.append(run)

        # Refrescar dashboard
        self.page.refresh()

        # Debe mostrar el total devengado formateado y el período
        total_text = self.page.lbl_payroll_total.text()
        self.assertIn("48,500,000.50", total_text)
        self.assertIn("2026-09", total_text)

    def test_info_rows_layout_populates_top_faculties(self):
        """Verifica que info_rows_layout muestre el desglose real de estudiantes por facultad."""
        self.page.refresh()
        # Debe haber al menos un widget en info_rows_layout
        self.assertGreater(self.page.info_rows_layout.count(), 0)

        # La primera fila debe corresponder a Ingeniería (3 estudiantes = 75%)
        first_row = self.page.info_rows_layout.itemAt(0).widget()
        self.assertIsNotNone(first_row)
        texts = [child.text() for child in first_row.findChildren(object) if hasattr(child, "text")]
        self.assertTrue(any("Ingeniería" in t for t in texts))
        self.assertTrue(any("3 est." in t for t in texts))

    def test_activity_panel_populates_real_audit_events(self):
        """Verifica que el panel de actividad reciente muestre registros de PayrollAudit."""
        cycle = self.manager.payroll_cycle_service
        # Añadir eventos de auditoría
        audit1 = PayrollAudit(
            audit_id="AUD-1", entity_type="PayrollPeriod", entity_id="PER-1",
            action="CREATE", timestamp="2026-09-11T08:00:00", actor="admin",
        )
        audit2 = PayrollAudit(
            audit_id="AUD-2", entity_type="PayrollRun", entity_id="RUN-1",
            action="CALCULATE", timestamp="2026-09-11T08:30:00", actor="contador",
        )
        cycle.audits.extend([audit1, audit2])

        self.page.refresh()

        # Debe contener los eventos en orden inverso (el más reciente primero)
        self.assertEqual(self.page.activity_rows_layout.count(), 2)
        top_audit_widget = self.page.activity_rows_layout.itemAt(0).widget()
        texts = [child.text() for child in top_audit_widget.findChildren(object) if hasattr(child, "text")]
        self.assertTrue(any("CÁLCULO" in t for t in texts))
        self.assertTrue(any("contador" in t for t in texts))

    def test_dynamic_academic_period_in_subtitle(self):
        """Verifica que el subtítulo muestre el período académico activo real de las inscripciones."""
        self.page.refresh()
        self.assertIn("Período 2026-2", self.page.lbl_subtitle.text())

        # Cambiar el período de las inscripciones activas
        for item in self.manager.enrollments:
            item.academic_period = "2027-1"
        self.page.refresh()
        self.assertIn("Período 2027-1", self.page.lbl_subtitle.text())

    def test_responsive_grid_relayout_on_resize(self):
        """Verifica que la grilla de StatCards se adapte a 4, 3 y 2 columnas según el ancho."""
        from PySide6.QtGui import QResizeEvent

        # Ancho amplio > 1200px -> 4 columnas
        self.page.resizeEvent(QResizeEvent(QSize(1300, 800), self.page.size()))
        self.assertEqual(self.page._current_cols, 4)
        # Las 8 tarjetas deben seguir en la grilla
        self.assertEqual(len(self.page._card_list), 8)
        self.assertEqual(self.page.cards_grid.count(), 8)

        # Ancho intermedio 900-1200px -> 3 columnas
        self.page.resizeEvent(QResizeEvent(QSize(1050, 800), self.page.size()))
        self.assertEqual(self.page._current_cols, 3)
        self.assertEqual(self.page.cards_grid.count(), 8)

        # Ancho compacto < 900px -> 2 columnas
        self.page.resizeEvent(QResizeEvent(QSize(750, 800), self.page.size()))
        self.assertEqual(self.page._current_cols, 2)
        self.assertEqual(self.page.cards_grid.count(), 8)


if __name__ == "__main__":
    unittest.main()
