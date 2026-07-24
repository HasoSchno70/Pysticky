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

        # Farbe an Position holen -- das muss dieselbe Farbe sein, die der
        # Canvas an dieser Zelle tatsaechlich anzeigt (sichtbares Composite
        # ueber alle Layer, oberstes sichtbares Layer gewinnt), nicht die des
        # aktiven Layers. Vorher las die Pipette immer nur
        # `ctx.pattern.active_layer`: war der aktive Layer an dieser Stelle
        # leer oder von einem hoeheren sichtbaren Layer ueberdeckt, nahm die
        # Pipette entweder gar keine Farbe auf oder eine falsche (verdeckte)
        # Farbe, obwohl der Nutzer visuell eindeutig eine andere Farbe sieht.
        # Ausnahme: Im "Nur aktive Ebene anzeigen"-Modus zeigt der Canvas
        # ebenfalls nur den aktiven Layer -- dann muss die Pipette dem folgen.
        if ctx.canvas.show_only_active_layer:
            color_idx = ctx.pattern.get_stitch_on_active_layer(ctx.grid_x, ctx.grid_y)
        else:
            color_idx = ctx.pattern.get_stitch(ctx.grid_x, ctx.grid_y)
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
