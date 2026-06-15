"""
Linien-Werkzeug zum Zeichnen gerader Linien.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen

from .base_tool import BaseTool, ToolContext


class LineTool(BaseTool):
    """
    Linien-Werkzeug für gerade Linien.

    - Klicken und Ziehen für Start- und Endpunkt
    - Vorschau während des Ziehens
    - Shift gedrückt: Nur horizontale/vertikale/diagonale Linien
    """

    def __init__(self) -> None:
        super().__init__()
        self._shift_held = False

    def get_cursor(self) -> Qt.CursorShape:
        return Qt.CursorShape.CrossCursor

    def on_mouse_press(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if event.button() != Qt.MouseButton.LeftButton:
            return []

        self._active = True
        # Snap-to-Grid anwenden
        x, y = ctx.snap(ctx.grid_x, ctx.grid_y)
        self._start_pos = (x, y)
        self._current_pos = self._start_pos
        self._shift_held = event.modifiers() & Qt.KeyboardModifier.ShiftModifier

        return []  # Noch keine Änderungen

    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if not self._active:
            return []

        self._shift_held = event.modifiers() & Qt.KeyboardModifier.ShiftModifier

        # Snap-to-Grid anwenden
        x, y = ctx.snap(ctx.grid_x, ctx.grid_y)
        self._current_pos = self._constrain_angle(x, y) if self._shift_held else (x, y)

        return []  # Vorschau wird in draw_preview gezeichnet

    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if event.button() != Qt.MouseButton.LeftButton or not self._active:
            return []

        self._active = False

        if not self._start_pos or not self._current_pos:
            return []

        # Snap-to-Grid anwenden für Endposition
        x, y = ctx.snap(ctx.grid_x, ctx.grid_y)
        end_pos = self._constrain_angle(x, y) if self._shift_held else (x, y)

        # Linie berechnen
        points = self._get_line_points(
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

    def _constrain_angle(self, x: int, y: int) -> tuple[int, int]:
        """Beschränkt auf 0°, 45°, 90° Winkel."""
        if not self._start_pos:
            return (x, y)

        dx = x - self._start_pos[0]
        dy = y - self._start_pos[1]

        adx, ady = abs(dx), abs(dy)

        # Näher an horizontal oder vertikal?
        if adx > 2 * ady:
            # Horizontal
            return (x, self._start_pos[1])
        elif ady > 2 * adx:
            # Vertikal
            return (self._start_pos[0], y)
        else:
            # Diagonal (45°)
            length = max(adx, ady)
            sx = 1 if dx >= 0 else -1
            sy = 1 if dy >= 0 else -1
            return (self._start_pos[0] + length * sx, self._start_pos[1] + length * sy)

    def draw_preview(self, ctx: ToolContext, painter: QPainter) -> None:
        if not self._active or not self._start_pos or not self._current_pos:
            return

        # Vorschau-Punkte berechnen
        points = self._get_line_points(
            self._start_pos[0], self._start_pos[1], self._current_pos[0], self._current_pos[1]
        )

        # Halbtransparent in aktueller Farbe zeichnen
        color_entry = ctx.pattern.get_color_entry(ctx.current_color_index)
        if color_entry:
            color = QColor(
                color_entry.thread.color.r,
                color_entry.thread.color.g,
                color_entry.thread.color.b,
                150,  # Halbtransparent
            )
        else:
            color = QColor(100, 200, 150, 150)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)

        for gx, gy in points:
            if self._is_valid_pos(ctx, gx, gy):
                sx, sy = self._grid_to_screen(ctx, gx, gy)
                painter.drawRect(sx, sy, ctx.cell_size, ctx.cell_size)

        # Umrandung für Vorschau
        painter.setPen(QPen(QColor(110, 198, 160), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Start-Punkt markieren
        sx, sy = self._grid_to_screen(ctx, self._start_pos[0], self._start_pos[1])
        painter.drawRect(sx, sy, ctx.cell_size, ctx.cell_size)

        # End-Punkt markieren
        ex, ey = self._grid_to_screen(ctx, self._current_pos[0], self._current_pos[1])
        painter.drawRect(ex, ey, ctx.cell_size, ctx.cell_size)

    def deactivate(self) -> None:
        super().deactivate()
        self._shift_held = False
