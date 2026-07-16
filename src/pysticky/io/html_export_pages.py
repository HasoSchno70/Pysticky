"""
HTML-Export Musterseiten-Mixin.

Enthält die Methode zur Generierung der einzelnen Musterseiten
mit Stich-Raster, Mini-Legende und Rückstich-Overlay.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.i18n import t
from .html_export import _html_encode

if TYPE_CHECKING:
    from ._export_base import _HTMLExportBase as _Base
else:
    _Base = object


class HTMLPagesMixin(_Base):
    """Mixin-Klasse für die Musterseiten-Generierung des HTML-Exports."""

    def _build_page_mini_index(self, pages_x: int, pages_y: int, cur_x: int, cur_y: int) -> str:
        """DEPRECATED: durch _build_page_navigator ersetzt.

        Bleibt als no-op für eventuelle externe Aufrufer — die kombinierte
        Navigator-Box rendert jetzt Index + Pfeile zusammen.
        """
        return ""

    def _build_page_neighbor_markers(
        self, pages_x: int, pages_y: int, cur_x: int, cur_y: int
    ) -> str:
        """DEPRECATED: durch _build_page_navigator ersetzt."""
        return ""

    def _build_page_navigator(self, pages_x: int, pages_y: int, cur_x: int, cur_y: int) -> str:
        """Kombinierte Navigations-Box: Seiten-Index-Grid mit Nachbar-Pfeilen.

        Layout (3x3 Table):

            .            [↑ Seite N]           .
            [← M]   [INDEX-GRID + aktuell]    [K →]
            .            [↓ L]                  .

        Die Pfeile zeigen, welche Seite an der jeweiligen Druck-Kante
        anschliesst — hilfreich beim Aneinanderlegen ausgedruckter Blätter.
        Das Index-Grid in der Mitte hebt die aktuelle Seite hervor.

        Bei 1x1-Patterns (eine einzige Seite) komplett leerer Output.
        """
        if pages_x * pages_y <= 1:
            return ""

        def page_at(px: int, py: int) -> int | None:
            if 0 <= px < pages_x and 0 <= py < pages_y:
                return py * pages_x + px + 1
            return None

        left = page_at(cur_x - 1, cur_y)
        right = page_at(cur_x + 1, cur_y)
        top = page_at(cur_x, cur_y - 1)
        bottom = page_at(cur_x, cur_y + 1)

        # Index-Grid bauen (Inhalt der mittleren Zelle)
        rows = []
        for py in range(pages_y):
            cells = []
            for px in range(pages_x):
                page_num = py * pages_x + px + 1
                is_current = px == cur_x and py == cur_y
                style = (
                    "background:#3498db;color:white;font-weight:bold;"
                    if is_current
                    else "background:#fff;color:#666;"
                )
                cells.append(
                    f"<td style='{style}border:1px solid #ccc;"
                    f"width:18px;height:14px;font-size:9px;text-align:center;'>"
                    f"{page_num}</td>"
                )
            rows.append(f"<tr>{''.join(cells)}</tr>")
        index_grid = (
            f"<table style='border-collapse:collapse;margin:0 auto;'>{''.join(rows)}</table>"
        )

        # Pfeil-Pillen
        pill_style = (
            "display:inline-block;color:#666;font-size:10px;"
            "background:#f5f5f5;padding:3px 8px;border-radius:4px;"
            "white-space:nowrap;"
        )
        top_pill = (
            f"<span style='{pill_style}'>{t('&uarr; Seite {n}').format(n=top)}</span>"
            if top
            else ""
        )
        bottom_pill = (
            f"<span style='{pill_style}'>{t('&darr; Seite {n}').format(n=bottom)}</span>"
            if bottom
            else ""
        )
        left_pill = (
            f"<span style='{pill_style}'>{t('&larr; Seite {n}').format(n=left)}</span>"
            if left
            else ""
        )
        right_pill = (
            f"<span style='{pill_style}'>{t('Seite {n} &rarr;').format(n=right)}</span>"
            if right
            else ""
        )

        # 3x3 Layout — feste, klare Zellen statt absoluter Positionierung
        return (
            "<div class='page-navigator' style='float:right;margin-left:12px;'>"
            "<div style='font-size:9px;color:#666;margin-bottom:2px;text-align:center;'>"
            f"{t('Seiten-Index')}"
            "</div>"
            "<table style='border-collapse:separate;border-spacing:4px;'>"
            f"<tr><td></td><td style='text-align:center;'>{top_pill}</td><td></td></tr>"
            f"<tr><td style='text-align:right;'>{left_pill}</td>"
            f"<td>{index_grid}</td>"
            f"<td style='text-align:left;'>{right_pill}</td></tr>"
            f"<tr><td></td><td style='text-align:center;'>{bottom_pill}</td><td></td></tr>"
            "</table>"
            "</div>"
        )

    def _generate_pattern_pages(self, pages_x: int, pages_y: int, title: str, date: str) -> str:
        """Generiert die Musterseiten."""
        from .export_common import get_watermark

        _author, copyright_ = get_watermark(self.pattern)

        total_pages = pages_x * pages_y
        pages = []
        page_nr = 1

        # Zellgröße für Musterseiten. Im DP-Modus auf den Drill-Pitch in
        # Pixeln umgerechnet (~96 DPI Annahme), damit die Bildschirm-
        # Anzeige in etwa die echte Drill-Größe zeigt. Plus separate
        # @media-print-CSS-Regel mit mm-Einheiten für den exakten Druck —
        # siehe _build_dp_print_css() im HTML-Header.
        dp_cell_mm = getattr(self, "_dp_cell_mm", None)
        if dp_cell_mm:
            # 1 mm = ca. 3.78 CSS-Pixel bei 96 DPI
            cell_size = max(8, round(dp_cell_mm * 3.78))
        else:
            cell_size = 16

        # Working-Chart-Overlap: jede Seite zeigt zusätzlich die ersten
        # N Stiche der Nachbarseite zur Orientierung beim Aneinanderlegen.
        overlap = getattr(self, "page_overlap_stitches", 0) or 0

        for page_y in range(pages_y):
            for page_x in range(pages_x):
                start_x = page_x * self.STITCHES_PER_PAGE_X
                start_y = page_y * self.STITCHES_PER_PAGE_Y
                # Effektives Page-End ist Page-Size + Overlap, aber nicht über
                # Pattern-Grenze hinaus. Auf der letzten Seite gibt es nichts
                # zum Overlappen, also begrenzt die Pattern-Width das.
                core_end_x = start_x + self.STITCHES_PER_PAGE_X - 1
                core_end_y = start_y + self.STITCHES_PER_PAGE_Y - 1
                end_x = min(core_end_x + overlap, self.pattern.width - 1)
                end_y = min(core_end_y + overlap, self.pattern.height - 1)

                # Overlap-Zone berechnen (welche Stiche markieren wir als overlap?)
                overlap_start_x = (
                    core_end_x + 1 if overlap > 0 and core_end_x < self.pattern.width - 1 else None
                )
                overlap_start_y = (
                    core_end_y + 1 if overlap > 0 and core_end_y < self.pattern.height - 1 else None
                )

                page_width = end_x - start_x + 1
                page_height = end_y - start_y + 1

                # Farben auf dieser Seite zählen
                page_color_counts = self._count_page_colors(start_x, start_y, end_x, end_y)

                # Rückstiche auf dieser Seite — im DP-Modus immer leer.
                is_dp_page = getattr(self.pattern, "mode", "stitch") == "diamond"
                page_backstitches = (
                    []
                    if is_dp_page
                    else self._get_page_backstitches(start_x, start_y, end_x, end_y)
                )

                # Tabelle
                table_rows = []

                # Kopfzeile
                header_cells = ["<td class='grid-header'></td>"]
                for x in range(page_width):
                    mx = start_x + x
                    classes = "grid-header"
                    if (mx + 1) % 10 == 0:
                        classes += " thick-right"
                    # Overlap-Spalten markieren (zur visuellen Trennung)
                    if overlap_start_x is not None and mx >= overlap_start_x:
                        classes += " overlap-col"

                    if mx == start_x or (x + 1) % 5 == 0 or (mx + 1) % 10 == 0:
                        header_cells.append(f"<td class='{classes}'>{mx + 1}</td>")
                    else:
                        header_cells.append(f"<td class='{classes}'></td>")

                table_rows.append(f"<tr>{''.join(header_cells)}</tr>")

                # Datenzeilen
                for y in range(page_height):
                    my = start_y + y

                    row_cells = []

                    # Zeilennummer
                    row_classes = "grid-header"
                    if (my + 1) % 10 == 0:
                        row_classes += " thick-bottom"
                    if overlap_start_y is not None and my >= overlap_start_y:
                        row_classes += " overlap-row"

                    if my == start_y or (y + 1) % 5 == 0 or (my + 1) % 10 == 0:
                        row_cells.append(f"<td class='{row_classes}'>{my + 1}</td>")
                    else:
                        row_cells.append(f"<td class='{row_classes}'></td>")

                    # Zellen
                    from .export_common import is_diamond_mode

                    is_dp_cells = is_diamond_mode(self.pattern)
                    for x in range(page_width):
                        mx = start_x + x

                        cell_classes = []
                        if (mx + 1) % 10 == 0:
                            cell_classes.append("thick-right")
                        if (my + 1) % 10 == 0:
                            cell_classes.append("thick-bottom")
                        # Overlap-Zellen visuell hinterlegen
                        in_overlap_x = overlap_start_x is not None and mx >= overlap_start_x
                        in_overlap_y = overlap_start_y is not None and my >= overlap_start_y
                        if in_overlap_x or in_overlap_y:
                            cell_classes.append("overlap-cell")

                        class_str = f" class='{' '.join(cell_classes)}'" if cell_classes else ""

                        if is_dp_cells:
                            # DP: farbiges Cell mit Drill-Farbe als Hintergrund.
                            # Die echte Drill-Facetten-Optik kommt über das
                            # SVG-Overlay; hier reicht die solide Farbe als
                            # Klebevorlage.
                            rgb = self._get_pixel_color(mx, my)
                            if rgb is not None:
                                bg = f"background:rgb({rgb[0]},{rgb[1]},{rgb[2]});"
                                row_cells.append(f"<td{class_str} style='{bg}'></td>")
                            else:
                                row_cells.append(f"<td{class_str}></td>")
                        else:
                            symbol = self._get_pixel_symbol(mx, my)
                            row_cells.append(f"<td{class_str}>{_html_encode(symbol)}</td>")

                    table_rows.append(f"<tr>{''.join(row_cells)}</tr>")

                # SVG-Größe berechnen (inklusive Header-Zeile/Spalte)
                # Header ist auch 16px breit/hoch
                svg_width = (page_width + 1) * cell_size + 2  # +2 für Border
                svg_height = (page_height + 1) * cell_size + 2

                # Rückstiche-SVG für diese Seite
                # Offset: Header-Spalte (16px) + Border (2px)
                backstitch_svg = self._generate_backstitches_svg(
                    cell_size,
                    offset_x=cell_size + 2,  # Header-Spalte + Border
                    offset_y=cell_size + 2,  # Header-Zeile + Border
                    start_stitch_x=start_x,
                    start_stitch_y=start_y,
                    end_stitch_x=end_x + 1,
                    end_stitch_y=end_y + 1,
                )

                # Halbstiche/Viertel/Dreiviertel-SVG für diese Seite —
                # zeigt Form + Farbe, das Symbol kommt aus der Tabelle drüber.
                partial_svg = self._generate_partial_stitches_svg(
                    cell_size,
                    offset_x=cell_size + 2,
                    offset_y=cell_size + 2,
                    start_stitch_x=start_x,
                    start_stitch_y=start_y,
                    end_stitch_x=end_x + 1,
                    end_stitch_y=end_y + 1,
                )

                # Mini-Legende - nur Farben auf dieser Seite
                mini_legend_items = []
                for stat in self._color_stats:
                    color_idx = stat["index"]
                    if color_idx not in page_color_counts:
                        continue

                    count = page_color_counts[color_idx]
                    thread = stat["thread"]

                    # Fadenbedarf berechnen: 3 Fäden pro Stich, 6 Fäden pro Strang
                    # Ein Strang hat 8m mit 6 Einzelfäden
                    # Bei 3 Fäden pro Stich: 2 Stiche pro "Strangeinheit"
                    # Grob: ~400 Stiche pro Strang bei 3 Fäden
                    threads_needed = count * 3  # Einzelfäden

                    code = _html_encode(thread.catalog_number or "")
                    # Im DP-Modus: kein Symbol, dafür Code prominent.
                    from .export_common import is_diamond_mode

                    if is_diamond_mode(self.pattern):
                        mini_legend_items.append(
                            f"<span class='mini-legend-item'>"
                            f"<span class='color-box' "
                            f"style='background:rgb({thread.color.r},{thread.color.g},{thread.color.b});"
                            f"width:14px;height:14px;border:1px solid #999;"
                            f"display:inline-block;vertical-align:middle;'></span>"
                            f"<b>{code}</b>"
                            f" <small>({count}\u00d7)</small></span>"
                        )
                    else:
                        mini_legend_items.append(
                            f"<span class='mini-legend-item'>"
                            f"<span class='color-box' style='background:rgb({thread.color.r},{thread.color.g},{thread.color.b})'></span>"
                            f"{_html_encode(stat['symbol'])}={code} "
                            f"<small>({count}\u00d7, {threads_needed}F)</small></span>"
                        )

                # Gesamtstiche auf der Seite
                total_page_stitches = sum(page_color_counts.values())

                # Backstitch-Info für Seite
                backstitch_info = ""
                if page_backstitches:
                    backstitch_info = t(" &middot; {n} R&uuml;ckstiche").format(
                        n=len(page_backstitches)
                    )

                # Kombinierter Page-Navigator: Index-Grid + Nachbar-Pfeile
                # in einem sauberen 3x3-Layout
                page_navigator = self._build_page_navigator(pages_x, pages_y, page_x, page_y)

                page_title_line = t("Seite {page} von {total}").format(
                    page=page_nr, total=total_pages
                )
                page_info_line = t(
                    "Spalten {sx}-{ex} &middot; Zeilen {sy}-{ey} &middot; {n} Stiche{backstitch_info}"
                ).format(
                    sx=start_x + 1,
                    ex=end_x + 1,
                    sy=start_y + 1,
                    ey=end_y + 1,
                    n=total_page_stitches,
                    backstitch_info=backstitch_info,
                )
                mini_legend_heading = t("Farben dieser Seite ({n}):").format(
                    n=len(page_color_counts)
                )
                mini_legend_backstitch_note = (
                    t(
                        "<br><b>R&uuml;ckstiche:</b> {n} Linien (als farbige Linien im Muster dargestellt)"
                    ).format(n=len(page_backstitches))
                    if page_backstitches
                    else ""
                )
                page_footer_line = t(
                    "{title} &middot; Seite {page}/{total} &middot; {date}"
                ).format(title=_html_encode(title), page=page_nr, total=total_pages, date=date)

                pages.append(f"""
<div class='page-break'></div>
<div id='seite{page_nr}'>
<div class='page-header'>
<div class='title'>{page_title_line}</div>
<div class='info'>{page_info_line}</div>
{page_navigator}
</div>

<div class='pattern-container'>
<table class='grid-table'>
{"".join(table_rows)}
</table>
<svg class='grid-svg-overlay' width='{svg_width}' height='{svg_height}'>
{partial_svg}
{backstitch_svg}
</svg>
</div>

<div class='mini-legend'>
<b>{mini_legend_heading}</b> {"".join(mini_legend_items)}
{mini_legend_backstitch_note}
</div>

<div class='page-footer'>{page_footer_line}{(" &middot; " + _html_encode(copyright_)) if copyright_ else ""}</div>
</div>""")

                page_nr += 1

        return "".join(pages)
