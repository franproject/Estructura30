"""Pruebas unitarias para la limpieza de código muerto, logging centralizado y sys.excepthook.

Verifica:
1. COMPONENTE HUÉRFANO:
   - gui/components/chip.py ya no existe en el sistema.
2. FUNCIÓN CLI:
   - ask_load_existing_data no existe en persistence.file_manager ni en persistence.__init__.
3. IMPORTACIÓN ESTÁTICA:
   - gui/main_window.py importa Enrollment estáticamente y no utiliza __import__.
4. LOGGING Y EXCEPTHOOK:
   - main.py define sys.excepthook con handle_uncaught_exception.
   - handle_uncaught_exception registra excepciones en el logger persistente.
   - handle_uncaught_exception muestra QMessageBox con información detallada.
   - KeyboardInterrupt se delega a sys.__excepthook__.
"""

import importlib
import logging
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QMessageBox


class TestSystemCleanupAndLogging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_chip_component_removed(self):
        """Verifica que gui/components/chip.py haya sido eliminado."""
        chip_path = Path(__file__).resolve().parent.parent / "gui" / "components" / "chip.py"
        self.assertFalse(chip_path.exists(), "El archivo gui/components/chip.py no debería existir.")

    def test_ask_load_existing_data_removed(self):
        """Verifica que ask_load_existing_data no exista en persistence."""
        import persistence
        import persistence.file_manager as fm

        self.assertFalse(hasattr(persistence, "ask_load_existing_data"))
        self.assertFalse(hasattr(fm, "ask_load_existing_data"))

    def test_main_window_has_no_dynamic_enrollment_import(self):
        """Verifica que gui/main_window.py use importación estática para Enrollment y no __import__."""
        main_window_path = Path(__file__).resolve().parent.parent / "gui" / "main_window.py"
        content = main_window_path.read_text(encoding="utf-8")

        self.assertNotIn('__import__("models.enrollment"', content)
        self.assertNotIn("fromlist=[\"Enrollment\"]", content)
        self.assertIn("from models.enrollment import Enrollment", content)

    def test_sys_excepthook_installed_in_main(self):
        """Verifica que main instale handle_uncaught_exception en sys.excepthook."""
        import main

        self.assertTrue(callable(main.handle_uncaught_exception))
        self.assertEqual(sys.excepthook, main.handle_uncaught_exception)

    def test_handle_uncaught_exception_logs_and_displays_dialog(self):
        """Verifica que una excepción no controlada se registre en el log y muestre QMessageBox."""
        import main

        try:
            raise RuntimeError("Error de prueba simulado para auditoría")
        except RuntimeError:
            exc_type, exc_value, exc_tb = sys.exc_info()

        with patch.object(main.logger, "critical") as mock_log, \
             patch.object(QMessageBox, "exec") as mock_box_exec:
            main.handle_uncaught_exception(exc_type, exc_value, exc_tb)

            # Debe registrar como error crítico con traceback
            mock_log.assert_called_once()
            log_msg = mock_log.call_args[0][1]
            self.assertIn("RuntimeError", log_msg)
            self.assertIn("Error de prueba simulado", log_msg)

            # Debe abrir el diálogo de alerta
            mock_box_exec.assert_called_once()

    def test_handle_uncaught_exception_keyboard_interrupt(self):
        """KeyboardInterrupt debe ser transferido a sys.__excepthook__ sin abrir diálogos."""
        import main

        try:
            raise KeyboardInterrupt()
        except KeyboardInterrupt:
            exc_type, exc_value, exc_tb = sys.exc_info()

        with patch.object(sys, "__excepthook__") as mock_orig_hook, \
             patch.object(main.logger, "critical") as mock_log:
            main.handle_uncaught_exception(exc_type, exc_value, exc_tb)

            mock_orig_hook.assert_called_once_with(exc_type, exc_value, exc_tb)
            mock_log.assert_not_called()


if __name__ == "__main__":
    unittest.main()

