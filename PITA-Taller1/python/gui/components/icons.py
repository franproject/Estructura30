"""Iconos vectoriales compartidos por los componentes de NexoCampus."""
from PySide6.QtCore import QByteArray, QSize
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


_PATHS = {
    "home": '<path d="M10 2L3 8v10h5v-6h4v6h5V8z"/>',
    "building": '<rect x="2" y="7" width="16" height="11" rx="1"/><path d="M1 7l9-5 9 5"/><rect x="8" y="13" width="4" height="5"/><rect x="5" y="9" width="2" height="2"/><rect x="13" y="9" width="2" height="2"/>',
    "hat": '<ellipse cx="10" cy="10" rx="8" ry="2.5"/><path d="M4 10.5c0 3 2.686 5.5 6 5.5s6-2.5 6-5.5"/><path d="M10 2v8"/><circle cx="10" cy="2" r="1.2"/>',
    "book": '<path d="M4 3h9a2 2 0 012 2v11a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2z"/><path d="M15 3a2 2 0 012 2v11a2 2 0 01-2 2"/><path d="M7 8h4M7 12h4"/>',
    "user": '<circle cx="10" cy="7" r="3.5"/><path d="M3 17c0-3.866 3.134-7 7-7s7 3.134 7 7"/>',
    "users": '<circle cx="7.5" cy="7" r="3"/><path d="M1 17c0-3.314 2.91-6 6.5-6"/><circle cx="13" cy="7" r="3"/><path d="M19 17c0-3.314-2.91-6-6.5-6"/>',
    "briefcase": '<rect x="2" y="7" width="16" height="11" rx="2"/><path d="M7 7V5a1 1 0 011-1h4a1 1 0 011 1v2M2 12h16"/>',
    "clipboard": '<rect x="4" y="4" width="12" height="14" rx="2"/><path d="M8 4V3a1 1 0 011-1h2a1 1 0 011 1v1M7 9h6M7 13h4"/>',
    "money": '<circle cx="10" cy="10" r="8"/><path d="M10 6v8M8 8.5a1.5 1.5 0 003 0c0-.828-.5-1.5-1.5-1.5S8 7.672 8 8.5V11a1.5 1.5 0 003 0"/>',
    "chart": '<rect x="3" y="10" width="3" height="7" rx="1"/><rect x="8.5" y="6" width="3" height="11" rx="1"/><rect x="14" y="3" width="3" height="14" rx="1"/><path d="M2 18h16"/>',
    "gear": '<circle cx="10" cy="10" r="2.5"/><path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.22 4.22l1.42 1.42M14.36 14.36l1.42 1.42M4.22 15.78l1.42-1.42M14.36 5.64l1.42-1.42"/>',
    "logout": '<path d="M13 4H5a1 1 0 00-1 1v10a1 1 0 001 1h8M16 10H8M13 7l3 3-3 3"/>',
    "bell": '<path d="M10 2a6 6 0 016 6v3l1.5 2.5H2.5L4 11V8a6 6 0 016-6zM8.5 17a1.5 1.5 0 003 0"/>',
    "search": '<circle cx="8.5" cy="8.5" r="5.5"/><path d="M13 13l4 4"/>',
    "save": '<path d="M3 3h11l3 3v11H3zM6 3v5h7V3M6 17v-5h8v5"/>',
    "refresh": '<path d="M17 10a7 7 0 01-12.6 4.2M3 10a7 7 0 0112.6-4.2M3 14v-4h4M17 6v4h-4"/>',
    "edit": '<path d="M14.5 2.5a2.121 2.121 0 013 3L7 16H4v-3z"/>',
    "trash": '<path d="M4 7h12M8 7V4h4v3M6 7l1 10h6l1-10"/>',
    "warning": '<path d="M10 2L1 18h18L10 2z"/><path d="M10 8v4M10 15h.01"/>',
    "download": '<path d="M10 3v10M6 9l4 4 4-4M3 17h14"/>',
    "eye": '<path d="M1 10s3-6 9-6 9 6 9 6-3 6-9 6-9-6-9-6z"/><circle cx="10" cy="10" r="3"/>',
    "wallet": '<path d="M2 5a2 2 0 012-2h12a2 2 0 012 2v2H2V5z"/><path d="M2 7h16v10a2 2 0 01-2 2H4a2 2 0 01-2-2V7z"/><circle cx="14" cy="12" r="1.5"/>',
    "clipboard-check": '<rect x="4" y="4" width="12" height="14" rx="2"/><path d="M8 4V3a1 1 0 011-1h2a1 1 0 011 1v1M7 11l2 2 4-4"/>',
    "book-open": '<path d="M2 4a2 2 0 012-2h5v15H4a2 2 0 00-2 2V4zM18 4a2 2 0 00-2-2h-5v15h5a2 2 0 012 2V4z"/>',
    "chevron-left": '<path d="M12 15l-5-5 5-5"/>',
    "chevron-right": '<path d="M8 5l5 5-5 5"/>',
    "arrow-right": '<path d="M4 10h12M12 6l4 4-4 4"/>',
    "check": '<polyline points="4 10 8 14 16 6"/>',
    "layers": '<polygon points="10 2 18 6 10 10 2 6 10 2"/><path d="M2 10l8 4 8-4M2 14l8 4 8-4"/>',
    "bolt": '<polygon points="11 1 3 11 9 11 8 19 17 8 11 8 11 1"/>',
    "file-text": '<path d="M12 2H4a2 2 0 00-2 2v12a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zM12 2v6h6M6 12h8M6 15h5"/>',
}


def pixmap(name: str, color: str = "#64748B", size: int = 18, dpr: float = 1.0) -> QPixmap:
    """Renderiza un icono SVG en un QPixmap de alta nitidez para un factor de escala específico."""
    body = _PATHS.get(name, _PATHS["home"])
    effective_px = max(1, int(round(size * dpr)))
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{effective_px}" height="{effective_px}" '
        f'viewBox="0 0 20 20" fill="none" stroke="{color}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )
    pm = QPixmap(QSize(effective_px, effective_px))
    pm.fill("transparent")
    painter = QPainter(pm)
    QSvgRenderer(QByteArray(svg.encode("utf-8"))).render(painter)
    painter.end()
    if dpr != 1.0:
        pm.setDevicePixelRatio(dpr)
    return pm


def icon(name: str, color: str = "#64748B", size: int = 18) -> QIcon:
    """Renderiza un icono SVG multi-resolución para garantizar nitidez a 100%, 125%, 150% y 200%."""
    q_icon = QIcon()
    for scale in (1.0, 1.25, 1.5, 2.0):
        q_icon.addPixmap(pixmap(name, color=color, size=size, dpr=scale))
    return q_icon