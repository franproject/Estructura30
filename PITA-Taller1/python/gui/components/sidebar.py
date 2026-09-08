"""Sidebar navegable con secciones expandibles para NexoCampus."""
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Sidebar(QFrame):
    """Barra lateral de navegación institucional."""
    
    navigate_requested = Signal(str)
    save_requested = Signal()
    reload_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        self._buttons = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Brand Box
        brand_frame = QFrame()
        brand_frame.setStyleSheet("padding: 20px 18px 14px; border-bottom: 1px solid rgba(255,255,255,0.08);")
        brand_layout = QVBoxLayout(brand_frame)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(2)

        title = QLabel("NexoCampus")
        title.setObjectName("brandName")
        sub = QLabel("Programa Integrado de\nTransacciones Académicas")
        sub.setObjectName("brandSub")

        brand_layout.addWidget(title)
        brand_layout.addWidget(sub)
        layout.addWidget(brand_frame)

        # Secciones de Navegación
        layout.addWidget(self._create_section_label("NAVEGACIÓN"))
        self._add_nav_button(layout, "Dashboard", "Inicio", is_sub=False)

        layout.addWidget(self._create_section_label("ACADÉMICO"))
        self._add_nav_button(layout, "Facultades", "Facultades", is_sub=True)
        self._add_nav_button(layout, "Programas", "Programas", is_sub=True)
        self._add_nav_button(layout, "Cursos", "Cursos", is_sub=True)

        layout.addWidget(self._create_section_label("PERSONAS"))
        self._add_nav_button(layout, "Estudiantes", "Estudiantes", is_sub=True)
        self._add_nav_button(layout, "Profesores", "Profesores", is_sub=True)
        self._add_nav_button(layout, "Administrativos", "Administrativos", is_sub=True)

        layout.addWidget(self._create_section_label("GESTIÓN"))
        self._add_nav_button(layout, "Inscripciones", "Inscripciones", is_sub=True)
        self._add_nav_button(layout, "Nómina", "Nómina", is_sub=True)

        layout.addWidget(self._create_section_label("HERRAMIENTAS"))
        self._add_nav_button(layout, "Reportes", "Reportes", is_sub=False)

        layout.addStretch()

        # Footer con Guardar / Cargar / Configuración
        footer_frame = QFrame()
        footer_frame.setStyleSheet("padding: 10px 12px 16px; border-top: 1px solid rgba(255,255,255,0.08);")
        footer_layout = QVBoxLayout(footer_frame)
        footer_layout.setSpacing(6)

        save_btn = QPushButton("💾  Guardar Datos")
        save_btn.setStyleSheet(
            "background: rgba(255,255,255,0.12); color: white; border: none; border-radius: 6px; padding: 8px; font-size: 11px; font-weight: 600;"
        )
        save_btn.clicked.connect(self.save_requested.emit)

        reload_btn = QPushButton("↻  Cargar Datos")
        reload_btn.setStyleSheet(
            "background: transparent; color: rgba(255,255,255,0.7); border: 1px solid rgba(255,255,255,0.2); border-radius: 6px; padding: 7px; font-size: 11px;"
        )
        reload_btn.clicked.connect(self.reload_requested.emit)

        footer_layout.addWidget(save_btn)
        footer_layout.addWidget(reload_btn)
        layout.addWidget(footer_frame)

    def _create_section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("navSectionLabel")
        return lbl

    def _add_nav_button(self, layout: QVBoxLayout, page_name: str, label_text: str, is_sub: bool = False):
        btn = QPushButton(label_text)
        btn.setObjectName("subNavButton" if is_sub else "navButton")
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self.set_active_page(page_name))
        self._buttons[page_name] = btn
        
        # Wrapper margin
        container = QWidget()
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(8 if is_sub else 6, 1, 8 if is_sub else 6, 1)
        c_layout.addWidget(btn)
        layout.addWidget(container)

    def set_active_page(self, page_name: str):
        for name, btn in self._buttons.items():
            is_active = (name == page_name)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.navigate_requested.emit(page_name)
