"""Sidebar navegable con secciones expandibles para NexoCampus."""
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .icons import icon


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
        self._active_page = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Brand Box
        brand_frame = QFrame()
        brand_frame.setMinimumHeight(76)
        brand_frame.setStyleSheet("border-bottom: 1px solid rgba(255,255,255,0.08);")
        brand_layout = QHBoxLayout(brand_frame)
        brand_layout.setContentsMargins(16, 12, 12, 10)
        brand_layout.setSpacing(10)

        logo = QLabel()
        logo.setFixedSize(36, 36)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("background: rgba(255,255,255,0.15); border-radius: 10px;")
        logo.setPixmap(icon("building", "#FFFFFF", 20).pixmap(20, 20))

        brand_text = QVBoxLayout()
        brand_text.setContentsMargins(0, 0, 0, 0)
        brand_text.setSpacing(2)
        title = QLabel("NexoCampus")
        title.setObjectName("brandName")
        title.setMinimumHeight(20)
        sub = QLabel("Programa Integrado de\nTransacciones Académicas")
        sub.setObjectName("brandSub")
        sub.setWordWrap(True)

        brand_text.addWidget(title)
        brand_text.addWidget(sub)
        brand_layout.addWidget(logo)
        brand_layout.addLayout(brand_text, stretch=1)
        layout.addWidget(brand_frame)

        # Área de navegación con scroll adaptable (evita ocultar botones de acción en resoluciones bajas)
        nav_scroll = QScrollArea()
        nav_scroll.setObjectName("sidebarNavScroll")
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        nav_scroll.setStyleSheet("background: transparent; border: none;")

        nav_widget = QWidget()
        nav_widget.setObjectName("sidebarNavWidget")
        nav_widget.setStyleSheet("background: transparent;")
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 4, 0, 4)
        nav_layout.setSpacing(2)

        # Secciones de Navegación
        nav_layout.addWidget(self._create_section_label("NAVEGACIÓN"))
        self._add_nav_button(nav_layout, "Dashboard", "Inicio", is_sub=False)

        nav_layout.addWidget(self._create_section_label("ACADÉMICO"))
        self._add_nav_button(nav_layout, "Facultades", "Facultades", is_sub=True)
        self._add_nav_button(nav_layout, "Programas", "Programas", is_sub=True)
        self._add_nav_button(nav_layout, "Cursos", "Cursos", is_sub=True)

        nav_layout.addWidget(self._create_section_label("PERSONAS"))
        self._add_nav_button(nav_layout, "Estudiantes", "Estudiantes", is_sub=True)
        self._add_nav_button(nav_layout, "Profesores", "Profesores", is_sub=True)
        self._add_nav_button(nav_layout, "Administrativos", "Administrativos", is_sub=True)

        nav_layout.addWidget(self._create_section_label("GESTIÓN"))
        self._add_nav_button(nav_layout, "Inscripciones", "Inscripciones", is_sub=True)
        self._add_nav_button(nav_layout, "Nómina", "Nómina", is_sub=True)

        nav_layout.addWidget(self._create_section_label("HERRAMIENTAS"))
        self._add_nav_button(nav_layout, "Reportes", "Reportes", is_sub=False)

        nav_layout.addStretch()
        nav_scroll.setWidget(nav_widget)
        layout.addWidget(nav_scroll, stretch=1)

        # Footer con Guardar y Cargar datos
        footer_frame = QFrame()
        footer_frame.setStyleSheet("border-top: 1px solid rgba(255,255,255,0.08);")
        footer_layout = QVBoxLayout(footer_frame)
        footer_layout.setContentsMargins(12, 8, 12, 10)
        footer_layout.setSpacing(6)

        save_btn = QPushButton("Guardar Datos")
        save_btn.setIcon(icon("save", "#FFFFFF", 16))
        save_btn.setStyleSheet(
            "background: rgba(255,255,255,0.12); color: white; border: none; border-radius: 6px; "
            "padding: 8px 10px; font-size: 11px; font-weight: 600; text-align: left;"
        )
        save_btn.setMinimumHeight(32)
        save_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        save_btn.clicked.connect(self.save_requested.emit)

        reload_btn = QPushButton("Cargar Datos")
        reload_btn.setIcon(icon("refresh", "rgba(255,255,255,0.7)", 16))
        reload_btn.setStyleSheet(
            "background: transparent; color: rgba(255,255,255,0.7); border: 1px solid rgba(255,255,255,0.2); "
            "border-radius: 6px; padding: 7px 10px; font-size: 11px; text-align: left;"
        )
        reload_btn.setMinimumHeight(32)
        reload_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
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
        icon_name = {
            "Dashboard": "home", "Facultades": "building", "Programas": "hat",
            "Cursos": "book", "Estudiantes": "user", "Profesores": "hat",
            "Administrativos": "briefcase", "Inscripciones": "clipboard",
            "Nómina": "money", "Reportes": "chart",
        }.get(page_name, "home")
        btn.setIcon(icon(icon_name, "#FFFFFF", 16))
        btn.setIconSize(QSize(16, 16))
        btn.setObjectName("subNavButton" if is_sub else "navButton")
        btn.setCheckable(True)
        btn.clicked.connect(lambda checked=False, p=page_name: self._on_button_clicked(p))
        self._buttons[page_name] = btn
        
        # Wrapper margin
        container = QWidget()
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(8 if is_sub else 6, 1, 8 if is_sub else 6, 1)
        c_layout.addWidget(btn)
        layout.addWidget(container)

    def _on_button_clicked(self, page_name: str):
        self.set_active_page(page_name, emit_signal=False)
        self.navigate_requested.emit(page_name)

    def set_active_page(self, page_name: str, emit_signal: bool = False):
        self._active_page = page_name
        for name, btn in self._buttons.items():
            is_active = (name == page_name)
            btn.setChecked(is_active)
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if emit_signal:
            self.navigate_requested.emit(page_name)
