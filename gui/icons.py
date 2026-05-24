"""
gui/icons.py — Icone SVG minimali (stile line-art) renderizzate via QSvgRenderer.

Tutte le icone usano `currentColor` come segnaposto, sostituito al render con
il colore desiderato (di default: text dim del tema). Approccio "Feather-like":
stroke 2px, no fill, line-cap rotondo, viewBox 24×24.

Uso:
    from gui.icons import icon, app_icon, ICON_CHAT
    btn.setIcon(icon(ICON_CHAT, color="#7aa2f7", size=18))
"""

from __future__ import annotations

from functools import lru_cache

from PyQt6.QtCore import Qt, QSize, QByteArray
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer


# ── Wrapper SVG base ─────────────────────────────────────────────

_WRAP = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
)


def _svg(body: str) -> str:
    return _WRAP.format(body=body)


# ── Icone funzioni (sidebar / azioni) ────────────────────────────

# Chat / message
ICON_CHAT = _svg(
    '<path d="M21 12a8 8 0 0 1-11.6 7.13L4 21l1.87-5.4A8 8 0 1 1 21 12z"/>'
)

# Folder
ICON_FOLDER = _svg(
    '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'
)

# Folder open
ICON_FOLDER_OPEN = _svg(
    '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v1"/>'
    '<path d="M3 9h18l-2 9a2 2 0 0 1-2 1.5H5A2 2 0 0 1 3 18z"/>'
)

# Search / magnifier
ICON_SEARCH = _svg(
    '<circle cx="11" cy="11" r="7"/>'
    '<line x1="21" y1="21" x2="16.65" y2="16.65"/>'
)

# Bar chart / analyze
ICON_CHART = _svg(
    '<line x1="6"  y1="20" x2="6"  y2="13"/>'
    '<line x1="12" y1="20" x2="12" y2="8"/>'
    '<line x1="18" y1="20" x2="18" y2="4"/>'
    '<line x1="3"  y1="20" x2="21" y2="20"/>'
)

# Document / read content (semantic)
ICON_DOC = _svg(
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
    '<polyline points="14 2 14 8 20 8"/>'
    '<line x1="8" y1="13" x2="16" y2="13"/>'
    '<line x1="8" y1="17" x2="13" y2="17"/>'
)

# Archive / backup
ICON_ARCHIVE = _svg(
    '<rect x="2"  y="3"  width="20" height="5"  rx="1"/>'
    '<path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/>'
    '<line x1="10" y1="12" x2="14" y2="12"/>'
)

# Settings / gear
ICON_SETTINGS = _svg(
    '<circle cx="12" cy="12" r="3"/>'
    '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>'
)

# Trash / clear
ICON_TRASH = _svg(
    '<polyline points="3 6 5 6 21 6"/>'
    '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
    '<line x1="10" y1="11" x2="10" y2="17"/>'
    '<line x1="14" y1="11" x2="14" y2="17"/>'
)

# Send / arrow
ICON_SEND = _svg(
    '<line x1="22" y1="2" x2="11" y2="13"/>'
    '<polygon points="22 2 15 22 11 13 2 9 22 2"/>'
)

# Stop / square
ICON_STOP = _svg(
    '<rect x="6" y="6" width="12" height="12" rx="1"/>'
)

# Refresh / swap
ICON_REFRESH = _svg(
    '<polyline points="21 4 21 10 15 10"/>'
    '<polyline points="3 20 3 14 9 14"/>'
    '<path d="M3.51 9a9 9 0 0 1 14.85-3.36L21 9"/>'
    '<path d="M20.49 15a9 9 0 0 1-14.85 3.36L3 15"/>'
)

# CPU / model chip
ICON_CHIP = _svg(
    '<rect x="6" y="6" width="12" height="12" rx="1"/>'
    '<rect x="9" y="9"  width="6" height="6" rx="0.5"/>'
    '<line x1="9"  y1="2" x2="9"  y2="4"/>'
    '<line x1="15" y1="2" x2="15" y2="4"/>'
    '<line x1="9"  y1="20" x2="9"  y2="22"/>'
    '<line x1="15" y1="20" x2="15" y2="22"/>'
    '<line x1="20" y1="9"  x2="22" y2="9"/>'
    '<line x1="20" y1="15" x2="22" y2="15"/>'
    '<line x1="2"  y1="9"  x2="4"  y2="9"/>'
    '<line x1="2"  y1="15" x2="4"  y2="15"/>'
)


# ── Logo dell'applicazione ───────────────────────────────────────

APP_LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" '
    'fill="none" stroke="currentColor" stroke-width="3" '
    'stroke-linecap="round" stroke-linejoin="round">'
    # Cartella stilizzata
    '<path d="M8 18a4 4 0 0 1 4-4h12l4 5h24a4 4 0 0 1 4 4v23a4 4 0 0 1-4 4H12'
    'a4 4 0 0 1-4-4z" fill="ACCENT_FILL"/>'
    # Cerchio "AI" sopra
    '<circle cx="44" cy="32" r="6" fill="white" stroke="currentColor"/>'
    '<circle cx="44" cy="32" r="2" fill="currentColor" stroke="none"/>'
    # Linee orizzontali (file)
    '<line x1="16" y1="32" x2="32" y2="32"/>'
    '<line x1="16" y1="40" x2="28" y2="40"/>'
    '</svg>'
)


# ── Render ───────────────────────────────────────────────────────

def _render(svg: str, color: str, size: int) -> QPixmap:
    s = svg.replace("currentColor", color).replace("ACCENT_FILL", color + "30")
    renderer = QSvgRenderer(QByteArray(s.encode("utf-8")))
    pix = QPixmap(QSize(size, size))
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter)
    painter.end()
    return pix


@lru_cache(maxsize=128)
def icon(svg: str, color: str = "#c0caf5", size: int = 18) -> QIcon:
    """Crea un QIcon a partire da una stringa SVG."""
    return QIcon(_render(svg, color, size))


def app_icon(color: str = "#7aa2f7") -> QIcon:
    """Icona dell'app, con varianti a più risoluzioni (per taskbar e finestra)."""
    ico = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        ico.addPixmap(_render(APP_LOGO_SVG, color, s))
    return ico
