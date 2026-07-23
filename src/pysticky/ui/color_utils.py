"""
Qt-Adapter für die Core-Farbtypen.

`ThreadColor` (core/thread.py) bleibt bewusst Qt-frei — die Konvertierung
zu/von `QColor` und daraus abgeleitete UI-Bausteine (Farb-Swatch-Icons)
wohnen deshalb hier auf der UI-Seite.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPen, QPixmap

from ..core.thread import ThreadColor
from .styles import THEME


def to_qcolor(color: ThreadColor, alpha: int = 255) -> QColor:
    """Konvertiert eine ThreadColor in eine QColor (optional mit Alpha)."""
    return QColor(color.r, color.g, color.b, alpha)


def from_qcolor(qcolor: QColor) -> ThreadColor:
    """Konvertiert eine QColor in eine ThreadColor (Alpha wird verworfen)."""
    return ThreadColor(qcolor.red(), qcolor.green(), qcolor.blue())


def _relative_luminance(color: QColor) -> float:
    """BT.601-Luminanz (konsistent mit ThreadColor.luminance)."""
    return (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255.0


def _wcag_contrast_ratio(lum_a: float, lum_b: float) -> float:
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


def ensure_contrast(color: QColor, background: QColor, min_ratio: float = 2.0) -> QColor:
    """Gibt `color` unverändert zurück, wenn sie ausreichend Kontrast gegen
    `background` hat -- sonst eine helle/dunkle Alternative je nach
    Hintergrund-Helligkeit.

    Gitterlinienfarben sind seit der Canvas-Settings-Verdrahtung
    (canvas-settings-wiring-2026-07) frei einstellbar, ebenso die
    Hintergrundfarbe leerer Zellen (empty_cell_color) -- eine feste, einmal
    gegen einen hellen Default abgestimmte Gitterfarbe (siehe
    grid-contrast-fix-2026-07) kann seitdem mit jeder beliebigen
    Hintergrundfarbe kollidieren. Diese Funktion macht die Wahl
    self-healing statt nur den einen Default-Fall zu fixen.
    """
    bg_lum = _relative_luminance(background)
    color_lum = _relative_luminance(color)
    if _wcag_contrast_ratio(bg_lum, color_lum) >= min_ratio:
        return color
    return QColor(210, 210, 210) if bg_lum < 0.5 else QColor(55, 55, 55)


def color_swatch_icon(
    color: ThreadColor | QColor,
    size: int = 16,
    *,
    rounded: bool = False,
    border: bool = True,
) -> QIcon:
    """
    Erstellt ein quadratisches Farb-Swatch-Icon (z.B. für Listen/Comboboxen).

    Args:
        color: Die darzustellende Farbe.
        size: Kantenlänge in Pixeln.
        rounded: Abgerundete Ecken mit Theme-Rahmen (für Garn-Listen).
        border: Grauer Rahmen um das Quadrat; ohne Rahmen wird nur gefüllt.

    Die Pixmap wird in physischen Pixeln angelegt (HiDPI-Audit Runde 41,
    Nachtrag zu Runde 40) -- sonst erscheint das Swatch auf einem
    HiDPI-Bildschirm unscharf hochskaliert, dasselbe Grundmuster wie
    `IconProvider._render_emoji_icon` (`ui/icons/icon_provider.py`). Alle
    Zeichenoperationen unten bleiben unverändert in logischen
    (`size`-basierten) Koordinaten. Nicht gecacht -- wird bei jedem Aufruf
    frisch gerendert, daher genügt eine statische Bildschirm-DPR-Lesung ohne
    Cache-Key-Beteiligung.
    """
    qcolor = color if isinstance(color, QColor) else to_qcolor(color)
    screen = QGuiApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen is not None else 1.0
    pixmap = QPixmap(max(1, round(size * dpr)), max(1, round(size * dpr)))
    pixmap.setDevicePixelRatio(dpr)

    if rounded:
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(qcolor)
        painter.setPen(QPen(QColor(THEME.border_light), 1))
        painter.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)
        painter.end()
    elif border:
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(1, 1, size - 2, size - 2, qcolor)
        painter.setPen(QColor(80, 80, 80))
        painter.drawRect(0, 0, size - 1, size - 1)
        painter.end()
    else:
        pixmap.fill(qcolor)

    return QIcon(pixmap)
