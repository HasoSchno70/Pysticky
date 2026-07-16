"""
Koordinaten-Mixin für Canvas.

Enthält Methoden zur Koordinaten-Umrechnung und Viewport-Berechnung.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect

from ....utils import clamp_int

if TYPE_CHECKING:
    from ..canvas import CrossStitchCanvas


class CoordinatesMixin:
    """Mixin für Koordinaten-Umrechnung und Viewport-Berechnung."""

    def _screen_to_grid(self: "CrossStitchCanvas", screen_x: int, screen_y: int) -> tuple[int, int]:
        """Konvertiert Screen-Koordinaten zu Grid-Koordinaten."""
        grid_x = (screen_x - self._offset_x) // self._cell_size
        grid_y = (screen_y - self._offset_y) // self._cell_size
        return (grid_x, grid_y)

    def _grid_to_screen(self: "CrossStitchCanvas", grid_x: int, grid_y: int) -> tuple[int, int]:
        """Konvertiert Grid-Koordinaten zu Screen-Koordinaten."""
        screen_x = grid_x * self._cell_size + self._offset_x
        screen_y = grid_y * self._cell_size + self._offset_y
        return (screen_x, screen_y)

    def _is_valid_grid_pos(self: "CrossStitchCanvas", x: int, y: int) -> bool:
        """Prüft ob eine Grid-Position gültig ist."""
        if not self._pattern:
            return False
        return 0 <= x < self._pattern.width and 0 <= y < self._pattern.height

    def _center_pattern(self: "CrossStitchCanvas") -> None:
        """Zentriert das Pattern im Canvas."""
        if not self._pattern:
            return

        pattern_width = self._pattern.width * self._cell_size
        pattern_height = self._pattern.height * self._cell_size

        self._offset_x = (self.width() - pattern_width) // 2
        self._offset_y = (self.height() - pattern_height) // 2

        self.offset_changed.emit(self._offset_x, self._offset_y)

    def _get_visible_grid_rect(self: "CrossStitchCanvas") -> QRect:
        """Berechnet den sichtbaren Grid-Bereich (für Viewport-Culling)."""
        if not self._pattern:
            return QRect()

        start_x = max(0, (-self._offset_x) // self._cell_size)
        start_y = max(0, (-self._offset_y) // self._cell_size)

        end_x = min(
            self._pattern.width,
            (self.width() - self._offset_x + self._cell_size - 1) // self._cell_size,
        )
        end_y = min(
            self._pattern.height,
            (self.height() - self._offset_y + self._cell_size - 1) // self._cell_size,
        )

        return QRect(start_x, start_y, max(0, end_x - start_x), max(0, end_y - start_y))

    def snap_position(self: "CrossStitchCanvas", x: int, y: int) -> tuple[int, int]:
        """Rundet Position auf Snap-Grid."""
        if not self._snap_to_grid:
            return (x, y)

        interval = self._snap_interval
        snapped_x = round(x / interval) * interval
        snapped_y = round(y / interval) * interval

        if self._pattern:
            snapped_x = clamp_int(snapped_x, 0, self._pattern.width - 1)
            snapped_y = clamp_int(snapped_y, 0, self._pattern.height - 1)

        return (snapped_x, snapped_y)
