"""
Bild-Export (PNG/JPG/BMP) für Kreuzstich-Muster.

Rendert das Muster als Rasterbild mit optionalem Raster und Symbolen.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen

from ..core.stitch_shapes import (
    bead_radius_factor,
    diamond_inset_pixels,
    diamond_should_draw_edge,
    french_knot_radius_factor,
    is_bead,
    is_diamond,
    is_french_knot,
    is_partial_stitch,
    partial_stitch_points,
)

if TYPE_CHECKING:
    from ..core import Pattern


def _fill_partial_stitch(
    painter: QPainter, stype: int, x: float, y: float, size: float, color: QColor
) -> None:
    """Füllt die Polygon-Form eines halben/Viertel-Stichs mit `color`."""
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
    """Zeichnet einen Französischen Knoten als gefüllten Kreis in der Zellmitte."""
    radius = max(1.0, size * french_knot_radius_factor())
    cx = x + size / 2.0
    cy = y + size / 2.0
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(QPointF(cx, cy), radius, radius)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)


def _fill_diamond_drill(painter: QPainter, x: float, y: float, size: float, color: QColor) -> None:
    """Zeichnet einen Diamond-Painting-Drill: facettiertes Quadrat.

    Eigenständige Kopie der Facetten-Geometrie aus
    `ui/diamond_drill_render.py::draw_diamond_drill` (dort für die drei
    QPainter-Canvas-Pfade). `io/` importiert bewusst nichts aus `ui/`
    (Layering), daher hier dupliziert statt geteilt -- die reine Geometrie
    (Inset/Edge-Schwellwerte) kommt weiterhin aus `core/stitch_shapes.py`.
    """
    inset = diamond_inset_pixels(size)
    x0, y0 = x + inset, y + inset
    x1, y1 = x + size - inset, y + size - inset
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0

    top = QPainterPath()
    top.moveTo(x0, y0)
    top.lineTo(x1, y0)
    top.lineTo(cx, cy)
    top.closeSubpath()

    right = QPainterPath()
    right.moveTo(x1, y0)
    right.lineTo(x1, y1)
    right.lineTo(cx, cy)
    right.closeSubpath()

    bottom = QPainterPath()
    bottom.moveTo(x1, y1)
    bottom.lineTo(x0, y1)
    bottom.lineTo(cx, cy)
    bottom.closeSubpath()

    left = QPainterPath()
    left.moveTo(x0, y1)
    left.lineTo(x0, y0)
    left.lineTo(cx, cy)
    left.closeSubpath()

    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.fillPath(top, color.lighter(145))
    painter.fillPath(right, color.lighter(110))
    painter.fillPath(left, color.darker(200 - 95))
    painter.fillPath(bottom, color.darker(200 - 70))

    if diamond_should_draw_edge(size):
        edge = QColor(0, 0, 0, 120)
        painter.setPen(edge)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(x0, y0, x1 - x0, y1 - y0))
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)


def _fill_bead(painter: QPainter, x: float, y: float, size: float, color: QColor) -> None:
    """Zeichnet eine Perle: größere Kugel mit Glanzpunkt."""
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


def _draw_backstitches(painter: QPainter, pattern: Pattern, cell_size: int) -> None:
    """Zeichnet alle Rückstich-Konturlinien des Musters.

    Fehlte bisher komplett im Bild-Export -- HTML- (`html_export.py::
    _generate_backstitches_svg`), PDF- (`pdf_export_drawings.py`) und
    Canvas-Renderer (`rendering_mixin.py::_draw_backstitches`) zeichnen
    Rückstiche seit jeher, der Raster-Export liess sie schlicht weg.

    Koordinaten sind wie überall im Rückstich-System in halben Stichen
    (siehe `core/backstitch_manager.py`); `half_cell` rechnet das in
    Pixel um. Schatten + Farblinie mit Rundkappen, analog zum
    HTML-Export (dort `stroke_width = max(1.5, cell_size / 8)`).

    Im DP-Modus wird nichts gezeichnet -- Diamond Painting kennt kein
    Rückstich-Konzept (ein per `convert_to_mode()` umgeschaltetes Pattern
    kann aber noch alte Backstitch-Daten tragen, siehe html_export_sections.py).
    """
    if getattr(pattern, "mode", "stitch") == "diamond":
        return
    if not pattern.backstitches:
        return

    half_cell = cell_size / 2.0
    stroke_width = max(1.5, cell_size / 8.0)

    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    for bs in pattern.backstitches:
        entry = pattern.get_color_entry(bs.color_index)
        color = QColor(0, 0, 0)
        if entry:
            tc = entry.thread.color
            color = QColor(tc.r, tc.g, tc.b)

        line = QLineF(bs.x1 * half_cell, bs.y1 * half_cell, bs.x2 * half_cell, bs.y2 * half_cell)

        # Schatten für Kontrast gegen helle/dunkle Hintergründe.
        shadow_pen = QPen(QColor(0, 0, 0, 80), stroke_width + 1)
        shadow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(shadow_pen)
        painter.drawLine(line)

        pen = QPen(color, stroke_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(line)
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
            thread_color = entry.thread.color
            palette[i] = (thread_color.r, thread_color.g, thread_color.b)

        valid = (composite != NO_STITCH) & (composite >= 0) & (composite < n_colors)

        # Im DP-Modus rendern FULL-Stiche (Typ 0) ebenfalls als Diamond-Drill,
        # analog PDF-/HTML-Export (siehe pdf_export_drawings.py::_add_stitch_shape)
        # und Canvas-Renderer (rendering_mixin.py, dort ueber diamond_view-Flag).
        is_dp_mode = getattr(pattern, "mode", "stitch") == "diamond"

        # Sonder-Stiche (French Knot / Bead / Partial / Diamond-Drill) werden
        # weiter einzeln gezeichnet; alle anderen (Vollstiche ausserhalb des
        # DP-Modus) rendern wir vektorisiert.
        special = np.zeros_like(type_grid, dtype=bool)
        for st in np.unique(type_grid):
            sti = int(st)
            if (
                is_french_knot(sti)
                or is_bead(sti)
                or is_partial_stitch(sti)
                or is_diamond(sti)
                or (is_dp_mode and sti == 0)
            ):
                special |= type_grid == st

        # Basisbild (1 Pixel/Stich): Hintergrund, dann Vollstiche einfärben.
        # Sonder-Stich-Zellen bleiben Hintergrund (sie werden überzeichnet).
        base = np.empty((h, w, 3), dtype=np.uint8)
        base[:] = bg
        full = valid & ~special
        base[full] = palette[composite[full]]

        # Auf Zellgröße hochskalieren (nearest -> harte Blöcke).
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
            # Sonder-Stiche einzeln zeichnen (nur gültige Farb-Zellen).
            for y, x in np.argwhere(special & valid):
                color_idx = int(composite[y, x])
                thread_color = pattern.color_entries[color_idx].thread.color
                color = QColor(thread_color.r, thread_color.g, thread_color.b)
                px = int(x) * cell_size
                py = int(y) * cell_size
                stype = int(type_grid[y, x])
                if is_diamond(stype) or (is_dp_mode and stype == 0):
                    _fill_diamond_drill(painter, px, py, cell_size, color)
                elif is_french_knot(stype):
                    _fill_french_knot(painter, px, py, cell_size, color)
                elif is_bead(stype):
                    _fill_bead(painter, px, py, cell_size, color)
                elif is_partial_stitch(stype):
                    _fill_partial_stitch(painter, stype, px, py, cell_size, color)

            # Rückstich-Konturlinien (fehlten bisher komplett, siehe
            # _draw_backstitches-Docstring).
            _draw_backstitches(painter, pattern, cell_size)

            # Symbole (optional, zwangsläufig pro Zelle).
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
