"""
Lasso-Auswahl-Werkzeug mit Freihand-Selektion.
"""

from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPen

from ..color_utils import to_qcolor
from ..styles import THEME
from .base_tool import BaseTool, ToolContext
from .select_tool import SelectTool  # Für gemeinsames Clipboard


class LassoSelectTool(BaseTool):
    """
    Lasso-Auswahl-Werkzeug für Freihand-Selektion.

    Auswahl:
    - Klick + Drag: Freihand-Lasso zeichnen
    - Loslassen: Schließt das Lasso automatisch
    - Klick in Auswahl + Drag: Inhalt verschieben
    - Escape: Auswahl aufheben

    Bearbeiten:
    - Ctrl+C: Kopieren
    - Ctrl+X: Ausschneiden
    - Ctrl+V: Einfügen
    - Delete: Löschen
    - F: Füllen

    Transformieren:
    - R: 90° rechts drehen
    - Shift+R: 90° links drehen
    - H: Horizontal spiegeln
    - V: Vertikal spiegeln
    """

    # Clipboard wird mit SelectTool geteilt (keine eigene Definition)

    def __init__(self) -> None:
        super().__init__()

        # Lasso-Punkte (in Grid-Koordinaten)
        self._lasso_points: list[tuple[int, int]] = []

        # Ausgewählte Pixel-Set
        self._selected_pixels: set[tuple[int, int]] = set()

        # Bounding-Box der Auswahl
        self._selection_bounds: QRect | None = None

        # Ziehen eines neuen Lassos
        self._is_selecting: bool = False

        # Verschieben der Auswahl mit Inhalt
        self._is_moving: bool = False
        self._move_start: tuple[int, int] | None = None
        self._original_bounds: QRect | None = None
        self._selection_content: list[tuple[int, int, int | None]] | None = None
        self._content_captured: bool = False

        # Einfügen-Modus
        self._is_pasting: bool = False
        self._paste_position: tuple[int, int] | None = None

        # Letzte Mausposition
        self._last_grid_pos: tuple[int, int] | None = None

    def get_cursor(self) -> Qt.CursorShape:
        if self._is_moving or self._is_pasting:
            return Qt.CursorShape.ClosedHandCursor
        elif self._selected_pixels and self._is_point_in_selection(self._last_grid_pos):
            return Qt.CursorShape.SizeAllCursor
        return Qt.CursorShape.CrossCursor

    def activate(self) -> None:
        super().activate()

    def deactivate(self) -> None:
        super().deactivate()
        self._is_selecting = False
        self._is_moving = False
        self._is_pasting = False
        self._content_captured = False

    @property
    def selection(self) -> QRect | None:
        """Gibt die Bounding-Box der Auswahl zurück."""
        return self._selection_bounds

    @property
    def selected_pixels(self) -> set[tuple[int, int]]:
        """Gibt das Set der ausgewählten Pixel zurück."""
        return self._selected_pixels

    @property
    def is_pasting(self) -> bool:
        return self._is_pasting

    def clear_selection(self) -> None:
        """Löscht die Auswahl."""
        self._selected_pixels.clear()
        self._selection_bounds = None
        self._lasso_points.clear()
        self._selection_content = None
        self._original_bounds = None
        self._is_selecting = False
        self._is_moving = False
        self._is_pasting = False
        self._content_captured = False

    def _is_point_in_selection(self, pos: tuple[int, int] | None) -> bool:
        if not pos or not self._selected_pixels:
            return False
        return pos in self._selected_pixels

    def _update_bounds(self) -> None:
        """Aktualisiert die Bounding-Box der ausgewählten Pixel."""
        if not self._selected_pixels:
            self._selection_bounds = None
            return

        min_x = min(p[0] for p in self._selected_pixels)
        max_x = max(p[0] for p in self._selected_pixels)
        min_y = min(p[1] for p in self._selected_pixels)
        max_y = max(p[1] for p in self._selected_pixels)

        self._selection_bounds = QRect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)

    def _fill_lasso_polygon(self, ctx: ToolContext) -> None:
        """Füllt das Lasso-Polygon mit Pixeln."""
        if len(self._lasso_points) < 3:
            return

        self._selected_pixels.clear()

        # Erstelle einen QPainterPath für das Polygon
        path = QPainterPath()
        path.moveTo(QPointF(self._lasso_points[0][0], self._lasso_points[0][1]))
        for x, y in self._lasso_points[1:]:
            path.lineTo(QPointF(x, y))
        path.closeSubpath()

        # Bounding Box berechnen
        min_x = max(0, min(p[0] for p in self._lasso_points))
        max_x = min(ctx.pattern.width - 1, max(p[0] for p in self._lasso_points))
        min_y = max(0, min(p[1] for p in self._lasso_points))
        max_y = min(ctx.pattern.height - 1, max(p[1] for p in self._lasso_points))

        # Alle Pixel innerhalb der Bounding Box prüfen
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                # Punkt in der Mitte des Pixels prüfen
                if path.contains(QPointF(x + 0.5, y + 0.5)):
                    self._selected_pixels.add((x, y))

        # Auch die Lasso-Linie selbst einschließen (Bresenham)
        for i in range(len(self._lasso_points)):
            p1 = self._lasso_points[i]
            p2 = self._lasso_points[(i + 1) % len(self._lasso_points)]
            self._add_line_pixels(p1, p2, ctx)

        self._update_bounds()

    def _add_line_pixels(self, p1: tuple[int, int], p2: tuple[int, int], ctx: ToolContext) -> None:
        """Fügt die Pixel einer Linie zur Auswahl hinzu (Bresenham)."""
        x1, y1 = p1
        x2, y2 = p2

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        x, y = x1, y1
        while True:
            if 0 <= x < ctx.pattern.width and 0 <= y < ctx.pattern.height:
                self._selected_pixels.add((x, y))

            if x == x2 and y == y2:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    # === Maus-Events ===

    def on_mouse_press(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if event.button() != Qt.MouseButton.LeftButton:
            return []

        x, y = ctx.grid_x, ctx.grid_y
        self._last_grid_pos = (x, y)

        # Im Einfüge-Modus: Klick platziert
        if self._is_pasting:
            return self._confirm_paste(ctx)

        # Klick in bestehende Auswahl -> Verschieben
        if self._selected_pixels and (x, y) in self._selected_pixels:
            self._is_moving = True
            self._move_start = (x, y)
            self._original_bounds = (
                QRect(self._selection_bounds) if self._selection_bounds else None
            )
            self._active = True

            if not self._content_captured:
                self._capture_selection_content(ctx)
                self._content_captured = True
            return []

        # Neues Lasso starten
        self._is_selecting = True
        self._lasso_points = [(x, y)]
        self._selected_pixels.clear()
        self._selection_bounds = None
        self._selection_content = None
        self._original_bounds = None
        self._content_captured = False
        self._active = True

        return []

    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        x, y = ctx.grid_x, ctx.grid_y
        self._last_grid_pos = (x, y)

        if self._is_pasting:
            self._paste_position = (x, y)
        elif self._is_selecting:
            # Nur hinzufügen wenn sich Position geändert hat
            if not self._lasso_points or self._lasso_points[-1] != (x, y):
                self._lasso_points.append((x, y))
        elif self._is_moving and self._move_start and self._selected_pixels:
            dx = x - self._move_start[0]
            dy = y - self._move_start[1]
            if dx != 0 or dy != 0:
                # Verschiebe alle ausgewählten Pixel
                self._selected_pixels = {(px + dx, py + dy) for px, py in self._selected_pixels}
                self._update_bounds()
                self._move_start = (x, y)

        return []

    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        changes = []

        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_selecting:
                self._is_selecting = False
                self._fill_lasso_polygon(ctx)
                self._active = False

            elif self._is_moving:
                self._is_moving = False
                self._active = False

                # Nur anwenden, wenn sich die Auswahl tatsaechlich bewegt hat
                # -- ein reiner Klick ohne Drag erzeugte sonst einen no-op
                # "Verschieben"-Undo-Eintrag (Loeschen+Wiedereinfuegen
                # derselben Pixel). Pendant zum gleichwertigen Check in
                # select_tool.py (Vergleich der topLeft()-Position).
                moved = (
                    self._original_bounds is not None
                    and self._selection_bounds is not None
                    and self._selection_bounds.topLeft() != self._original_bounds.topLeft()
                )
                if moved and self._selection_content and self._selected_pixels:
                    changes = self._apply_move(ctx)
                    self._content_captured = False
                    self._selection_content = None

        return changes

    def _capture_selection_content(self, ctx: ToolContext) -> None:
        """Erfasst den Inhalt der Auswahl."""
        if not self._selected_pixels or not self._selection_bounds:
            return

        layer = ctx.pattern.active_layer
        if not layer:
            return

        self._selection_content = []
        for x, y in self._selected_pixels:
            if self._is_valid_pos(ctx, x, y):
                color_idx = layer.get_stitch(x, y)
                rel_x = x - self._selection_bounds.left()
                rel_y = y - self._selection_bounds.top()
                self._selection_content.append((rel_x, rel_y, color_idx))

    def _apply_move(self, ctx: ToolContext) -> list[tuple[int, int, int | None]]:
        """Wendet die Verschiebung an."""
        if not self._selection_content or not self._selection_bounds or not self._original_bounds:
            return []

        changes = []

        # Alte Positionen löschen
        for rel_x, rel_y, _ in self._selection_content:
            old_x = self._original_bounds.left() + rel_x
            old_y = self._original_bounds.top() + rel_y
            if self._is_valid_pos(ctx, old_x, old_y):
                changes.append((old_x, old_y, None))

        # Neue Positionen setzen
        for rel_x, rel_y, color_idx in self._selection_content:
            new_x = self._selection_bounds.left() + rel_x
            new_y = self._selection_bounds.top() + rel_y
            if self._is_valid_pos(ctx, new_x, new_y) and color_idx is not None:
                changes.append((new_x, new_y, color_idx))

        return changes

    # === Kopieren / Einfügen ===

    def copy_selection(self, ctx: ToolContext) -> bool:
        """Kopiert die Auswahl in die Zwischenablage."""
        if not self._selected_pixels or not self._selection_bounds:
            return False

        layer = ctx.pattern.active_layer
        if not layer:
            return False

        SelectTool._clipboard = []

        for x, y in self._selected_pixels:
            if self._is_valid_pos(ctx, x, y):
                color_idx = layer.get_stitch(x, y)
                rel_x = x - self._selection_bounds.left()
                rel_y = y - self._selection_bounds.top()
                SelectTool._clipboard.append((rel_x, rel_y, color_idx))

        SelectTool._clipboard_size = (
            self._selection_bounds.width(),
            self._selection_bounds.height(),
        )
        return True

    def cut_selection(self, ctx: ToolContext) -> list[tuple[int, int, int | None]]:
        """Schneidet die Auswahl aus."""
        if not self.copy_selection(ctx):
            return []
        return self.delete_selection(ctx)

    def start_paste(self, ctx: ToolContext) -> bool:
        """Startet den Einfüge-Modus."""
        if not SelectTool._clipboard:
            return False

        self._is_pasting = True
        self._paste_position = (ctx.grid_x, ctx.grid_y)
        self._active = True
        return True

    def _confirm_paste(self, ctx: ToolContext) -> list[tuple[int, int, int | None]]:
        """Bestätigt das Einfügen."""
        if not SelectTool._clipboard or not self._paste_position:
            self._is_pasting = False
            return []

        changes = []
        px, py = self._paste_position

        # Neue Auswahl aus eingefügten Pixeln
        self._selected_pixels.clear()

        for rel_x, rel_y, color_idx in SelectTool._clipboard:
            new_x = px + rel_x
            new_y = py + rel_y
            if self._is_valid_pos(ctx, new_x, new_y):
                self._selected_pixels.add((new_x, new_y))
                if color_idx is not None:
                    changes.append((new_x, new_y, color_idx))

        self._update_bounds()
        self._is_pasting = False
        self._active = False

        return changes

    def cancel_paste(self) -> None:
        """Bricht das Einfügen ab."""
        self._is_pasting = False
        self._paste_position = None
        self._active = False

    # === Löschen / Füllen ===

    def delete_selection(self, ctx: ToolContext) -> list[tuple[int, int, int | None]]:
        """Löscht den Inhalt der Auswahl."""
        if not self._selected_pixels:
            return []

        changes = []
        for x, y in self._selected_pixels:
            if self._is_valid_pos(ctx, x, y):
                changes.append((x, y, None))

        self._selection_content = None
        self._content_captured = False
        return changes

    def fill_selection(self, ctx: ToolContext) -> list[tuple[int, int, int | None]]:
        """Füllt die Auswahl mit der aktuellen Farbe."""
        if not self._selected_pixels:
            return []

        changes = []
        for x, y in self._selected_pixels:
            if self._is_valid_pos(ctx, x, y):
                changes.append((x, y, ctx.current_color_index))
        return changes

    # === Transformieren ===

    def rotate_selection(
        self, ctx: ToolContext, clockwise: bool = True
    ) -> list[tuple[int, int, int | None]]:
        """Dreht den Inhalt der Auswahl um 90°."""
        if not self._selected_pixels or not self._selection_bounds:
            return []

        layer = ctx.pattern.active_layer
        if not layer:
            return []

        left = self._selection_bounds.left()
        top = self._selection_bounds.top()
        w = self._selection_bounds.width()
        h = self._selection_bounds.height()

        # Inhalt lesen
        content = []
        for x, y in self._selected_pixels:
            if self._is_valid_pos(ctx, x, y):
                color_idx = layer.get_stitch(x, y)
                rel_x = x - left
                rel_y = y - top
                content.append((rel_x, rel_y, color_idx))

        # Rotieren
        rotated_pixels = set()
        rotated_content = []

        for rel_x, rel_y, color_idx in content:
            if clockwise:
                new_rel_x = h - 1 - rel_y
                new_rel_y = rel_x
            else:
                new_rel_x = rel_y
                new_rel_y = w - 1 - rel_x
            rotated_content.append((new_rel_x, new_rel_y, color_idx))
            rotated_pixels.add((left + new_rel_x, top + new_rel_y))

        # Änderungen berechnen
        changes = []

        # Alte Position löschen
        for x, y in self._selected_pixels:
            if self._is_valid_pos(ctx, x, y):
                changes.append((x, y, None))

        # Neue Position setzen
        for new_rel_x, new_rel_y, color_idx in rotated_content:
            gx = left + new_rel_x
            gy = top + new_rel_y
            if self._is_valid_pos(ctx, gx, gy) and color_idx is not None:
                changes.append((gx, gy, color_idx))

        # Auswahl aktualisieren
        self._selected_pixels = rotated_pixels
        self._update_bounds()
        self._content_captured = False

        return changes

    def flip_selection_horizontal(self, ctx: ToolContext) -> list[tuple[int, int, int | None]]:
        """Spiegelt den Inhalt horizontal."""
        if not self._selected_pixels or not self._selection_bounds:
            return []

        layer = ctx.pattern.active_layer
        if not layer:
            return []

        left = self._selection_bounds.left()
        w = self._selection_bounds.width()

        changes = []
        new_content = {}

        # Inhalt lesen und spiegeln
        for x, y in self._selected_pixels:
            if self._is_valid_pos(ctx, x, y):
                color_idx = layer.get_stitch(x, y)
                new_x = left + (w - 1) - (x - left)
                new_content[(new_x, y)] = color_idx

        # Löschen und neu setzen
        for x, y in self._selected_pixels:
            if self._is_valid_pos(ctx, x, y):
                changes.append((x, y, None))

        for (x, y), color_idx in new_content.items():
            if self._is_valid_pos(ctx, x, y):
                changes.append((x, y, color_idx))

        # Auswahl aktualisieren
        self._selected_pixels = set(new_content.keys())
        self._update_bounds()
        self._content_captured = False

        return changes

    def flip_selection_vertical(self, ctx: ToolContext) -> list[tuple[int, int, int | None]]:
        """Spiegelt den Inhalt vertikal."""
        if not self._selected_pixels or not self._selection_bounds:
            return []

        layer = ctx.pattern.active_layer
        if not layer:
            return []

        top = self._selection_bounds.top()
        h = self._selection_bounds.height()

        changes = []
        new_content = {}

        # Inhalt lesen und spiegeln
        for x, y in self._selected_pixels:
            if self._is_valid_pos(ctx, x, y):
                color_idx = layer.get_stitch(x, y)
                new_y = top + (h - 1) - (y - top)
                new_content[(x, new_y)] = color_idx

        # Löschen und neu setzen
        for x, y in self._selected_pixels:
            if self._is_valid_pos(ctx, x, y):
                changes.append((x, y, None))

        for (x, y), color_idx in new_content.items():
            if self._is_valid_pos(ctx, x, y):
                changes.append((x, y, color_idx))

        # Auswahl aktualisieren
        self._selected_pixels = set(new_content.keys())
        self._update_bounds()
        self._content_captured = False

        return changes

    # === Tastatur ===

    def on_key_press(self, ctx: ToolContext, event) -> bool:
        key = event.key()

        if key == Qt.Key.Key_Escape:
            if self._is_pasting:
                self.cancel_paste()
                return True
            self.clear_selection()
            return True

        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            return True  # Wird über MainWindow gehandelt

        return False

    # === Zeichnen ===

    def draw_preview(self, ctx: ToolContext, painter: QPainter) -> None:
        # Einfüge-Vorschau
        if self._is_pasting and self._paste_position and SelectTool._clipboard:
            self._draw_paste_preview(ctx, painter)
            painter.setPen(QColor(THEME.accent_blue))
            painter.drawText(10, 20, "Klicken zum Einfügen | Esc: Abbrechen")
            return

        # Lasso beim Zeichnen
        if self._is_selecting and len(self._lasso_points) > 1:
            self._draw_lasso_path(ctx, painter)

        # Bestehende Auswahl
        elif self._selected_pixels:
            self._draw_selected_pixels(ctx, painter)

            if self._is_moving and self._selection_content:
                self._draw_content_preview(ctx, painter)

        # Hinweise
        if self._selected_pixels and not self._is_moving:
            painter.setPen(QColor(THEME.accent_secondary))
            hint = "Lasso: Ctrl+C/X/V | Del | R/H/V | Ziehen"
            painter.drawText(10, 20, hint)
        elif self._is_moving:
            painter.setPen(QColor(THEME.accent_blue))
            painter.drawText(10, 20, "Loslassen zum Platzieren")
        elif self._is_selecting:
            painter.setPen(QColor(THEME.accent_secondary))
            painter.drawText(10, 20, "Lasso zeichnen...")

    def _draw_lasso_path(self, ctx: ToolContext, painter: QPainter) -> None:
        """Zeichnet den Lasso-Pfad während des Zeichnens."""
        if len(self._lasso_points) < 2:
            return

        # Lasso-Linie
        pen = QPen(QColor(THEME.accent_secondary), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)

        for i in range(len(self._lasso_points) - 1):
            x1, y1 = self._lasso_points[i]
            x2, y2 = self._lasso_points[i + 1]

            sx1, sy1 = self._grid_to_screen(ctx, x1, y1)
            sx2, sy2 = self._grid_to_screen(ctx, x2, y2)

            # Zur Mitte des Pixels
            sx1 += ctx.cell_size // 2
            sy1 += ctx.cell_size // 2
            sx2 += ctx.cell_size // 2
            sy2 += ctx.cell_size // 2

            painter.drawLine(sx1, sy1, sx2, sy2)

        # Linie zum Startpunkt (Vorschau des Schließens)
        if len(self._lasso_points) > 2:
            pen.setStyle(Qt.PenStyle.DotLine)
            pen.setColor(QColor(THEME.accent_secondary))
            pen.setWidth(1)
            painter.setPen(pen)

            x1, y1 = self._lasso_points[-1]
            x2, y2 = self._lasso_points[0]

            sx1, sy1 = self._grid_to_screen(ctx, x1, y1)
            sx2, sy2 = self._grid_to_screen(ctx, x2, y2)

            sx1 += ctx.cell_size // 2
            sy1 += ctx.cell_size // 2
            sx2 += ctx.cell_size // 2
            sy2 += ctx.cell_size // 2

            painter.drawLine(sx1, sy1, sx2, sy2)

    def _draw_selected_pixels(self, ctx: ToolContext, painter: QPainter) -> None:
        """Zeichnet die ausgewählten Pixel."""
        if not self._selected_pixels:
            return

        # Füllung für ausgewählte Pixel (nicht beim Verschieben)
        if not (self._is_moving and self._selection_content):
            fill_color = QColor(THEME.accent_secondary)
            fill_color.setAlpha(60)

            for x, y in self._selected_pixels:
                if self._is_valid_pos(ctx, x, y):
                    sx, sy = self._grid_to_screen(ctx, x, y)
                    painter.fillRect(sx, sy, ctx.cell_size, ctx.cell_size, fill_color)

        # Marching Ants am Rand
        self._draw_selection_border(ctx, painter)

    def _draw_selection_border(self, ctx: ToolContext, painter: QPainter) -> None:
        """Zeichnet den Rahmen um die Auswahl."""
        if not self._selected_pixels:
            return

        pen = QPen(QColor(THEME.text_primary), 1, Qt.PenStyle.DashLine)
        pen.setDashPattern([3, 3])
        painter.setPen(pen)

        for x, y in self._selected_pixels:
            sx, sy = self._grid_to_screen(ctx, x, y)

            # Oberer Rand
            if (x, y - 1) not in self._selected_pixels:
                painter.drawLine(sx, sy, sx + ctx.cell_size, sy)

            # Unterer Rand
            if (x, y + 1) not in self._selected_pixels:
                painter.drawLine(sx, sy + ctx.cell_size, sx + ctx.cell_size, sy + ctx.cell_size)

            # Linker Rand
            if (x - 1, y) not in self._selected_pixels:
                painter.drawLine(sx, sy, sx, sy + ctx.cell_size)

            # Rechter Rand
            if (x + 1, y) not in self._selected_pixels:
                painter.drawLine(sx + ctx.cell_size, sy, sx + ctx.cell_size, sy + ctx.cell_size)

    def _draw_paste_preview(self, ctx: ToolContext, painter: QPainter) -> None:
        """Zeichnet die Vorschau beim Einfügen."""
        if not self._paste_position or not SelectTool._clipboard:
            return

        px, py = self._paste_position

        for rel_x, rel_y, color_idx in SelectTool._clipboard:
            if color_idx is None:
                continue

            gx = px + rel_x
            gy = py + rel_y

            if not self._is_valid_pos(ctx, gx, gy):
                continue

            color_entry = ctx.pattern.get_color_entry(color_idx)
            if color_entry:
                color = to_qcolor(color_entry.thread.color, 180)
            else:
                color = QColor(150, 150, 150, 180)

            sx, sy = self._grid_to_screen(ctx, gx, gy)
            painter.fillRect(sx + 1, sy + 1, ctx.cell_size - 2, ctx.cell_size - 2, color)

        # Rahmen um eingefügten Bereich
        w, h = SelectTool._clipboard_size
        sx1, sy1 = self._grid_to_screen(ctx, px, py)
        sx2, sy2 = self._grid_to_screen(ctx, px + w, py + h)

        pen = QPen(QColor(THEME.accent_blue), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(sx1, sy1, sx2 - sx1, sy2 - sy1)

    def _draw_content_preview(self, ctx: ToolContext, painter: QPainter) -> None:
        """Zeichnet die Vorschau des verschobenen Inhalts."""
        if not self._selection_content or not self._selection_bounds:
            return

        for rel_x, rel_y, color_idx in self._selection_content:
            if color_idx is None:
                continue

            new_x = self._selection_bounds.left() + rel_x
            new_y = self._selection_bounds.top() + rel_y

            if not self._is_valid_pos(ctx, new_x, new_y):
                continue

            color_entry = ctx.pattern.get_color_entry(color_idx)
            if color_entry:
                color = to_qcolor(color_entry.thread.color, 200)
            else:
                color = QColor(150, 150, 150, 200)

            sx, sy = self._grid_to_screen(ctx, new_x, new_y)
            painter.fillRect(sx + 1, sy + 1, ctx.cell_size - 2, ctx.cell_size - 2, color)
