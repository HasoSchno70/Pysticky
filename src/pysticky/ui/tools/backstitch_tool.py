"""
Rückstich-Tool (Backstitch) für Konturen und Details.
"""

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen

from ..color_utils import to_qcolor
from .base_tool import BaseTool, ToolContext


@dataclass
class BackstitchPreview:
    """Vorschau für Rückstich."""

    x1: int  # In halben Stichen
    y1: int
    x2: int
    y2: int
    color_index: int


@dataclass
class BackstitchAction:
    """Aktion für das Undo-System."""

    action: str  # "add" oder "remove"
    x1: int
    y1: int
    x2: int
    y2: int
    color_index: int


class BackstitchTool(BaseTool):
    """
    Rückstich-Werkzeug für Konturen und Details.

    Rückstiche sind Linien zwischen Eckpunkten/Mitten von Stichen.
    Sie werden über den normalen Kreuzstichen gezeichnet.

    Bedienung:
    - Linksklick: Startpunkt setzen, dann Endpunkt (Linie wird gezeichnet)
    - Weitere Klicks: Verkettete Linien (Endpunkt wird neuer Startpunkt)
    - Rechtsklick: Linie abbrechen ODER bestehenden Rückstich löschen
    - ESC: Linie abbrechen
    """

    def __init__(self):
        super().__init__()
        self._start_x: int | None = None
        self._start_y: int | None = None
        self._preview: BackstitchPreview | None = None
        self._snap_to_grid = True  # Snap zu Ecken/Mitten
        self._pending_action: BackstitchAction | None = None

    @property
    def snap_to_grid(self) -> bool:
        return self._snap_to_grid

    @snap_to_grid.setter
    def snap_to_grid(self, value: bool) -> None:
        self._snap_to_grid = value

    def activate(self) -> None:
        """Wird aufgerufen wenn das Werkzeug ausgewählt wird."""
        self._start_x = None
        self._start_y = None
        self._preview = None
        self._pending_action = None
        self._active = False

    def deactivate(self) -> None:
        """Wird aufgerufen wenn zu einem anderen Werkzeug gewechselt wird."""
        self._start_x = None
        self._start_y = None
        self._preview = None
        self._pending_action = None
        self._active = False

    def _to_half_stitch(self, screen_x: int, screen_y: int, ctx: ToolContext) -> tuple[int, int]:
        """
        Konvertiert Bildschirm-Koordinaten zu halben Stichen.

        Snap-Punkte:
        - Ecken: (0,0), (2,0), (0,2), (2,2)
        - Mitte: (1,1)
        - Kanten-Mitten: (1,0), (0,1), (2,1), (1,2)
        """
        cell_size = ctx.cell_size

        # Relative Position zum Offset
        rel_x = screen_x - ctx.offset_x
        rel_y = screen_y - ctx.offset_y

        # Zelle bestimmen
        cell_x = rel_x // cell_size
        cell_y = rel_y // cell_size

        # Position innerhalb der Zelle
        in_cell_x = rel_x % cell_size
        in_cell_y = rel_y % cell_size

        # Basis-Position (Zelle in halben Stichen)
        base_x = cell_x * 2
        base_y = cell_y * 2

        if self._snap_to_grid:
            # Snap zu nächstem Punkt (Drittel der Zelle)
            third = cell_size // 3

            if in_cell_x < third:
                snap_x = 0
            elif in_cell_x < 2 * third:
                snap_x = 1
            else:
                snap_x = 2

            if in_cell_y < third:
                snap_y = 0
            elif in_cell_y < 2 * third:
                snap_y = 1
            else:
                snap_y = 2

            return (base_x + snap_x, base_y + snap_y)
        else:
            # Kontinuierlich (2 Punkte pro Zelle)
            snap_x = 0 if in_cell_x < cell_size // 2 else 2
            snap_y = 0 if in_cell_y < cell_size // 2 else 2
            return (base_x + snap_x, base_y + snap_y)

    def on_mouse_press(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        """Mausklick verarbeiten."""
        self._pending_action = None

        # Rechtsklick: Abbrechen oder Löschen
        if event.button() == Qt.MouseButton.RightButton:
            if self._start_x is not None:
                # Aktive Linie abbrechen
                self._start_x = None
                self._start_y = None
                self._preview = None
                self._active = False
            else:
                # Versuchen, Rückstich an Position zu löschen
                half_x, half_y = self._to_half_stitch(
                    int(event.position().x()), int(event.position().y()), ctx
                )
                # Suche den Backstitch zum Löschen
                bs = ctx.pattern.backstitch_manager.find_at(half_x, half_y, tolerance=2)
                if bs:
                    self._pending_action = BackstitchAction(
                        action="remove",
                        x1=bs.x1,
                        y1=bs.y1,
                        x2=bs.x2,
                        y2=bs.y2,
                        color_index=bs.color_index,
                    )
            return []

        # Linksklick
        if event.button() != Qt.MouseButton.LeftButton:
            return []

        half_x, half_y = self._to_half_stitch(
            int(event.position().x()), int(event.position().y()), ctx
        )

        if self._start_x is None:
            # Startpunkt setzen
            self._start_x = half_x
            self._start_y = half_y
            self._active = True
        else:
            # Endpunkt - Backstitch erstellen
            if half_x != self._start_x or half_y != self._start_y:
                self._pending_action = BackstitchAction(
                    action="add",
                    x1=self._start_x,
                    y1=self._start_y,
                    x2=half_x,
                    y2=half_y,
                    color_index=ctx.current_color_index,
                )
                # Für verkettete Linien: Endpunkt wird neuer Startpunkt
                self._start_x = half_x
                self._start_y = half_y
                self._preview = None
                # _active bleibt True für verkettete Linien

        return []  # Keine Stich-Änderungen

    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        """Mausbewegung verarbeiten."""
        if self._start_x is not None:
            half_x, half_y = self._to_half_stitch(
                int(event.position().x()), int(event.position().y()), ctx
            )

            if half_x != self._start_x or half_y != self._start_y:
                self._preview = BackstitchPreview(
                    self._start_x, self._start_y, half_x, half_y, ctx.current_color_index
                )
            else:
                self._preview = None

        return []

    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        """Maustaste losgelassen."""
        return []

    def on_key_press(self, ctx: ToolContext, event) -> bool:
        """Tastendruck verarbeiten."""
        from PySide6.QtCore import Qt

        if event.key() == Qt.Key.Key_Escape:
            # Linie abbrechen
            if self._start_x is not None:
                self._start_x = None
                self._start_y = None
                self._preview = None
                self._active = False
                return True

        return False

    def draw_preview(self, ctx: ToolContext, painter: QPainter) -> None:
        """
        Zeichnet die Vorschau des Backstitch.

        Hinweis: Das Canvas zeichnet die Vorschau bereits in _draw_backstitches.
        Diese Methode wird hier für Konsistenz mit anderen Tools implementiert,
        aber das Canvas kann entscheiden, welche Methode es verwendet.
        """
        if not self._active:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        half_cell = ctx.cell_size // 2

        # Startpunkt anzeigen
        if self._start_x is not None and self._start_y is not None:
            sx = self._start_x * half_cell + ctx.offset_x
            sy = self._start_y * half_cell + ctx.offset_y

            painter.setPen(QPen(QColor(110, 198, 160), 2))
            painter.setBrush(QColor(110, 198, 160, 150))
            painter.drawEllipse(sx - 5, sy - 5, 10, 10)

        # Vorschau-Linie
        if self._preview:
            entry = ctx.pattern.get_color_entry(self._preview.color_index)
            if entry:
                color = to_qcolor(entry.thread.color)
            else:
                color = QColor(110, 198, 160)

            x1 = self._preview.x1 * half_cell + ctx.offset_x
            y1 = self._preview.y1 * half_cell + ctx.offset_y
            x2 = self._preview.x2 * half_cell + ctx.offset_x
            y2 = self._preview.y2 * half_cell + ctx.offset_y

            # Gestrichelte Vorschau
            pen = QPen(color, max(2, ctx.cell_size // 6), Qt.PenStyle.DashLine)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(x1, y1, x2, y2)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    @property
    def preview(self) -> BackstitchPreview | None:
        """Gibt die aktuelle Vorschau zurück."""
        return self._preview

    @property
    def start_point(self) -> tuple[int, int] | None:
        """Gibt den aktuellen Startpunkt zurück (oder None)."""
        if self._start_x is not None:
            return (self._start_x, self._start_y)
        return None

    @property
    def has_start_point(self) -> bool:
        """Gibt zurück, ob ein Startpunkt gesetzt ist."""
        return self._start_x is not None

    @property
    def pending_action(self) -> BackstitchAction | None:
        """Gibt die ausstehende Aktion zurück und löscht sie."""
        action = self._pending_action
        self._pending_action = None
        return action

    def get_cursor(self) -> Qt.CursorShape:
        """Gibt den Cursor für dieses Werkzeug zurück."""
        return Qt.CursorShape.CrossCursor

    def cancel(self) -> None:
        """Bricht die aktuelle Linie ab."""
        self._start_x = None
        self._start_y = None
        self._preview = None
        self._active = False
        self._pending_action = None
