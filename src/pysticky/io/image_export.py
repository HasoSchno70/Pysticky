"""
Bild-Export (PNG/JPG/BMP) für Kreuzstich-Muster.

Rendert das Muster als Rasterbild mit optionalem Raster und Symbolen.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath

from ..core.stitch_shapes import (
    bead_radius_factor,
    french_knot_radius_factor,
    is_bead,
    is_french_knot,
    is_partial_stitch,
    partial_stitch_points,
)

if TYPE_CHECKING:
    from ..core import Pattern


def _fill_partial_stitch(
    painter: QPainter, stype: int, x: float, y: float, size: float, color: QColor
) -> None:
    """Fuellt die Polygon-Form eines halben/Viertel-Stichs mit `color`."""
    pts = partial_stitch_points(stype, x, y, size)
    if not pts:
        return
    path = QPainterPath()
    path.moveTo(QPointF(*pts[0]))
    for p in pts[1:]:
        path.lineTo(QPointF(*p))
    path.closeSubpath()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.fillPath(path, color)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)


def _fill_french_knot(painter: QPainter, x: float, y: float, size: float, color: QColor) -> None:
    """Zeichnet einen Franzoesischen Knoten als gefuellten Kreis in der Zellmitte."""
    radius = max(1.0, size * french_knot_radius_factor())
    cx = x + size / 2.0
    cy = y + size / 2.0
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(QPointF(cx, cy), radius, radius)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)


def _fill_bead(painter: QPainter, x: float, y: float, size: float, color: QColor) -> None:
    """Zeichnet eine Perle: groessere Kugel mit Glanzpunkt."""
    radius = max(1.5, size * bead_radius_factor())
    cx = x + size / 2.0
    cy = y + size / 2.0
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(QPointF(cx, cy), radius, radius)
    # Glanzpunkt
    highlight = color.lighter(150)
    highlight.setAlphaF(0.85)
    painter.setBrush(highlight)
    h_r = max(1.0, radius / 3.0)
    painter.drawEllipse(QPointF(cx - radius / 2.5, cy - radius / 2.5), h_r, h_r)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)


class ImageExporter:
    """Exportiert ein Kreuzstich-Muster als Rasterbild."""

    def __init__(self, pattern: Pattern) -> None:
        self._pattern = pattern

    def export(
        self,
        filepath: str | Path,
        cell_size: int = 10,
        show_grid: bool = True,
        show_symbols: bool = False,
    ) -> bool:
        """
        Exportiert das Muster als Bild.

        Args:
            filepath: Zieldatei (.png, .jpg, .bmp)
            cell_size: Pixelgröße pro Stich (4-100)
            show_grid: Rasterlinien zeichnen
            show_symbols: Farbsymbole zeichnen

        Returns:
            True bei Erfolg
        """
        from ..core import NO_STITCH

        pattern = self._pattern
        cell_size = max(4, min(100, cell_size))

        img_w = pattern.width * cell_size
        img_h = pattern.height * cell_size
        image = QImage(img_w, img_h, QImage.Format.Format_ARGB32)
        image.fill(QColor(250, 250, 245))

        painter = QPainter()
        if not painter.begin(image):
            return False

        try:
            composite = pattern.layer_stack.get_composite_grid()
            type_grid = pattern.layer_stack.get_composite_stitch_type_grid()

            # Stiche zeichnen
            for y in range(pattern.height):
                for x in range(pattern.width):
                    color_idx = int(composite[y, x])
                    if color_idx == NO_STITCH or color_idx >= len(pattern.color_entries):
                        continue

                    entry = pattern.color_entries[color_idx]
                    c = entry.thread.color
                    color = QColor(c.r, c.g, c.b)
                    px = x * cell_size
                    py = y * cell_size

                    stype = int(type_grid[y, x])
                    if is_french_knot(stype):
                        # Stoff-Hintergrund + Punkt
                        painter.fillRect(
                            QRectF(px, py, cell_size, cell_size),
                            QColor(250, 250, 245),
                        )
                        _fill_french_knot(painter, px, py, cell_size, color)
                    elif is_bead(stype):
                        painter.fillRect(
                            QRectF(px, py, cell_size, cell_size),
                            QColor(250, 250, 245),
                        )
                        _fill_bead(painter, px, py, cell_size, color)
                    elif is_partial_stitch(stype):
                        _fill_partial_stitch(painter, stype, px, py, cell_size, color)
                    else:
                        painter.fillRect(QRectF(px, py, cell_size, cell_size), color)

                    if show_symbols and cell_size >= 8 and entry.symbol:
                        text_color = QColor(0, 0, 0) if c.is_light else QColor(255, 255, 255)
                        painter.setPen(text_color)
                        font_size = max(4, int(cell_size * 0.6))
                        painter.setFont(QFont("Segoe UI", font_size))
                        painter.drawText(
                            QRectF(px, py, cell_size, cell_size),
                            Qt.AlignmentFlag.AlignCenter,
                            entry.symbol,
                        )

            # Rasterlinien
            if show_grid:
                painter.setPen(QColor(200, 200, 200))
                for x in range(pattern.width + 1):
                    px = x * cell_size
                    painter.drawLine(px, 0, px, img_h)
                for y in range(pattern.height + 1):
                    py = y * cell_size
                    painter.drawLine(0, py, img_w, py)

                # Hauptraster (alle 10)
                painter.setPen(QColor(140, 140, 140))
                for x in range(0, pattern.width + 1, 10):
                    px = x * cell_size
                    painter.drawLine(px, 0, px, img_h)
                for y in range(0, pattern.height + 1, 10):
                    py = y * cell_size
                    painter.drawLine(0, py, img_w, py)
        finally:
            painter.end()

        filepath = str(filepath)
        fmt = None
        if filepath.lower().endswith(".jpg") or filepath.lower().endswith(".jpeg"):
            fmt = "JPEG"
        elif filepath.lower().endswith(".bmp"):
            fmt = "BMP"

        return image.save(filepath, fmt)
