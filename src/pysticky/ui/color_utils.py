"""
Qt-Adapter für die Core-Farbtypen.

`ThreadColor` (core/thread.py) bleibt bewusst Qt-frei — die Konvertierung
zu/von `QColor` und daraus abgeleitete UI-Bausteine (Farb-Swatch-Icons)
wohnen deshalb hier auf der UI-Seite.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

from ..core.thread import ThreadColor
from .styles import THEME


def to_qcolor(color: ThreadColor, alpha: int = 255) -> QColor:
    """Konvertiert eine ThreadColor in eine QColor (optional mit Alpha)."""
    return QColor(color.r, color.g, color.b, alpha)


def from_qcolor(qcolor: QColor) -> ThreadColor:
    """Konvertiert eine QColor in eine ThreadColor (Alpha wird verworfen)."""
    return ThreadColor(qcolor.red(), qcolor.green(), qcolor.blue())


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
    """
    qcolor = color if isinstance(color, QColor) else to_qcolor(color)
    pixmap = QPixmap(size, size)

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
