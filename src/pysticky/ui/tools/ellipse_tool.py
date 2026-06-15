"""
Ellipsen-Werkzeug zum Zeichnen von Ellipsen/Kreisen.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen

from .base_tool import BaseTool, ToolContext


class EllipseTool(BaseTool):
    """
    Ellipsen-Werkzeug.

    - Klicken und Ziehen für Bounding Box
    - filled=False: Nur Umriss
    - filled=True: Gefüllte Ellipse
    - Shift gedrückt: Kreis
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
        self._current_pos = self._constrain_circle(x, y) if self._shift_held else (x, y)

        return []

    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if event.button() != Qt.MouseButton.LeftButton or not self._active:
            return []

        self._active = False

        if not self._start_pos or not self._current_pos:
            return []

        # Snap-to-Grid
        x, y = ctx.snap(ctx.grid_x, ctx.grid_y)
        end_pos = self._constrain_circle(x, y) if self._shift_held else (x, y)

        points = self._get_ellipse_points(
            self._start_pos[0], self._start_pos[1], end_pos[0], end_pos[1]
        )

        changes = []
        for x, y in points:
            if self._is_valid_pos(ctx, x, y):
                changes.append((x, y, ctx.current_color_index))

        self._start_pos = None
        self._current_pos = None

        return changes

    def _constrain_circle(self, x: int, y: int) -> tuple[int, int]:
        """Beschränkt auf einen Kreis."""
        if not self._start_pos:
            return (x, y)

        dx = x - self._start_pos[0]
        dy = y - self._start_pos[1]

        size = max(abs(dx), abs(dy))
        sx = 1 if dx >= 0 else -1
        sy = 1 if dy >= 0 else -1

        return (self._start_pos[0] + size * sx, self._start_pos[1] + size * sy)

    def _get_ellipse_points(self, x1: int, y1: int, x2: int, y2: int) -> list[tuple[int, int]]:
        """Punkte für eine Ellipse (Midpoint-Algorithmus)."""
        points = set()

        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        rx = abs(x2 - x1) // 2
        ry = abs(y2 - y1) // 2

        if rx == 0 and ry == 0:
            return [(cx, cy)]

        if rx == 0:
            # Vertikale Linie
            for y in range(min(y1, y2), max(y1, y2) + 1):
                points.add((cx, y))
            return list(points)

        if ry == 0:
            # Horizontale Linie
            for x in range(min(x1, x2), max(x1, x2) + 1):
                points.add((x, cy))
            return list(points)

        # Midpoint Ellipse Algorithm
        x, y = 0, ry
        rx2, ry2 = rx * rx, ry * ry

        # Region 1
        p1 = ry2 - rx2 * ry + 0.25 * rx2
        while ry2 * x < rx2 * y:
            if self._filled:
                for xi in range(cx - x, cx + x + 1):
                    points.add((xi, cy + y))
                    points.add((xi, cy - y))
            else:
                points.add((cx + x, cy + y))
                points.add((cx - x, cy + y))
                points.add((cx + x, cy - y))
                points.add((cx - x, cy - y))

            x += 1
            if p1 < 0:
                p1 += 2 * ry2 * x + ry2
            else:
                y -= 1
                p1 += 2 * ry2 * x - 2 * rx2 * y + ry2

        # Region 2
        p2 = ry2 * (x + 0.5) ** 2 + rx2 * (y - 1) ** 2 - rx2 * ry2
        while y >= 0:
            if self._filled:
                for xi in range(cx - x, cx + x + 1):
                    points.add((xi, cy + y))
                    points.add((xi, cy - y))
            else:
                points.add((cx + x, cy + y))
                points.add((cx - x, cy + y))
                points.add((cx + x, cy - y))
                points.add((cx - x, cy - y))

            y -= 1
            if p2 > 0:
                p2 += rx2 - 2 * rx2 * y
            else:
                x += 1
                p2 += 2 * ry2 * x - 2 * rx2 * y + rx2

        return list(points)

    def draw_preview(self, ctx: ToolContext, painter: QPainter) -> None:
        if not self._active or not self._start_pos or not self._current_pos:
            return

        points = self._get_ellipse_points(
            self._start_pos[0], self._start_pos[1], self._current_pos[0], self._current_pos[1]
        )

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

        # Bounding Box
        min_x = min(self._start_pos[0], self._current_pos[0])
        min_y = min(self._start_pos[1], self._current_pos[1])
        max_x = max(self._start_pos[0], self._current_pos[0])
        max_y = max(self._start_pos[1], self._current_pos[1])

        sx, sy = self._grid_to_screen(ctx, min_x, min_y)
        w = (max_x - min_x + 1) * ctx.cell_size
        h = (max_y - min_y + 1) * ctx.cell_size

        painter.setPen(QPen(QColor(110, 198, 160, 100), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(sx, sy, w, h)

    def deactivate(self) -> None:
        super().deactivate()
        self._shift_held = False
