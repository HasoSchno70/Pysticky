"""
Zeichnungs-Mixin für den PDF-Export.

Enthält Methoden zur Erstellung von Vorschau- und Muster-Zeichnungen
als reportlab Drawing-Objekte.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect, String
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from ..core.stitch_shapes import (
    bead_radius_factor,
    diamond_inset_pixels,
    diamond_should_draw_edge,
    french_knot_radius_factor,
    is_bead,
    is_diamond,
    is_french_knot,
    is_partial_stitch,
    normalized_partial_stitch_shape,
)

if TYPE_CHECKING:
    from ..core import ColorPath
    from ._export_base import _PDFExportBase as _Base
else:
    _Base = object


class PDFDrawingsMixin(_Base):
    """Mixin mit Zeichnungs-Methoden für den PDF-Export."""

    def _add_drill_shape(
        self, drawing, rx: float, ry: float, cell_w: float, cell_h: float, fill_color
    ) -> None:
        """Fuegt einen Diamond-Painting-Drill (4 Facetten) ins Drawing.

        PDF-Y waechst nach oben — die "obere" Facette ist also die mit dem
        groesseren Y. Wir invertieren entsprechend, damit das Glanzlicht
        oben landet wenn das Bild aufrecht steht.

        Inset adaptiv (siehe stitch_shapes.diamond_inset_pixels): bei kleiner
        Zellgroesse beruehren sich die Drills nahtlos.
        """
        min_side = min(cell_w, cell_h)
        inset = diamond_inset_pixels(min_side)
        x0, y0 = rx + inset, ry + inset
        x1, y1 = rx + cell_w - inset, ry + cell_h - inset
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0

        def _shaded(color, factor: int):
            """factor 100 = unchanged, 150 = lighter, 70 = darker."""
            r, g, b = color.red, color.green, color.blue
            if factor >= 100:
                amt = (factor - 100) / 100.0
                return colors.Color(
                    r + (1.0 - r) * amt,
                    g + (1.0 - g) * amt,
                    b + (1.0 - b) * amt,
                )
            amt = factor / 100.0
            return colors.Color(r * amt, g * amt, b * amt)

        # In PDF-Koordinaten (Y waechst nach oben) ist y1 die obere Kante.
        c_top = _shaded(fill_color, 145)  # Glanzlicht
        c_right = _shaded(fill_color, 110)
        c_left = _shaded(fill_color, 95)
        c_bottom = _shaded(fill_color, 70)  # Schatten

        drawing.add(Polygon([x0, y1, x1, y1, cx, cy], strokeColor=None, fillColor=c_top))
        drawing.add(Polygon([x1, y1, x1, y0, cx, cy], strokeColor=None, fillColor=c_right))
        drawing.add(Polygon([x1, y0, x0, y0, cx, cy], strokeColor=None, fillColor=c_bottom))
        drawing.add(Polygon([x0, y0, x0, y1, cx, cy], strokeColor=None, fillColor=c_left))
        # Dunkler Kantenrand fuer Trennschaerfe — nur bei groesserer Zelle,
        # bei kleinem cell_size frisst der Rand den Drill auf.
        if diamond_should_draw_edge(min_side):
            drawing.add(
                Rect(
                    x0,
                    y0,
                    x1 - x0,
                    y1 - y0,
                    strokeColor=colors.Color(0, 0, 0, 0.4),
                    strokeWidth=0.3,
                    fillColor=None,
                )
            )

    def _add_stitch_shape(
        self,
        drawing,
        x: int,
        y: int,
        rx: float,
        ry: float,
        cell_w: float,
        cell_h: float,
        fill_color,
        height: float,
    ) -> None:
        """
        Fuegt entweder ein Rect (FULL) oder ein Polygon (halb/Viertel) ins Drawing.

        PDF-Y ist invertiert (0 = unten). Die Eckpunkt-Berechnung kompensiert
        das, indem sie die normalisierten 0..1-Punkte aus `partial_stitch_points`
        per `1 - ny` spiegelt.

        Im DP-Modus wird stattdessen die Drill-Optik (4 Facetten) gerendert —
        sowohl fuer echte DIAMOND-Stiche als auch fuer FULL-Stiche bei
        Pattern.mode='diamond' (analog Canvas-Renderer).
        """
        stype = self._get_pixel_stitch_type(x, y)
        is_dp_mode = getattr(self.pattern, "mode", "stitch") == "diamond"

        if is_diamond(stype) or (is_dp_mode and stype == 0):
            # Stoff/Klebegrund unter dem Drill
            drawing.add(
                Rect(
                    rx,
                    ry,
                    cell_w + 0.3,
                    cell_h + 0.3,
                    strokeColor=None,
                    fillColor=colors.HexColor("#ebe8dc"),
                )
            )
            self._add_drill_shape(drawing, rx, ry, cell_w, cell_h, fill_color)
            return

        if is_french_knot(stype):
            # Heller Hintergrund (Stofffarbe) damit der Punkt sichtbar wird
            drawing.add(
                Rect(
                    rx,
                    ry,
                    cell_w + 0.3,
                    cell_h + 0.3,
                    strokeColor=None,
                    fillColor=colors.HexColor("#fafafa"),
                )
            )
            radius = max(0.5, min(cell_w, cell_h) * french_knot_radius_factor())
            cx = rx + cell_w / 2.0
            cy = ry + cell_h / 2.0
            drawing.add(Circle(cx, cy, radius, strokeColor=None, fillColor=fill_color))
            return

        if is_bead(stype):
            # Perle: Hintergrund + Kugel + Glanzpunkt
            drawing.add(
                Rect(
                    rx,
                    ry,
                    cell_w + 0.3,
                    cell_h + 0.3,
                    strokeColor=None,
                    fillColor=colors.HexColor("#fafafa"),
                )
            )
            radius = max(1.0, min(cell_w, cell_h) * bead_radius_factor())
            cx = rx + cell_w / 2.0
            cy = ry + cell_h / 2.0
            drawing.add(Circle(cx, cy, radius, strokeColor=None, fillColor=fill_color))
            # Glanzpunkt: Mischfarbe aus fill_color + Weiss
            hr = (fill_color.red + 1.0) / 2.0
            hg = (fill_color.green + 1.0) / 2.0
            hb = (fill_color.blue + 1.0) / 2.0
            highlight = colors.Color(hr, hg, hb)
            drawing.add(
                Circle(
                    cx - radius / 2.5,
                    cy + radius / 2.5,
                    radius / 3.0,
                    strokeColor=None,
                    fillColor=highlight,
                )
            )
            return

        if not is_partial_stitch(stype):
            drawing.add(
                Rect(rx, ry, cell_w + 0.3, cell_h + 0.3, strokeColor=None, fillColor=fill_color)
            )
            return

        # Polygon-Punkte aus normalisierter Form, mit Y-Flip fuer PDF-Koordinaten
        flat_points: list[float] = []
        for nx_norm, ny_norm in normalized_partial_stitch_shape(stype):
            px = rx + nx_norm * cell_w
            py = ry + (1.0 - ny_norm) * cell_h  # PDF-Y oben->unten flip
            flat_points.extend([px, py])

        drawing.add(Polygon(points=flat_points, strokeColor=None, fillColor=fill_color))

    def _create_path_preview_drawing(
        self,
        color_paths: list["ColorPath"],
        page_width: int,
        page_height: int,
        max_draw_width: float,
        max_draw_height: float,
    ) -> Drawing | None:
        """
        Erstellt eine Vorschau-Zeichnung der Stickpfade für eine Seite.

        Args:
            color_paths: Gefilterte Farbpfade für diese Seite
            page_width: Breite der Seite in Stichen
            page_height: Höhe der Seite in Stichen
            max_draw_width: Maximale Zeichnungsbreite in reportlab-Einheiten
            max_draw_height: Maximale Zeichnungshöhe in reportlab-Einheiten

        Returns:
            Drawing mit allen Pfaden oder None wenn keine Pfade
        """
        if not color_paths:
            return None

        # Aspect Ratio beibehalten
        aspect = page_width / page_height if page_height > 0 else 1
        if aspect > max_draw_width / max_draw_height:
            width = max_draw_width
            height = max_draw_width / aspect
        else:
            height = max_draw_height
            width = max_draw_height * aspect

        cell_w = width / page_width
        cell_h = height / page_height

        drawing = Drawing(width, height)

        # Hintergrund und Rahmen
        drawing.add(
            Rect(
                0,
                0,
                width,
                height,
                strokeColor=colors.HexColor("#333333"),
                fillColor=colors.HexColor("#fafafa"),
                strokeWidth=0.5,
            )
        )

        # Gitter (nur wenn Zellen groß genug)
        if cell_w >= 2:
            grid_color = colors.HexColor("#e0e0e0")
            for x in range(page_width + 1):
                px = x * cell_w
                drawing.add(Line(px, 0, px, height, strokeColor=grid_color, strokeWidth=0.2))
            for y in range(page_height + 1):
                py = y * cell_h
                drawing.add(Line(0, py, width, py, strokeColor=grid_color, strokeWidth=0.2))

        # 10er-Linien stärker
        if cell_w >= 1:
            major_color = colors.HexColor("#999999")
            for x in range(0, page_width + 1, 10):
                px = x * cell_w
                drawing.add(Line(px, 0, px, height, strokeColor=major_color, strokeWidth=0.5))
            for y in range(0, page_height + 1, 10):
                py = y * cell_h
                drawing.add(Line(0, py, width, py, strokeColor=major_color, strokeWidth=0.5))

        # Pfade zeichnen
        line_width = max(0.5, min(cell_w / 6, 1.5))
        point_radius = max(0.5, min(cell_w / 4, 2))

        for path in color_paths:
            entry = self.pattern.get_color_entry(path.color_index)
            if entry:
                tc = entry.thread.color
                path_color = colors.Color(tc.r / 255, tc.g / 255, tc.b / 255)
            else:
                path_color = colors.HexColor("#888888")

            # Linien zeichnen
            if len(path.steps) > 1:
                prev_step = None
                for step in path.steps:
                    if prev_step:
                        x1 = prev_step.x * cell_w + cell_w / 2
                        y1 = height - (prev_step.y * cell_h + cell_h / 2)  # Y invertiert
                        x2 = step.x * cell_w + cell_w / 2
                        y2 = height - (step.y * cell_h + cell_h / 2)

                        if step.is_jump:
                            # Sprung: gestrichelte Linie in Rot
                            drawing.add(
                                Line(
                                    x1,
                                    y1,
                                    x2,
                                    y2,
                                    strokeColor=colors.HexColor("#dd5555"),
                                    strokeWidth=line_width,
                                    strokeDashArray=[2, 2],
                                )
                            )
                        else:
                            drawing.add(
                                Line(x1, y1, x2, y2, strokeColor=path_color, strokeWidth=line_width)
                            )
                    prev_step = step

            # Punkte zeichnen
            for i, step in enumerate(path.steps):
                cx = step.x * cell_w + cell_w / 2
                cy = height - (step.y * cell_h + cell_h / 2)

                # Start-Marker (grüner Kreis)
                if i == 0:
                    drawing.add(
                        Circle(
                            cx,
                            cy,
                            point_radius * 1.5,
                            strokeColor=colors.HexColor("#33aa33"),
                            strokeWidth=max(0.5, line_width * 0.8),
                            fillColor=None,
                        )
                    )
                # End-Marker (rotes Quadrat)
                elif i == len(path.steps) - 1:
                    marker_size = point_radius * 1.2
                    drawing.add(
                        Rect(
                            cx - marker_size,
                            cy - marker_size,
                            marker_size * 2,
                            marker_size * 2,
                            strokeColor=colors.HexColor("#dd5555"),
                            strokeWidth=max(0.5, line_width * 0.8),
                            fillColor=None,
                        )
                    )
                else:
                    # Normaler Punkt
                    drawing.add(
                        Circle(cx, cy, point_radius, strokeColor=None, fillColor=path_color)
                    )

        return drawing

    def _create_preview_drawing(self, max_width: float, max_height: float) -> Drawing | None:
        """Erstellt eine Vorschau-Zeichnung des Musters."""
        # Größe berechnen
        aspect = self.pattern.width / self.pattern.height
        if aspect > max_width / max_height:
            width = max_width
            height = max_width / aspect
        else:
            height = max_height
            width = max_height * aspect

        cell_w = width / self.pattern.width
        cell_h = height / self.pattern.height

        drawing = Drawing(width, height)

        # Rahmen
        drawing.add(
            Rect(
                0,
                0,
                width,
                height,
                strokeColor=colors.HexColor("#333333"),
                fillColor=colors.HexColor("#fafafa"),
                strokeWidth=1,
            )
        )

        # Stiche zeichnen
        for y in range(self.pattern.height):
            for x in range(self.pattern.width):
                color = self._get_pixel_color(x, y)
                if color:
                    rx = x * cell_w
                    # Y-Koordinate invertieren (PDF: 0 ist unten)
                    ry = height - (y + 1) * cell_h

                    fill_color = colors.Color(color[0] / 255, color[1] / 255, color[2] / 255)
                    self._add_stitch_shape(
                        drawing, x, y, rx, ry, cell_w, cell_h, fill_color, height
                    )

        # Rückstiche
        half_cell_w = cell_w / 2
        half_cell_h = cell_h / 2

        for bs in self.pattern.backstitches:
            entry = self.pattern.get_color_entry(bs.color_index)
            if entry:
                stroke_color = colors.Color(
                    entry.thread.color.r / 255,
                    entry.thread.color.g / 255,
                    entry.thread.color.b / 255,
                )
            else:
                stroke_color = colors.black

            x1 = bs.x1 * half_cell_w
            y1 = height - bs.y1 * half_cell_h
            x2 = bs.x2 * half_cell_w
            y2 = height - bs.y2 * half_cell_h

            drawing.add(
                Line(x1, y1, x2, y2, strokeColor=stroke_color, strokeWidth=max(0.5, cell_w / 10))
            )

        return drawing

    def _create_pattern_drawing_with_paths(
        self, start_x: int, start_y: int, end_x: int, end_y: int, page_paths: list
    ) -> Drawing:
        """
        Erstellt das Stickmuster als Drawing mit integrierten Pfadlinien.
        Die Pfadlinien werden dünn und dezent unter den Symbolen gezeichnet.
        """
        page_width = end_x - start_x + 1
        page_height = end_y - start_y + 1

        # Zellengröße berechnen (dynamisch basierend auf Papierformat).
        # Im DP-Modus: fester Drill-Pitch fuer 1:1-Druck. Damit passt der
        # echte 2.5/2.8/3.0mm-Drill genau in das ausgedruckte Raster.
        available_width = self._available_width
        # Platz für Zeilennummern links und Spaltennummern oben
        header_size = 8 * mm
        grid_width = available_width - header_size

        dp_cell = getattr(self, "_dp_cell_size", None)
        if dp_cell is not None:
            cell_size = dp_cell
        else:
            cell_size = min(4 * mm, grid_width / page_width)

        # Gesamtgröße der Zeichnung
        total_width = header_size + page_width * cell_size
        total_height = header_size + page_height * cell_size

        drawing = Drawing(total_width, total_height)

        # Offset für das Gitter (nach Header)
        grid_offset_x = header_size
        grid_offset_y = 0  # Y=0 ist unten in reportlab

        # === 1. Hintergrund und Gitter zeichnen ===

        # Weißer Hintergrund für Gitter
        drawing.add(
            Rect(
                grid_offset_x,
                grid_offset_y,
                page_width * cell_size,
                page_height * cell_size,
                strokeColor=colors.HexColor("#333333"),
                fillColor=colors.white,
                strokeWidth=1,
            )
        )

        # Gitterlinien
        grid_color = colors.HexColor("#cccccc")
        major_color = colors.HexColor("#333333")

        for x in range(page_width + 1):
            px = grid_offset_x + x * cell_size
            mx = start_x + x
            # 10er-Linien dicker
            if mx % 10 == 0:
                line_width = 1.0
                line_color = major_color
            else:
                line_width = 0.25
                line_color = grid_color
            drawing.add(
                Line(
                    px,
                    grid_offset_y,
                    px,
                    grid_offset_y + page_height * cell_size,
                    strokeColor=line_color,
                    strokeWidth=line_width,
                )
            )

        for y in range(page_height + 1):
            py = grid_offset_y + y * cell_size
            my = start_y + (page_height - y)  # Y invertiert
            if my % 10 == 0:
                line_width = 1.0
                line_color = major_color
            else:
                line_width = 0.25
                line_color = grid_color
            drawing.add(
                Line(
                    grid_offset_x,
                    py,
                    grid_offset_x + page_width * cell_size,
                    py,
                    strokeColor=line_color,
                    strokeWidth=line_width,
                )
            )

        # === 2. Pfadlinien zeichnen (UNTER den Symbolen) ===

        if page_paths:
            line_width = max(0.3, min(cell_size / 12, 0.8))  # Dünne Linien

            for path in page_paths:
                entry = self.pattern.get_color_entry(path.color_index)
                if entry:
                    tc = entry.thread.color
                    # Etwas gesättigtere/dunklere Version der Farbe für bessere Sichtbarkeit
                    path_color = colors.Color(
                        min(1, tc.r / 255 * 0.7),
                        min(1, tc.g / 255 * 0.7),
                        min(1, tc.b / 255 * 0.7),
                        0.6,  # Leicht transparent
                    )
                else:
                    path_color = colors.Color(0.5, 0.5, 0.5, 0.6)

                # Linien zwischen aufeinanderfolgenden Stichen zeichnen
                if len(path.steps) > 1:
                    prev_step = None
                    for step in path.steps:
                        if prev_step:
                            # Zellmittelpunkte berechnen
                            x1 = grid_offset_x + prev_step.x * cell_size + cell_size / 2
                            y1 = (
                                grid_offset_y
                                + (page_height - 1 - prev_step.y) * cell_size
                                + cell_size / 2
                            )
                            x2 = grid_offset_x + step.x * cell_size + cell_size / 2
                            y2 = (
                                grid_offset_y
                                + (page_height - 1 - step.y) * cell_size
                                + cell_size / 2
                            )

                            if step.is_jump:
                                # Sprung: gestrichelte rote Linie
                                drawing.add(
                                    Line(
                                        x1,
                                        y1,
                                        x2,
                                        y2,
                                        strokeColor=colors.Color(0.9, 0.3, 0.3, 0.5),
                                        strokeWidth=line_width,
                                        strokeDashArray=[1.5, 1.5],
                                    )
                                )
                            else:
                                # Normale Verbindung
                                drawing.add(
                                    Line(
                                        x1,
                                        y1,
                                        x2,
                                        y2,
                                        strokeColor=path_color,
                                        strokeWidth=line_width,
                                    )
                                )
                        prev_step = step

        # === 3. Cell-Inhalt zeichnen ===
        # Stick-Modus: Symbole als Text (klassischer Stick-Plan).
        # Diamond-Modus: Drill-Cells (facettierte Quadrate in Thread-Farbe),
        # weil DP keine Symbole nutzt und die Vorlage die Klebefolie selbst
        # ist — der User muss Drill-Farben direkt erkennen koennen.
        from .export_common import is_diamond_mode

        is_dp = is_diamond_mode(self.pattern)

        font_size = max(5, min(cell_size * 0.7, 9))

        for y in range(page_height):
            for x in range(page_width):
                mx = start_x + x
                my = start_y + y
                # Zellmittelpunkt berechnen (in PDF-Y; gespiegelt)
                cx = grid_offset_x + x * cell_size + cell_size / 2
                rx = grid_offset_x + x * cell_size
                # PDF-Y: 0 ist unten, Page-Header oben
                cy = grid_offset_y + (page_height - 1 - y) * cell_size + cell_size / 2
                ry = grid_offset_y + (page_height - 1 - y) * cell_size

                if is_dp:
                    # Drill mit echter Farbe rendern. Statt _get_pixel_symbol
                    # nutzen wir _get_pixel_color (RGB-Tuple oder None).
                    rgb = self._get_pixel_color(mx, my)
                    if rgb is None:
                        continue
                    fill_color = colors.Color(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
                    # Klebegrund-Hintergrund + facettierter Drill
                    drawing.add(
                        Rect(
                            rx,
                            ry,
                            cell_size + 0.3,
                            cell_size + 0.3,
                            strokeColor=None,
                            fillColor=colors.HexColor("#ebe8dc"),
                        )
                    )
                    self._add_drill_shape(
                        drawing,
                        rx,
                        ry,
                        cell_size,
                        cell_size,
                        fill_color,
                    )
                else:
                    symbol = self._get_pixel_symbol(mx, my)
                    if symbol:
                        # Symbol zeichnen
                        drawing.add(
                            String(
                                cx,
                                cy
                                - font_size
                                / 3,  # Leicht nach unten versetzt für vertikale Zentrierung
                                symbol,
                                fontSize=font_size,
                                fillColor=colors.black,
                                textAnchor="middle",
                            )
                        )

        # === 4. Zeilen- und Spaltennummern ===

        number_font_size = max(5, min(6, cell_size * 0.6))
        number_color = colors.HexColor("#666666")

        # Spaltennummern (oben)
        for x in range(page_width):
            mx = start_x + x
            # Nur bestimmte Nummern anzeigen
            if mx == start_x or (x + 1) % 5 == 0 or (mx + 1) % 10 == 0:
                cx = grid_offset_x + x * cell_size + cell_size / 2
                cy = grid_offset_y + page_height * cell_size + 2 * mm
                drawing.add(
                    String(
                        cx,
                        cy,
                        str(mx + 1),
                        fontSize=number_font_size,
                        fillColor=number_color,
                        textAnchor="middle",
                    )
                )

        # Zeilennummern (links)
        for y in range(page_height):
            my = start_y + y
            if my == start_y or (y + 1) % 5 == 0 or (my + 1) % 10 == 0:
                cx = grid_offset_x - 2 * mm
                cy = (
                    grid_offset_y
                    + (page_height - 1 - y) * cell_size
                    + cell_size / 2
                    - number_font_size / 3
                )
                drawing.add(
                    String(
                        cx,
                        cy,
                        str(my + 1),
                        fontSize=number_font_size,
                        fillColor=number_color,
                        textAnchor="end",
                    )
                )

        return drawing
