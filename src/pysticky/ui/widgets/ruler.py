"""
Lineal-Widget für den Canvas.

Features:
- Anzeige von Stich-Positionen
- Klicken zum Navigieren
- Hover-Highlight
- Canvas-Mausposition hervorheben
- Major/Minor Intervalle
"""

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen, QPolygon
from PySide6.QtWidgets import QWidget

from ...core.i18n import t
from ..styles import THEME


class RulerWidget(QWidget):
    """
    Lineal-Widget das Stich-Positionen anzeigt.

    Kann horizontal (oben) oder vertikal (links) sein.
    Klicken navigiert zur entsprechenden Position.
    """

    RULER_SIZE = 25

    # Signal: Position geklickt (Grid-Koordinate)
    position_clicked = Signal(int)

    def __init__(self, orientation: Qt.Orientation, parent=None) -> None:
        super().__init__(parent)

        self._orientation = orientation
        self._offset: int = 0
        self._cell_size: int = 20
        self._pattern_size: int = 50
        self._major_interval: int = 10
        self._hover_pos: int = -1  # Grid-Position unter Maus (Lineal)
        self._canvas_pos: int = -1  # Grid-Position der Maus auf Canvas

        # Farben aus THEME
        self._bg_color = QColor(THEME.bg_light)
        self._text_color = QColor(THEME.text_secondary)
        self._line_color = QColor(THEME.border_light)
        self._major_color = QColor(THEME.accent_primary)
        self._hover_color = QColor(THEME.accent_primary)
        self._hover_color.setAlpha(60)
        self._canvas_marker_color = QColor(THEME.success)
        self._canvas_marker_color.setAlpha(100)
        self._highlight_color = QColor(THEME.accent_secondary)

        if orientation == Qt.Orientation.Horizontal:
            self.setFixedHeight(self.RULER_SIZE)
        else:
            self.setFixedWidth(self.RULER_SIZE)

        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_parameters(self, offset: int, cell_size: int, pattern_size: int) -> None:
        self._offset = offset
        self._cell_size = cell_size
        self._pattern_size = pattern_size
        self.update()

    def set_canvas_position(self, pos: int) -> None:
        """Setzt die aktuelle Canvas-Mausposition (Grid-Koordinate)."""
        if self._canvas_pos != pos:
            self._canvas_pos = pos
            self.update()

    def clear_canvas_position(self) -> None:
        """Löscht die Canvas-Mausposition."""
        if self._canvas_pos != -1:
            self._canvas_pos = -1
            self.update()

    def _screen_to_grid(self, pos: int) -> int:
        """Konvertiert Screen-Position zu Grid-Position."""
        return (pos - self._offset) // self._cell_size

    def _grid_to_screen(self, grid: int) -> int:
        """Konvertiert Grid-Position zu Screen-Position."""
        return grid * self._cell_size + self._offset

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._bg_color)

        font_size = min(10, max(7, self._cell_size // 3))
        font = QFont("Segoe UI", font_size)
        painter.setFont(font)

        if self._orientation == Qt.Orientation.Horizontal:
            self._draw_horizontal(painter)
        else:
            self._draw_vertical(painter)

    def _draw_horizontal(self, painter: QPainter) -> None:
        start = max(0, -self._offset // self._cell_size - 1)
        end = min(self._pattern_size, (self.width() - self._offset) // self._cell_size + 1)

        # Canvas-Position Marker (grün)
        if 0 <= self._canvas_pos < self._pattern_size:
            canvas_x = self._grid_to_screen(self._canvas_pos)
            painter.fillRect(canvas_x, 0, self._cell_size, self.height(), self._canvas_marker_color)

            # Dreieck-Marker unten
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(THEME.success))
            cx = canvas_x + self._cell_size // 2
            triangle = QPolygon(
                [
                    QPoint(cx - 4, self.height()),
                    QPoint(cx + 4, self.height()),
                    QPoint(cx, self.height() - 6),
                ]
            )
            painter.drawPolygon(triangle)

        # Hover-Highlight (wenn Maus über Lineal)
        if 0 <= self._hover_pos < self._pattern_size and self._hover_pos != self._canvas_pos:
            hover_x = self._grid_to_screen(self._hover_pos)
            painter.fillRect(hover_x, 0, self._cell_size, self.height(), self._hover_color)

        for i in range(start, end + 1):
            x = i * self._cell_size + self._offset

            if x < 0 or x > self.width():
                continue

            is_major = i % self._major_interval == 0
            is_hovered = i == self._hover_pos
            is_canvas = i == self._canvas_pos

            if is_major:
                if is_canvas:
                    color = QColor(THEME.success)
                elif is_hovered:
                    color = self._highlight_color
                else:
                    color = self._major_color

                painter.setPen(QPen(color, 2 if (is_hovered or is_canvas) else 1))
                painter.drawLine(x, self.height() - 12, x, self.height())

                painter.setPen(color if (is_hovered or is_canvas) else self._text_color)
                text = str(i)
                text_width = painter.fontMetrics().horizontalAdvance(text)
                painter.drawText(x - text_width // 2, self.height() - 14, text)
            else:
                if is_canvas:
                    color = QColor(THEME.success)
                elif is_hovered:
                    color = self._highlight_color
                else:
                    color = self._line_color

                painter.setPen(QPen(color, 1))
                painter.drawLine(x, self.height() - 6, x, self.height())

        # Untere Linie
        painter.setPen(QPen(self._line_color, 1))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

    def _draw_vertical(self, painter: QPainter) -> None:
        start = max(0, -self._offset // self._cell_size - 1)
        end = min(self._pattern_size, (self.height() - self._offset) // self._cell_size + 1)

        # Canvas-Position Marker (grün)
        if 0 <= self._canvas_pos < self._pattern_size:
            canvas_y = self._grid_to_screen(self._canvas_pos)
            painter.fillRect(0, canvas_y, self.width(), self._cell_size, self._canvas_marker_color)

            # Dreieck-Marker rechts
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(THEME.success))
            cy = canvas_y + self._cell_size // 2
            triangle = QPolygon(
                [
                    QPoint(self.width(), cy - 4),
                    QPoint(self.width(), cy + 4),
                    QPoint(self.width() - 6, cy),
                ]
            )
            painter.drawPolygon(triangle)

        # Hover-Highlight (wenn Maus über Lineal)
        if 0 <= self._hover_pos < self._pattern_size and self._hover_pos != self._canvas_pos:
            hover_y = self._grid_to_screen(self._hover_pos)
            painter.fillRect(0, hover_y, self.width(), self._cell_size, self._hover_color)

        for i in range(start, end + 1):
            y = i * self._cell_size + self._offset

            if y < 0 or y > self.height():
                continue

            is_major = i % self._major_interval == 0
            is_hovered = i == self._hover_pos
            is_canvas = i == self._canvas_pos

            if is_major:
                if is_canvas:
                    color = QColor(THEME.success)
                elif is_hovered:
                    color = self._highlight_color
                else:
                    color = self._major_color

                painter.setPen(QPen(color, 2 if (is_hovered or is_canvas) else 1))
                painter.drawLine(self.width() - 12, y, self.width(), y)

                painter.setPen(color if (is_hovered or is_canvas) else self._text_color)
                text = str(i)
                painter.drawText(2, y + 4, text)
            else:
                if is_canvas:
                    color = QColor(THEME.success)
                elif is_hovered:
                    color = self._highlight_color
                else:
                    color = self._line_color

                painter.setPen(QPen(color, 1))
                painter.drawLine(self.width() - 6, y, self.width(), y)

        # Rechte Linie
        painter.setPen(QPen(self._line_color, 1))
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._orientation == Qt.Orientation.Horizontal:
            self._hover_pos = self._screen_to_grid(int(event.position().x()))
        else:
            self._hover_pos = self._screen_to_grid(int(event.position().y()))

        # Bounds-Check
        if self._hover_pos < 0 or self._hover_pos >= self._pattern_size:
            self._hover_pos = -1

        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if 0 <= self._hover_pos < self._pattern_size:
                self.position_clicked.emit(self._hover_pos)

    def leaveEvent(self, event) -> None:
        self._hover_pos = -1
        self.update()


class RulerCorner(QWidget):
    """
    Ecke zwischen den Linealen.

    Klicken zentriert das Muster.
    Zeigt auch die aktuelle Grid-Position an.
    """

    center_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(RulerWidget.RULER_SIZE, RulerWidget.RULER_SIZE)
        self._bg_color = QColor(THEME.bg_light)
        self._hover = False
        self._canvas_x: int = -1
        self._canvas_y: int = -1

        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(t("Klicken zum Zentrieren"))

    def set_canvas_position(self, x: int, y: int) -> None:
        """Setzt die aktuelle Canvas-Position für die Anzeige."""
        if self._canvas_x != x or self._canvas_y != y:
            self._canvas_x = x
            self._canvas_y = y
            self.update()

    def clear_canvas_position(self) -> None:
        """Löscht die Canvas-Position."""
        self._canvas_x = -1
        self._canvas_y = -1
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        if self._hover:
            painter.fillRect(self.rect(), QColor(THEME.accent_primary + "40"))
        else:
            painter.fillRect(self.rect(), self._bg_color)

        # Koordinaten oder Kreuz-Symbol
        if self._canvas_x >= 0 and self._canvas_y >= 0:
            # Zeige Koordinaten
            painter.setPen(QColor(THEME.success))
            font = QFont("Segoe UI", 6)
            painter.setFont(font)
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter, f"{self._canvas_x}\n{self._canvas_y}"
            )
        else:
            # Kreuz-Symbol
            painter.setPen(QPen(QColor(THEME.accent_primary), 2))
            cx, cy = self.width() // 2, self.height() // 2
            size = 6
            painter.drawLine(cx - size, cy, cx + size, cy)
            painter.drawLine(cx, cy - size, cx, cy + size)

        # Rahmenlinien
        painter.setPen(QPen(QColor(THEME.border_light), 1))
        painter.drawLine(0, self.height() - 1, self.width() - 1, self.height() - 1)
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height() - 1)

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.center_clicked.emit()
