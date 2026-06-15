"""
Füll-Werkzeug (Flood Fill) mit Scanline-Algorithmus.
"""

from collections import deque

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent

from .base_tool import BaseTool, ToolContext


class FillTool(BaseTool):
    """
    Füll-Werkzeug (Flood Fill / Farbeimer).

    - Klick: Füllt zusammenhängenden Bereich mit aktueller Farbe
    - Verwendet effizienten Scanline-Algorithmus
    """

    def get_cursor(self) -> Qt.CursorShape:
        return Qt.CursorShape.PointingHandCursor

    def on_mouse_press(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if event.button() != Qt.MouseButton.LeftButton:
            return []

        if not self._is_valid_pos(ctx, ctx.grid_x, ctx.grid_y):
            return []

        # Flood Fill ausführen
        return self._scanline_fill(ctx, ctx.grid_x, ctx.grid_y, ctx.current_color_index)

    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        return []

    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        return []

    def _scanline_fill(
        self, ctx: ToolContext, start_x: int, start_y: int, new_color_idx: int
    ) -> list[tuple[int, int, int | None]]:
        """
        Scanline Flood-Fill-Algorithmus.

        Effizienter als rekursiver/stack-basierter Ansatz.
        Scannt horizontal und fügt Zeilen darüber/darunter zur Queue hinzu.
        """
        layer = ctx.pattern.active_layer
        if not layer:
            return []

        target_color = layer.get_stitch(start_x, start_y)

        # Wenn gleiche Farbe, nichts tun
        if target_color == new_color_idx:
            return []

        width = ctx.pattern.width
        height = ctx.pattern.height

        changes = []
        visited = set()
        queue = deque()
        queue.append((start_x, start_y))

        while queue:
            x, y = queue.popleft()

            # Bereits besucht?
            if (x, y) in visited:
                continue

            # Gültige Position?
            if not (0 <= x < width and 0 <= y < height):
                continue

            # Richtige Farbe?
            if layer.get_stitch(x, y) != target_color:
                continue

            # Nach links scannen bis zur Grenze
            left = x
            while (
                left > 0
                and layer.get_stitch(left - 1, y) == target_color
                and (left - 1, y) not in visited
            ):
                left -= 1

            # Nach rechts scannen bis zur Grenze
            right = x
            while (
                right < width - 1
                and layer.get_stitch(right + 1, y) == target_color
                and (right + 1, y) not in visited
            ):
                right += 1

            # Alle Pixel in dieser Zeile füllen
            for fill_x in range(left, right + 1):
                if (fill_x, y) not in visited:
                    # Nochmal prüfen (wichtig!)
                    if layer.get_stitch(fill_x, y) == target_color:
                        visited.add((fill_x, y))
                        changes.append((fill_x, y, new_color_idx))

            # Zeilen darüber und darunter zur Queue hinzufügen
            for fill_x in range(left, right + 1):
                # Zeile darüber
                if y > 0 and (fill_x, y - 1) not in visited:
                    if layer.get_stitch(fill_x, y - 1) == target_color:
                        queue.append((fill_x, y - 1))

                # Zeile darunter
                if y < height - 1 and (fill_x, y + 1) not in visited:
                    if layer.get_stitch(fill_x, y + 1) == target_color:
                        queue.append((fill_x, y + 1))

        return changes
