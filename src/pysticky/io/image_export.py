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

        Raises:
            RuntimeError: Wenn der Maler nicht initialisiert werden kann
                (z. B. Bild zu gross).
            OSError: Wenn die Datei nicht geschrieben werden kann.
        """
        import numpy as np

        from ..core import NO_STITCH

        pattern = self._pattern
        cell_size = max(4, min(100, cell_size))

        img_w = pattern.width * cell_size
        img_h = pattern.height * cell_size

        composite = pattern.layer_stack.get_composite_grid()
        type_grid = pattern.layer_stack.get_composite_stitch_type_grid()
        h, w = composite.shape
        bg = (250, 250, 245)

        # Farb-LUT (color_idx -> RGB)
        n_colors = len(pattern.color_entries)
        palette = np.empty((max(n_colors, 1), 3), dtype=np.uint8)
        for i, entry in enumerate(pattern.color_entries):
            col = entry.thread.color
            palette[i] = (col.r, col.g, col.b)

        valid = (composite != NO_STITCH) & (composite >= 0) & (composite < n_colors)

        # Sonder-Stiche (French Knot / Bead / Partial) werden weiter einzeln
        # gezeichnet; alle anderen (Vollstiche) rendern wir vektorisiert.
        special = np.zeros_like(type_grid, dtype=bool)
        for st in np.unique(type_grid):
            sti = int(st)
            if is_french_knot(sti) or is_bead(sti) or is_partial_stitch(sti):
                special |= type_grid == st

        # Basisbild (1 Pixel/Stich): Hintergrund, dann Vollstiche einfaerben.
        # Sonder-Stich-Zellen bleiben Hintergrund (sie werden ueberzeichnet).
        base = np.empty((h, w, 3), dtype=np.uint8)
        base[:] = bg
        full = valid & ~special
        base[full] = palette[composite[full]]

        # Auf Zellgroesse hochskalieren (nearest -> harte Bloecke).
        base = np.ascontiguousarray(base)
        src = QImage(base.data, w, h, w * 3, QImage.Format.Format_RGB888)
        image = src.scaled(
            img_w,
            img_h,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        ).convertToFormat(QImage.Format.Format_ARGB32)

        painter = QPainter()
        if not painter.begin(image):
            raise RuntimeError(
                f"Bild-Maler konnte nicht initialisiert werden "
                f"(Bild evtl. zu gross: {img_w}x{img_h} Pixel)."
            )

        try:
            # Sonder-Stiche einzeln zeichnen (nur gueltige Farb-Zellen).
            for y, x in np.argwhere(special & valid):
                color_idx = int(composite[y, x])
                col = pattern.color_entries[color_idx].thread.color
                color = QColor(col.r, col.g, col.b)
                px = int(x) * cell_size
                py = int(y) * cell_size
                stype = int(type_grid[y, x])
                if is_french_knot(stype):
                    _fill_french_knot(painter, px, py, cell_size, color)
                elif is_bead(stype):
                    _fill_bead(painter, px, py, cell_size, color)
                elif is_partial_stitch(stype):
                    _fill_partial_stitch(painter, stype, px, py, cell_size, color)

            # Symbole (optional, zwangslaeufig pro Zelle).
            if show_symbols and cell_size >= 8:
                painter.setFont(QFont("Segoe UI", max(4, int(cell_size * 0.6))))
                for y, x in np.argwhere(valid):
                    entry = pattern.color_entries[int(composite[y, x])]
                    if not entry.symbol:
                        continue
                    c = entry.thread.color
                    text_color = QColor(0, 0, 0) if c.is_light else QColor(255, 255, 255)
                    painter.setPen(text_color)
                    painter.drawText(
                        QRectF(int(x) * cell_size, int(y) * cell_size, cell_size, cell_size),
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
        fmt: str | None = None
        if filepath.lower().endswith(".jpg") or filepath.lower().endswith(".jpeg"):
            fmt = "JPEG"
        elif filepath.lower().endswith(".bmp"):
            fmt = "BMP"

        # PySide6 akzeptiert zur Laufzeit str als Format; der Stub verlangt bytes.
        if not image.save(filepath, fmt):  # type: ignore[arg-type]
            raise OSError(f"Bild konnte nicht gespeichert werden: {filepath}")
        return True
