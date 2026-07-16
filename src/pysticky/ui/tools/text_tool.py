"""
Text-Werkzeug zum Platzieren von Text als Stiche.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QImage, QMouseEvent, QPainter, QPen

from ...utils import clamp_int
from ..color_utils import to_qcolor
from ..styles import THEME
from .base_tool import BaseTool, ToolContext


class TextTool(BaseTool):
    """
    Text-Werkzeug.

    - Text eingeben und platzieren
    - Mit Maus verschieben
    - Enter: Text zeichnen
    - Escape: Abbrechen

    Der Text wird als Bitmap gerendert und dann in Stiche umgewandelt.
    """

    def __init__(self) -> None:
        super().__init__()

        # Text-Einstellungen
        self._text: str = ""
        self._font_family: str = "Arial"
        self._font_size: int = 12
        self._bold: bool = False
        self._italic: bool = False

        # Positionierung
        self._position: tuple[int, int] | None = None  # Grid-Position
        self._dragging: bool = False
        self._drag_offset: tuple[int, int] = (0, 0)

        # Vorschau-Bitmap
        self._preview_pixels: list[tuple[int, int]] | None = None
        self._preview_size: tuple[int, int] = (0, 0)

    def get_cursor(self) -> Qt.CursorShape:
        if self._dragging:
            return Qt.CursorShape.ClosedHandCursor
        elif self._position:
            return Qt.CursorShape.OpenHandCursor
        return Qt.CursorShape.IBeamCursor

    def activate(self) -> None:
        super().activate()
        self._position = None
        self._dragging = False
        self._preview_pixels = None

    def deactivate(self) -> None:
        super().deactivate()
        self._position = None
        self._dragging = False
        self._preview_pixels = None

    # === Text-Einstellungen ===

    def set_text(self, text: str) -> None:
        """Setzt den Text."""
        self._text = text
        self._update_preview()

    def set_font_family(self, family: str) -> None:
        """Setzt die Schriftart."""
        self._font_family = family
        self._update_preview()

    def set_font_size(self, size: int) -> None:
        """Setzt die Schriftgröße."""
        self._font_size = clamp_int(size, 6, 72)
        self._update_preview()

    def set_bold(self, bold: bool) -> None:
        """Setzt fett."""
        self._bold = bold
        self._update_preview()

    def set_italic(self, italic: bool) -> None:
        """Setzt kursiv."""
        self._italic = italic
        self._update_preview()

    @property
    def text(self) -> str:
        return self._text

    @property
    def font_family(self) -> str:
        return self._font_family

    @property
    def font_size(self) -> int:
        return self._font_size

    @property
    def bold(self) -> bool:
        return self._bold

    @property
    def italic(self) -> bool:
        return self._italic

    @property
    def has_preview(self) -> bool:
        """Gibt zurück ob eine Vorschau existiert."""
        return self._position is not None and self._preview_pixels is not None

    # === Vorschau ===

    def _update_preview(self) -> None:
        """Aktualisiert die Vorschau-Pixel."""
        if not self._text:
            self._preview_pixels = None
            self._preview_size = (0, 0)
            return

        # Font erstellen
        font = QFont(self._font_family, self._font_size)
        font.setBold(self._bold)
        font.setItalic(self._italic)

        # Textgröße berechnen
        metrics = QFontMetrics(font)
        rect = metrics.boundingRect(self._text)

        width = rect.width() + 4
        height = rect.height() + 4

        if width <= 0 or height <= 0:
            self._preview_pixels = None
            self._preview_size = (0, 0)
            return

        # Text in Bitmap rendern
        image = QImage(width, height, QImage.Format.Format_Mono)
        image.fill(1)  # Weiß

        painter = QPainter(image)
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(-rect.left() + 2, -rect.top() + 2, self._text)
        painter.end()

        # Schwarze Pixel sammeln
        self._preview_pixels = []
        for y in range(height):
            for x in range(width):
                # Mono-Format: 0 = schwarz, 1 = weiß
                if image.pixelIndex(x, y) == 0:
                    self._preview_pixels.append((x, y))

        self._preview_size = (width, height)

    def _get_text_pixels_at_position(self) -> list[tuple[int, int]]:
        """Gibt die Text-Pixel an der aktuellen Position zurück."""
        if not self._preview_pixels or not self._position:
            return []

        px, py = self._position
        return [(px + x, py + y) for x, y in self._preview_pixels]

    # === Maus-Events ===

    def on_mouse_press(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if event.button() != Qt.MouseButton.LeftButton:
            return []

        if not self._text:
            return []

        # Vorschau aktualisieren falls nötig
        if self._preview_pixels is None:
            self._update_preview()

        if self._position is None:
            # Erste Platzierung
            self._position = (ctx.grid_x, ctx.grid_y)
            self._active = True
        else:
            # Prüfen ob Klick auf Text (zum Verschieben)
            pixels = self._get_text_pixels_at_position()
            if (ctx.grid_x, ctx.grid_y) in pixels or self._is_near_text(ctx.grid_x, ctx.grid_y):
                self._dragging = True
                self._drag_offset = (ctx.grid_x - self._position[0], ctx.grid_y - self._position[1])
            else:
                # Neue Position
                self._position = (ctx.grid_x, ctx.grid_y)

        return []

    def _is_near_text(self, x: int, y: int) -> bool:
        """Prüft ob ein Punkt in der Nähe des Textes ist."""
        if not self._position or not self._preview_size:
            return False

        px, py = self._position
        w, h = self._preview_size

        return px <= x <= px + w and py <= y <= py + h

    def on_mouse_move(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if self._dragging and self._position:
            # Text verschieben
            self._position = (ctx.grid_x - self._drag_offset[0], ctx.grid_y - self._drag_offset[1])

        return []

    def on_mouse_release(
        self, ctx: ToolContext, event: QMouseEvent
    ) -> list[tuple[int, int, int | None]]:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
        return []

    def on_key_press(self, ctx: ToolContext, event) -> bool:
        key = event.key()

        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            # Text zeichnen - wird über MainWindow gehandelt
            # Hier nur True zurückgeben um das Event zu konsumieren
            return True

        elif key == Qt.Key.Key_Escape:
            # Abbrechen
            self._position = None
            self._active = False
            return True

        return False

    def confirm_text(self, ctx: ToolContext) -> list[tuple[int, int, int | None]]:
        """Bestätigt den Text und gibt die Änderungen zurück."""
        if not self._position or not self._preview_pixels:
            return []

        changes = []
        for x, y in self._get_text_pixels_at_position():
            if self._is_valid_pos(ctx, x, y):
                changes.append((x, y, ctx.current_color_index))

        # Reset
        self._position = None
        self._active = False

        return changes

    def draw_preview(self, ctx: ToolContext, painter: QPainter) -> None:
        if not self._position or not self._preview_pixels:
            return

        # Farbe für Vorschau
        color_entry = ctx.pattern.get_color_entry(ctx.current_color_index)
        if color_entry:
            color = to_qcolor(color_entry.thread.color, 180)
        else:
            color = QColor(100, 200, 150, 180)

        # Text-Pixel zeichnen
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)

        for gx, gy in self._get_text_pixels_at_position():
            if self._is_valid_pos(ctx, gx, gy):
                sx, sy = self._grid_to_screen(ctx, gx, gy)
                painter.drawRect(sx, sy, ctx.cell_size, ctx.cell_size)

        # Bounding Box zeichnen
        if self._preview_size[0] > 0 and self._preview_size[1] > 0:
            sx, sy = self._grid_to_screen(ctx, self._position[0], self._position[1])
            w = self._preview_size[0] * ctx.cell_size
            h = self._preview_size[1] * ctx.cell_size

            painter.setPen(QPen(QColor(THEME.accent_primary), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(sx, sy, w, h)

        # Hinweistext
        painter.setPen(QColor(THEME.accent_primary))
        hint = "Enter: Bestätigen | Esc: Abbrechen | Ziehen: Verschieben"
        painter.drawText(10, 20, hint)
