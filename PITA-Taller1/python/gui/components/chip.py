"""Etiqueta/Chip para visualizar estados académicos y alertas."""
from PySide6.QtWidgets import QLabel


class Chip(QLabel):
    """Badge/Chip redondeado con colores de estado."""

    def __init__(self, text: str, variant: str = "green", parent=None):
        super().__init__(text, parent)
        self.set_variant(variant)

    def set_variant(self, variant: str):
        styles = {
            "green": "background-color: #DCFCE7; color: #15803D;",
            "red": "background-color: #FEE2E2; color: #DC2626;",
            "amber": "background-color: #FEF9C3; color: #B45309;",
            "blue": "background-color: #DBEAFE; color: #1D4ED8;",
            "gray": "background-color: #F1F5F9; color: #64748B;",
        }
        style = styles.get(variant, styles["gray"])
        self.setStyleSheet(
            f"{style} border-radius: 12px; padding: 3px 10px; font-size: 11px; font-weight: 600;"
        )
