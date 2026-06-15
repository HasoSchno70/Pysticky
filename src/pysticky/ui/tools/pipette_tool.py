"""
Pipetten-Werkzeug zum Aufnehmen von Farben.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent

from .base_tool import BaseTool, ToolContext


class PipetteTool(BaseTool):
    """
    Pipetten-Werkzeug zum Aufnehmen von Farben.

    - Klick: Nimmt die Farbe an der Position auf
    - Emittiert Signal mit Farbindex
    """

    def __init__(self) -> None:
        super().__init__()
        self._picked_color_index: int | None = None

    def get_cursor(self) -> Qt.CursorShape:
        return Qt.CursorShape.CrossCursor

    @property
    def picked_color_index(self) -> int | None:
        """Gibt den zuletzt aufgenommenen Farbindex zurück."""
        return self._picked_color_index

    def on_mouse_press(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if event.button() != Qt.MouseButton.LeftButton:
            return []

        if not self._is_valid_pos(ctx, ctx.grid_x, ctx.grid_y):
            return []

        # Farbe an Position holen
        layer = ctx.pattern.active_layer
        if layer:
            color_idx = layer.get_stitch(ctx.grid_x, ctx.grid_y)
            if color_idx is not None:
                self._picked_color_index = color_idx

        # Keine Änderungen am Muster
        return []

    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        return []

    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        return []
