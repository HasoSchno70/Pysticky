"""
Fortschritts-Werkzeug zum Markieren von Stichen als erledigt.

Ermöglicht es dem Benutzer, Stiche als "gestickt" zu markieren,
um den Fortschritt beim Nachsticken eines Musters zu verfolgen.

Bedienung:
    - Linke Maustaste: Stich als erledigt markieren
    - Rechte Maustaste: Markierung aufheben
    - Drag: Mehrere Stiche auf einmal markieren/entmarkieren
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent

from .base_tool import BaseTool, ToolContext

# Sentinel-Werte für den Rückgabewert
# (werden im Canvas erkannt und als Completion-Signals weitergeleitet)
MARK_COMPLETED = -100
UNMARK_COMPLETED = -101


class ProgressTool(BaseTool):
    """
    Fortschritts-Werkzeug.

    Markiert oder entmarkiert Stiche als erledigt.
    Unterstützt Drag für schnelles Markieren mehrerer Stiche.
    """

    def __init__(self) -> None:
        super().__init__()
        self._last_pos: tuple[int, int] | None = None
        self._marking: bool = True  # True = markieren, False = entmarkieren

    def get_cursor(self) -> Qt.CursorShape:
        return Qt.CursorShape.PointingHandCursor

    def on_mouse_press(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        """Startet das Markieren/Entmarkieren."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._active = True
            self._marking = True
        elif event.button() == Qt.MouseButton.RightButton:
            self._active = True
            self._marking = False
        else:
            return []

        self._last_pos = (ctx.grid_x, ctx.grid_y)
        marker = MARK_COMPLETED if self._marking else UNMARK_COMPLETED

        if self._is_valid_pos(ctx, ctx.grid_x, ctx.grid_y):
            return [(ctx.grid_x, ctx.grid_y, marker)]
        return []

    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        """Markiert Stiche entlang des Drag-Pfades."""
        if not self._active:
            return []

        changes = []
        current = (ctx.grid_x, ctx.grid_y)
        marker = MARK_COMPLETED if self._marking else UNMARK_COMPLETED

        if self._last_pos and self._last_pos != current:
            # Bresenham-Linie zwischen letzter und aktueller Position
            points = self._get_line_points(
                self._last_pos[0], self._last_pos[1], current[0], current[1]
            )
            for x, y in points:
                if self._is_valid_pos(ctx, x, y):
                    changes.append((x, y, marker))

        self._last_pos = current
        return changes

    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        """Beendet das Markieren."""
        self._active = False
        self._last_pos = None
        return []

    def deactivate(self) -> None:
        """Setzt den Zustand zurück."""
        super().deactivate()
        self._last_pos = None
