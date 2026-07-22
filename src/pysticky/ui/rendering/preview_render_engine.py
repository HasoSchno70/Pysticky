"""
Render-Engine für Muster-Vorschau.

Erzeugt QImage-Bilder in verschiedenen Darstellungsmodi:
- Stoff-Vorschau (realistisch mit Fadentextur)
- Pixel-Vorschau (flache Farben)
- Symbol-Plan (schwarz-weiß mit Symbolen)
"""

from enum import Enum, auto
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
)

from ...core.layer import NO_STITCH
from ..color_utils import to_qcolor

if TYPE_CHECKING:
    from ...core import Pattern


class RenderMode(Enum):
    """Darstellungsmodus für die Vorschau."""

    FABRIC = auto()  # Stoff-Vorschau (realistisch)
    PIXEL = auto()  # Pixel-Vorschau (flache Farben)
    SYMBOL = auto()  # Symbol-Plan (zum Drucken)


class PreviewRenderEngine:
    """
    Render-Engine die QImage-Bilder für die Muster-Vorschau erzeugt.

    Unterstützt Viewport-Culling für performantes Scrollen und
    verschiedene Detailstufen abhängig von der Zellgröße.
    """

    # Stoff-Farben (gleich wie FabricPreviewWidget)
    FABRIC_COLORS = {
        "Weiß": QColor(255, 255, 255),
        "Ecru": QColor(245, 240, 225),
        "Beige": QColor(235, 225, 205),
        "Hellblau": QColor(220, 235, 250),
        "Hellgrün": QColor(225, 245, 225),
        "Hellrosa": QColor(255, 235, 240),
        "Schwarz": QColor(20, 20, 20),
        "Dunkelblau": QColor(30, 45, 80),
    }

    def __init__(self, pattern: "Pattern") -> None:
        self._pattern = pattern
        self._render_mode = RenderMode.FABRIC
        self._fabric_color = QColor(255, 255, 255)
        self._show_backstitches = True
        self._show_completion = False
        # Default entspricht dem Canvas-Default (rendering_mixin.py /
        # canvas.py) -- ueberschrieben via set_backstitch_style(), sobald der
        # Aufrufer (PatternPreviewDialog) den live konfigurierten Linien-/
        # Kappenstil des Editors kennt.
        self._backstitch_line_style = Qt.PenStyle.SolidLine
        self._backstitch_cap_style = Qt.PenCapStyle.RoundCap
        self._backstitch_width_offset = 0

        # Cache
        self._composite_grid: np.ndarray | None = None
        self._composite_stitch_types: np.ndarray | None = None
        self._color_lut: list[tuple[int, int, int]] | None = None
        self._rebuild_cache()

    # =========================================================================
    # Konfiguration
    # =========================================================================

    @property
    def render_mode(self) -> RenderMode:
        return self._render_mode

    def set_render_mode(self, mode: RenderMode) -> None:
        self._render_mode = mode

    def set_fabric_color(self, color: QColor) -> None:
        self._fabric_color = color

    def set_show_backstitches(self, show: bool) -> None:
        self._show_backstitches = show

    def set_show_completion(self, show: bool) -> None:
        self._show_completion = show

    def set_backstitch_style(
        self,
        line_style: Qt.PenStyle,
        cap_style: Qt.PenCapStyle,
        width_offset: int = 0,
    ) -> None:
        """Übernimmt Linien-/Kappenstil + Dicken-Offset für Rückstiche.

        Ohne diesen Aufruf zeichnet die Vorschau Rückstiche immer
        durchgezogen mit rundem Kappenstil in fester Dicke — unabhängig
        davon, was der Nutzer im Backstitch-Options-Dock eingestellt hat
        (siehe ui/canvas/mixins/rendering_mixin.py::_draw_backstitches, das
        `_backstitch_line_style`/`_backstitch_cap_style`/
        `_backstitch_width_offset` vom Canvas liest). Farbe wurde schon
        immer korrekt übernommen (via get_color_entry) — nur Stil und Dicke
        fielen in der "Muster-Vorschau" stillschweigend auf den Default
        zurück.
        """
        self._backstitch_line_style = line_style
        self._backstitch_cap_style = cap_style
        self._backstitch_width_offset = width_offset

    def _rebuild_cache(self) -> None:
        """Baut den Composite-Grid-Cache neu auf."""
        if self._pattern and self._pattern.width > 0 and self._pattern.height > 0:
            self._composite_grid = self._pattern.layer_stack.get_composite_grid()
            self._composite_stitch_types = (
                self._pattern.layer_stack.get_composite_stitch_type_grid()
            )
        else:
            self._composite_grid = None
            self._composite_stitch_types = None

        # Farb-Lookup-Tabelle
        self._color_lut = []
        for entry in self._pattern.color_entries:
            c = entry.thread.color
            self._color_lut.append((c.r, c.g, c.b))

    # =========================================================================
    # Haupt-Render-Methoden
    # =========================================================================

    def render(self, cell_size: int, viewport: QRect | None = None) -> QImage:
        """
        Rendert das Muster als QImage.

        Args:
            cell_size: Pixel pro Stich-Zelle
            viewport: Sichtbarer Bereich in Pixel-Koordinaten (optional für Culling)

        Returns:
            QImage mit dem gerenderten Muster
        """
        if self._composite_grid is None:
            self._rebuild_cache()

        if self._composite_grid is None:
            # Leeres Muster
            img = QImage(100, 100, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(
                self._fabric_color
                if self._render_mode != RenderMode.SYMBOL
                else QColor(255, 255, 255)
            )
            return img

        grid = self._composite_grid
        pat_h, pat_w = grid.shape

        if viewport is not None:
            # Viewport-Culling: bestimme sichtbare Zellen
            margin = 2
            x_start = max(0, viewport.x() // cell_size - margin)
            y_start = max(0, viewport.y() // cell_size - margin)
            x_end = min(pat_w, (viewport.x() + viewport.width()) // cell_size + margin + 1)
            y_end = min(pat_h, (viewport.y() + viewport.height()) // cell_size + margin + 1)
        else:
            x_start, y_start = 0, 0
            x_end, y_end = pat_w, pat_h

        # Bild-Dimensionen für den sichtbaren Ausschnitt
        img_w = (x_end - x_start) * cell_size
        img_h = (y_end - y_start) * cell_size

        if img_w <= 0 or img_h <= 0:
            img = QImage(1, 1, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(Qt.GlobalColor.transparent)
            return img

        img = QImage(img_w, img_h, QImage.Format.Format_ARGB32_Premultiplied)

        # Hintergrund füllen
        if self._render_mode == RenderMode.SYMBOL:
            img.fill(QColor(255, 255, 255))
        else:
            img.fill(self._fabric_color)

        painter = QPainter(img)

        # Offset: Pixel-Position von Zelle (x_start, y_start) = (0, 0) im Bild
        x_offset = 0
        y_offset = 0

        sub_grid = grid[y_start:y_end, x_start:x_end]
        # Stitch-Type-Slice parallel zum Color-Grid — für halbe/Viertel-Rendering
        if self._composite_stitch_types is not None:
            sub_types = self._composite_stitch_types[y_start:y_end, x_start:x_end]
        else:
            sub_types = np.zeros_like(sub_grid, dtype=np.uint8)

        if self._render_mode == RenderMode.FABRIC:
            self._render_fabric(
                painter,
                sub_grid,
                sub_types,
                cell_size,
                x_offset,
                y_offset,
                x_start,
                y_start,
                x_end,
                y_end,
            )
        elif self._render_mode == RenderMode.PIXEL:
            self._render_pixel(painter, sub_grid, sub_types, cell_size, x_offset, y_offset)
        elif self._render_mode == RenderMode.SYMBOL:
            self._render_symbol(painter, sub_grid, sub_types, cell_size, x_offset, y_offset)

        # Rückstiche
        if self._show_backstitches:
            self._draw_backstitches(
                painter, cell_size, x_start, y_start, x_offset, y_offset, x_end, y_end
            )

        # Completion-Overlay
        if self._show_completion:
            self._draw_completion(
                painter, cell_size, x_start, y_start, x_offset, y_offset, x_end, y_end
            )

        painter.end()

        # Metadaten für den Canvas
        img._cell_range = (x_start, y_start, x_end, y_end)
        return img

    def render_full(self, cell_size: int) -> QImage:
        """
        Rendert das komplette Muster in voller Auflösung (für Export).

        Args:
            cell_size: Pixel pro Stich-Zelle

        Returns:
            QImage des gesamten Musters
        """
        return self.render(cell_size, viewport=None)

    # =========================================================================
    # Stoff-Vorschau (Realistisch)
    # =========================================================================

    def _render_fabric(
        self,
        painter: QPainter,
        sub_grid: np.ndarray,
        sub_types: np.ndarray,
        cell_size: int,
        x_off: int,
        y_off: int,
        x_start: int,
        y_start: int,
        x_end: int,
        y_end: int,
    ) -> None:
        """Rendert realistische Stoff-Vorschau mit Fadentextur."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        sub_h, sub_w = sub_grid.shape

        # Stoff-Textur (Löcher) zeichnen
        if cell_size >= 4:
            self._draw_fabric_texture(painter, sub_w, sub_h, cell_size, x_off, y_off)

        # Kreuzstiche zeichnen
        filled = np.argwhere(sub_grid != NO_STITCH)
        for sy, sx in filled:
            color_idx = int(sub_grid[sy, sx])
            if color_idx < 0 or color_idx >= len(self._color_lut):
                continue

            r, g, b = self._color_lut[color_idx]
            base_color = QColor(r, g, b)

            px = x_off + sx * cell_size
            py = y_off + sy * cell_size

            stype = int(sub_types[sy, sx])
            is_dp_mode = getattr(self._pattern, "mode", "stitch") == "diamond"
            # DIAMOND-Stitch-Type oder FULL im DP-Modus -> facettierter Drill
            if stype == 11 or (is_dp_mode and stype == 0):
                self._draw_diamond_drill_preview(painter, px, py, cell_size, base_color)
            elif stype == 0:
                # Voller Kreuzstich
                if cell_size >= 6:
                    self._draw_cross_stitch_detailed(painter, px, py, cell_size, base_color)
                else:
                    self._draw_cross_stitch_simple(painter, px, py, cell_size, base_color)
            elif stype == 9:
                # French Knot: kleiner Kreis in der Mitte
                self._draw_french_knot_fabric(painter, px, py, cell_size, base_color)
            elif stype == 10:
                # Perle (Bead): größerer Kreis mit Glanz
                self._draw_bead_fabric(painter, px, py, cell_size, base_color)
            else:
                # Halbe / Viertel: gefülltes Dreieck
                self._draw_partial_stitch_fabric(painter, px, py, cell_size, stype, base_color)

    @staticmethod
    def _draw_diamond_drill_preview(
        painter: QPainter, x: int, y: int, size: int, color: QColor
    ) -> None:
        """Diamond-Painting-Drill in der Pattern-Vorschau.

        Vier dreieckige Facetten mit Glanzlicht oben (hell), Schatten unten
        (dunkel), seitlich mittel. Adaptiver Inset: bei kleiner Zelle (<12px)
        berühren sich die Drills nahtlos, damit die Vorlage nicht ausgewaschen
        weiss wirkt. Konsistent zur Canvas-Drill-Darstellung.
        """
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPainterPath

        from ...core.stitch_shapes import diamond_inset_pixels, diamond_should_draw_edge

        inset = int(diamond_inset_pixels(size))
        x0 = x + inset
        y0 = y + inset
        x1 = x + size - inset
        y1 = y + size - inset
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0

        alpha = color.alpha()

        def _shift(c: QColor, factor: int) -> QColor:
            shifted = c.lighter(factor) if factor >= 100 else c.darker(200 - factor)
            shifted.setAlpha(alpha)
            return shifted

        c_top = _shift(color, 145)
        c_right = _shift(color, 110)
        c_left = _shift(color, 95)
        c_bottom = _shift(color, 70)

        # Vier Facetten als Dreiecke (Eckpunkt → benachbarter Eckpunkt → Mitte)
        for pts, fill in (
            ([(x0, y0), (x1, y0), (cx, cy)], c_top),
            ([(x1, y0), (x1, y1), (cx, cy)], c_right),
            ([(x1, y1), (x0, y1), (cx, cy)], c_bottom),
            ([(x0, y1), (x0, y0), (cx, cy)], c_left),
        ):
            path = QPainterPath()
            path.moveTo(*pts[0])
            for px2, py2 in pts[1:]:
                path.lineTo(px2, py2)
            path.closeSubpath()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.fillPath(path, fill)

        if diamond_should_draw_edge(size):
            edge = QColor(0, 0, 0, min(120, alpha))
            painter.setPen(QPen(edge, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(x0, y0, x1 - x0, y1 - y0)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    def _draw_french_knot_fabric(
        self, painter: QPainter, x: int, y: int, size: int, color: QColor
    ) -> None:
        """French Knot in der Stoff-Vorschau: gefüllter Kreis mit Schatten."""
        from ...core.stitch_shapes import french_knot_radius_factor

        radius = max(1, int(size * french_knot_radius_factor()))
        cx = x + size // 2
        cy = y + size // 2
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # Schatten für 3D-Wirkung
        if size >= 8:
            shadow = color.darker(150)
            painter.setBrush(shadow)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(cx - radius + 1, cy - radius + 1, 2 * radius, 2 * radius)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - radius, cy - radius, 2 * radius, 2 * radius)

    def _draw_bead_fabric(
        self, painter: QPainter, x: int, y: int, size: int, color: QColor
    ) -> None:
        """Perle in der Stoff-Vorschau: größere Kugel mit Schatten + Glanz."""
        from ...core.stitch_shapes import bead_radius_factor

        radius = max(2, int(size * bead_radius_factor()))
        cx = x + size // 2
        cy = y + size // 2
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        if size >= 8:
            shadow = color.darker(150)
            painter.setBrush(shadow)
            painter.drawEllipse(cx - radius + 1, cy - radius + 2, 2 * radius, 2 * radius)
        painter.setBrush(color)
        painter.drawEllipse(cx - radius, cy - radius, 2 * radius, 2 * radius)
        # Glanzpunkt
        if size >= 6:
            highlight = color.lighter(150)
            highlight.setAlphaF(0.85)
            painter.setBrush(highlight)
            h_r = max(1, radius // 3)
            painter.drawEllipse(cx - radius // 2, cy - radius // 2, 2 * h_r, 2 * h_r)

    def _draw_fabric_texture(
        self, painter: QPainter, cols: int, rows: int, cell_size: int, x_off: int, y_off: int
    ) -> None:
        """Zeichnet die Stoff-Textur (Löcher im Aida)."""
        hole_color = self._fabric_color.darker(110)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(hole_color))

        hole_size = max(1, cell_size // 4)

        for y in range(rows + 1):
            hy = y_off + y * cell_size - hole_size // 2
            for x in range(cols + 1):
                hx = x_off + x * cell_size - hole_size // 2
                painter.drawEllipse(hx, hy, hole_size, hole_size)

    def _draw_cross_stitch_detailed(
        self, painter: QPainter, x: int, y: int, size: int, color: QColor
    ) -> None:
        """Zeichnet einen Kreuzstich mit Multi-Strang-Effekt (cell_size >= 6)."""
        margin = size // 6
        thread_width = max(1, size // 5)
        strand_offset = max(1, thread_width // 3)
        half_width = max(1, thread_width // 2)

        shadow = color.darker(140)
        highlight = color.lighter(120)
        mid = color

        # Erster Arm: \ (top-left → bottom-right)
        for i in range(-1, 2):
            off = i * strand_offset
            # Schatten
            painter.setPen(QPen(shadow, half_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(
                x + margin + off + 1,
                y + margin + 1,
                x + size - margin + off + 1,
                y + size - margin + 1,
            )
            # Faden (mit Highlight/Schatten-Variation)
            strand_color = highlight if i == -1 else (shadow.lighter(120) if i == 1 else mid)
            painter.setPen(
                QPen(strand_color, half_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            )
            painter.drawLine(
                x + margin + off, y + margin, x + size - margin + off, y + size - margin
            )

        # Zweiter Arm: / (top-right → bottom-left) — liegt oben drauf
        for i in range(-1, 2):
            off = i * strand_offset
            # Schatten
            painter.setPen(QPen(shadow, half_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(
                x + size - margin - off + 1,
                y + margin + 1,
                x + margin - off + 1,
                y + size - margin + 1,
            )
            # Faden
            strand_color = highlight if i == -1 else (shadow.lighter(120) if i == 1 else mid)
            painter.setPen(
                QPen(strand_color, half_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            )
            painter.drawLine(
                x + size - margin - off, y + margin, x + margin - off, y + size - margin
            )

    def _draw_cross_stitch_simple(
        self, painter: QPainter, x: int, y: int, size: int, color: QColor
    ) -> None:
        """Zeichnet einen einfachen Kreuzstich (cell_size < 6)."""
        thread_width = max(1, size // 4)
        margin = max(1, size // 6)

        # Schatten
        shadow = color.darker(130)
        painter.setPen(QPen(shadow, thread_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(
            x + margin + 1, y + margin + 1, x + size - margin + 1, y + size - margin + 1
        )
        painter.drawLine(
            x + size - margin + 1, y + margin + 1, x + margin + 1, y + size - margin + 1
        )

        # Hauptfaden
        painter.setPen(QPen(color, thread_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(x + margin, y + margin, x + size - margin, y + size - margin)
        painter.drawLine(x + size - margin, y + margin, x + margin, y + size - margin)

    def _draw_partial_stitch_fabric(
        self, painter: QPainter, x: int, y: int, size: int, stype: int, color: QColor
    ) -> None:
        """
        Zeichnet halben/Viertel/Dreiviertel-Stich in der Stoff-Vorschau.

        Statt geometrisch perfekter gefüllter Dreiecke (wirkt wie Symbol)
        zeichnen wir echte diagonale Stick-Fäden — näher am echten Sticken.

        - Halbstich (1, 2): EIN Diagonalstrang in der entsprechenden Richtung
        - Viertel (3-6): kurzer Strang von Center in die Eck-Quadranten
        - Dreiviertel (7): voller Halbstich + Viertel-Strang in Gegenrichtung
        """
        margin = max(1, size // 6)
        thread_w = max(2, size // 4) if size >= 6 else max(1, size // 4)
        shadow = color.darker(140)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        def stroke(x1, y1, x2, y2, w=thread_w, shadow_offset=1):
            """Zeichnet einen einzelnen Stick-Faden mit Schatten."""
            if size >= 8:
                painter.setPen(QPen(shadow, w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(
                    x1 + shadow_offset, y1 + shadow_offset, x2 + shadow_offset, y2 + shadow_offset
                )
            painter.setPen(QPen(color, w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(x1, y1, x2, y2)

        # Eck-Punkte mit margin
        tl = (x + margin, y + margin)
        tr = (x + size - margin, y + margin)
        bl = (x + margin, y + size - margin)
        br = (x + size - margin, y + size - margin)
        # Mittelpunkte (für Viertel-Stiche)
        mid = (x + size // 2, y + size // 2)

        # WICHTIG: Konvention im Projekt (siehe stitch.py):
        #   HALF_TL_BR = 1 → "/" (Faden von Bottom-Left nach Top-Right)
        #   HALF_TR_BL = 2 → "\" (Faden von Top-Left nach Bottom-Right)
        # Das ist auf den ersten Blick verwirrend, weil die Namen die
        # Diagonale beschreiben, nicht die Faden-Richtung.
        if stype == 1:
            # "/" Faden
            stroke(*bl, *tr)
        elif stype == 2:
            # "\" Faden
            stroke(*tl, *br)
        elif stype == 3:
            # QUARTER_TL: kurzer Strang von Mid nach TL
            stroke(*mid, *tl)
        elif stype == 4:
            # QUARTER_TR: kurzer Strang von Mid nach TR
            stroke(*mid, *tr)
        elif stype == 5:
            # QUARTER_BL: kurzer Strang von Mid nach BL
            stroke(*mid, *bl)
        elif stype == 6:
            # QUARTER_BR: kurzer Strang von Mid nach BR
            stroke(*mid, *br)
        elif stype == 7:
            # THREE_QUARTER: ein voller "/" + Viertel-Strang nach TR
            stroke(*bl, *tr)
            stroke(*mid, *tr)
        else:
            # Unbekannt -> Fallback: voller Kreuzstich
            if size >= 6:
                self._draw_cross_stitch_detailed(painter, x, y, size, color)
            else:
                self._draw_cross_stitch_simple(painter, x, y, size, color)

    def _draw_partial_stitch_pixel(
        self, painter: QPainter, x: int, y: int, size: int, stype: int, color: QColor
    ) -> None:
        """Halb/Viertel-Stich im Pixel-Modus: gefülltes Dreieck ohne Schatten."""
        path = QPainterPath()
        fx = float(x)
        fy = float(y)
        half = size / 2.0
        right = fx + size
        bottom = fy + size

        if stype == 1:
            path.moveTo(fx, fy)
            path.lineTo(right, fy)
            path.lineTo(fx, bottom)
        elif stype == 2:
            path.moveTo(fx, fy)
            path.lineTo(right, fy)
            path.lineTo(right, bottom)
        elif stype == 3:
            path.moveTo(fx, fy)
            path.lineTo(fx + half, fy)
            path.lineTo(fx, fy + half)
        elif stype == 4:
            path.moveTo(fx + half, fy)
            path.lineTo(right, fy)
            path.lineTo(right, fy + half)
        elif stype == 5:
            path.moveTo(fx, fy + half)
            path.lineTo(fx, bottom)
            path.lineTo(fx + half, bottom)
        elif stype == 6:
            path.moveTo(right, fy + half)
            path.lineTo(fx + half, bottom)
            path.lineTo(right, bottom)
        elif stype == 7:
            # THREE_QUARTER = volles Quadrat MINUS genau das Dreieck aus
            # stype==5 (QUARTER_BL) oben -- war vorher faelschlich das
            # volle Rechteck, optisch identisch zu einem FULL-Stich
            # (derselbe Bug wie core/stitch_shapes.py::_PARTIAL_SHAPES[7]
            # und rendering_mixin.py::_draw_partial_stitch, beide ebenfalls
            # gefixt).
            path.moveTo(fx, fy)
            path.lineTo(right, fy)
            path.lineTo(right, bottom)
            path.lineTo(fx + half, bottom)
            path.lineTo(fx, fy + half)
        else:
            painter.fillRect(x, y, size, size, color)
            return

        path.closeSubpath()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawPath(path)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    # =========================================================================
    # Pixel-Vorschau (Flache Farben)
    # =========================================================================

    def _render_pixel(
        self,
        painter: QPainter,
        sub_grid: np.ndarray,
        sub_types: np.ndarray,
        cell_size: int,
        x_off: int,
        y_off: int,
    ) -> None:
        """Rendert flache Farbblöcke pro Zelle."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        sub_h, sub_w = sub_grid.shape
        filled = np.argwhere(sub_grid != NO_STITCH)

        # Farb-Cache
        color_cache: dict[int, QColor] = {}

        for sy, sx in filled:
            color_idx = int(sub_grid[sy, sx])
            if color_idx < 0 or color_idx >= len(self._color_lut):
                continue

            if color_idx not in color_cache:
                r, g, b = self._color_lut[color_idx]
                color_cache[color_idx] = QColor(r, g, b)

            px = x_off + sx * cell_size
            py = y_off + sy * cell_size

            stype = int(sub_types[sy, sx])
            is_dp_mode = getattr(self._pattern, "mode", "stitch") == "diamond"
            if stype == 11 or (is_dp_mode and stype == 0):
                # Drill statt einfachem Rechteck — gilt für DIAMOND-Type
                # ODER FULL im DP-Pattern (Auto-Mapping).
                self._draw_diamond_drill_preview(
                    painter,
                    px,
                    py,
                    cell_size,
                    color_cache[color_idx],
                )
                continue
            if stype == 0:
                painter.fillRect(px, py, cell_size, cell_size, color_cache[color_idx])
            elif stype == 9:
                # French Knot: heller Hintergrund + Kreis-Punkt
                painter.fillRect(px, py, cell_size, cell_size, self._fabric_color)
                from ...core.stitch_shapes import french_knot_radius_factor

                radius = max(1, int(cell_size * french_knot_radius_factor()))
                cx = px + cell_size // 2
                cy = py + cell_size // 2
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(color_cache[color_idx]))
                painter.drawEllipse(cx - radius, cy - radius, 2 * radius, 2 * radius)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            else:
                # Pixel-Modus: gefülltes Dreieck ohne Schatten-Akzent
                self._draw_partial_stitch_pixel(
                    painter, px, py, cell_size, stype, color_cache[color_idx]
                )

        # Dünne Ränder zwischen Zellen (nur bei größeren Zellen)
        if cell_size >= 8:
            border_color = self._fabric_color.darker(115)
            pen = QPen(border_color, 1)
            painter.setPen(pen)

            # Vertikale Linien
            for sx in range(sub_w + 1):
                lx = x_off + sx * cell_size
                painter.drawLine(lx, y_off, lx, y_off + sub_h * cell_size)
            # Horizontale Linien
            for sy in range(sub_h + 1):
                ly = y_off + sy * cell_size
                painter.drawLine(x_off, ly, x_off + sub_w * cell_size, ly)

    # =========================================================================
    # Symbol-Plan
    # =========================================================================

    def _render_symbol(
        self,
        painter: QPainter,
        sub_grid: np.ndarray,
        sub_types: np.ndarray,
        cell_size: int,
        x_off: int,
        y_off: int,
    ) -> None:
        """Rendert einen Symbol-Plan mit Gitternetz.

        Berücksichtigt den Stich-Typ damit man auf einem ausgedruckten Plan
        Halb-/Viertel-Stiche von vollen unterscheiden kann:
        - Voll (0): Symbol in der Zellmitte (klassisch)
        - Halb (1, 2): kleines Symbol + dünne Diagonale in Faden-Richtung
        - Viertel (3-6): mini-Symbol in der jeweiligen Ecke
        - Dreiviertel (7): voller Symbol-Bereich mit Diagonal-Indikator
        - French Knot (9), Bead (10): ausgefüllter Punkt
        """
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        sub_h, sub_w = sub_grid.shape

        # Gitternetz zeichnen
        self._draw_symbol_grid(painter, sub_w, sub_h, cell_size, x_off, y_off)

        font_full = QFont("Segoe UI Symbol", max(6, int(cell_size * 0.65)))
        font_full.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        font_part = QFont("Segoe UI Symbol", max(5, int(cell_size * 0.40)))
        font_part.setHintingPreference(QFont.HintingPreference.PreferFullHinting)

        filled = np.argwhere(sub_grid != NO_STITCH)
        ink = QColor(0, 0, 0)
        diag_pen = QPen(ink, max(1, cell_size // 14))

        for sy, sx in filled:
            color_idx = int(sub_grid[sy, sx])
            if color_idx < 0 or color_idx >= len(self._pattern.color_entries):
                continue

            entry = self._pattern.color_entries[color_idx]
            symbol = entry.symbol
            stype = int(sub_types[sy, sx])

            px = x_off + sx * cell_size
            py = y_off + sy * cell_size

            self._draw_symbol_for_stitch(
                painter,
                px,
                py,
                cell_size,
                symbol,
                stype,
                font_full,
                font_part,
                ink,
                diag_pen,
            )

    def _draw_symbol_for_stitch(
        self,
        painter: QPainter,
        px: int,
        py: int,
        cs: int,
        symbol: str,
        stype: int,
        font_full: QFont,
        font_part: QFont,
        ink: QColor,
        diag_pen: QPen,
    ) -> None:
        """Zeichnet ein Symbol entsprechend dem Stich-Typ in eine Zelle."""
        full_rect = QRectF(px, py, cs, cs)
        half_w = cs / 2

        painter.setPen(QPen(ink))

        if stype == 0:
            # Voller Kreuzstich: Symbol in der Mitte
            painter.setFont(font_full)
            painter.drawText(full_rect, Qt.AlignmentFlag.AlignCenter, symbol)
        elif stype == 1:
            # "/" Halbstich: Symbol in der oberen-rechten Hälfte + "/"-Diagonale
            painter.setPen(diag_pen)
            painter.drawLine(int(px), int(py + cs), int(px + cs), int(py))
            painter.setPen(QPen(ink))
            painter.setFont(font_part)
            sym_rect = QRectF(px + half_w * 0.55, py + 1, half_w * 0.5, half_w * 0.7)
            painter.drawText(sym_rect, Qt.AlignmentFlag.AlignCenter, symbol)
        elif stype == 2:
            # "\" Halbstich: Symbol in der oberen-linken Hälfte + "\"-Diagonale
            painter.setPen(diag_pen)
            painter.drawLine(int(px), int(py), int(px + cs), int(py + cs))
            painter.setPen(QPen(ink))
            painter.setFont(font_part)
            sym_rect = QRectF(px + 1, py + 1, half_w * 0.5, half_w * 0.7)
            painter.drawText(sym_rect, Qt.AlignmentFlag.AlignCenter, symbol)
        elif stype in (3, 4, 5, 6):
            # Viertel: Symbol klein in der Ecke
            painter.setFont(font_part)
            corners = {
                3: QRectF(px + 1, py + 1, half_w, half_w),  # TL
                4: QRectF(px + half_w, py + 1, half_w - 1, half_w),  # TR
                5: QRectF(px + 1, py + half_w, half_w, half_w - 1),  # BL
                6: QRectF(px + half_w, py + half_w, half_w - 1, half_w - 1),  # BR
            }
            painter.drawText(corners[stype], Qt.AlignmentFlag.AlignCenter, symbol)
        elif stype == 7:
            # Dreiviertel: vollwertiges Symbol + Diagonal-Indikator
            painter.setPen(diag_pen)
            painter.drawLine(int(px), int(py + cs), int(px + cs), int(py))
            painter.setPen(QPen(ink))
            painter.setFont(font_full)
            painter.drawText(full_rect, Qt.AlignmentFlag.AlignCenter, symbol)
        elif stype == 9:
            # French Knot: ausgefüllter Punkt
            painter.setBrush(ink)
            painter.setPen(Qt.PenStyle.NoPen)
            r = max(2, cs // 5)
            painter.drawEllipse(int(px + cs // 2 - r), int(py + cs // 2 - r), 2 * r, 2 * r)
        elif stype == 10:
            # Bead: größerer Punkt mit Glanz
            painter.setBrush(ink)
            painter.setPen(Qt.PenStyle.NoPen)
            r = max(3, cs // 4)
            painter.drawEllipse(int(px + cs // 2 - r), int(py + cs // 2 - r), 2 * r, 2 * r)
        else:
            # Fallback: voller Symbol-Modus
            painter.setFont(font_full)
            painter.drawText(full_rect, Qt.AlignmentFlag.AlignCenter, symbol)

    def _draw_symbol_grid(
        self, painter: QPainter, cols: int, rows: int, cell_size: int, x_off: int, y_off: int
    ) -> None:
        """Zeichnet das Gitternetz für den Symbol-Plan."""
        # Normales Gitter
        normal_pen = QPen(QColor(200, 200, 200), 1)
        bold_pen = QPen(QColor(60, 60, 60), 2)

        total_w = cols * cell_size
        total_h = rows * cell_size

        # Vertikale Linien
        for x in range(cols + 1):
            lx = x_off + x * cell_size
            painter.setPen(bold_pen if x % 10 == 0 else normal_pen)
            painter.drawLine(lx, y_off, lx, y_off + total_h)

        # Horizontale Linien
        for y in range(rows + 1):
            ly = y_off + y * cell_size
            painter.setPen(bold_pen if y % 10 == 0 else normal_pen)
            painter.drawLine(x_off, ly, x_off + total_w, ly)

    # =========================================================================
    # Rückstiche
    # =========================================================================

    def _draw_backstitches(
        self,
        painter: QPainter,
        cell_size: int,
        x_start: int,
        y_start: int,
        x_off: int,
        y_off: int,
        x_end: int,
        y_end: int,
    ) -> None:
        """Zeichnet alle sichtbaren Rückstiche."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        half_cell = cell_size / 2.0
        thread_width = max(1, cell_size // 5 + self._backstitch_width_offset)

        # Sichtbarer Bereich in Halbzell-Koordinaten
        vis_x1 = x_start * 2
        vis_y1 = y_start * 2
        vis_x2 = x_end * 2
        vis_y2 = y_end * 2

        for bs in self._pattern.backstitches:
            # Culling: prüfe ob der Backstitch im sichtbaren Bereich liegt
            bx_min = min(bs.x1, bs.x2)
            bx_max = max(bs.x1, bs.x2)
            by_min = min(bs.y1, bs.y2)
            by_max = max(bs.y1, bs.y2)

            if bx_max < vis_x1 or bx_min > vis_x2 or by_max < vis_y1 or by_min > vis_y2:
                continue

            entry = self._pattern.get_color_entry(bs.color_index)
            if entry:
                color = to_qcolor(entry.thread.color)
            else:
                color = QColor(0, 0, 0)

            # Koordinaten relativ zum Bild (Offset: x_start, y_start)
            x1 = x_off + (bs.x1 - x_start * 2) * half_cell
            y1 = y_off + (bs.y1 - y_start * 2) * half_cell
            x2 = x_off + (bs.x2 - x_start * 2) * half_cell
            y2 = y_off + (bs.y2 - y_start * 2) * half_cell

            # Schatten
            painter.setPen(
                QPen(
                    QColor(0, 0, 0, 80),
                    thread_width + 2,
                    self._backstitch_line_style,
                    self._backstitch_cap_style,
                )
            )
            painter.drawLine(int(x1) + 1, int(y1) + 1, int(x2) + 1, int(y2) + 1)

            # Hauptlinie
            if self._render_mode == RenderMode.SYMBOL:
                # Gestrichelt im Symbol-Plan (feste Konvention fuer gedruckte
                # Plaene, unabhaengig vom editierbaren Canvas-Linienstil)
                pen = QPen(color, thread_width, Qt.PenStyle.DashLine, self._backstitch_cap_style)
            else:
                pen = QPen(
                    color, thread_width, self._backstitch_line_style, self._backstitch_cap_style
                )
            painter.setPen(pen)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

    # =========================================================================
    # Completion-Overlay
    # =========================================================================

    def _draw_completion(
        self,
        painter: QPainter,
        cell_size: int,
        x_start: int,
        y_start: int,
        x_off: int,
        y_off: int,
        x_end: int,
        y_end: int,
    ) -> None:
        """Zeichnet das Completion-Overlay auf fertige Stiche."""
        overlay_color = QColor(0, 200, 80, 50)

        for layer in self._pattern.layer_stack:
            if not layer.visible:
                continue

            sub_completion = layer.completion_grid[y_start:y_end, x_start:x_end]
            sub_grid = layer.grid[y_start:y_end, x_start:x_end]

            mask = sub_completion & (sub_grid != NO_STITCH)
            completed = np.argwhere(mask)

            for sy, sx in completed:
                px = x_off + sx * cell_size
                py = y_off + sy * cell_size
                painter.fillRect(px, py, cell_size, cell_size, overlay_color)

                # Häkchen bei größeren Zellen
                if cell_size >= 12:
                    painter.setPen(
                        QPen(
                            QColor(0, 180, 60, 180),
                            max(1, cell_size // 8),
                            Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap,
                        )
                    )
                    cx = px + cell_size // 2
                    cy = py + cell_size // 2
                    s = cell_size // 4
                    painter.drawLine(cx - s, cy, cx - s // 2, cy + s)
                    painter.drawLine(cx - s // 2, cy + s, cx + s, cy - s)
