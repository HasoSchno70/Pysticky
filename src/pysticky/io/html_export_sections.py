"""
HTML-Export Sektionen-Mixin.

Enthält die Methoden zur Generierung der HTML-Abschnitte:
Header, Navigation, Deckblatt, Vorschau, Legende und Übersichtskarte.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.i18n import t
from .html_export import _html_encode

if TYPE_CHECKING:
    from ._export_base import _HTMLExportBase as _Base
else:
    _Base = object


class HTMLSectionsMixin(_Base):
    """Mixin-Klasse für HTML-Sektionen des Kreuzstich-Exports."""

    def _generate_header(self, title: str) -> str:
        """Generiert den HTML-Header mit CSS."""
        return f"""<!DOCTYPE html>
<html lang='de'>
<head>
<meta charset='UTF-8'>
<title>{t("Stickmuster: {title}").format(title=_html_encode(title))}</title>
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; padding-top: 60px; }}
.container {{ max-width: 210mm; margin: auto; background: white; padding: 15mm; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
h1 {{ text-align: center; color: #333; margin-bottom: 10px; font-size: 24px; }}
h2 {{ text-align: center; color: #555; margin: 15px 0 10px 0; font-size: 16px; }}
h3 {{ text-align: center; color: #666; margin: 10px 0; font-size: 14px; }}

/* Deckblatt */
.cover-page {{ text-align: center; padding: 0; min-height: 100vh; display: flex; flex-direction: column; }}
.cover-header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 20px; }}
.cover-icon {{ font-size: 64px; margin-bottom: 15px; }}
.cover-title {{ font-size: 36px; font-weight: 300; margin: 0 0 10px 0; letter-spacing: 2px; }}
.cover-subtitle {{ font-size: 24px; font-weight: 600; margin: 0; opacity: 0.95; }}
.cover-date {{ font-size: 14px; margin-top: 15px; opacity: 0.8; }}
.cover-body {{ flex: 1; padding: 30px 20px; display: flex; flex-direction: column; align-items: center; }}
.cover-preview {{ margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
.cover-preview-inner {{ border: 3px solid #667eea; border-radius: 8px; overflow: hidden; }}
.cover-preview-label {{ font-size: 12px; color: #666; margin-top: 10px; font-style: italic; }}
.cover-info {{ margin: 20px auto; max-width: 500px; text-align: left; width: 100%; }}
.cover-info table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }}
.cover-info td {{ padding: 12px 16px; border-bottom: 1px solid #f0f0f0; }}
.cover-info tr:last-child td {{ border-bottom: none; }}
.cover-info td:first-child {{ font-weight: 600; color: #667eea; width: 45%; background: #fafbff; }}
.cover-footer {{ padding: 20px; background: #f8f9fa; border-top: 1px solid #eee; }}
.cover-footer-text {{ font-size: 11px; color: #999; }}

/* Statistik-Karten */
.stats-box {{ display: flex; justify-content: center; gap: 15px; margin: 25px 0; flex-wrap: wrap; }}
.stat-item {{ text-align: center; padding: 20px 25px; background: white; border-radius: 12px; box-shadow: 0 3px 15px rgba(102,126,234,0.15); border: 1px solid #e8ecf4; min-width: 100px; }}
.stat-value {{ font-size: 26px; font-weight: 700; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
.stat-label {{ font-size: 11px; color: #888; margin-top: 6px; text-transform: uppercase; letter-spacing: 1px; }}
.stat-icon {{ font-size: 24px; margin-bottom: 8px; }}

/* Seitenumbruch */
.page-break {{ page-break-before: always; }}

/* Tabellen */
.legend-table {{ border-collapse: collapse; margin: 15px auto; width: 100%; }}
.legend-table th {{ background: #3498db; color: white; padding: 10px 8px; text-align: left; font-size: 12px; }}
.legend-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 11px; }}
.legend-table tr:nth-child(even) {{ background: #f9f9f9; }}
.legend-table tr:hover {{ background: #f0f7ff; }}
.color-box {{ width: 24px; height: 24px; display: inline-block; border: 1px solid #333; vertical-align: middle; border-radius: 3px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}

/* Vorschau */
.preview-container {{ position: relative; display: inline-block; margin: 15px auto; border: 2px solid #333; }}
.preview-table {{ border-collapse: collapse; border: 0; }}
.preview-table td {{ border: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.preview-svg-overlay {{ position: absolute; top: 0; left: 0; pointer-events: none; }}

/* Übersicht */
.overview-section {{ text-align: center; }}
.overview-header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px 12px 0 0; }}
.overview-header h1 {{ color: white; margin: 0 0 5px 0; font-size: 22px; }}
.overview-header p {{ margin: 0; opacity: 0.9; font-size: 13px; }}
.overview-container {{ display: flex; gap: 30px; justify-content: center; align-items: flex-start; flex-wrap: wrap; padding: 25px; background: #f8f9fa; border-radius: 0 0 12px 12px; border: 1px solid #e0e0e0; border-top: none; }}
.overview-preview-box {{ background: white; padding: 15px; border-radius: 10px; box-shadow: 0 3px 15px rgba(0,0,0,0.1); }}
.overview-preview-title {{ font-size: 12px; color: #666; margin-bottom: 10px; font-weight: 600; }}
.overview-preview-inner {{ border: 2px solid #667eea; border-radius: 6px; overflow: hidden; }}
.overview-grid-box {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 3px 15px rgba(0,0,0,0.1); flex: 1; max-width: 400px; }}
.overview-grid-title {{ font-size: 12px; color: #666; margin-bottom: 15px; font-weight: 600; }}
.overview-table {{ border: none; width: 100%; border-collapse: collapse; }}
.overview-table td {{ border: none; padding: 0; vertical-align: top; }}
.overview-cell {{ display: block; margin: 4px; padding: 12px 8px; background: linear-gradient(145deg, #ffffff, #f0f0f0); border: 2px solid #e0e0e0; border-radius: 8px; text-decoration: none; color: #333; transition: all 0.2s ease; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
.overview-cell:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102,126,234,0.3); border-color: #667eea; }}
.overview-cell-nr {{ font-size: 18px; font-weight: 700; color: #667eea; display: block; }}
.overview-cell-range {{ font-size: 9px; color: #888; display: block; margin-top: 3px; }}
.overview-info {{ margin-top: 20px; padding: 15px; background: white; border-radius: 8px; border-left: 4px solid #667eea; text-align: left; }}
.overview-info p {{ margin: 5px 0; font-size: 12px; color: #555; }}

/* Muster-Raster */
.pattern-container {{ position: relative; display: inline-block; }}
.grid-table {{ border-collapse: collapse; margin: 15px auto; border: 2px solid #333; }}
.grid-table td {{ border: 1px solid #ccc; width: 16px; height: 16px; text-align: center; font-size: 10px; font-weight: bold; vertical-align: middle; padding: 1px; }}
.grid-header {{ background-color: #ecf0f1; font-weight: bold; font-size: 9px; color: #333; }}
td.thick-right {{ border-right: 2px solid #333; }}
td.thick-bottom {{ border-bottom: 2px solid #333; }}
/* Working-Chart-Overlap: gestrichelter Rand + leicht abgedunkelt zur Trennung */
td.overlap-col {{ background-color: #f3e9c6 !important; border-left: 1px dashed #b58900; }}
td.overlap-row {{ background-color: #f3e9c6 !important; border-top: 1px dashed #b58900; }}
td.overlap-cell {{ background-color: rgba(243, 233, 198, 0.45); }}
.grid-svg-overlay {{ position: absolute; top: 0; left: 0; pointer-events: none; }}

/* Backstitch-Legende */
.backstitch-info {{ margin-top: 10px; padding: 8px 12px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px; font-size: 11px; color: #856404; }}
.backstitch-info strong {{ color: #664d03; }}

/* Navigation */
.nav-bar {{ position: fixed; top: 0; left: 0; right: 0; background: #2c3e50; padding: 10px 20px; z-index: 1000; display: flex; justify-content: space-between; align-items: center; }}
.nav-bar a {{ color: white; text-decoration: none; padding: 5px 15px; border-radius: 4px; margin: 0 5px; }}
.nav-bar a:hover {{ background: #34495e; }}
.nav-bar .btn-print {{ background: #27ae60; }}
.nav-bar .btn-print:hover {{ background: #2ecc71; }}

/* Seiten-Header */
.page-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 15px; }}
.page-header .title {{ font-size: 14px; font-weight: bold; color: #333; }}
.page-header .info {{ font-size: 11px; color: #666; }}

/* Mini-Legende */
.mini-legend {{ margin-top: 15px; padding: 10px; background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px; font-size: 10px; }}
.mini-legend-item {{ display: inline-block; margin: 3px 8px; white-space: nowrap; }}
.mini-legend .color-box {{ width: 14px; height: 14px; margin-right: 4px; }}

/* Footer */
.page-footer {{ text-align: center; font-size: 10px; color: #999; margin-top: 20px; padding-top: 10px; border-top: 1px solid #eee; }}

/* Druck */
@media print {{
  .nav-bar {{ display: none !important; }}
  body {{ padding-top: 0; background: white; }}
  .container {{ box-shadow: none; padding: 5mm; max-width: none; }}
  .grid-table td {{ width: 14px; height: 14px; font-size: 9px; }}
  .cover-header {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  .overview-header {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  .stat-value {{ color: #667eea; -webkit-text-fill-color: #667eea; }}
  @page {{ size: A4; margin: 10mm; }}
}}
{self._dp_print_css()}
</style>
</head>
<body>"""

    def _generate_navigation(self, pages_x: int, pages_y: int) -> str:
        """Generiert die Navigationsleiste."""
        total_pages = pages_x * pages_y

        nav = ["<div class='nav-bar'>", "<div>"]
        nav.append(f"<a href='#deckblatt'>{t('Deckblatt')}</a>")
        nav.append(f"<a href='#vorschau'>{t('Vorschau')}</a>")
        nav.append(f"<a href='#legende'>{t('Legende')}</a>")
        nav.append(f"<a href='#uebersicht'>{t('&Uuml;bersicht')}</a>")

        if total_pages <= 10:
            for i in range(1, total_pages + 1):
                nav.append(f"<a href='#seite{i}'>{t('S.{n}').format(n=i)}</a>")
        else:
            nav.append(f"<a href='#seite1'>{t('Muster &rarr;')}</a>")

        nav.append("</div>")
        nav.append(
            f"<div><a href='javascript:window.print()' class='btn-print'>&#128424; {t('Als PDF drucken')}</a></div>"
        )
        nav.append("</div>")

        return "\n".join(nav)

    def _watermark(self) -> tuple[str, str]:
        """Liefert (author, copyright) — Pattern-Metadaten oder Settings-Defaults."""
        from .export_common import get_watermark

        return get_watermark(self.pattern)

    def _dp_print_css(self) -> str:
        """Zusätzliche Print-CSS-Regeln für 1:1-Drill-Druck im DP-Modus.

        Setzt die Cell-Größe beim Drucken auf den exakten Drill-Pitch in
        Millimetern (2.5/2.8/3.0 mm). So passt der echte Drill genau auf
        die ausgedruckte Klebefolien-Zelle. Auf dem Bildschirm bleibt die
        Pixel-Anzeige (~9 px) — wer auf dem Bildschirm größer sehen will,
        nutzt Strg++.
        """
        pitch = getattr(self, "_dp_cell_mm", None)
        if not pitch:
            return ""
        # !important damit unsere DP-Regel die globalen 14px überschreibt.
        # `padding:0` weil Symbole/Drill-Nummern in der 1:1-Cell keinen
        # Platz haben — wer Nummern sieht, muss die Bildschirm-Anzeige nutzen.
        return (
            "@media print {\n"
            "  .grid-table td {\n"
            f"    width: {pitch}mm !important;\n"
            f"    height: {pitch}mm !important;\n"
            "    padding: 0 !important;\n"
            "    font-size: 0 !important;\n"
            "  }\n"
            "  .grid-svg-overlay { width: 100% !important; height: 100% !important; }\n"
            "}"
        )

    def _generate_cover(
        self, title: str, date: str, phys_width: float, phys_height: float, total_pages: int
    ) -> str:
        """Generiert das Deckblatt."""
        # Mini-Vorschau berechnen
        mini_w = 200.0
        mini_h = mini_w * self.pattern.height / self.pattern.width
        if mini_h > 150:
            mini_h = 150.0
            mini_w = mini_h * self.pattern.width / self.pattern.height

        cell_w = mini_w / self.pattern.width
        cell_h = mini_h / self.pattern.height

        # Modus-spezifische Terminologie + Drill-Rendering-Flag laden
        from .export_common import (
            fabric_label_for,
            is_diamond_mode,
            svg_shape_for_stitch,
            terms_for,
        )

        terms = terms_for(self.pattern)
        is_dp = is_diamond_mode(self.pattern)

        # SVG für Vorschau (halbe/Viertel als Polygone, Drills im DP-Modus
        # als facettierte Quadrate).
        svg_rects = []
        for y in range(self.pattern.height):
            for x in range(self.pattern.width):
                color = self._get_pixel_color(x, y)
                if color:
                    rx = x * cell_w
                    ry = y * cell_h
                    stype = self._get_pixel_stitch_type(x, y)
                    svg_rects.append(
                        svg_shape_for_stitch(
                            stype,
                            rx,
                            ry,
                            cell_w,
                            cell_h,
                            color,
                            as_diamond=is_dp,
                        )
                    )

        # Rückstiche existieren nur im Stick-Modus — im DP nicht rendern.
        if is_dp:
            backstitch_svg = ""
            backstitch_count = 0
            backstitch_info = ""
        else:
            backstitch_svg = self._generate_backstitches_svg(cell_w)
            backstitch_count = len(self.pattern.backstitches)
            backstitch_info = (
                t("<tr><td>&#8600; R&uuml;ckstiche</td><td>{n} Linien</td></tr>").format(
                    n=backstitch_count
                )
                if backstitch_count > 0
                else ""
            )

        fabric_name = fabric_label_for(self.pattern)

        # Wasserzeichen — author + copyright für Cover
        author, copyright_ = self._watermark()
        author_html = (
            f"<p class='cover-date'>{t('von {author}').format(author=_html_encode(author))}</p>"
            if author
            else ""
        )

        # Cover-Title und Subtitle je Modus
        cover_title = t("DIAMOND-PAINTING-VORLAGE") if is_dp else t("KREUZSTICH-MUSTER")
        cover_icon = "&#128142;" if is_dp else "&#9986;"  # 💎 vs. ✂

        # Stats-Box: im DP-Modus zeigen wir "Drills" statt "Stiche" und
        # ersetzen Rückstiche-Kachel durch Drill-Anzahl-Wiederholung (oder
        # weglassen — eleganter weglassen).
        stats_total_unit = terms["unit_plural"]
        stats_supply_label = terms["supply_unit"]

        # Size-Text: "40 × 40 Stiche" vs "40 × 40 Drills"
        size_text = terms["size_unit_template"].format(
            w=self.pattern.width,
            h=self.pattern.height,
        )
        totals_text = terms["totals_template"].format(n=self._total_stitches)

        preview_label_suffix = t(" (inkl. R&uuml;ckstiche)") if backstitch_count > 0 else ""
        backstitch_stat_tile = (
            t(
                "<div class='stat-item'><div class='stat-icon'>&#8600;</div>"
                "<div class='stat-value'>{n}</div><div class='stat-label'>R&uuml;ckstiche</div></div>"
            ).format(n=backstitch_count)
            if backstitch_count > 0
            else ""
        )

        return f"""
<div id='deckblatt' class='cover-page'>
<div class='cover-header'>
<div class='cover-icon'>{cover_icon}</div>
<h1 class='cover-title'>{cover_title}</h1>
<p class='cover-subtitle'>{_html_encode(title)}</p>
{author_html}
<p class='cover-date'>{t("Erstellt am {date}").format(date=date)}</p>
</div>

<div class='cover-body'>
<div class='cover-preview'>
<div class='cover-preview-inner'>
<svg width='{int(mini_w)}' height='{int(mini_h)}' style='display:block;'>
{"".join(svg_rects)}
{backstitch_svg}
</svg>
</div>
<div class='cover-preview-label'>{terms["preview_caption"]}{preview_label_suffix}</div>
</div>

<div class='stats-box'>
<div class='stat-item'><div class='stat-icon'>&#128208;</div><div class='stat-value'>{self.pattern.width}&times;{self.pattern.height}</div><div class='stat-label'>{stats_total_unit}</div></div>
<div class='stat-item'><div class='stat-icon'>&#127912;</div><div class='stat-value'>{len(self._color_stats)}</div><div class='stat-label'>{t("Farben")}</div></div>
<div class='stat-item'><div class='stat-icon'>{terms["supply_icon"]}</div><div class='stat-value'>{self._total_skeins}</div><div class='stat-label'>{stats_supply_label}</div></div>
<div class='stat-item'><div class='stat-icon'>&#128196;</div><div class='stat-value'>{total_pages}</div><div class='stat-label'>{t("Seiten")}</div></div>
{backstitch_stat_tile}
</div>

<div class='cover-info'>
<table>
<tr><td>&#128207; {t("Mustergr&ouml;&szlig;e")}</td><td>{size_text}</td></tr>
<tr><td>&#129526; {terms["fabric_label"]}</td><td>{_html_encode(fabric_name)}</td></tr>
<tr><td>&#128207; {t("Fertige Gr&ouml;&szlig;e")}</td><td>{t("{w} &times; {h} cm").format(w=f"{phys_width:.1f}", h=f"{phys_height:.1f}")}</td></tr>
<tr><td>&#127912; {t("Anzahl Farben")}</td><td>{t("{n} verschiedene Farben").format(n=len(self._color_stats))}</td></tr>
<tr><td>&#10010; {t("Gesamt")}</td><td>{totals_text}</td></tr>
{backstitch_info}
<tr><td>{terms["supply_icon"]} {terms["supply_label"]}</td><td>{t("ca. {n} {unit}").format(n=self._total_skeins, unit=stats_supply_label)}</td></tr>
<tr><td>&#128196; {t("Musterseiten")}</td><td>{t("{n} Seiten").format(n=total_pages)}</td></tr>
{self._render_started_date_row()}
</table>
</div>
{self._render_notes_block()}
</div>

<div class='cover-footer'>
<p class='cover-footer-text'>{t("Erstellt mit PySticky &middot; {date}").format(date=date)}{(" &middot; " + _html_encode(copyright_)) if copyright_ else ""}</p>
</div>
</div>"""

    def _render_started_date_row(self) -> str:
        """Optionale Zeile mit dem Stickdatum."""
        started = (self.pattern.metadata.get("started_date") or "").strip()
        if not started:
            return ""
        from datetime import date

        try:
            d = date.fromisoformat(started)
            display = d.strftime("%d.%m.%Y")
        except ValueError:
            display = started
        return t("<tr><td>&#128197; Begonnen am</td><td>{date}</td></tr>").format(
            date=_html_encode(display)
        )

    def _render_notes_block(self) -> str:
        """Notizen-Block (optional) — sichtbar wenn Notizen gepflegt sind."""
        notes = (self.pattern.metadata.get("notes") or "").strip()
        if not notes:
            return ""
        lines = "<br>".join(_html_encode(line) for line in notes.split("\n"))
        return (
            "<div class='cover-info' style='margin-top: 16px;'>"
            f"<table><tr><td style='vertical-align: top;'>&#128221; {t('Notizen')}</td>"
            f"<td>{lines}</td></tr></table></div>"
        )

    def _generate_preview(self, phys_width: float, phys_height: float) -> str:
        """Generiert die Farbvorschau."""
        from .export_common import fabric_label_for

        fabric_name = fabric_label_for(self.pattern)

        # Zellengröße berechnen
        max_width = 650
        max_height = 900
        cell_size = min(max_width / self.pattern.width, max_height / self.pattern.height)
        cell_size = max(1, min(8, cell_size))

        total_width = self.pattern.width * cell_size
        total_height = self.pattern.height * cell_size

        # SVG-basierte Vorschau (statt <table>), damit halbe + Viertel-Stiche
        # als Polygone gerendert werden können. Im DP-Modus zusätzlich
        # facettierte Drills statt einfachen Quadraten.
        from .export_common import is_diamond_mode, svg_shape_for_stitch

        is_dp_preview = is_diamond_mode(self.pattern)
        bg_fill = "#ebe8dc" if is_dp_preview else "#fafafa"
        svg_elements: list[str] = [
            f"<rect x='0' y='0' width='{total_width:.1f}' height='{total_height:.1f}' fill='{bg_fill}'/>"
        ]
        for y in range(self.pattern.height):
            for x in range(self.pattern.width):
                color = self._get_pixel_color(x, y)
                if not color:
                    continue
                stype = self._get_pixel_stitch_type(x, y)
                svg_elements.append(
                    svg_shape_for_stitch(
                        stype,
                        x * cell_size,
                        y * cell_size,
                        cell_size,
                        cell_size,
                        color,
                        as_diamond=is_dp_preview,
                    )
                )
        # rows ist Legacy-Name, jetzt eine einzige SVG — Template unten erwartet
        # eine Liste, also ein einzelnes Element reicht.
        rows = ["".join(svg_elements)]

        # Rückstiche für Vorschau
        backstitch_svg = self._generate_backstitches_svg(cell_size)

        backstitch_info = ""
        if self.pattern.backstitches:
            backstitch_info = t(
                "<div class='backstitch-info'><strong>&#8600; R&uuml;ckstiche:</strong> "
                "{n} Linien werden &uuml;ber dem Muster gezeigt.</div>"
            ).format(n=len(self.pattern.backstitches))

        return f"""
<div class='page-break'></div>
<div id='vorschau'>
<h1>{t("Vorschau des fertigen Musters")}</h1>
<h3>{t("Fertige Gr&ouml;&szlig;e auf {fabric}: {w} &times; {h} cm").format(fabric=_html_encode(fabric_name), w=f"{phys_width:.1f}", h=f"{phys_height:.1f}")}</h3>
<div class='preview-container'>
<svg class='preview-svg' width='{total_width:.1f}' height='{total_height:.1f}'
     shape-rendering='crispEdges'>
{"".join(rows)}
{backstitch_svg}
</svg>
</div>
{backstitch_info}
</div>"""

    def _generate_legend(self) -> str:
        """Generiert die Legende."""
        cross_ref_palettes = getattr(self, "cross_ref_palettes", []) or []
        if cross_ref_palettes:
            from ..core.thread_cross_ref import find_equivalents

        # Nur Garn-Stiche in der Hauptlegende; Beads kommen unten in eigene Sektion
        thread_stats = [s for s in self._color_stats if not s.get("is_bead", False)]
        bead_stats = [s for s in self._color_stats if s.get("is_bead", False)]

        rows = []
        for i, stat in enumerate(thread_stats, 1):
            thread = stat["thread"]
            percent = (
                (stat["count"] * 100.0 / self._total_stitches) if self._total_stitches > 0 else 0
            )

            # Cross-Reference-Zellen (eine Spalte pro Ziel-Palette)
            cross_cells = ""
            if cross_ref_palettes:
                equivalents = find_equivalents(thread, cross_ref_palettes)
                for palette_name in cross_ref_palettes:
                    eq = equivalents.get(palette_name)
                    if eq:
                        cross_cells += f"<td>{_html_encode(eq.catalog_number or eq.name)}</td>"
                    else:
                        cross_cells += "<td>—</td>"

            # Bei Tweed-Blends: beide Garnnummern in der Garnnr-Spalte zeigen
            from .export_common import is_diamond_mode

            is_dp_legend = is_diamond_mode(self.pattern)
            if thread.is_blend:
                thread_label = " + ".join(
                    f"{c.manufacturer or ''} {c.catalog_number or ''}".strip()
                    for c in thread.blend_components
                )
                if thread.strand_ratios:
                    thread_label += f" ({'+'.join(str(r) for r in thread.strand_ratios)})"
            elif is_dp_legend:
                # Im DP nur die Drill-Nummer — der Manufacturer würde
                # "DMC Diamond Painting 169" daraus machen und die Spalte
                # sprengen / mit der Name-Spalte überlappen.
                thread_label = thread.catalog_number or ""
            else:
                thread_label = f"{thread.manufacturer or ''} {thread.catalog_number or ''}".strip()

            rows.append(f"""<tr>
<td>{i}</td>
<td style='text-align:center;font-size:14px;'><b>{_html_encode(stat["symbol"])}</b></td>
<td><div class='color-box' style='background:rgb({thread.color.r},{thread.color.g},{thread.color.b})'></div></td>
<td><b>{_html_encode(thread_label)}</b></td>
<td>{_html_encode(thread.name)}</td>
{cross_cells}<td style='text-align:right;'>{stat["count"]}</td>
<td style='text-align:right;'>{percent:.1f}%</td>
<td style='text-align:center;font-weight:bold;'>{stat["skeins"]}</td>
</tr>""")

        # Summenzeile wird unten modus-spezifisch separat angehängt
        # (siehe summary_row), damit das colspan stimmt — im DP-Modus
        # entfällt die Symbol-Spalte.

        # Bead-Sektion (analog zur Backstitch-Sektion)
        bead_section = ""
        if bead_stats:
            bead_rows = []
            total_beads = 0
            for stat in bead_stats:
                thread = stat["thread"]
                count = stat["count"]
                total_beads += count
                bead_rows.append(f"""<tr>
<td><div class='color-box' style='background:rgb({thread.color.r},{thread.color.g},{thread.color.b});width:18px;height:18px;border-radius:50%;'></div></td>
<td>{_html_encode(stat["symbol"])}</td>
<td>{_html_encode(thread.manufacturer or "")} {_html_encode(thread.catalog_number or "")}</td>
<td>{_html_encode(thread.name)}</td>
<td style='text-align:right;'>{count}</td>
</tr>""")

            bead_section = f"""
<h2 style='margin-top:30px;'>&#9679; {t("Perlen (Beads)")}</h2>
<p style='text-align:center;color:#666;font-size:12px;'>{t("Perlen werden über dem Stoff angenaeht und kommen meist am Ende der Stickarbeit dran.")}</p>
<table class='legend-table' style='max-width:600px;'>
<tr><th>{t("Farbe")}</th><th>{t("Symbol")}</th><th>{t("Perlen-Nr.")}</th><th>{t("Farbname")}</th><th>{t("Anzahl")}</th></tr>
{"".join(bead_rows)}
<tr style='background:#e8f4fc;font-weight:bold;'>
<td colspan='4' style='text-align:right;'>{t("Gesamt:")}</td>
<td style='text-align:right;'>{total_beads}</td>
</tr>
</table>"""

        # Backstitch-Info in der Legende — im DP-Modus weglassen (DP hat
        # keine Rückstich-Linien als Konzept).
        backstitch_section = ""
        is_dp_mode = getattr(self.pattern, "mode", "stitch") == "diamond"
        if self.pattern.backstitches and not is_dp_mode:
            # Zähle Backstitches pro Farbe
            bs_by_color: dict[int, int] = {}
            for bs in self.pattern.backstitches:
                bs_by_color[bs.color_index] = bs_by_color.get(bs.color_index, 0) + 1

            bs_rows = []
            for color_idx, count in sorted(bs_by_color.items()):
                entry = self.pattern.get_color_entry(color_idx)
                if entry:
                    thread = entry.thread
                    bs_rows.append(f"""<tr>
<td><div class='color-box' style='background:rgb({thread.color.r},{thread.color.g},{thread.color.b});width:18px;height:18px;'></div></td>
<td>{_html_encode(entry.symbol)}</td>
<td>{_html_encode(thread.manufacturer or "")} {_html_encode(thread.catalog_number or "")}</td>
<td>{_html_encode(thread.name)}</td>
<td style='text-align:right;'>{count}</td>
</tr>""")

            backstitch_section = f"""
<h2 style='margin-top:30px;'>&#8600; {t("R&uuml;ckstiche")}</h2>
<p style='text-align:center;color:#666;font-size:12px;'>{t("R&uuml;ckstiche werden nach den Kreuzstichen gearbeitet und bilden Konturen und Details.")}</p>
<table class='legend-table' style='max-width:600px;'>
<tr><th>{t("Farbe")}</th><th>{t("Symbol")}</th><th>{t("Garnnummer")}</th><th>{t("Farbname")}</th><th>{t("Anzahl")}</th></tr>
{"".join(bs_rows)}
<tr style='background:#e8f4fc;font-weight:bold;'>
<td colspan='4' style='text-align:right;'>{t("Gesamt:")}</td>
<td style='text-align:right;'>{len(self.pattern.backstitches)}</td>
</tr>
</table>"""

        # Header — falls Cross-Ref aktiv, zusätzliche Spalten einbauen
        cross_ref_headers = "".join(f"<th>{_html_encode(name)}</th>" for name in cross_ref_palettes)

        # Modus-spezifische Spaltenköpfe und Section-Header.
        from .export_common import is_diamond_mode, terms_for

        terms = terms_for(self.pattern)
        is_dp = is_diamond_mode(self.pattern)
        legend_title = t("Drill-Legende und Material") if is_dp else t("Legende und Materialbedarf")
        unit_col = terms["unit_plural"]  # Stiche / Drills
        supply_col = terms["supply_unit"]  # Stränge / Drills
        code_col = terms["code_header"]  # Garnnummer / Drill-Code
        # Im DP-Modus entfällt die Symbol-Spalte (Drills tragen ihre
        # Identität über den Code, nicht über Unicode-Symbole).
        if is_dp:
            symbol_header = ""
        else:
            symbol_header = f"<th>{t('Symbol')}</th>"

        # Zur Vereinfachung: im DP-Modus zusätzlich die Symbol-Spalte
        # aus den Rows herausfiltern (sie steht im Format "<td...>Symbol</td>").
        if is_dp:
            filtered_rows = []
            for row in rows:
                # zweites <td> überspringen (Symbol-Zelle)
                start = row.find("<td", row.find("<td") + 1)  # zweites <td
                end = row.find("</td>", start) + len("</td>")
                filtered_rows.append(row[:start] + row[end:])
            rows_html = "".join(filtered_rows)
            # Summary-Row colspan ebenfalls reduzieren
            summary_colspan = 4 + len(cross_ref_palettes)
        else:
            rows_html = "".join(rows)
            summary_colspan = 5 + len(cross_ref_palettes)

        # Summary-Row neu bauen (wir brauchen modus-spezifischen colspan)
        summary_row = f"""<tr style='background:#e8f4fc;font-weight:bold;'>
<td colspan='{summary_colspan}' style='text-align:right;'>{t("Gesamt:")}</td>
<td style='text-align:right;'>{self._total_stitches}</td>
<td style='text-align:right;'>100%</td>
<td style='text-align:center;'>{self._total_skeins}</td>
</tr>"""

        legend_summary_line = t(
            "{n} Farben &middot; {stitches} {unit} &middot; ca. {supply_n} {supply_unit} ben&ouml;tigt"
        ).format(
            n=len(thread_stats),
            stitches=self._total_stitches,
            unit=unit_col,
            supply_n=self._total_skeins,
            supply_unit=supply_col,
        )

        return f"""
<div class='page-break'></div>
<div id='legende'>
<h1>{legend_title}</h1>
<h3>{legend_summary_line}</h3>
<table class='legend-table'>
<tr><th>{t("Nr.")}</th>{symbol_header}<th>{t("Farbe")}</th><th>{code_col}</th><th>{t("Farbname")}</th>{cross_ref_headers}<th>{unit_col}</th><th>%</th><th>{supply_col}</th></tr>
{rows_html}
{summary_row}
</table>
{backstitch_section}
{bead_section}
</div>"""

    def _generate_overview(self, pages_x: int, pages_y: int) -> str:
        """Generiert die Übersichtskarte."""
        total_pages = pages_x * pages_y

        # SVG-Vorschau
        overview_w = 250.0
        overview_h = overview_w * self.pattern.height / self.pattern.width
        if overview_h > 180:
            overview_h = 180.0
            overview_w = overview_h * self.pattern.width / self.pattern.height

        cell_w = overview_w / self.pattern.width
        cell_h = overview_h / self.pattern.height

        # Muster als SVG (halbe/Viertel als Polygone, Drills im DP-Modus
        # als facettierte Quadrate).
        from .export_common import is_diamond_mode, svg_shape_for_stitch, terms_for

        is_dp_overview = is_diamond_mode(self.pattern)
        overview_unit_label = terms_for(self.pattern)["unit_plural"]
        svg_rects = []
        for y in range(self.pattern.height):
            for x in range(self.pattern.width):
                color = self._get_pixel_color(x, y)
                if color:
                    rx = x * cell_w
                    ry = y * cell_h
                    stype = self._get_pixel_stitch_type(x, y)
                    svg_rects.append(
                        svg_shape_for_stitch(
                            stype,
                            rx,
                            ry,
                            cell_w,
                            cell_h,
                            color,
                            as_diamond=is_dp_overview,
                        )
                    )

        # Rückstiche für Übersicht — im DP-Modus weglassen.
        backstitch_svg = "" if is_dp_overview else self._generate_backstitches_svg(cell_w)

        # Rasterlinien
        grid_lines = []
        for sx in range(1, pages_x):
            line_x = sx * self.STITCHES_PER_PAGE_X * cell_w
            grid_lines.append(
                f"<line x1='{line_x:.1f}' y1='0' x2='{line_x:.1f}' y2='{overview_h:.1f}' stroke='rgba(255,255,255,0.9)' stroke-width='2'/>"
            )

        for sy in range(1, pages_y):
            line_y = sy * self.STITCHES_PER_PAGE_Y * cell_h
            grid_lines.append(
                f"<line x1='0' y1='{line_y:.1f}' x2='{overview_w:.1f}' y2='{line_y:.1f}' stroke='rgba(255,255,255,0.9)' stroke-width='2'/>"
            )

        # Seitennummern
        page_labels = []
        page_nr = 1
        page_cell_w = self.STITCHES_PER_PAGE_X * cell_w
        page_cell_h = self.STITCHES_PER_PAGE_Y * cell_h

        for sy in range(pages_y):
            for sx in range(pages_x):
                cx = sx * page_cell_w + page_cell_w / 2
                cy = sy * page_cell_h + page_cell_h / 2
                page_labels.append(
                    f"<text x='{cx:.1f}' y='{cy + 5:.1f}' text-anchor='middle' font-size='14' font-weight='bold' fill='white' stroke='#333' stroke-width='0.8'>{page_nr}</text>"
                )
                page_nr += 1

        # Seitenkacheln
        page_cells = []
        page_nr = 1
        for sy in range(pages_y):
            page_cells.append("<tr>")
            for sx in range(pages_x):
                range_x1 = sx * self.STITCHES_PER_PAGE_X + 1
                range_x2 = min((sx + 1) * self.STITCHES_PER_PAGE_X, self.pattern.width)
                range_y1 = sy * self.STITCHES_PER_PAGE_Y + 1
                range_y2 = min((sy + 1) * self.STITCHES_PER_PAGE_Y, self.pattern.height)

                page_cells.append(f"""<td>
<a href='#seite{page_nr}' class='overview-cell'>
<span class='overview-cell-nr'>{page_nr}</span>
<span class='overview-cell-range'>X: {range_x1}-{range_x2}</span>
<span class='overview-cell-range'>Y: {range_y1}-{range_y2}</span>
</a></td>""")
                page_nr += 1
            page_cells.append("</tr>")

        overview_summary_line = t(
            "{total} Musterseiten &middot; {px} Spalten &times; {py} Zeilen &middot; je 40&times;40 {unit}"
        ).format(total=total_pages, px=pages_x, py=pages_y, unit=overview_unit_label)

        overview_backstitch_note = (
            t(
                "<p><strong>&#8600; R&uuml;ckstiche:</strong> {n} R&uuml;ckstiche werden auf den "
                "Musterseiten als Linien angezeigt.</p>"
            ).format(n=len(self.pattern.backstitches))
            if self.pattern.backstitches
            else ""
        )

        return f"""
<div class='page-break'></div>
<div id='uebersicht' class='overview-section'>
<div class='overview-header'>
<h1>&#128506; {t("Seiten&uuml;bersicht")}</h1>
<p>{overview_summary_line}</p>
</div>

<div class='overview-container'>
<div class='overview-preview-box'>
<div class='overview-preview-title'>&#128444; {t("Muster&uuml;bersicht")}</div>
<div class='overview-preview-inner'>
<svg width='{int(overview_w)}' height='{int(overview_h)}' style='display:block;'>
{"".join(svg_rects)}
{backstitch_svg}
{"".join(grid_lines)}
{"".join(page_labels)}
</svg>
</div>
</div>

<div class='overview-grid-box'>
<div class='overview-grid-title'>&#128196; {t("Seiten ausw&auml;hlen")}</div>
<table class='overview-table'>
{"".join(page_cells)}
</table>
</div>
</div>

<div class='overview-info'>
<p><strong>&#128161; {t("Tipp:")}</strong> {t("Klicken Sie auf eine Seitennummer um direkt zur entsprechenden Musterseite zu springen.")}</p>
<p><strong>&#128209; {t("Seitenformat:")}</strong> {t("Jede Seite zeigt einen Bereich von 40&times;40 Stichen mit 10er-Rasterlinien.")}</p>
{overview_backstitch_note}
</div>
</div>"""
