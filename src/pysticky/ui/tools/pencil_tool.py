"""
Stift-Werkzeug zum Zeichnen einzelner Stiche.

Unterstützt Tablet-Pressure: Wenn ein Stift mit Druck aktiv ist, wird die
Brush-Größe proportional zum Druck moduliert (0..max_brush_size, kreis-
förmig). Bei Maus-Eingabe (Pressure = 0) wird ein einzelner Stich gesetzt.
"""

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QMouseEvent

from .base_tool import BaseTool, ToolContext


class PencilTool(BaseTool):
    """
    Stift-Werkzeug für freihändiges Zeichnen.

    - Linke Maustaste: Stiche setzen
    - Zeichnet kontinuierlich beim Ziehen (mit Linien-Interpolation)
    - Mit Tablet-Stift: Brush-Größe via Druckstärke
    """

    def __init__(self) -> None:
        super().__init__()
        self._last_pos: tuple[int, int] | None = None
        # Cached pro Press-Event: max-brush und ob Pressure aktiv ist.
        # So müssen wir QSettings nicht pro Move-Event neu lesen.
        self._brush_max_size: int = 1
        self._pressure_enabled: bool = False

    def get_cursor(self) -> Qt.CursorShape:
        return Qt.CursorShape.ArrowCursor

    def _refresh_brush_settings(self) -> None:
        """Liest die Tablet-Brush-Settings einmal pro Press-Event."""
        s = QSettings()
        self._pressure_enabled = s.value("tablet/pressure_enabled", True, type=bool)
        # max_brush_size: 1 = aus (immer einzelner Stich)
        self._brush_max_size = max(1, int(s.value("tablet/max_brush_size", 5, type=int)))

    def _brush_cells(self, ctx: ToolContext, cx: int, cy: int) -> list[tuple[int, int]]:
        """
        Berechnet die zu zeichnenden Zellen rund um (cx, cy) basierend
        auf der aktuellen Tablet-Pressure.

        Bei Pressure=0 oder deaktiviertem Pressure: nur die Zentrumszelle.
        Bei Pressure>0: kreisförmiger Brush mit Radius = round(pressure * (max_size - 1)).
        """
        if not self._pressure_enabled or self._brush_max_size <= 1:
            return [(cx, cy)]

        canvas = ctx.canvas
        # Defensiv: nur Float-Werte akzeptieren (Mock-Objekte ignorieren)
        raw_pressure = getattr(canvas, "_tablet_pressure", 0.0)
        raw_in_use = getattr(canvas, "_tablet_in_use", False)
        if not isinstance(raw_pressure, (int, float)):
            return [(cx, cy)]
        if not isinstance(raw_in_use, bool):
            return [(cx, cy)]
        if not raw_in_use or raw_pressure <= 0.0:
            return [(cx, cy)]
        pressure = float(raw_pressure)

        radius = int(round(pressure * (self._brush_max_size - 1)))
        if radius <= 0:
            return [(cx, cy)]

        cells: list[tuple[int, int]] = []
        r_sq = radius * radius
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= r_sq:
                    cells.append((cx + dx, cy + dy))
        return cells

    def on_mouse_press(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if event.button() != Qt.MouseButton.LeftButton:
            return []

        self._active = True
        self._last_pos = (ctx.grid_x, ctx.grid_y)
        self._refresh_brush_settings()

        return self._collect_changes(ctx, ctx.grid_x, ctx.grid_y)

    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if not self._active:
            return []

        changes: list[tuple[int, int, int | None]] = []
        current = (ctx.grid_x, ctx.grid_y)

        # Linie zwischen letzter und aktueller Position interpolieren
        if self._last_pos and self._last_pos != current:
            points = self._get_line_points(
                self._last_pos[0], self._last_pos[1], current[0], current[1]
            )

            for x, y in points:
                changes.extend(self._collect_changes(ctx, x, y))
        else:
            changes.extend(self._collect_changes(ctx, current[0], current[1]))

        self._last_pos = current
        return changes

    def _collect_changes(
        self, ctx: ToolContext, cx: int, cy: int
    ) -> list[tuple[int, int, int | None]]:
        """Erzeugt Änderungen für alle Brush-Zellen rund um (cx, cy)."""
        result: list[tuple[int, int, int | None]] = []
        for x, y in self._brush_cells(ctx, cx, cy):
            if self._is_valid_pos(ctx, x, y):
                result.append((x, y, ctx.current_color_index))
        return result

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
