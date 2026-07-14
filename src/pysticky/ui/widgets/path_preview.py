"""
Vorschau-Widget fuer die Stickpfad-Visualisierung.

Zeigt den optimierten Stickpfad mit Zoom, Pan und
verschiedenen Anzeigeoptionen (Nummern, Spruenge, Gitter).
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QMouseEvent,
    QPainter,
    QPen,
    QPolygonF,
    QWheelEvent,
)
from PySide6.QtWidgets import QWidget

from ...core import ColorPath, Pattern
from .custom_tooltip import hide_custom_tooltip, show_custom_tooltip


class PathPreviewWidget(QWidget):
    """Widget zur Visualisierung des Stickpfads mit Zoom und Pan."""

    zoom_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pattern: Pattern | None = None
        self._color_path: ColorPath | None = None
        self._all_color_paths: list[ColorPath] = []
        self._show_numbers: bool = False
        self._show_jumps: bool = True
        self._show_grid: bool = True
        self._show_context: bool = True

        self._zoom: float = 1.0
        self._min_zoom: float = 0.1
        self._max_zoom: float = 10.0
        self._offset_x: float = 0.0
        self._offset_y: float = 0.0
        self._base_cell_size: int = 10

        self._panning: bool = False
        self._last_mouse_pos: QPointF | None = None

        # Aktuelle Farbhelligkeit fuer dynamischen Hintergrund
        self._current_color_luminance: float = 0.5

        self.setMinimumSize(200, 200)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)

    def set_pattern(self, pattern: Pattern) -> None:
        self._pattern = pattern
        self.fit_to_view()
        self.update()

    def set_color_path(self, color_path: ColorPath | None) -> None:
        self._color_path = color_path
        # Helligkeit der aktuellen Farbe ermitteln
        if color_path and self._pattern:
            entry = self._pattern.get_color_entry(color_path.color_index)
            if entry:
                self._current_color_luminance = entry.thread.color.luminance
            else:
                self._current_color_luminance = 0.5
        else:
            self._current_color_luminance = 0.5
        self.update()

    def set_all_color_paths(self, color_paths: list[ColorPath]) -> None:
        """Setzt alle Farbpfade fuer die Kontext-Darstellung."""
        self._all_color_paths = color_paths

    def set_show_numbers(self, show: bool) -> None:
        self._show_numbers = show
        self.update()

    def set_show_jumps(self, show: bool) -> None:
        self._show_jumps = show
        self.update()

    def set_show_context(self, show: bool) -> None:
        self._show_context = show
        self.update()

    def fit_to_view(self) -> None:
        if not self._pattern:
            return

        margin = 20
        available_w = max(100, self.width() - margin * 2)
        available_h = max(100, self.height() - margin * 2)

        pattern_w = self._pattern.width * self._base_cell_size
        pattern_h = self._pattern.height * self._base_cell_size

        if pattern_w == 0 or pattern_h == 0:
            return

        zoom_w = available_w / pattern_w
        zoom_h = available_h / pattern_h
        self._zoom = min(zoom_w, zoom_h, self._max_zoom)
        self._zoom = max(self._zoom, self._min_zoom)

        actual_w = pattern_w * self._zoom
        actual_h = pattern_h * self._zoom
        self._offset_x = (self.width() - actual_w) / 2
        self._offset_y = (self.height() - actual_h) / 2

        self.zoom_changed.emit(int(self._zoom * 100))

    def set_zoom(self, zoom_percent: int) -> None:
        old_zoom = self._zoom
        self._zoom = max(self._min_zoom, min(self._max_zoom, zoom_percent / 100.0))

        if old_zoom != self._zoom:
            center_x = self.width() / 2
            center_y = self.height() / 2
            scale_factor = self._zoom / old_zoom
            self._offset_x = center_x - (center_x - self._offset_x) * scale_factor
            self._offset_y = center_y - (center_y - self._offset_y) * scale_factor
            self.zoom_changed.emit(int(self._zoom * 100))
            self.update()

    def zoom_in(self) -> None:
        self.set_zoom(int(self._zoom * 100 * 1.25))

    def zoom_out(self) -> None:
        self.set_zoom(int(self._zoom * 100 / 1.25))

    @property
    def cell_size(self) -> float:
        return self._base_cell_size * self._zoom

    def _get_background_color(self) -> QColor:
        """Ermittelt passenden Hintergrund basierend auf Farbhelligkeit."""
        if self._current_color_luminance > 0.6:
            return QColor(50, 50, 58)
        elif self._current_color_luminance < 0.4:
            return QColor(235, 235, 240)
        else:
            return QColor(170, 170, 180)

    def _get_grid_color(self) -> QColor:
        """Ermittelt passende Gitterfarbe."""
        if self._current_color_luminance > 0.6:
            return QColor(80, 80, 90)
        elif self._current_color_luminance < 0.4:
            return QColor(200, 200, 210)
        else:
            return QColor(150, 150, 160)

    def _get_text_color(self) -> QColor:
        """Ermittelt passende Textfarbe."""
        if self._current_color_luminance > 0.6:
            return QColor(200, 200, 200)
        else:
            return QColor(60, 60, 60)

    def _stitch_at_pos(self, pos: QPointF):
        """Ermittelt den Stich an einer Bildschirmposition."""
        if not self._color_path or not self._pattern:
            return None
        cell = self.cell_size
        if cell <= 0:
            return None
        gx = int((pos.x() - self._offset_x) / cell)
        gy = int((pos.y() - self._offset_y) / cell)
        for step in self._color_path.steps:
            if step.x == gx and step.y == gy:
                return step
        return None

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._pattern:
            self.fit_to_view()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self._pattern:
            return

        mouse_pos = event.position()
        old_zoom = self._zoom

        delta = event.angleDelta().y()
        if delta > 0:
            self._zoom = min(self._max_zoom, self._zoom * 1.15)
        else:
            self._zoom = max(self._min_zoom, self._zoom / 1.15)

        if old_zoom != self._zoom:
            scale_factor = self._zoom / old_zoom
            self._offset_x = mouse_pos.x() - (mouse_pos.x() - self._offset_x) * scale_factor
            self._offset_y = mouse_pos.y() - (mouse_pos.y() - self._offset_y) * scale_factor
            self.zoom_changed.emit(int(self._zoom * 100))
            self.update()

        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.LeftButton):
            self._panning = True
            self._last_mouse_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._panning and self._last_mouse_pos:
            delta = event.position() - self._last_mouse_pos
            self._offset_x += delta.x()
            self._offset_y += delta.y()
            self._last_mouse_pos = event.position()
            self.update()
        else:
            # Hover-Tooltip
            step = self._stitch_at_pos(event.position())
            if step:
                tip = f"Schritt {step.step_number}  |  Position ({step.x}, {step.y})  |  Distanz: {step.distance_from_prev:.1f}"
                if step.is_jump:
                    tip += "  |  \u26a0 Sprung!"
                show_custom_tooltip(tip, event.globalPosition().toPoint())
            else:
                hide_custom_tooltip()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.LeftButton):
            self._panning = False
            self._last_mouse_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        event.accept()

    def paintEvent(self, event) -> None:
        if not self._pattern:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dynamischer Hintergrund
        bg_color = self._get_background_color()
        painter.fillRect(self.rect(), bg_color)

        self._paint_content(painter, self._offset_x, self._offset_y, self.cell_size, True)

    def _paint_content(
        self, painter: QPainter, ox: float, oy: float, cell: float, show_info: bool = True
    ) -> None:
        """Zeichnet den Inhalt - wird auch fuer Export verwendet."""
        if not self._pattern:
            return

        grid_color = self._get_grid_color()
        text_color = self._get_text_color()

        # Grid
        if self._show_grid and cell >= 3:
            pen = QPen(grid_color, 1)
            painter.setPen(pen)
            pw = self._pattern.width
            ph = self._pattern.height
            for x in range(pw + 1):
                px = ox + x * cell
                painter.drawLine(int(px), int(oy), int(px), int(oy + ph * cell))
            for y in range(ph + 1):
                py = oy + y * cell
                painter.drawLine(int(ox), int(py), int(ox + pw * cell), int(py))

        # Rahmen
        painter.setPen(QPen(grid_color.darker(120), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(ox, oy, self._pattern.width * cell, self._pattern.height * cell))

        # Kontext: alle anderen Farben blass im Hintergrund
        if self._show_context and self._all_color_paths and self._color_path:
            active_idx = self._color_path.color_index
            for cp in self._all_color_paths:
                if cp.color_index == active_idx:
                    continue
                entry = self._pattern.get_color_entry(cp.color_index)
                if not entry:
                    continue
                tc = entry.thread.color
                ctx_color = QColor(tc.r, tc.g, tc.b, 45)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(ctx_color)
                for step in cp.steps:
                    painter.drawRect(
                        QRectF(ox + step.x * cell + 1, oy + step.y * cell + 1, cell - 2, cell - 2)
                    )

        # Aktiver Pfad
        if self._color_path:
            entry = self._pattern.get_color_entry(self._color_path.color_index)
            color = (
                QColor(entry.thread.color.r, entry.thread.color.g, entry.thread.color.b)
                if entry
                else QColor(200, 200, 200)
            )

            # Gefuellte Zellen
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            for step in self._color_path.steps:
                painter.drawRect(
                    QRectF(ox + step.x * cell + 0.5, oy + step.y * cell + 0.5, cell - 1, cell - 1)
                )

            # Linien mit Pfeilspitzen
            if len(self._color_path.steps) > 1:
                prev_step = None
                line_width = max(1, int(cell / 8))
                line_color = (
                    color.darker(150) if self._current_color_luminance > 0.5 else color.lighter(150)
                )

                for step in self._color_path.steps:
                    if prev_step:
                        x1 = ox + prev_step.x * cell + cell / 2
                        y1 = oy + prev_step.y * cell + cell / 2
                        x2 = ox + step.x * cell + cell / 2
                        y2 = oy + step.y * cell + cell / 2

                        if step.is_jump and self._show_jumps:
                            pen = QPen(QColor(220, 80, 80), line_width, Qt.PenStyle.DashLine)
                        else:
                            pen = QPen(line_color, line_width)
                        painter.setPen(pen)
                        painter.setBrush(Qt.BrushStyle.NoBrush)
                        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

                        # Pfeilspitze bei genug Platz
                        if cell >= 12:
                            self._draw_arrowhead(painter, x1, y1, x2, y2, cell, pen.color())

                    prev_step = step

            # Nummern
            if self._show_numbers and cell >= 16:
                if entry and entry.thread.color.luminance > 0.5:
                    num_color = QColor(0, 0, 0)
                else:
                    num_color = QColor(255, 255, 255)
                painter.setPen(num_color)
                font = painter.font()
                font.setPixelSize(max(8, int(cell / 3)))
                painter.setFont(font)
                for i, step in enumerate(self._color_path.steps):
                    x = ox + step.x * cell + cell / 2
                    y = oy + step.y * cell + cell / 2
                    painter.drawText(
                        QRectF(x - cell / 2, y - cell / 2, cell, cell),
                        Qt.AlignmentFlag.AlignCenter,
                        str(i + 1),
                    )

            # Start/Ende Marker
            if self._color_path.steps:
                marker_size = max(cell * 0.8, 10)
                pen_width = max(2, int(cell / 5))

                # Start (gruen)
                start = self._color_path.steps[0]
                sx = ox + start.x * cell + cell / 2
                sy = oy + start.y * cell + cell / 2
                painter.setPen(QPen(QColor(30, 220, 30), pen_width))
                painter.setBrush(QColor(30, 220, 30, 50))
                painter.drawEllipse(QPointF(sx, sy), marker_size / 2, marker_size / 2)

                # "S" Label
                if cell >= 10:
                    painter.setPen(QColor(30, 220, 30))
                    font = painter.font()
                    font.setPixelSize(max(10, int(cell / 2)))
                    font.setBold(True)
                    painter.setFont(font)
                    painter.drawText(
                        QRectF(sx - cell, sy - cell * 1.5, cell * 2, cell),
                        Qt.AlignmentFlag.AlignCenter,
                        "S",
                    )

                # Ende (rot)
                end = self._color_path.steps[-1]
                ex = ox + end.x * cell + cell / 2
                ey = oy + end.y * cell + cell / 2
                painter.setPen(QPen(QColor(220, 50, 50), pen_width))
                painter.setBrush(QColor(220, 50, 50, 50))
                painter.drawRect(
                    QRectF(ex - marker_size / 2, ey - marker_size / 2, marker_size, marker_size)
                )

                # "E" Label
                if cell >= 10:
                    painter.setPen(QColor(220, 50, 50))
                    painter.drawText(
                        QRectF(ex - cell, ey + cell * 0.5, cell * 2, cell),
                        Qt.AlignmentFlag.AlignCenter,
                        "E",
                    )

        # Info-Text (nur in Widget, nicht beim Export)
        if show_info:
            painter.setPen(text_color)
            font = painter.font()
            font.setPixelSize(11)
            font.setBold(False)
            painter.setFont(font)
            info = f"Zoom: {int(self._zoom * 100)}%  |  Mausrad: Zoom  |  Ziehen: Verschieben"
            if self._color_path:
                info += f"  |  {self._color_path.stitch_count} Stiche, {self._color_path.jump_count} Sprünge"
            painter.drawText(5, self.height() - 5, info)

    @staticmethod
    def _draw_arrowhead(
        painter: QPainter, x1: float, y1: float, x2: float, y2: float, cell: float, color: QColor
    ) -> None:
        """Zeichnet eine kleine Pfeilspitze am Endpunkt der Linie."""
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1:
            return

        # Normalisierter Richtungsvektor
        ux = dx / length
        uy = dy / length

        arrow_size = min(cell * 0.3, 8)

        # Spitze etwas vor dem Endpunkt
        tip_x = x2 - ux * 2
        tip_y = y2 - uy * 2

        # Seitliche Punkte
        px = -uy * arrow_size
        py = ux * arrow_size

        p1 = QPointF(tip_x, tip_y)
        p2 = QPointF(tip_x - ux * arrow_size + px, tip_y - uy * arrow_size + py)
        p3 = QPointF(tip_x - ux * arrow_size - px, tip_y - uy * arrow_size - py)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(QPolygonF([p1, p2, p3]))

    def render_to_image(self, cell_size: int = 15, margin: int = 30) -> QImage | None:
        """Rendert den aktuellen Pfad als Bild fuer Export."""
        if not self._pattern or not self._color_path:
            return None

        # Bildgroesse berechnen
        width = self._pattern.width * cell_size + margin * 2
        height = self._pattern.height * cell_size + margin * 2 + 60

        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(self._get_background_color())

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Inhalt zeichnen
        self._paint_content(painter, margin, margin, cell_size, show_info=False)

        # Legende hinzufuegen
        entry = self._pattern.get_color_entry(self._color_path.color_index)
        color_name = entry.thread.name if entry else f"Farbe {self._color_path.color_index}"

        text_color = self._get_text_color()
        painter.setPen(text_color)
        font = QFont()
        font.setPixelSize(14)
        font.setBold(True)
        painter.setFont(font)

        legend_y = height - 50
        painter.drawText(margin, legend_y, f"Farbe: {color_name}")

        font.setBold(False)
        font.setPixelSize(12)
        painter.setFont(font)
        painter.drawText(
            margin,
            legend_y + 18,
            f"Stiche: {self._color_path.stitch_count}  |  "
            f"Spruenge: {self._color_path.jump_count}  |  "
            f"Distanz: {self._color_path.total_distance:.1f}",
        )

        # Legende fuer Marker
        painter.drawText(
            margin, legend_y + 36, "\u25cb S = Start  |  \u25a1 E = Ende  |  - - - = Sprung"
        )

        painter.end()
        return image
