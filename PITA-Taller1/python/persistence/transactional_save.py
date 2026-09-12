"""Transactional batch saving mechanism for the PITA academic and payroll system.

Ensures ACID-like consistency (Atomicity, Consistency, Isolation) when persisting
multiple JSON entities to disk.
"""

from __future__ import annotations

import inspect
import os
import shutil
from pathlib import Path
from typing import Any, Callable, Optional, Union


class TransactionalSave:
    """Coordinates atomic batch file writes using a staging directory on the same volume.

    Workflow:
    1. Prepares an empty staging directory (e.g., `data/.tmp_save/`).
    2. Stages each file using a provided saver callable targeting the staging path.
    3. If any stage operation fails or raises an error, rollbacks immediately:
       cleans up the staging directory and leaves all existing target files untouched.
    4. Upon successful staging of all files, performs an atomic commit:
       - Generates `.bak` backups for existing target files.
       - Swaps each staged file into its destination using `os.replace()`.
       - Cleans up the staging directory.
    """

    def __init__(
        self,
        data_directory: Union[str, Path, None] = None,
        staging_folder: str = ".tmp_save",
    ) -> None:
        if data_directory is None:
            from persistence.file_manager import DATA_DIRECTORY
            self.data_directory = Path(DATA_DIRECTORY)
        else:
            self.data_directory = Path(data_directory)

        self.staging_folder = staging_folder
        self.staging_dir = self.data_directory / staging_folder
        self._staged_files: list[tuple[str, Path, Path]] = []
        self._committed: bool = False
        self._aborted: bool = False

    def prepare(self) -> None:
        """Cleans and creates a fresh staging directory."""
        if self.staging_dir.exists():
            shutil.rmtree(self.staging_dir, ignore_errors=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self._staged_files.clear()
        self._committed = False
        self._aborted = False

    def stage(self, filename: str, save_fn: Callable[..., Any]) -> Path:
        """Executes save_fn writing to the staging path.

        Args:
            filename: Target file name (e.g. 'students.json').
            save_fn: Callable that accepts the staged path or takes no arguments.
                     Must return a truthy value or create a non-empty file.

        Returns:
            The Path to the staged file.

        Raises:
            RuntimeError: If save_fn fails, returns False, or the file is not created.
        """
        if self._committed or self._aborted:
            raise RuntimeError(
                f"No se puede agregar '{filename}': la transacción ya fue "
                f"{'confirmada' if self._committed else 'abortada'}."
            )

        staged_path = self.staging_dir / filename
        target_path = self.data_directory / filename

        try:
            sig = inspect.signature(save_fn)
            if len(sig.parameters) == 0:
                result = save_fn()
            else:
                result = save_fn(staged_path)
        except Exception as exc:
            self.rollback()
            raise RuntimeError(
                f"Error al escribir '{filename}' en el directorio temporal: {exc}"
            ) from exc

        # Check success: function must not return False, and file must exist
        if result is False or not staged_path.exists():
            self.rollback()
            raise RuntimeError(
                f"Fallo al escribir '{filename}' en el directorio temporal "
                "(retornó False o no se creó el archivo)."
            )

        self._staged_files.append((filename, staged_path, target_path))
        return staged_path

    def commit(self) -> None:
        """Atomically moves all staged files to their target destinations."""
        if self._committed:
            return
        if self._aborted:
            raise RuntimeError("No se puede hacer commit de una transacción abortada.")

        if not self._staged_files:
            self.cleanup()
            self._committed = True
            return

        # Pre-verify that all staged files are physically present before committing
        for filename, staged_path, _ in self._staged_files:
            if not staged_path.exists():
                self.rollback()
                raise RuntimeError(
                    f"Consistencia rota: archivo de staging ausente antes del commit: '{filename}'"
                )

        # Execute atomic replacement with .bak backups
        try:
            for _, staged_path, target_path in self._staged_files:
                if target_path.exists() and target_path.is_file():
                    backup_path = target_path.with_name(f"{target_path.name}.bak")
                    try:
                        shutil.copy2(target_path, backup_path)
                    except OSError:
                        pass
                os.replace(staged_path, target_path)
        except Exception as exc:
            # If replacement fails (e.g. disk or OS error), clean up and abort
            self.rollback()
            raise RuntimeError(f"Fallo crítico durante el commit atómico: {exc}") from exc

        self._committed = True
        self.cleanup()

    def rollback(self) -> None:
        """Aborts the transaction and cleans up the staging directory without modifying targets."""
        self._aborted = True
        self._staged_files.clear()
        self.cleanup()

    def cleanup(self) -> None:
        """Removes the staging directory."""
        if self.staging_dir.exists():
            shutil.rmtree(self.staging_dir, ignore_errors=True)

    def __enter__(self) -> "TransactionalSave":
        self.prepare()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            self.rollback()
            return False  # Propagate exception

        if not self._committed and not self._aborted:
            try:
                self.commit()
            except Exception:
                self.rollback()
                raise
        return False


def batch_save_state(manager: Any, data_directory: Union[str, Path, None] = None) -> bool:
    """Guarda atómicamente todas las entidades académicas y de nómina del sistema.

    Utiliza TransactionalSave para escribir en un staging temporal (.tmp_save).
    Si alguna entidad falla, aborta y revierte sin modificar ningún archivo existente en disco.
    Si todas tienen éxito, realiza el reemplazo atómico con copias de seguridad .bak.

    Args:
        manager: Instancia de EntityManager (o dict con colecciones y payroll_cycle_service).
        data_directory: Ruta al directorio de datos (opcional, por defecto DATA_DIRECTORY).

    Returns:
        True si todos los archivos fueron guardados y confirmados exitosamente.

    Raises:
        RuntimeError: Si ocurre algún error durante la preparación, escritura o confirmación.
    """
    from persistence.file_manager import (
        DATA_DIRECTORY,
        save_administrative_staff,
        save_courses,
        save_enrollments,
        save_faculties,
        save_payroll_audit,
        save_payroll_novelties,
        save_payroll_periods,
        save_payroll_runs,
        save_professors,
        save_programs,
        save_students,
    )

    target_dir = Path(data_directory) if data_directory else DATA_DIRECTORY

    def get_attr(name: str, default: Any = None) -> Any:
        if isinstance(manager, dict):
            return manager.get(name, default)
        return getattr(manager, name, default)

    faculties = get_attr("faculties", [])
    programs = get_attr("programs", [])
    courses = get_attr("courses", [])
    students = get_attr("students", [])
    professors = get_attr("professors", [])
    administrative_staff = get_attr("administrative_staff", [])
    enrollments = get_attr("enrollments", [])

    cycle = get_attr("payroll_cycle_service")

    with TransactionalSave(target_dir) as tx:
        # 7 Entidades académicas
        tx.stage("faculties.json", lambda p: save_faculties(faculties, file_path=p))
        tx.stage("programs.json", lambda p: save_programs(programs, file_path=p))
        tx.stage("courses.json", lambda p: save_courses(courses, file_path=p))
        tx.stage("students.json", lambda p: save_students(students, file_path=p))
        tx.stage("professors.json", lambda p: save_professors(professors, file_path=p))
        tx.stage(
            "administrative_staff.json",
            lambda p: save_administrative_staff(administrative_staff, file_path=p),
        )
        tx.stage("enrollments.json", lambda p: save_enrollments(enrollments, file_path=p))

        # 4 Entidades de ciclo de nómina
        if cycle is not None:
            periods = getattr(cycle, "periods", [])
            runs = getattr(cycle, "runs", [])
            novelties = getattr(cycle, "novelties", [])
            audits = getattr(cycle, "audits", [])

            tx.stage("payroll_periods.json", lambda p: save_payroll_periods(periods, file_path=p))
            tx.stage("payroll_runs.json", lambda p: save_payroll_runs(runs, file_path=p))
            tx.stage("payroll_novelties.json", lambda p: save_payroll_novelties(novelties, file_path=p))
            tx.stage("payroll_audit.json", lambda p: save_payroll_audit(audits, file_path=p))

    return True

