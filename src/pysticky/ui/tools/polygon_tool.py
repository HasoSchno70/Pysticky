"""
Polygon-Werkzeug zum Zeichnen von Polygonen.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen

from ..color_utils import to_qcolor
from ..styles import THEME
from .base_tool import BaseTool, ToolContext


class PolygonTool(BaseTool):
    """
    Polygon-Werkzeug.

    - Linksklick: Punkt hinzufügen
    - Rechtsklick: Polygon schließen und zeichnen
    - Escape: Abbrechen
    - filled=False: Nur Umriss
    - filled=True: Gefülltes Polygon
    """

    def __init__(self, filled: bool = False) -> None:
        super().__init__()
        self._filled = filled
        self._points: list[tuple[int, int]] = []
        self._current_pos: tuple[int, int] | None = None

    def get_cursor(self) -> Qt.CursorShape:
        return Qt.CursorShape.CrossCursor

    def activate(self) -> None:
        super().activate()
        self._points = []
        self._current_pos = None

    def deactivate(self) -> None:
        super().deactivate()
        self._points = []
        self._current_pos = None

    def on_mouse_press(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        # Snap-to-Grid
        x, y = ctx.snap(ctx.grid_x, ctx.grid_y)
        pos = (x, y)

        if event.button() == Qt.MouseButton.LeftButton:
            # Punkt hinzufügen
            if not self._points or pos != self._points[-1]:
                self._points.append(pos)
                self._active = True
            return []

        elif event.button() == Qt.MouseButton.RightButton:
            # Polygon schließen und zeichnen
            if len(self._points) >= 3:
                # Punkte für das Polygon berechnen
                points = self._get_polygon_points(ctx)

                changes = []
                for x, y in points:
                    if self._is_valid_pos(ctx, x, y):
                        changes.append((x, y, ctx.current_color_index))

                # Reset
                self._points = []
                self._active = False
                self._current_pos = None

                return changes
            else:
                # Zu wenig Punkte - abbrechen
                self._points = []
                self._active = False
                return []

        return []

    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        # Snap-to-Grid
        x, y = ctx.snap(ctx.grid_x, ctx.grid_y)
        self._current_pos = (x, y)
        return []

    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        return []

    def on_key_press(self, ctx: "ToolContext", event) -> bool:
        """Escape bricht ab, Backspace entfernt letzten Punkt."""
        if event.key() == Qt.Key.Key_Escape:
            self._points = []
            self._active = False
            self._current_pos = None
            return True
        elif event.key() == Qt.Key.Key_Backspace:
            if self._points:
                self._points.pop()
                if not self._points:
                    self._active = False
            return True
        return False

    def _get_polygon_points(self, ctx: ToolContext) -> list[tuple[int, int]]:
        """Berechnet alle Punkte des Polygons."""
        if len(self._points) < 3:
            return []

        points = set()

        # Alle Kanten des Polygons zeichnen
        for i in range(len(self._points)):
            p1 = self._points[i]
            p2 = self._points[(i + 1) % len(self._points)]  # Schließt zum Start

            line_points = self._get_line_points(p1[0], p1[1], p2[0], p2[1])
            points.update(line_points)

        if self._filled:
            # Polygon füllen mit Scanline-Algorithmus
            points.update(self._fill_polygon(ctx))

        return list(points)

    def _fill_polygon(self, ctx: ToolContext) -> set[tuple[int, int]]:
        """Füllt das Polygon mit Scanline-Algorithmus."""
        if len(self._points) < 3:
            return set()

        filled = set()

        # Bounding Box auf den gültigen Musterbereich begrenzen. Klickpunkte
        # können (z.B. bei weit herausgezoomtem/verschobenem Canvas) weit
        # außerhalb von Pattern.width/height liegen. Ohne Clamping würde die
        # Scanline über den gesamten rohen Koordinatenbereich laufen -- bei
        # extremen Ausreißern (Zoom+Pan weit weg vom Muster) potenziell
        # Millionen nutzloser Zellen erzeugen, die anschließend in
        # on_mouse_press() ohnehin über _is_valid_pos() verworfen werden.
        # Gleiches Muster ist bereits in lasso_select_tool.py::_fill_lasso_polygon
        # umgesetzt.
        min_y = max(0, min(p[1] for p in self._points))
        max_y = min(ctx.pattern.height - 1, max(p[1] for p in self._points))
        min_x = max(0, min(p[0] for p in self._points))
        max_x = min(ctx.pattern.width - 1, max(p[0] for p in self._points))

        # Scanline für jede Y-Zeile
        for y in range(min_y, max_y + 1):
            # Schnittpunkte mit Kanten finden
            intersections = []

            for i in range(len(self._points)):
                p1 = self._points[i]
                p2 = self._points[(i + 1) % len(self._points)]

                y1, y2 = p1[1], p2[1]
                x1, x2 = p1[0], p2[0]

                # Prüfen ob Kante die Scanline kreuzt
                if y1 == y2:
                    continue  # Horizontale Kante überspringen

                if min(y1, y2) <= y < max(y1, y2):
                    # X-Koordinate des Schnittpunkts berechnen
                    x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                    intersections.append(x)

            # Schnittpunkte sortieren
            intersections.sort()

            # Pixel zwischen Paaren von Schnittpunkten füllen
            for i in range(0, len(intersections) - 1, 2):
                x_start = max(min_x, int(intersections[i]))
                x_end = min(max_x, int(intersections[i + 1]))

                for x in range(x_start, x_end + 1):
                    filled.add((x, y))

        return filled

    def draw_preview(self, ctx: ToolContext, painter: QPainter) -> None:
        if not self._points:
            return

        # Farbe für Vorschau
        color_entry = ctx.pattern.get_color_entry(ctx.current_color_index)
        if color_entry:
            color = to_qcolor(color_entry.thread.color, 150)
        else:
            color = QColor(100, 200, 150, 150)

        # Bereits gesetzte Punkte und Linien zeichnen
        preview_points = set()

        for i in range(len(self._points) - 1):
            p1, p2 = self._points[i], self._points[i + 1]
            line_pts = self._get_line_points(p1[0], p1[1], p2[0], p2[1])
            preview_points.update(line_pts)

        # Linie zum aktuellen Mauszeiger
        if self._current_pos and len(self._points) > 0:
            last = self._points[-1]
            line_pts = self._get_line_points(
                last[0], last[1], self._current_pos[0], self._current_pos[1]
            )
            preview_points.update(line_pts)

        # Punkte zeichnen (halbtransparent)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)

        for gx, gy in preview_points:
            if self._is_valid_pos(ctx, gx, gy):
                sx, sy = self._grid_to_screen(ctx, gx, gy)
                painter.drawRect(sx, sy, ctx.cell_size, ctx.cell_size)

        # Startpunkt markieren (grün)
        if self._points:
            sx, sy = self._grid_to_screen(ctx, self._points[0][0], self._points[0][1])
            painter.setPen(QPen(QColor(THEME.accent_primary), 2))
            painter.setBrush(QColor(110, 198, 160, 100))
            painter.drawRect(sx, sy, ctx.cell_size, ctx.cell_size)

        # Alle gesetzten Punkte markieren
        painter.setPen(QPen(QColor(THEME.text_primary), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for pt in self._points:
            sx, sy = self._grid_to_screen(ctx, pt[0], pt[1])
            painter.drawRect(sx + 2, sy + 2, ctx.cell_size - 4, ctx.cell_size - 4)

        # Schließ-Linie (gestrichelt) zum Startpunkt anzeigen
        if len(self._points) >= 2 and self._current_pos:
            start = self._points[0]

            # Gestrichelte Linie vom aktuellen Punkt zum Start
            painter.setPen(QPen(QColor(THEME.accent_primary), 1, Qt.PenStyle.DashLine))

            sx1, sy1 = self._grid_to_screen(ctx, self._current_pos[0], self._current_pos[1])
            sx2, sy2 = self._grid_to_screen(ctx, start[0], start[1])

            # Mittelpunkt der Zellen
            cx1 = sx1 + ctx.cell_size // 2
            cy1 = sy1 + ctx.cell_size // 2
            cx2 = sx2 + ctx.cell_size // 2
            cy2 = sy2 + ctx.cell_size // 2

            painter.drawLine(cx1, cy1, cx2, cy2)

        # Hinweistext
        if len(self._points) >= 1:
            painter.setPen(QColor(THEME.accent_primary))
            painter.setFont(painter.font())

            hint = f"Punkte: {len(self._points)}"
            if len(self._points) >= 3:
                hint += " | Rechtsklick: Schließen"
            else:
                hint += " | Min. 3 Punkte"

            painter.drawText(10, 20, hint)
