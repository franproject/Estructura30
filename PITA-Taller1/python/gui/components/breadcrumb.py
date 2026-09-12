"""Componente de ruta de navegación (Breadcrumbs) para NexoCampus."""
from typing import List, Optional, Sequence, Tuple, Union

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from .icons import icon


class Breadcrumb(QFrame):
    """Barra horizontal que muestra la ubicación del usuario en la jerarquía del sistema."""

    navigate_requested = Signal(str)

    # Mapa por defecto de páginas a rutas jerárquicas
    DEFAULT_ROUTES = {
        "Dashboard": [("Inicio", "Dashboard")],
        "Inicio": [("Inicio", "Dashboard")],
        "Facultades": [("Gestión Académica", None), ("Facultades", "Facultades")],
        "Programas": [("Gestión Académica", None), ("Programas", "Programas")],
        "Cursos": [("Gestión Académica", None), ("Cursos y Asignaturas", "Cursos")],
        "Estudiantes": [("Gestión Académica", None), ("Estudiantes", "Estudiantes")],
        "Profesores": [("Gestión Académica", None), ("Profesores", "Profesores")],
        "Administrativos": [("Gestión Administrativa", None), ("Personal Administrativo", "Administrativos")],
        "Inscripciones": [("Gestión Académica", None), ("Inscripciones y Matrículas", "Inscripciones")],
        "Nómina": [("Nómina", "Nómina")],
        "Reportes": [("Herramientas", None), ("Reportes", "Reportes")],
        "Períodos": [("Nómina", "Nómina"), ("Períodos Académicos", None)],
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("breadcrumbBar")
        self.setFixedHeight(38)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._current_page = "Dashboard"
        self._current_subpath = None
        self._segments: List[Tuple[str, Optional[str]]] = []

        self._build_ui()
        self.set_page("Dashboard")

    def _build_ui(self):
        self._root_layout = QHBoxLayout(self)
        self._root_layout.setContentsMargins(24, 0, 24, 0)
        self._root_layout.setSpacing(6)

        # Contenedor de segmentos de breadcrumb
        self._segments_container = QWidget()
        self._segments_container.setObjectName("breadcrumbSegmentsContainer")
        self._segments_layout = QHBoxLayout(self._segments_container)
        self._segments_layout.setContentsMargins(0, 0, 0, 0)
        self._segments_layout.setSpacing(6)
        self._root_layout.addWidget(self._segments_container)

        self._root_layout.addStretch()

        # Insignia de cambios no guardados
        self.unsaved_badge = QFrame()
        self.unsaved_badge.setObjectName("breadcrumbUnsavedBadge")
        badge_layout = QHBoxLayout(self.unsaved_badge)
        badge_layout.setContentsMargins(8, 3, 10, 3)
        badge_layout.setSpacing(6)

        dot_label = QLabel("●")
        dot_label.setObjectName("breadcrumbUnsavedDot")
        badge_layout.addWidget(dot_label)

        self.unsaved_text = QLabel("Cambios sin guardar (Ctrl+S)")
        self.unsaved_text.setObjectName("breadcrumbUnsavedText")
        badge_layout.addWidget(self.unsaved_text)

        self.unsaved_badge.setToolTip("Existen modificaciones en memoria pendientes de guardar en disco (Ctrl+S)")
        self.unsaved_badge.setVisible(False)
        self._root_layout.addWidget(self.unsaved_badge)

    def set_page(self, page_name: str, sub_path: Optional[str] = None):
        """Actualiza la ruta para una página conocida y sub-ruta opcional."""
        self._current_page = page_name
        self._current_subpath = sub_path

        base_route = self.DEFAULT_ROUTES.get(page_name)
        if base_route is None:
            route: List[Tuple[str, Optional[str]]] = [("Inicio", "Dashboard"), (page_name, page_name)]
        else:
            route = list(base_route)

        if sub_path:
            if route and route[-1][1] == page_name:
                route[-1] = (route[-1][0], page_name)
            route.append((sub_path, None))

        self.set_path(route)

    def set_path(self, segments: Sequence[Union[str, Tuple[str, Optional[str]]]]):
        """Configura la lista explícita de segmentos (texto, destino_navegacion_o_None)."""
        # Limpiar layout previo inmediatamente
        while self._segments_layout.count() > 0:
            item = self._segments_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        norm_segments: List[Tuple[str, Optional[str]]] = []
        for s in segments:
            if isinstance(s, tuple):
                norm_segments.append(s)
            else:
                norm_segments.append((str(s), None))

        self._segments = norm_segments
        total = len(norm_segments)

        for i, (label_text, target) in enumerate(norm_segments):
            is_last = (i == total - 1)

            if i == 0 and label_text == "Inicio":
                home_btn = QPushButton()
                home_btn.setObjectName("breadcrumbHomeButton")
                home_btn.setIcon(icon("home", "#64748B", 14))
                home_btn.setToolTip("Ir al Inicio (Dashboard)")
                home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                home_btn.clicked.connect(lambda _, t=target or "Dashboard": self._on_segment_clicked(t))
                self._segments_layout.addWidget(home_btn)

            if target and not is_last:
                btn = QPushButton(label_text)
                btn.setObjectName("breadcrumbLink")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda _, t=target: self._on_segment_clicked(t))
                self._segments_layout.addWidget(btn)
            elif not is_last:
                lbl = QLabel(label_text)
                lbl.setObjectName("breadcrumbAncestor")
                self._segments_layout.addWidget(lbl)
            else:
                lbl = QLabel(label_text)
                lbl.setObjectName("breadcrumbCurrent")
                self._segments_layout.addWidget(lbl)

            if not is_last:
                sep = QLabel("›")
                sep.setObjectName("breadcrumbSeparator")
                self._segments_layout.addWidget(sep)

    def get_text_path(self) -> str:
        """Retorna la representación textual plana de la ruta."""
        return " › ".join(label for label, _ in self._segments)

    def set_unsaved_indicator(self, has_unsaved: bool):
        """Muestra u oculta la insignia visual de cambios pendientes sin guardar."""
        self.unsaved_badge.setVisible(has_unsaved)

    def _on_segment_clicked(self, target: Optional[str]):
        if target:
            self.navigate_requested.emit(target)
