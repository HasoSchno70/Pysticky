"""
Farbverlauf-Tool für automatische Übergänge zwischen 2 Farben.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen

from ...core.color_math import delta_e
from ...utils import clamp_int
from ..color_utils import to_qcolor
from .base_tool import BaseTool, ToolContext


class GradientTool(BaseTool):
    """
    Werkzeug zum Zeichnen von Farbverläufen.

    Der Benutzer wählt Startfarbe und Endfarbe, dann zieht er
    eine Linie. Die Farben werden automatisch interpoliert.
    """

    def __init__(self) -> None:
        super().__init__()
        self._start_pos: tuple[int, int] | None = None
        self._end_pos: tuple[int, int] | None = None
        self._start_color_index: int = 0
        self._end_color_index: int = 1
        self._preview_points: list[tuple[int, int, int]] = []  # x, y, color_index

    def get_cursor(self) -> Qt.CursorShape:
        return Qt.CursorShape.CrossCursor

    def set_start_color(self, index: int) -> None:
        """Setzt die Startfarbe."""
        self._start_color_index = index

    def set_end_color(self, index: int) -> None:
        """Setzt die Endfarbe."""
        self._end_color_index = index

    @property
    def start_color_index(self) -> int:
        return self._start_color_index

    @property
    def end_color_index(self) -> int:
        return self._end_color_index

    def activate(self) -> None:
        super().activate()
        self._start_pos = None
        self._end_pos = None
        self._preview_points = []

    def deactivate(self) -> None:
        super().deactivate()
        self._start_pos = None
        self._end_pos = None
        self._preview_points = []

    def on_mouse_press(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if event.button() != Qt.MouseButton.LeftButton:
            return []

        if not ctx.pattern:
            return []

        x, y = ctx.grid_x, ctx.grid_y
        if not (0 <= x < ctx.pattern.width and 0 <= y < ctx.pattern.height):
            return []

        self._start_pos = (x, y)
        self._end_pos = (x, y)
        self._start_color_index = ctx.current_color_index
        self._preview_points = []

        return []

    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if self._start_pos is None:
            return []

        if not ctx.pattern:
            return []

        x = clamp_int(ctx.grid_x, 0, ctx.pattern.width - 1)
        y = clamp_int(ctx.grid_y, 0, ctx.pattern.height - 1)
        self._end_pos = (x, y)

        # Vorschau berechnen
        self._calculate_gradient(ctx)

        return []

    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if event.button() != Qt.MouseButton.LeftButton:
            return []

        if self._start_pos is None or self._end_pos is None:
            return []

        # Finale Punkte berechnen
        self._calculate_gradient(ctx)

        # Änderungen zurückgeben
        changes = [(x, y, color_idx) for x, y, color_idx in self._preview_points]

        # Reset
        self._start_pos = None
        self._end_pos = None
        self._preview_points = []

        return changes

    def _calculate_gradient(self, ctx: ToolContext) -> None:
        """Berechnet die Punkte des Farbverlaufs."""
        if self._start_pos is None or self._end_pos is None:
            return

        if not ctx.pattern or len(ctx.pattern.color_entries) < 2:
            return

        x1, y1 = self._start_pos
        x2, y2 = self._end_pos

        # Bresenham-Linie für die Punkte
        points = self._bresenham_line(x1, y1, x2, y2)

        if len(points) <= 1:
            # Nur ein Punkt
            self._preview_points = [(x1, y1, self._start_color_index)]
            return

        # Farben der beiden Endpunkte holen
        start_entry = ctx.pattern.get_color_entry(self._start_color_index)
        end_entry = ctx.pattern.get_color_entry(self._end_color_index)

        if not start_entry or not end_entry:
            return

        start_rgb = (
            start_entry.thread.color.r,
            start_entry.thread.color.g,
            start_entry.thread.color.b,
        )
        end_rgb = (end_entry.thread.color.r, end_entry.thread.color.g, end_entry.thread.color.b)

        # Punkte mit interpolierten Farben
        self._preview_points = []
        num_points = len(points)

        for i, (x, y) in enumerate(points):
            # Interpolationsfaktor (0 bis 1)
            t = i / max(1, num_points - 1)

            # Interpolierte Farbe berechnen
            interp_r = int(start_rgb[0] + t * (end_rgb[0] - start_rgb[0]))
            interp_g = int(start_rgb[1] + t * (end_rgb[1] - start_rgb[1]))
            interp_b = int(start_rgb[2] + t * (end_rgb[2] - start_rgb[2]))

            # Nächste passende Farbe in der Palette finden
            best_idx = self._find_closest_color(ctx.pattern, interp_r, interp_g, interp_b)

            self._preview_points.append((x, y, best_idx))

    def _find_closest_color(self, pattern, r: int, g: int, b: int) -> int:
        """Findet die ähnlichste Farbe in der Palette.

        Nutzt CIEDE2000 (wie fill_tool.py/palette_conversion_dialog.py/
        similar_colors_dialog.py etc.), nicht rohe RGB-Euklid-Distanz --
        letztere gewichtet Helligkeits- vs. Farbton-Unterschiede anders als
        menschliche Wahrnehmung und konnte bei einem Farbverlauf sichtbar
        falsche/unruhige Zwischenfarben waehlen.
        """
        best_dist = float("inf")
        best_idx = 0
        target_rgb = (r, g, b)

        for i, entry in enumerate(pattern.color_entries):
            c = entry.thread.color
            dist = delta_e(target_rgb, (c.r, c.g, c.b))

            if dist < best_dist:
                best_dist = dist
                best_idx = i

        return best_idx

    def _bresenham_line(self, x1: int, y1: int, x2: int, y2: int) -> list[tuple[int, int]]:
        """Bresenham-Linienalgorithmus."""
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

    def draw_preview(self, ctx: ToolContext, painter: QPainter) -> None:
        """Zeichnet die Vorschau des Farbverlaufs."""
        if not self._preview_points or not ctx.pattern:
            return

        cell_size = ctx.cell_size
        offset_x = ctx.offset_x
        offset_y = ctx.offset_y

        for x, y, color_idx in self._preview_points:
            entry = ctx.pattern.get_color_entry(color_idx)
            if entry:
                color = to_qcolor(entry.thread.color, 180)  # Halbtransparent

                screen_x = x * cell_size + offset_x
                screen_y = y * cell_size + offset_y

                painter.fillRect(screen_x, screen_y, cell_size, cell_size, color)

        # Start- und Endpunkt markieren
        if self._start_pos:
            x, y = self._start_pos
            screen_x = x * cell_size + offset_x
            screen_y = y * cell_size + offset_y
            painter.setPen(QPen(QColor(0, 255, 0), 2))
            painter.drawRect(screen_x, screen_y, cell_size, cell_size)

        if self._end_pos:
            x, y = self._end_pos
            screen_x = x * cell_size + offset_x
            screen_y = y * cell_size + offset_y
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawRect(screen_x, screen_y, cell_size, cell_size)
