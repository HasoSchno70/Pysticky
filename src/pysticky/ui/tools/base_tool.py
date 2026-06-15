"""
Basis-Klasse für alle Zeichenwerkzeuge.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QPainter

if TYPE_CHECKING:
    from ...core import Pattern
    from ..canvas import CrossStitchCanvas


@dataclass
class ToolContext:
    """Kontext-Informationen für Werkzeuge."""

    canvas: "CrossStitchCanvas"
    pattern: "Pattern"
    current_color_index: int
    grid_x: int
    grid_y: int
    screen_x: int
    screen_y: int
    cell_size: int
    offset_x: int
    offset_y: int

    def snap(self, x: int, y: int) -> tuple[int, int]:
        """Rastet Koordinaten auf das magnetische Raster ein (falls aktiviert)."""
        return self.canvas.snap_position(x, y)

    @property
    def snap_enabled(self) -> bool:
        """Prüft ob Snap-to-Grid aktiviert ist."""
        return self.canvas.snap_to_grid

    @property
    def snap_interval(self) -> int:
        """Gibt das Snap-Intervall zurück."""
        return self.canvas.snap_interval


class BaseTool(ABC):
    """
    Abstrakte Basis-Klasse für alle Zeichenwerkzeuge.

    Jedes Werkzeug implementiert seine eigene Logik für:
    - Mausinteraktionen (press, move, release)
    - Vorschau-Zeichnung
    - Tastatureingaben
    """

    def __init__(self) -> None:
        self._active = False
        self._start_pos: tuple[int, int] | None = None
        self._current_pos: tuple[int, int] | None = None

    @property
    def name(self) -> str:
        """Name des Werkzeugs."""
        return self.__class__.__name__.replace("Tool", "")

    @property
    def is_active(self) -> bool:
        """Gibt zurück ob das Werkzeug gerade aktiv ist (z.B. beim Zeichnen)."""
        return self._active

    def activate(self) -> None:
        """Wird aufgerufen wenn das Werkzeug ausgewählt wird."""
        self._active = False
        self._start_pos = None
        self._current_pos = None

    def deactivate(self) -> None:
        """Wird aufgerufen wenn zu einem anderen Werkzeug gewechselt wird."""
        self._active = False
        self._start_pos = None
        self._current_pos = None

    @abstractmethod
    def on_mouse_press(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        """
        Maus gedrückt.

        Returns:
            Liste von (x, y, color_index) Änderungen. color_index=None bedeutet löschen.
        """
        pass

    @abstractmethod
    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        """
        Maus bewegt (während gedrückt).

        Returns:
            Liste von (x, y, color_index) Änderungen.
        """
        pass

    @abstractmethod
    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        """
        Maus losgelassen.

        Returns:
            Liste von (x, y, color_index) Änderungen.
        """
        pass

    def on_key_press(self, ctx: ToolContext, event: QKeyEvent) -> bool:
        """
        Taste gedrückt.

        Returns:
            True wenn das Event behandelt wurde.
        """
        return False

    def draw_preview(self, ctx: ToolContext, painter: QPainter) -> None:
        """
        Zeichnet eine Vorschau (z.B. Linie während des Ziehens).

        Wird bei jedem Paint-Event aufgerufen wenn das Werkzeug aktiv ist.
        """
        pass

    def get_cursor(self) -> Qt.CursorShape:
        """Gibt den Cursor für dieses Werkzeug zurück."""
        return Qt.CursorShape.ArrowCursor

    # === Hilfsmethoden ===

    def _grid_to_screen(self, ctx: ToolContext, gx: int, gy: int) -> tuple[int, int]:
        """Konvertiert Grid- zu Bildschirmkoordinaten."""
        return (gx * ctx.cell_size + ctx.offset_x, gy * ctx.cell_size + ctx.offset_y)

    def _is_valid_pos(self, ctx: ToolContext, x: int, y: int) -> bool:
        """Prüft ob eine Position gültig ist."""
        return 0 <= x < ctx.pattern.width and 0 <= y < ctx.pattern.height

    def _get_line_points(self, x1: int, y1: int, x2: int, y2: int) -> list[tuple[int, int]]:
        """Bresenham-Algorithmus für Linien."""
        points = []
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        x, y = x1, y1
        while True:
            points.append((x, y))
            if x == x2 and y == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

        return points
