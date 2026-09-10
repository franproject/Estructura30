import sys
from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow


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
