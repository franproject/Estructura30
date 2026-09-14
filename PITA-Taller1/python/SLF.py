import logging
import sys
import traceback
from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QMessageBox
from gui.main_window import MainWindow

# Configuración centralizada de logging persistente
logging.basicConfig(
    level=logging.WARNING,
    filename="nexocampus.log",
    filemode="a",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger("nexocampus")


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """Manejador global para excepciones no capturadas."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Registrar en log centralizado con traceback completo
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_text = "".join(tb_lines)
    logger.critical("Excepción no capturada en la aplicación:\n%s", tb_text)

    # Notificar al usuario mediante diálogo crítico
    error_summary = f"{exc_type.__name__}: {exc_value}"
    detailed_info = (
        f"Se ha producido un error imprevisto en el sistema:\n\n"
        f"{error_summary}\n\n"
        f"El detalle técnico ha sido registrado en 'nexocampus.log' para auditoría."
    )

    app = QApplication.instance()
    if app is not None:
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error Inesperado - NexoCampus")
            msg_box.setText("Se ha producido un error imprevisto en la aplicación.")
            msg_box.setInformativeText(detailed_info)
            msg_box.setDetailedText(tb_text)
            msg_box.exec()
        except Exception:
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
    else:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)


sys.excepthook = handle_uncaught_exception


def _force_light_palette(app: QApplication) -> None:
    """Evita fondos negros en diálogos cuando Windows usa tema oscuro."""
    palette = QPalette()
    window = QColor("#F8FAFC")
    base = QColor("#FFFFFF")
    text = QColor("#0F172A")
    muted = QColor("#64748B")
    highlight = QColor("#16A34A")
    palette.setColor(QPalette.ColorRole.Window, window)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, base)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F1F5F9"))
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, base)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.ToolTipBase, base)
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    palette.setColor(QPalette.ColorRole.PlaceholderText, muted)
    palette.setColor(QPalette.ColorRole.Highlight, highlight)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)
    app.setStyle("Fusion")


def _load_app_stylesheet(app: QApplication) -> None:
    qss_path = Path(__file__).resolve().parent / "gui" / "styles" / "app.qss"
    try:
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
    except OSError:
        pass


def main():
    app = QApplication(sys.argv)
    _force_light_palette(app)
    _load_app_stylesheet(app)
    ventana = MainWindow()
    ventana.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
