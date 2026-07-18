"""
Füll-Werkzeug (Flood Fill) mit Scanline-Algorithmus.
"""

from collections import deque

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QMouseEvent

from ...core.color_math import delta_e
from .base_tool import BaseTool, ToolContext

# Toleranz ist in den Settings 0-100% skaliert; 50 ΔE ist der praktische
# Ober-Wert, den similar_colors_dialog.py für "noch zusammenführbar" nutzt.
_MAX_TOLERANCE_DELTA_E = 50.0


class FillTool(BaseTool):
    """
    Füll-Werkzeug (Flood Fill / Farbeimer).

    - Klick: Füllt zusammenhängenden Bereich mit aktueller Farbe
    - Verwendet effizienten Scanline-Algorithmus
    - Farbtoleranz (Settings → Werkzeuge) erlaubt das Miteinschließen
      ähnlicher (nicht nur exakt gleicher) Nachbarfarben
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

        settings = QSettings()
        tolerance_pct = settings.value("fill_tolerance", 0, type=int)
        max_delta_e = _MAX_TOLERANCE_DELTA_E * (tolerance_pct / 100)

        # Einstellungen → Werkzeuge → Füllen → "Diagonal füllen": der
        # Scanline-Algorithmus ist strukturell 4-fach verbunden (scannt nur
        # links/rechts + direkt darueber/darunter) -- fuer 8-fach-
        # Konnektivitaet (auch diagonale Nachbarn) eine separate, simplere
        # BFS-Variante, die den schnellen Scanline-Pfad im Default-Fall
        # (False) unangetastet laesst.
        if settings.value("fill_diagonal", False, type=bool):
            return self._diagonal_fill(
                ctx, ctx.grid_x, ctx.grid_y, ctx.current_color_index, max_delta_e
            )

        # Flood Fill ausführen
        return self._scanline_fill(
            ctx, ctx.grid_x, ctx.grid_y, ctx.current_color_index, max_delta_e
        )

    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        return []

    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        return []

    def _scanline_fill(
        self,
        ctx: ToolContext,
        start_x: int,
        start_y: int,
        new_color_idx: int,
        max_delta_e: float = 0.0,
    ) -> list[tuple[int, int, int | None]]:
        """
        Scanline Flood-Fill-Algorithmus.

        Effizienter als rekursiver/stack-basierter Ansatz.
        Scannt horizontal und fügt Zeilen darüber/darunter zur Queue hinzu.

        max_delta_e > 0 lässt auch Nachbarfarben mitfüllen, die der
        Startfarbe farblich ähnlich (aber nicht identisch) sind.
        """
        layer = ctx.pattern.active_layer
        if not layer:
            return []

        target_color = layer.get_stitch(start_x, start_y)

        # Wenn gleiche Farbe, nichts tun
        if target_color == new_color_idx:
            return []

        target_rgb = None
        if max_delta_e > 0 and target_color is not None:
            target_entry = ctx.pattern.get_color_entry(target_color)
            if target_entry:
                target_rgb = target_entry.thread.color.to_tuple()

        def matches(idx: int | None) -> bool:
            if idx == target_color:
                return True
            if target_rgb is None or idx is None:
                return False
            entry = ctx.pattern.get_color_entry(idx)
            if not entry:
                return False
            return delta_e(target_rgb, entry.thread.color.to_tuple()) <= max_delta_e

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
            if not matches(layer.get_stitch(x, y)):
                continue

            # Nach links scannen bis zur Grenze
            left = x
            while (
                left > 0 and matches(layer.get_stitch(left - 1, y)) and (left - 1, y) not in visited
            ):
                left -= 1

            # Nach rechts scannen bis zur Grenze
            right = x
            while (
                right < width - 1
                and matches(layer.get_stitch(right + 1, y))
                and (right + 1, y) not in visited
            ):
                right += 1

            # Alle Pixel in dieser Zeile füllen
            for fill_x in range(left, right + 1):
                if (fill_x, y) not in visited:
                    # Nochmal prüfen (wichtig!)
                    if matches(layer.get_stitch(fill_x, y)):
                        visited.add((fill_x, y))
                        changes.append((fill_x, y, new_color_idx))

            # Zeilen darüber und darunter zur Queue hinzufügen
            for fill_x in range(left, right + 1):
                # Zeile darüber
                if y > 0 and (fill_x, y - 1) not in visited:
                    if matches(layer.get_stitch(fill_x, y - 1)):
                        queue.append((fill_x, y - 1))

                # Zeile darunter
                if y < height - 1 and (fill_x, y + 1) not in visited:
                    if matches(layer.get_stitch(fill_x, y + 1)):
                        queue.append((fill_x, y + 1))

        return changes

    def _diagonal_fill(
        self,
        ctx: ToolContext,
        start_x: int,
        start_y: int,
        new_color_idx: int,
        max_delta_e: float = 0.0,
    ) -> list[tuple[int, int, int | None]]:
        """8-fach verbundener Flood-Fill (inkl. diagonaler Nachbarn) per BFS.

        Einfacher, aber langsamer als der Scanline-Algorithmus -- nur
        aktiv, wenn "Diagonal füllen" eingeschaltet ist.
        """
        layer = ctx.pattern.active_layer
        if not layer:
            return []

        target_color = layer.get_stitch(start_x, start_y)
        if target_color == new_color_idx:
            return []

        target_rgb = None
        if max_delta_e > 0 and target_color is not None:
            target_entry = ctx.pattern.get_color_entry(target_color)
            if target_entry:
                target_rgb = target_entry.thread.color.to_tuple()

        def matches(idx: int | None) -> bool:
            if idx == target_color:
                return True
            if target_rgb is None or idx is None:
                return False
            entry = ctx.pattern.get_color_entry(idx)
            if not entry:
                return False
            return delta_e(target_rgb, entry.thread.color.to_tuple()) <= max_delta_e

        width = ctx.pattern.width
        height = ctx.pattern.height

        changes = []
        visited = {(start_x, start_y)}
        queue = deque([(start_x, start_y)])

        while queue:
            x, y = queue.popleft()
            if not matches(layer.get_stitch(x, y)):
                continue
            changes.append((x, y, new_color_idx))

            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < width and 0 <= ny < height):
                        continue
                    if (nx, ny) in visited:
                        continue
                    if matches(layer.get_stitch(nx, ny)):
                        visited.add((nx, ny))
                        queue.append((nx, ny))

        return changes
