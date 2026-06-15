"""
Screen-EyeDropper.

Erfasst einen Screenshot des gesamten Bildschirms, zeigt ihn als
Vollbild-Overlay an, und laesst den User per Klick eine Farbe picken.
Die gepickte Farbe wird gegen alle geladenen Garn-Paletten gematcht und
liefert den nahesten Thread (CIE-Lab Delta-E) zurueck.

Headless-testbar: Die Pixel-Pick-Logik (`pick_color_at` und
`find_nearest_thread`) ist separat exposed.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor, QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout

from ...core.color_math import nearest_index_by_lab
from ...core.i18n import t
from ...core.palette import get_palette_manager
from ...core.thread import Thread


def pick_color_at(pixmap: QPixmap, x: int, y: int) -> Optional[QColor]:
    """Liest die Farbe an Pixel (x, y) im gegebenen Pixmap aus.

    Liefert None, wenn (x, y) ausserhalb der Pixmap liegt.
    """
    if pixmap.isNull():
        return None
    if x < 0 or y < 0 or x >= pixmap.width() or y >= pixmap.height():
        return None
    image = pixmap.toImage()
    return QColor(image.pixel(x, y))


def find_nearest_thread(
    color: QColor,
    palette_names: Optional[list[str]] = None,
) -> Optional[Thread]:
    """Findet den naehesten Thread in den angegebenen (oder allen) Paletten.

    Matching per CIE-Lab Delta-E. Wenn `palette_names=None`, werden alle
    geladenen Paletten durchsucht, Bead-Paletten ausgeschlossen.
    """
    pm = get_palette_manager()
    pm.load_all()

    if palette_names is None:
        palette_names = [
            n
            for n in pm.available_palettes
            if (pm.get_palette(n) and not pm.get_palette(n).is_beads)
        ]

    # Alle Threads sammeln
    all_threads: list[Thread] = []
    for name in palette_names:
        palette = pm.get_palette(name)
        if palette is not None:
            all_threads.extend(palette.threads)

    if not all_threads:
        return None

    best_idx = nearest_index_by_lab(
        (color.red(), color.green(), color.blue()),
        [(t.color.r, t.color.g, t.color.b) for t in all_threads],
    )
    return all_threads[best_idx]


class ScreenEyedropperDialog(QDialog):
    """Vollbild-Overlay mit Screenshot, das einen Klick zur Farbe konvertiert."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        self._picked_color: Optional[QColor] = None
        self._picked_thread: Optional[Thread] = None

        # Screenshot des Primaerbildschirms aufnehmen
        screen = QApplication.primaryScreen()
        if screen is None:
            # Headless-Fallback: leeres Pixmap
            self._screenshot = QPixmap(1, 1)
        else:
            self._screenshot = screen.grabWindow(0)

        # Vollbild ueber dem Screenshot
        if not self._screenshot.isNull():
            self.resize(self._screenshot.size())
            self.move(0, 0)

        self._setup_ui()

    @property
    def picked_color(self) -> Optional[QColor]:
        return self._picked_color

    @property
    def picked_thread(self) -> Optional[Thread]:
        return self._picked_thread

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Hint oben: "Klicke zum Picken, Esc zum Abbrechen"
        hint = QLabel(
            t("Klicke irgendwo auf den Bildschirm, um eine Farbe zu picken. Esc = abbrechen.")
        )
        hint.setStyleSheet(
            "background: rgba(0,0,0,180); color: white; "
            "padding: 8px 16px; font-size: 14px; font-weight: bold;"
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        layout.addStretch()

    def paintEvent(self, event) -> None:
        if self._screenshot.isNull():
            return
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._screenshot)
        # Halbtransparenter Overlay damit Klar wird, dass wir im Pick-Mode sind
        painter.fillRect(self.rect(), QColor(0, 0, 0, 30))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            self.reject()
            return
        pos = event.position().toPoint()
        color = pick_color_at(self._screenshot, pos.x(), pos.y())
        if color is None:
            self.reject()
            return
        self._picked_color = color
        # Naechsten Thread suchen
        self._picked_thread = find_nearest_thread(color)
        self.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)
