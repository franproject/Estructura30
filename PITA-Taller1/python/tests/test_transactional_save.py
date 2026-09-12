"""Pruebas unitarias para el mecanismo de guardado atómico por lote (TransactionalSave)."""

import json
import os
import shutil
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from models.administrative import Administrative
from models.course import Course
from models.enrollment import Enrollment
from models.faculty import Faculty
from models.linked_list import LinkedList
from models.payroll_audit import PayrollAudit
from models.payroll_novelty import PayrollNovelty
from models.payroll_period import PayrollPeriod, PayrollPeriodStatus
from models.payroll_run import PayrollRun
from models.professor import Professor
from models.program import Program
from models.student import Student
from persistence.file_manager import load_all_entities
from persistence.transactional_save import TransactionalSave, batch_save_state
from services.entity_manager import EntityManager


class TestTransactionalSave(unittest.TestCase):
    """Verifica el comportamiento transaccional: atomicidad, rollback y generación de backups."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="pita_test_tx_"))
        self.staging_dir = self.test_dir / ".tmp_save"

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_atomic_save_success_and_cleanup(self):
        """Verifica que un guardado exitoso actualiza los archivos, crea .bak y limpia el staging."""
        # 1. Crear archivos existentes previos
        file1 = self.test_dir / "file1.json"
        file2 = self.test_dir / "file2.json"
        file1.write_text(json.dumps({"version": 1}), encoding="utf-8")
        file2.write_text(json.dumps({"version": 1}), encoding="utf-8")

        # 2. Ejecutar guardado transaccional
        with TransactionalSave(self.test_dir) as tx:
            tx.stage("file1.json", lambda p: p.write_text(json.dumps({"version": 2}), encoding="utf-8"))
            tx.stage("file2.json", lambda p: p.write_text(json.dumps({"version": 2}), encoding="utf-8"))
            tx.stage("file3_new.json", lambda p: p.write_text(json.dumps({"version": 2}), encoding="utf-8"))

        # 3. Verificaciones post-commit
        self.assertEqual(json.loads(file1.read_text(encoding="utf-8"))["version"], 2)
        self.assertEqual(json.loads(file2.read_text(encoding="utf-8"))["version"], 2)

        file3 = self.test_dir / "file3_new.json"
        self.assertTrue(file3.exists())
        self.assertEqual(json.loads(file3.read_text(encoding="utf-8"))["version"], 2)

        # Backups generados para preexistentes
        bak1 = self.test_dir / "file1.json.bak"
        bak2 = self.test_dir / "file2.json.bak"
        self.assertTrue(bak1.exists())
        self.assertTrue(bak2.exists())
        self.assertEqual(json.loads(bak1.read_text(encoding="utf-8"))["version"], 1)
        self.assertEqual(json.loads(bak2.read_text(encoding="utf-8"))["version"], 1)

        # Archivo nuevo no debe tener backup .bak previo
        self.assertFalse((self.test_dir / "file3_new.json.bak").exists())

        # Directorio temporal de staging debe haber sido eliminado
        self.assertFalse(self.staging_dir.exists())

    def test_atomic_save_rollback_on_exception(self):
        """Verifica que si ocurre una excepción a mitad del lote, ningún archivo destino se modifica."""
        file1 = self.test_dir / "file1.json"
        file2 = self.test_dir / "file2.json"
        file1.write_text(json.dumps({"version": "original_1"}), encoding="utf-8")
        file2.write_text(json.dumps({"version": "original_2"}), encoding="utf-8")

        def failing_saver(path):
            raise IOError("Simulated disk write failure!")

        with self.assertRaises(RuntimeError) as ctx:
            with TransactionalSave(self.test_dir) as tx:
                tx.stage("file1.json", lambda p: p.write_text(json.dumps({"version": "mutated_1"}), encoding="utf-8"))
                tx.stage("file2.json", failing_saver)

        self.assertIn("Simulated disk write failure", str(ctx.exception))

        # Ningún archivo destino debe haber cambiado
        self.assertEqual(json.loads(file1.read_text(encoding="utf-8"))["version"], "original_1")
        self.assertEqual(json.loads(file2.read_text(encoding="utf-8"))["version"], "original_2")

        # No se deben haber creado backups .bak
        self.assertFalse((self.test_dir / "file1.json.bak").exists())
        self.assertFalse((self.test_dir / "file2.json.bak").exists())

        # El directorio temporal de staging debe haber sido limpiado
        self.assertFalse(self.staging_dir.exists())

    def test_atomic_save_rollback_when_save_fn_returns_false(self):
        """Verifica que si una función de guardado retorna False, se aborta y limpia."""
        file1 = self.test_dir / "target.json"
        file1.write_text(json.dumps({"data": "safe"}), encoding="utf-8")

        with self.assertRaises(RuntimeError) as ctx:
            with TransactionalSave(self.test_dir) as tx:
                tx.stage("target.json", lambda p: False)

        self.assertIn("Fallo al escribir 'target.json'", str(ctx.exception))
        self.assertEqual(json.loads(file1.read_text(encoding="utf-8"))["data"], "safe")
        self.assertFalse(self.staging_dir.exists())

    def test_batch_save_state_persists_all_11_entities(self):
        """Verifica que batch_save_state guarda exitosamente las 11 colecciones."""
        manager = EntityManager()
        faculty = Faculty(1, "Ingenieria", "Decano", "Edificio A")
        program = Program(101, "Sistemas", 1, "Pregrado")
        course = Course(201, "Estructuras de Datos", 101, 3, 3, 301, 40, True)
        student = Student(401, "Carlos Gomez", "CC", "1000", "2000-01-01", "carlos@mail.com", "123", 101, 3, "REGULAR", 4.2, True)
        prof = Professor(301, "Dra. Lopez", "CC", "2000", "lopez@mail.com", "456", 1, "PLANTA", "ASOCIADO", "PhD", 10, "TIEMPO_COMPLETO", 40, "NINGUNO", 10.0, 10.0, 10.0, 10.0, 0.0, 40.0, 50000.0, 5000000.0, 200000.0, 200000.0, 416666.0, 416666.0, 208333.0, 4600000.0, True)
        admin = Administrative(501, "Ana Ruiz", "CC", "3000", "ana@mail.com", "789", "Secretaria", "PROFESIONAL", "PLANTA", 3000000.0, 120000.0, 120000.0, 250000.0, 250000.0, 125000.0, 2760000.0, True)
        enrollment = Enrollment(601, 401, 201, "2026-1", 4.5, "APROBADA", "2026-02-01")

        manager.faculties.insert(faculty)
        manager.programs.insert(program)
        manager.courses.insert(course)
        manager.students.insert(student)
        manager.professors.insert(prof)
        manager.administrative_staff.insert(admin)
        manager.enrollments.insert(enrollment)

        period = PayrollPeriod(
            "2026-06", 2026, 6, "2026-06-01", "2026-06-30",
            PayrollPeriodStatus.CLOSED, closed_at="2026-06-30T12:00:00",
        )
        run = PayrollRun(run_id="RUN-001", period_id="2026-06", details=[])
        novelty = PayrollNovelty("NOV-001", "2026-06", "301", "BONUS", "2026-06-01", amount="200000", description="Bono docente")
        audit = PayrollAudit("AUD-001", "RUN", "RUN-001", "CALCULATE", "2026-06-30T10:00:00", actor="OPERATOR")

        manager.payroll_cycle_service.periods.append(period)
        manager.payroll_cycle_service.runs.append(run)
        manager.payroll_cycle_service.novelties.append(novelty)
        manager.payroll_cycle_service.audits.append(audit)

        # Ejecutar batch_save_state
        result = batch_save_state(manager, self.test_dir)
        self.assertTrue(result)

        # Verificar existencia física de los 11 archivos
        expected_files = [
            "faculties.json",
            "programs.json",
            "courses.json",
            "students.json",
            "professors.json",
            "administrative_staff.json",
            "enrollments.json",
            "payroll_periods.json",
            "payroll_runs.json",
            "payroll_novelties.json",
            "payroll_audit.json",
        ]
        for fname in expected_files:
            fpath = self.test_dir / fname
            self.assertTrue(fpath.exists(), f"Falta archivo esperado: {fname}")
            self.assertGreater(fpath.stat().st_size, 2, f"Archivo vacío: {fname}")

        # Comprobar que los datos son cargables por load_all_entities
        loaded = load_all_entities(self.test_dir)
        self.assertEqual(len(list(loaded["faculties"])), 1)
        self.assertEqual(len(list(loaded["students"])), 1)
        self.assertEqual(len(list(loaded["enrollments"])), 1)

        # Staging no debe quedar en disco
        self.assertFalse(self.staging_dir.exists())

    def test_batch_save_state_aborts_completely_on_error(self):
        """Verifica que si falla el guardado de nómina, las entidades académicas no se alteran."""
        manager = EntityManager()
        faculty = Faculty(1, "Original Facultad", "Decano", "Edificio A")
        manager.faculties.insert(faculty)

        # Guardado inicial
        batch_save_state(manager, self.test_dir)
        faculties_file = self.test_dir / "faculties.json"
        original_content = faculties_file.read_text(encoding="utf-8")

        # Modificamos en memoria la facultad
        faculty.name = "Facultad Modificada En Memoria"

        # Simulamos un fallo catastrófico en save_payroll_audit
        with patch("persistence.file_manager.save_payroll_audit", side_effect=OSError("Permiso denegado")):
            with self.assertRaises(RuntimeError) as ctx:
                batch_save_state(manager, self.test_dir)

            self.assertIn("Permiso denegado", str(ctx.exception))

        # El archivo en disco debe mantener el contenido original intacto
        self.assertEqual(faculties_file.read_text(encoding="utf-8"), original_content)
        self.assertFalse(self.staging_dir.exists())


class TestMainWindowSaveStateAtomic(unittest.TestCase):
    """Verifica el comportamiento de _save_state en MainWindow con diálogos informativos."""

    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    def test_save_state_calls_batch_save_state_and_shows_info_dialog(self):
        from PySide6.QtWidgets import QMessageBox
        from gui.main_window import MainWindow

        window = MagicMock()
        window.manager = EntityManager()

        with patch("gui.main_window.batch_save_state", return_value=True) as mock_batch_save, \
             patch.object(QMessageBox, "information") as mock_info, \
             patch.object(QMessageBox, "critical") as mock_crit:

            MainWindow._save_state(window)

            mock_batch_save.assert_called_once()
            mock_info.assert_called_once()
            mock_crit.assert_not_called()

            # Verificar que el mensaje informa guardado atómico
            info_args = mock_info.call_args[0]
            self.assertIn("atómica", info_args[2])

    def test_save_state_shows_critical_dialog_when_batch_save_fails(self):
        from PySide6.QtWidgets import QMessageBox
        from gui.main_window import MainWindow

        window = MagicMock()
        window.manager = EntityManager()

        with patch("gui.main_window.batch_save_state", side_effect=RuntimeError("Error en disco")) as mock_batch_save, \
             patch.object(QMessageBox, "information") as mock_info, \
             patch.object(QMessageBox, "critical") as mock_crit:

            MainWindow._save_state(window)

            mock_batch_save.assert_called_once()
            mock_info.assert_not_called()
            mock_crit.assert_called_once()

            crit_args = mock_crit.call_args[0]
            self.assertIn("No se guardó ningún cambio para preservar la consistencia", crit_args[2])
            self.assertIn("Error en disco", crit_args[2])


if __name__ == "__main__":
    unittest.main()

