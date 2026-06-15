"""
Auswahl-Werkzeug mit Kopieren, Einfügen, Drehen und Spiegeln.
"""

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen

from ..styles import THEME
from .base_tool import BaseTool, ToolContext


class SelectTool(BaseTool):
    """
    Auswahl-Werkzeug für rechteckige Selektion.

    Auswahl:
    - Klick + Drag: Rechteck aufziehen
    - Shift: Quadratische Auswahl
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

    # Clipboard (Klassenvariable für alle Instanzen)
    _clipboard: list[tuple[int, int, int | None]] | None = None
    _clipboard_size: tuple[int, int] = (0, 0)

    def __init__(self) -> None:
        super().__init__()

        # Auswahl
        self._selection: QRect | None = None

        # Ziehen einer neuen Auswahl
        self._start_pos: tuple[int, int] | None = None
        self._current_pos: tuple[int, int] | None = None
        self._is_selecting: bool = False

        # Verschieben der Auswahl mit Inhalt
        self._is_moving: bool = False
        self._move_start: tuple[int, int] | None = None
        self._original_selection: QRect | None = None
        self._selection_content: list[tuple[int, int, int | None]] | None = None
        self._content_captured: bool = False

        # Einfügen-Modus
        self._is_pasting: bool = False
        self._paste_position: tuple[int, int] | None = None

        # Shift gedrückt
        self._shift_pressed: bool = False

    def get_cursor(self) -> Qt.CursorShape:
        if self._is_moving or self._is_pasting:
            return Qt.CursorShape.ClosedHandCursor
        elif self._selection and self._is_point_in_selection(self._current_pos):
            return Qt.CursorShape.SizeAllCursor
        return Qt.CursorShape.CrossCursor

    def activate(self) -> None:
        super().activate()

    def deactivate(self) -> None:
        super().deactivate()
        self._is_selecting = False
        self._is_moving = False
        self._is_pasting = False
        self._start_pos = None
        self._current_pos = None
        self._content_captured = False

    @property
    def selection(self) -> QRect | None:
        return self._selection

    @property
    def is_pasting(self) -> bool:
        return self._is_pasting

    def clear_selection(self) -> None:
        """Löscht die Auswahl."""
        self._selection = None
        self._selection_content = None
        self._original_selection = None
        self._is_selecting = False
        self._is_moving = False
        self._is_pasting = False
        self._content_captured = False

    def _is_point_in_selection(self, pos: tuple[int, int] | None) -> bool:
        if not pos or not self._selection:
            return False
        x, y = pos
        return self._selection.contains(x, y)

    # === Maus-Events ===

    def on_mouse_press(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if event.button() != Qt.MouseButton.LeftButton:
            return []

        self._shift_pressed = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        x, y = ctx.grid_x, ctx.grid_y

        # Im Einfüge-Modus: Klick platziert
        if self._is_pasting:
            return self._confirm_paste(ctx)

        # Klick in bestehende Auswahl -> Verschieben
        if self._selection and self._selection.contains(x, y):
            self._is_moving = True
            self._move_start = (x, y)
            self._original_selection = QRect(self._selection)
            self._active = True

            if not self._content_captured:
                self._capture_selection_content(ctx)
                self._content_captured = True
            return []

        # Neue Auswahl
        self._is_selecting = True
        self._start_pos = (x, y)
        self._current_pos = (x, y)
        self._selection = None
        self._selection_content = None
        self._original_selection = None
        self._content_captured = False
        self._active = True

        return []

    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        x, y = ctx.grid_x, ctx.grid_y
        self._current_pos = (x, y)
        self._shift_pressed = event.modifiers() & Qt.KeyboardModifier.ShiftModifier

        if self._is_pasting:
            self._paste_position = (x, y)
        elif self._is_selecting and self._start_pos:
            self._update_selection_rect(ctx)
        elif self._is_moving and self._move_start and self._selection:
            dx = x - self._move_start[0]
            dy = y - self._move_start[1]
            if dx != 0 or dy != 0:
                self._selection.translate(dx, dy)
                self._move_start = (x, y)

        return []

    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        changes = []

        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_selecting:
                self._is_selecting = False
                self._update_selection_rect(ctx)
                if self._selection and (
                    self._selection.width() < 1 or self._selection.height() < 1
                ):
                    self._selection = None
                self._active = False

            elif self._is_moving:
                self._is_moving = False
                self._active = False

                if self._selection_content and self._selection and self._original_selection:
                    if self._selection.topLeft() != self._original_selection.topLeft():
                        changes = self._apply_move(ctx)
                        self._original_selection = QRect(self._selection)
                        # Nach dem Verschieben: Inhalt neu erfassen beim nächsten Klick
                        # Damit werden die Pixel an der neuen Position korrekt erfasst
                        self._content_captured = False
                        self._selection_content = None

        return changes

    def _update_selection_rect(self, ctx: ToolContext) -> None:
        if not self._start_pos or not self._current_pos:
            return

        x1, y1 = self._start_pos
        x2, y2 = self._current_pos

        if self._shift_pressed:
            size = max(abs(x2 - x1), abs(y2 - y1))
            x2 = x1 + size if x2 >= x1 else x1 - size
            y2 = y1 + size if y2 >= y1 else y1 - size

        left = max(0, min(x1, x2))
        top = max(0, min(y1, y2))
        right = min(ctx.pattern.width - 1, max(x1, x2))
        bottom = min(ctx.pattern.height - 1, max(y1, y2))

        self._selection = QRect(left, top, right - left + 1, bottom - top + 1)

    def _capture_selection_content(self, ctx: ToolContext) -> None:
        if not self._selection:
            return

        layer = ctx.pattern.active_layer
        if not layer:
            return

        self._selection_content = []
        for y in range(self._selection.top(), self._selection.top() + self._selection.height()):
            for x in range(
                self._selection.left(), self._selection.left() + self._selection.width()
            ):
                if self._is_valid_pos(ctx, x, y):
                    color_idx = layer.get_stitch(x, y)
                    rel_x = x - self._selection.left()
                    rel_y = y - self._selection.top()
                    self._selection_content.append((rel_x, rel_y, color_idx))

    def _apply_move(self, ctx: ToolContext) -> list[tuple[int, int, int | None]]:
        if not self._selection_content or not self._selection or not self._original_selection:
            return []

        changes = []

        # Alte Position löschen
        for rel_x, rel_y, _ in self._selection_content:
            old_x = self._original_selection.left() + rel_x
            old_y = self._original_selection.top() + rel_y
            if self._is_valid_pos(ctx, old_x, old_y):
                changes.append((old_x, old_y, None))

        # Neue Position setzen
        for rel_x, rel_y, color_idx in self._selection_content:
            new_x = self._selection.left() + rel_x
            new_y = self._selection.top() + rel_y
            if self._is_valid_pos(ctx, new_x, new_y) and color_idx is not None:
                changes.append((new_x, new_y, color_idx))

        return changes

    # === Kopieren / Einfügen ===

    def copy_selection(self, ctx: ToolContext) -> bool:
        """Kopiert die Auswahl in die Zwischenablage."""
        if not self._selection:
            return False

        layer = ctx.pattern.active_layer
        if not layer:
            return False

        SelectTool._clipboard = []
        w = self._selection.width()
        h = self._selection.height()

        for y in range(self._selection.top(), self._selection.top() + h):
            for x in range(self._selection.left(), self._selection.left() + w):
                if self._is_valid_pos(ctx, x, y):
                    color_idx = layer.get_stitch(x, y)
                    rel_x = x - self._selection.left()
                    rel_y = y - self._selection.top()
                    SelectTool._clipboard.append((rel_x, rel_y, color_idx))

        SelectTool._clipboard_size = (w, h)
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

        for rel_x, rel_y, color_idx in SelectTool._clipboard:
            new_x = px + rel_x
            new_y = py + rel_y
            if self._is_valid_pos(ctx, new_x, new_y) and color_idx is not None:
                changes.append((new_x, new_y, color_idx))

        # Neue Auswahl um eingefügten Bereich
        w, h = SelectTool._clipboard_size
        self._selection = QRect(px, py, w, h)
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
        if not self._selection:
            return []

        changes = []
        for y in range(self._selection.top(), self._selection.top() + self._selection.height()):
            for x in range(
                self._selection.left(), self._selection.left() + self._selection.width()
            ):
                if self._is_valid_pos(ctx, x, y):
                    changes.append((x, y, None))

        self._selection_content = None
        self._content_captured = False
        return changes

    def fill_selection(self, ctx: ToolContext) -> list[tuple[int, int, int | None]]:
        """Füllt die Auswahl mit der aktuellen Farbe."""
        if not self._selection:
            return []

        changes = []
        for y in range(self._selection.top(), self._selection.top() + self._selection.height()):
            for x in range(
                self._selection.left(), self._selection.left() + self._selection.width()
            ):
                if self._is_valid_pos(ctx, x, y):
                    changes.append((x, y, ctx.current_color_index))
        return changes

    # === Transformieren ===

    def rotate_selection(
        self, ctx: ToolContext, clockwise: bool = True
    ) -> list[tuple[int, int, int | None]]:
        """Dreht den Inhalt der Auswahl um 90°."""
        if not self._selection:
            return []

        layer = ctx.pattern.active_layer
        if not layer:
            return []

        w = self._selection.width()
        h = self._selection.height()
        left = self._selection.left()
        top = self._selection.top()

        # Inhalt lesen
        content = []
        for y in range(h):
            for x in range(w):
                gx, gy = left + x, top + y
                if self._is_valid_pos(ctx, gx, gy):
                    color_idx = layer.get_stitch(gx, gy)
                    content.append((x, y, color_idx))

        # Rotieren
        rotated = []
        for x, y, color_idx in content:
            if clockwise:
                # 90° rechts: (x,y) -> (h-1-y, x)
                new_x = h - 1 - y
                new_y = x
            else:
                # 90° links: (x,y) -> (y, w-1-x)
                new_x = y
                new_y = w - 1 - x
            rotated.append((new_x, new_y, color_idx))

        # Neue Größe (w und h tauschen)
        new_w, new_h = h, w

        # Änderungen berechnen
        changes = []

        # Alte Position löschen
        for y in range(h):
            for x in range(w):
                gx, gy = left + x, top + y
                if self._is_valid_pos(ctx, gx, gy):
                    changes.append((gx, gy, None))

        # Neue Position setzen
        for new_x, new_y, color_idx in rotated:
            gx = left + new_x
            gy = top + new_y
            if self._is_valid_pos(ctx, gx, gy) and color_idx is not None:
                changes.append((gx, gy, color_idx))

        # Auswahl aktualisieren
        self._selection = QRect(left, top, new_w, new_h)
        self._content_captured = False

        return changes

    def flip_selection_horizontal(self, ctx: ToolContext) -> list[tuple[int, int, int | None]]:
        """Spiegelt den Inhalt horizontal."""
        if not self._selection:
            return []

        layer = ctx.pattern.active_layer
        if not layer:
            return []

        w = self._selection.width()
        h = self._selection.height()
        left = self._selection.left()
        top = self._selection.top()

        # Inhalt lesen und horizontal spiegeln
        changes = []
        rows = []

        for y in range(h):
            row = []
            for x in range(w):
                gx, gy = left + x, top + y
                if self._is_valid_pos(ctx, gx, gy):
                    row.append(layer.get_stitch(gx, gy))
                else:
                    row.append(None)
            rows.append(row)

        # Jede Zeile umdrehen und schreiben
        for y, row in enumerate(rows):
            row.reverse()
            for x, color_idx in enumerate(row):
                gx, gy = left + x, top + y
                if self._is_valid_pos(ctx, gx, gy):
                    changes.append((gx, gy, color_idx))

        self._content_captured = False
        return changes

    def flip_selection_vertical(self, ctx: ToolContext) -> list[tuple[int, int, int | None]]:
        """Spiegelt den Inhalt vertikal."""
        if not self._selection:
            return []

        layer = ctx.pattern.active_layer
        if not layer:
            return []

        w = self._selection.width()
        h = self._selection.height()
        left = self._selection.left()
        top = self._selection.top()

        # Inhalt lesen
        rows = []
        for y in range(h):
            row = []
            for x in range(w):
                gx, gy = left + x, top + y
                if self._is_valid_pos(ctx, gx, gy):
                    row.append(layer.get_stitch(gx, gy))
                else:
                    row.append(None)
            rows.append(row)

        # Zeilen umdrehen und schreiben
        rows.reverse()
        changes = []
        for y, row in enumerate(rows):
            for x, color_idx in enumerate(row):
                gx, gy = left + x, top + y
                if self._is_valid_pos(ctx, gx, gy):
                    changes.append((gx, gy, color_idx))

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

        # Auswahl beim Ziehen
        if self._is_selecting and self._start_pos and self._current_pos:
            self._draw_selection_rect(ctx, painter, preview=True)

        # Bestehende Auswahl
        elif self._selection:
            self._draw_selection_rect(ctx, painter, preview=False)

            if self._is_moving and self._selection_content:
                self._draw_content_preview(ctx, painter)

        # Hinweise
        if self._selection and not self._is_moving:
            painter.setPen(QColor(THEME.accent_primary))
            hint = "Ctrl+C/X/V | Del | R/H/V | Ziehen"
            painter.drawText(10, 20, hint)
        elif self._is_moving:
            painter.setPen(QColor(THEME.accent_blue))
            painter.drawText(10, 20, "Loslassen zum Platzieren")

    def _draw_paste_preview(self, ctx: ToolContext, painter: QPainter) -> None:
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
                color = QColor(
                    color_entry.thread.color.r,
                    color_entry.thread.color.g,
                    color_entry.thread.color.b,
                    180,
                )
            else:
                color = QColor(150, 150, 150, 180)

            sx, sy = self._grid_to_screen(ctx, gx, gy)
            painter.fillRect(sx + 1, sy + 1, ctx.cell_size - 2, ctx.cell_size - 2, color)

        # Rahmen
        w, h = SelectTool._clipboard_size
        sx1, sy1 = self._grid_to_screen(ctx, px, py)
        sx2, sy2 = self._grid_to_screen(ctx, px + w, py + h)

        pen = QPen(QColor(THEME.accent_blue), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(sx1, sy1, sx2 - sx1, sy2 - sy1)

    def _draw_content_preview(self, ctx: ToolContext, painter: QPainter) -> None:
        if not self._selection_content or not self._selection:
            return

        for rel_x, rel_y, color_idx in self._selection_content:
            if color_idx is None:
                continue

            new_x = self._selection.left() + rel_x
            new_y = self._selection.top() + rel_y

            if not self._is_valid_pos(ctx, new_x, new_y):
                continue

            color_entry = ctx.pattern.get_color_entry(color_idx)
            if color_entry:
                color = QColor(
                    color_entry.thread.color.r,
                    color_entry.thread.color.g,
                    color_entry.thread.color.b,
                    200,
                )
            else:
                color = QColor(150, 150, 150, 200)

            sx, sy = self._grid_to_screen(ctx, new_x, new_y)
            painter.fillRect(sx + 1, sy + 1, ctx.cell_size - 2, ctx.cell_size - 2, color)

    def _draw_selection_rect(
        self, ctx: ToolContext, painter: QPainter, preview: bool = False
    ) -> None:
        if preview and self._start_pos and self._current_pos:
            x1, y1 = self._start_pos
            x2, y2 = self._current_pos

            if self._shift_pressed:
                size = max(abs(x2 - x1), abs(y2 - y1))
                x2 = x1 + size if x2 >= x1 else x1 - size
                y2 = y1 + size if y2 >= y1 else y1 - size

            left, right = min(x1, x2), max(x1, x2)
            top, bottom = min(y1, y2), max(y1, y2)

            sx1, sy1 = self._grid_to_screen(ctx, left, top)
            sx2, sy2 = self._grid_to_screen(ctx, right + 1, bottom + 1)
        elif self._selection:
            sx1, sy1 = self._grid_to_screen(ctx, self._selection.left(), self._selection.top())
            sx2, sy2 = self._grid_to_screen(
                ctx,
                self._selection.left() + self._selection.width(),
                self._selection.top() + self._selection.height(),
            )
        else:
            return

        width = sx2 - sx1
        height = sy2 - sy1

        # Füllung (nicht beim Verschieben)
        if not (self._is_moving and self._selection_content):
            fill_color = QColor(THEME.accent_primary) if not preview else QColor(THEME.accent_blue)
            fill_color.setAlpha(40)
            painter.fillRect(sx1, sy1, width, height, fill_color)

        # Marching Ants
        pen = QPen(QColor(THEME.text_primary), 2, Qt.PenStyle.DashLine)
        pen.setDashPattern([4, 4])
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(sx1, sy1, width, height)

        if not preview:
            pen2 = QPen(QColor(THEME.bg_dark), 2, Qt.PenStyle.DashLine)
            pen2.setDashPattern([4, 4])
            pen2.setDashOffset(4)
            painter.setPen(pen2)
            painter.drawRect(sx1, sy1, width, height)

        # Griffe
        handle_size = 8
        handle_color = QColor(THEME.accent_primary) if not preview else QColor(THEME.accent_blue)
        painter.setPen(QPen(Qt.GlobalColor.white, 1))
        painter.setBrush(handle_color)

        for cx, cy in [(sx1, sy1), (sx2, sy1), (sx1, sy2), (sx2, sy2)]:
            painter.drawRect(cx - handle_size // 2, cy - handle_size // 2, handle_size, handle_size)

        # Größe
        if self._selection:
            w, h = self._selection.width(), self._selection.height()
        else:
            w = abs(self._current_pos[0] - self._start_pos[0]) + 1
            h = abs(self._current_pos[1] - self._start_pos[1]) + 1

        painter.setPen(QColor(THEME.text_primary))
        painter.drawText(sx1 + 4, sy1 - 6, f"{w} × {h}")
