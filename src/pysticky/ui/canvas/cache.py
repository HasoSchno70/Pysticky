"""
Cache-Manager für Canvas-Rendering.

Verwaltet Farb-Cache für QColor-Objekte um wiederholte
Objekterstellung zu vermeiden.
"""

from PySide6.QtGui import QColor


class CanvasCache:
    """
    Cache-Manager für Canvas-Rendering.

    Verwaltet Farb-Cache für QColor-Objekte um wiederholte
    Objekterstellung zu vermeiden.
    """

    def __init__(self) -> None:
        # QColor-Cache (Key: RGBA als int)
        self._color_cache: dict[int, QColor] = {}

        # Symbol-Farben (für helle/dunkle Hintergründe)
        self._symbol_colors: dict[bool, QColor] = {
            True: QColor(0, 0, 0),  # Für helle Farben -> schwarzer Text
            False: QColor(255, 255, 255),  # Für dunkle Farben -> weißer Text
        }

    def get_color(self, r: int, g: int, b: int, a: int = 255) -> QColor:
        """Gibt eine gecachte QColor zurück."""
        key = (r << 24) | (g << 16) | (b << 8) | a
        if key not in self._color_cache:
            self._color_cache[key] = QColor(r, g, b, a)
        return self._color_cache[key]

    def get_symbol_color(self, is_light_background: bool) -> QColor:
        """Gibt die Symbol-Farbe für hellen/dunklen Hintergrund zurück."""
        return self._symbol_colors[is_light_background]

    def clear(self) -> None:
        """Leert den Farb-Cache."""
        self._color_cache.clear()
