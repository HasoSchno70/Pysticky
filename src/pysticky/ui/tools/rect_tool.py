"""
Rechteck-Werkzeug zum Zeichnen von Rechtecken.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen

from .base_tool import BaseTool, ToolContext


class RectTool(BaseTool):
    """
    Rechteck-Werkzeug.

    - Klicken und Ziehen für Eckpunkte
    - filled=False: Nur Umriss
    - filled=True: Gefülltes Rechteck
    - Shift gedrückt: Quadrat
    """

    def __init__(self, filled: bool = False) -> None:
        super().__init__()
        self._filled = filled
        self._shift_held = False

    def get_cursor(self) -> Qt.CursorShape:
        return Qt.CursorShape.CrossCursor

    def on_mouse_press(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if event.button() != Qt.MouseButton.LeftButton:
            return []

        self._active = True
        # Snap-to-Grid
        x, y = ctx.snap(ctx.grid_x, ctx.grid_y)
        self._start_pos = (x, y)
        self._current_pos = self._start_pos
        self._shift_held = event.modifiers() & Qt.KeyboardModifier.ShiftModifier

        return []

    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if not self._active:
            return []

        self._shift_held = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        # Snap-to-Grid
        x, y = ctx.snap(ctx.grid_x, ctx.grid_y)
        self._current_pos = self._constrain_square(x, y) if self._shift_held else (x, y)

        return []

    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if event.button() != Qt.MouseButton.LeftButton or not self._active:
            return []

        self._active = False

        if not self._start_pos or not self._current_pos:
            return []

        # Snap-to-Grid für Endposition
        x, y = ctx.snap(ctx.grid_x, ctx.grid_y)
        end_pos = self._constrain_square(x, y) if self._shift_held else (x, y)

        # Rechteck berechnen
        points = self._get_rect_points(
            self._start_pos[0], self._start_pos[1], end_pos[0], end_pos[1]
        )

        # Änderungen sammeln
        changes = []
        for x, y in points:
            if self._is_valid_pos(ctx, x, y):
                changes.append((x, y, ctx.current_color_index))

        self._start_pos = None
        self._current_pos = None

        return changes

    def _constrain_square(self, x: int, y: int) -> tuple[int, int]:
        """Beschränkt auf ein Quadrat."""
        if not self._start_pos:
            return (x, y)

        dx = x - self._start_pos[0]
        dy = y - self._start_pos[1]

        # Größere Dimension als Seitenlänge
        size = max(abs(dx), abs(dy))
        sx = 1 if dx >= 0 else -1
        sy = 1 if dy >= 0 else -1

        return (self._start_pos[0] + size * sx, self._start_pos[1] + size * sy)

    def _get_rect_points(self, x1: int, y1: int, x2: int, y2: int) -> list[tuple[int, int]]:
        """Punkte für ein Rechteck."""
        points = []
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)

        if self._filled:
            # Gefüllt
            for y in range(min_y, max_y + 1):
                for x in range(min_x, max_x + 1):
                    points.append((x, y))
        else:
            # Nur Umriss
            for x in range(min_x, max_x + 1):
                points.append((x, min_y))
                points.append((x, max_y))
            for y in range(min_y + 1, max_y):
                points.append((min_x, y))
                points.append((max_x, y))

        return points

    def draw_preview(self, ctx: ToolContext, painter: QPainter) -> None:
        if not self._active or not self._start_pos or not self._current_pos:
            return

        # Vorschau-Punkte berechnen
        points = self._get_rect_points(
            self._start_pos[0], self._start_pos[1], self._current_pos[0], self._current_pos[1]
        )

        # Halbtransparent in aktueller Farbe zeichnen
        color_entry = ctx.pattern.get_color_entry(ctx.current_color_index)
        if color_entry:
            color = QColor(
                color_entry.thread.color.r,
                color_entry.thread.color.g,
                color_entry.thread.color.b,
                150,
            )
        else:
            color = QColor(100, 200, 150, 150)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)

        for gx, gy in points:
            if self._is_valid_pos(ctx, gx, gy):
                sx, sy = self._grid_to_screen(ctx, gx, gy)
                painter.drawRect(sx, sy, ctx.cell_size, ctx.cell_size)

        # Umrandung
        min_x = min(self._start_pos[0], self._current_pos[0])
        min_y = min(self._start_pos[1], self._current_pos[1])
        max_x = max(self._start_pos[0], self._current_pos[0])
        max_y = max(self._start_pos[1], self._current_pos[1])

        sx, sy = self._grid_to_screen(ctx, min_x, min_y)
        w = (max_x - min_x + 1) * ctx.cell_size
        h = (max_y - min_y + 1) * ctx.cell_size

        painter.setPen(QPen(QColor(110, 198, 160), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(sx, sy, w, h)

    def deactivate(self) -> None:
        super().deactivate()
        self._shift_held = False
