"""
Bewegen-Werkzeug (Hand-Tool / Pan).

Reines Navigations-Tool im Photoshop-Stil:
- Linksklick + Drag pannt die Ansicht.
- Klick allein setzt keinen Stich — der Tool-Code gibt leere Change-Listen
  zurueck; die Pan-Logik selbst sitzt im Canvas-EventsMixin und wird
  aktiviert, sobald das MOVE-Tool ausgewaehlt ist.
- Mittelmaus-Pan bleibt unabhaengig vom aktiven Werkzeug verfuegbar.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent

from .base_tool import BaseTool, ToolContext


class MoveTool(BaseTool):
    """No-op-Werkzeug fuer Pan-Navigation."""

    def get_cursor(self) -> Qt.CursorShape:
        return Qt.CursorShape.OpenHandCursor

    def on_mouse_press(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        return []

    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        return []

    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        return []
