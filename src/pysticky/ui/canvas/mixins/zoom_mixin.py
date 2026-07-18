"""
Zoom-Mixin für Canvas.

Enthält alle Zoom-Funktionen.
"""

from typing import TYPE_CHECKING

from ....utils import clamp_int

if TYPE_CHECKING:
    from ..canvas import CrossStitchCanvas


class ZoomMixin:
    """Mixin für Zoom-Funktionalität."""

    def zoom_in(self: "CrossStitchCanvas") -> None:
        """Vergrößert die Ansicht multiplikativ um ZOOM_STEP (mind. +1px,
        damit kleine Zellgrößen bei ZOOM_STEP nahe 1.0 nicht steckenbleiben)."""
        target = max(self._cell_size + 1, round(self._cell_size * self.ZOOM_STEP))
        self._set_cell_size(min(target, self.MAX_CELL_SIZE))

    def zoom_out(self: "CrossStitchCanvas") -> None:
        """Verkleinert die Ansicht multiplikativ um ZOOM_STEP (mind. -1px)."""
        target = min(self._cell_size - 1, round(self._cell_size / self.ZOOM_STEP))
        self._set_cell_size(max(target, self.MIN_CELL_SIZE))

    def zoom_fit(self: "CrossStitchCanvas") -> None:
        """Passt die Ansicht an das Fenster an."""
        if not self._pattern:
            return

        available_width = self.width() - 40
        available_height = self.height() - 40

        cell_w = available_width // self._pattern.width
        cell_h = available_height // self._pattern.height

        new_size = max(self.MIN_CELL_SIZE, min(cell_w, cell_h, self.MAX_CELL_SIZE))
        self._set_cell_size(new_size)
        self._center_pattern()

    def zoom_reset(self: "CrossStitchCanvas") -> None:
        """Setzt den Zoom auf 100% zurück."""
        self._set_cell_size(self.DEFAULT_CELL_SIZE)
        self._center_pattern()

    def set_zoom(self: "CrossStitchCanvas", factor: float) -> None:
        """Setzt den Zoom-Faktor (1.0 = 100%)."""
        new_size = int(self.DEFAULT_CELL_SIZE * factor)
        new_size = clamp_int(new_size, self.MIN_CELL_SIZE, self.MAX_CELL_SIZE)
        self._set_cell_size(new_size)

    def get_zoom_percent(self: "CrossStitchCanvas") -> float:
        """Gibt den aktuellen Zoom in Prozent zurück."""
        return (self._cell_size / self.DEFAULT_CELL_SIZE) * 100.0

    def _set_cell_size(self: "CrossStitchCanvas", size: int) -> None:
        """Setzt die Zellgröße und aktualisiert die Ansicht."""
        old_size = self._cell_size
        self._cell_size = size

        if self._pattern:
            # Zoom um Bildschirmmitte
            center_x = self.width() // 2
            center_y = self.height() // 2

            grid_x = (center_x - self._offset_x) / old_size
            grid_y = (center_y - self._offset_y) / old_size

            self._offset_x = int(center_x - grid_x * self._cell_size)
            self._offset_y = int(center_y - grid_y * self._cell_size)

        self.zoom_changed.emit(self._cell_size / self.DEFAULT_CELL_SIZE)
        self.offset_changed.emit(self._offset_x, self._offset_y)
        self.update()
