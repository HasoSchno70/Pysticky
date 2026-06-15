"""
Radierer-Werkzeug zum Entfernen von Stichen.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent

from .base_tool import BaseTool, ToolContext


class EraserTool(BaseTool):
    """
    Radierer-Werkzeug zum Löschen von Stichen.

    - Linke Maustaste: Stiche entfernen
    - Kontinuierliches Löschen beim Ziehen
    """

    def __init__(self) -> None:
        super().__init__()
        self._last_pos: tuple[int, int] | None = None

    def get_cursor(self) -> Qt.CursorShape:
        return Qt.CursorShape.ArrowCursor

    def on_mouse_press(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if event.button() != Qt.MouseButton.LeftButton:
            return []

        self._active = True
        self._last_pos = (ctx.grid_x, ctx.grid_y)

        if self._is_valid_pos(ctx, ctx.grid_x, ctx.grid_y):
            return [(ctx.grid_x, ctx.grid_y, None)]  # None = löschen
        return []

    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if not self._active:
            return []

        changes = []
        current = (ctx.grid_x, ctx.grid_y)

        # Linie zwischen letzter und aktueller Position interpolieren
        if self._last_pos and self._last_pos != current:
            points = self._get_line_points(
                self._last_pos[0], self._last_pos[1], current[0], current[1]
            )

            for x, y in points:
                if self._is_valid_pos(ctx, x, y):
                    changes.append((x, y, None))  # None = löschen

        self._last_pos = current
        return changes

    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if event.button() != Qt.MouseButton.LeftButton:
            return []

        self._active = False
        self._last_pos = None
        return []

    def deactivate(self) -> None:
        super().deactivate()
        self._last_pos = None
