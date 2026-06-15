"""
HTML-Export fuer Kreuzstich-Muster.

Erstellt druckbare HTML-Dateien mit:
- Deckblatt mit Vorschau und Statistiken
- Farbvorschau des fertigen Musters (inkl. Rueckstiche)
- Legende mit Garnbedarf
- Uebersichtskarte der Seiten
- Musterseiten (40x40 Stiche pro Seite)
"""

import logging
from datetime import datetime
from html import escape as _html_escape
from math import ceil
from pathlib import Path
from typing import TYPE_CHECKING

from .export_cache import CompositeGridCache
from .export_common import (
    count_page_colors,
    get_pixel_color,
    get_pixel_stitch_type,
    get_pixel_symbol,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..core import Pattern


def _html_encode(text: str) -> str:
    """
    Escapt HTML-Sonderzeichen (<, >, &) fuer Body-Text.

    Umlaute bleiben als UTF-8 erhalten, weil das erzeugte HTML
    <meta charset='UTF-8'> deklariert. Falls der Input bereits Entity-
    Versionen einzelner Sonderzeichen enthaelt (`&times;`, `&amp;`),
    werden die zuerst auf das Klartext-Zeichen zurueckgesetzt, damit
    `escape()` sie nicht doppel-escapt.
    """
    if not text:
        return text
    text = text.replace("&times;", "×").replace("&amp;", "&")
    return _html_escape(text, quote=False)


# Mixin-Importe nach _html_encode, da die Mixins diese Funktion importieren
from .html_export_pages import HTMLPagesMixin  # noqa: E402
from .html_export_sections import HTMLSectionsMixin  # noqa: E402


class HTMLExporter(HTMLSectionsMixin, HTMLPagesMixin):
    """Exportiert Kreuzstich-Muster als druckbare HTML-Datei."""

    STITCHES_PER_PAGE_X = 40
    STITCHES_PER_PAGE_Y = 40

    # Stiche pro Strang je nach Stofftyp
    STITCHES_PER_SKEIN = {
        11: 2500,  # Aida 11
        14: 1800,  # Aida 14
        16: 1600,  # Aida 16
        18: 1400,  # Aida 18
        22: 1200,  # Aida 22
        28: 1000,  # Aida 28
        32: 800,  # Aida 32
    }

    def __init__(
        self,
        pattern: "Pattern",
        cross_ref_palettes: list[str] | None = None,
        page_overlap_stitches: int = 0,
    ) -> None:
        self.pattern = pattern
        self._color_stats: list[dict] = []
        self._total_stitches = 0
        self._total_skeins = 0
        self._cache: CompositeGridCache | None = None
        # Optionale Hersteller-Cross-Reference fuer die Legende.
        # Wenn gesetzt (z.B. ["Anchor", "Madeira"]), erscheinen entsprechende
        # Spalten mit der naehesten Garn-Entsprechung.
        self.cross_ref_palettes: list[str] = cross_ref_palettes or []
        # Working-Chart-Pages mit Overlap: jede Seite zeigt zusaetzlich die
        # ersten N Stiche der Nachbarseite (rechts/unten). 0 = kein Overlap
        # (Standard, ist genau das bisherige Verhalten).
        self.page_overlap_stitches: int = max(0, int(page_overlap_stitches))

        # DP-Modus: 1:1-Druck-Massstab. Wir berechnen pro Seite, wie viele
        # Drills bei Drill-Pitch (2.5/2.8/3.0 mm) und A4-nutzbarer-Breite
        # passen. So passt der ausgedruckte Klebegrund Drill-fuer-Drill zur
        # echten Drill-Groesse.
        from .export_common import drill_pitch_mm, is_diamond_mode

        self._dp_cell_mm: float | None = None
        if is_diamond_mode(self.pattern):
            self._dp_cell_mm = drill_pitch_mm(self.pattern)
            # A4 mit 15mm Margin -> 180mm Breite/267mm Hoehe (Hochformat).
            # Header-Spalte links + Spalten-Header oben kosten ~8mm.
            available_mm_w = 180.0 - 8.0
            available_mm_h = 267.0 - 8.0
            self.STITCHES_PER_PAGE_X = max(1, int(available_mm_w / self._dp_cell_mm))
            self.STITCHES_PER_PAGE_Y = max(1, int(available_mm_h / self._dp_cell_mm))

    def export(self, filepath: str | Path) -> bool:
        """Exportiert das Muster als HTML-Datei."""
        filepath = Path(filepath)
        if not filepath.suffix.lower() == ".html":
            filepath = filepath.with_suffix(".html")

        # Statistiken berechnen
        self._calculate_statistics()

        # Komposit-Grid einmalig pre-computen — alle Per-Pixel-Lookups
        # gehen anschliessend ueber den Cache statt durch den Layer-Stack.
        self._cache = CompositeGridCache(self.pattern)

        # Seitenaufteilung
        pages_x = ceil(self.pattern.width / self.STITCHES_PER_PAGE_X)
        pages_y = ceil(self.pattern.height / self.STITCHES_PER_PAGE_Y)
        total_pages = pages_x * pages_y

        # Titel
        title = filepath.stem
        date = datetime.now().strftime("%d.%m.%Y")

        # Physische Größe (fabric_count ist Stiche pro Inch)
        stitches_per_cm = self.pattern.fabric_count / 2.54
        phys_width = self.pattern.width / stitches_per_cm
        phys_height = self.pattern.height / stitches_per_cm

        # HTML generieren
        html_parts = []

        # Header
        html_parts.append(self._generate_header(title))

        # Navigation
        html_parts.append(self._generate_navigation(pages_x, pages_y))

        html_parts.append("<div class='container'>")

        # Deckblatt
        html_parts.append(self._generate_cover(title, date, phys_width, phys_height, total_pages))

        # Vorschau
        html_parts.append(self._generate_preview(phys_width, phys_height))

        # Legende
        html_parts.append(self._generate_legend())

        # Übersichtskarte
        html_parts.append(self._generate_overview(pages_x, pages_y))

        # Musterseiten
        html_parts.append(self._generate_pattern_pages(pages_x, pages_y, title, date))

        # Footer
        html_parts.append("</div></body></html>")

        # Datei schreiben
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(html_parts))
            return True
        except OSError as e:
            logger.error("Fehler beim HTML-Export: %s", e)
            return False

    def _calculate_statistics(self) -> None:
        """Berechnet Farbstatistiken und Garnbedarf.

        Verwendet iterate_composite_stitches(), damit nur sichtbare Layer
        berücksichtigt werden und bei Überlappungen nur der oberste Stich zählt.
        """
        self._color_stats = []
        stitch_counts: dict[int, int] = {}

        # Stiche pro Farbe zählen (nur sichtbare Layer, oberster Stich)
        for _x, _y, color_idx in self.pattern.iterate_composite_stitches():
            stitch_counts[color_idx] = stitch_counts.get(color_idx, 0) + 1

        # Modus-spezifischer "Bedarf"-Wert:
        # - Stitch: Stränge pro Farbe (Garn-Verbrauch)
        # - Diamond: Drill-Anzahl plus 10% Reserve (Verluste durch fallende Drills)
        is_dp = getattr(self.pattern, "mode", "stitch") == "diamond"
        stitches_per_skein = self.STITCHES_PER_SKEIN.get(self.pattern.fabric_count, 1800)

        # Statistiken aufbauen
        self._total_stitches = 0
        self._total_skeins = 0

        for i, entry in enumerate(self.pattern.color_entries):
            count = stitch_counts.get(i, 0)
            # Bead-Farben werden NICHT als Stränge gerechnet — Beads sind Perlen,
            # keine Garn-Stränge. Sie kommen in eine eigene Bead-Sektion.
            if entry.is_bead:
                self._color_stats.append(
                    {
                        "index": i,
                        "symbol": entry.symbol,
                        "thread": entry.thread,
                        "count": count,
                        "skeins": 0,
                        "is_bead": True,
                    }
                )
                continue

            if is_dp:
                # Drill-Bedarf = Stiche * 1.10 (10% Reserve fuer Verluste).
                # Wir nutzen weiterhin das `skeins`-Feld, damit die HTML/PDF-
                # Templates nicht mit zwei Datenmodellen rechnen muessen —
                # die Templates beschriften es modus-spezifisch.
                skeins = int(count * 1.10) if count > 0 else 0
            else:
                skeins = ceil(count / stitches_per_skein) if count > 0 else 0
                if count > 1000:
                    skeins += 1  # Extra Strang bei vielen Stichen

            self._color_stats.append(
                {
                    "index": i,
                    "symbol": entry.symbol,
                    "thread": entry.thread,
                    "count": count,
                    "skeins": skeins,
                    "is_bead": False,
                }
            )

            self._total_stitches += count
            self._total_skeins += skeins

    def _generate_backstitches_svg(
        self,
        cell_size: float,
        offset_x: float = 0,
        offset_y: float = 0,
        start_stitch_x: int = 0,
        start_stitch_y: int = 0,
        end_stitch_x: int | None = None,
        end_stitch_y: int | None = None,
    ) -> str:
        """
        Generiert SVG-Linien für Rückstiche.

        Args:
            cell_size: Größe einer Zelle in Pixeln
            offset_x, offset_y: Offset für die Linien
            start_stitch_x, start_stitch_y: Start-Stich (für Seitenausschnitt)
            end_stitch_x, end_stitch_y: End-Stich (für Seitenausschnitt)

        Returns:
            SVG-Linien als String
        """
        if not self.pattern.backstitches:
            return ""

        if end_stitch_x is None:
            end_stitch_x = self.pattern.width
        if end_stitch_y is None:
            end_stitch_y = self.pattern.height

        # Halbe Stiche in Pixel umrechnen
        half_cell = cell_size / 2

        lines = []
        for bs in self.pattern.backstitches:
            # Prüfen ob der Backstitch im sichtbaren Bereich liegt
            # Backstitch-Koordinaten sind in halben Stichen
            # Stich (0,0) hat halbe Stiche von (0,0) bis (2,2)
            bs_stitch_x1 = bs.x1 // 2
            bs_stitch_y1 = bs.y1 // 2
            bs_stitch_x2 = bs.x2 // 2
            bs_stitch_y2 = bs.y2 // 2

            # Prüfen ob mindestens ein Endpunkt im Bereich liegt
            in_range_1 = (
                start_stitch_x <= bs_stitch_x1 < end_stitch_x
                and start_stitch_y <= bs_stitch_y1 < end_stitch_y
            )
            in_range_2 = (
                start_stitch_x <= bs_stitch_x2 < end_stitch_x
                and start_stitch_y <= bs_stitch_y2 < end_stitch_y
            )

            if not (in_range_1 or in_range_2):
                continue

            # Farbe holen
            entry = self.pattern.get_color_entry(bs.color_index)
            if entry:
                color = f"rgb({entry.thread.color.r},{entry.thread.color.g},{entry.thread.color.b})"
            else:
                color = "rgb(0,0,0)"

            # Koordinaten berechnen (relativ zum Seitenausschnitt)
            x1 = (bs.x1 - start_stitch_x * 2) * half_cell + offset_x
            y1 = (bs.y1 - start_stitch_y * 2) * half_cell + offset_y
            x2 = (bs.x2 - start_stitch_x * 2) * half_cell + offset_x
            y2 = (bs.y2 - start_stitch_y * 2) * half_cell + offset_y

            # Liniendicke basierend auf Zellgröße
            stroke_width = max(1.5, cell_size / 8)

            # Linie mit Schatten für bessere Sichtbarkeit
            lines.append(
                f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' "
                f"stroke='rgba(0,0,0,0.3)' stroke-width='{stroke_width + 1:.1f}' "
                f"stroke-linecap='round'/>"
            )
            lines.append(
                f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' "
                f"stroke='{color}' stroke-width='{stroke_width:.1f}' "
                f"stroke-linecap='round'/>"
            )

        return "\n".join(lines)

    def _generate_partial_stitches_svg(
        self,
        cell_size: float,
        offset_x: float,
        offset_y: float,
        start_stitch_x: int,
        start_stitch_y: int,
        end_stitch_x: int,
        end_stitch_y: int,
    ) -> str:
        """Generiert SVG-Polygone für Halb-/Viertel-/Dreiviertel-Stiche.

        Wird im HTML-Export als Overlay zwischen Tabelle und Backstitches
        gezeichnet — so sieht der User auf jeder Seite, welche Halbstiche
        in welcher Farbe wo sitzen, und kann das Symbol darüber lesen.
        """
        from ..core.stitch_shapes import (
            bead_radius_factor,
            french_knot_radius_factor,
            is_bead,
            is_french_knot,
            is_partial_stitch,
            normalized_partial_stitch_shape,
        )

        if not self.pattern:
            return ""

        elements: list[str] = []

        for sy in range(start_stitch_y, end_stitch_y):
            if sy >= self.pattern.height:
                break
            for sx in range(start_stitch_x, end_stitch_x):
                if sx >= self.pattern.width:
                    break

                stype = self._get_pixel_stitch_type(sx, sy)
                if stype == 0:
                    continue  # Voller Kreuzstich → nur Symbol genuegt

                color_rgb = self._get_pixel_color(sx, sy)
                if color_rgb is None:
                    continue
                r, g, b = color_rgb
                fill = f"rgb({r},{g},{b})"

                # Zell-Position relativ zum Seiten-Offset
                cx_left = (sx - start_stitch_x) * cell_size + offset_x
                cy_top = (sy - start_stitch_y) * cell_size + offset_y

                # WICHTIG: SVG liegt im DOM ueber der Tabelle, deshalb
                # fill-opacity: das Symbol in der Tabelle scheint durch und
                # bleibt lesbar. ~0.55 ist Erfahrungswert (Symbol kontrastiert
                # noch klar, Farbe ist trotzdem deutlich erkennbar).
                opacity = "0.55"

                if is_french_knot(stype):
                    radius = max(1.5, cell_size * french_knot_radius_factor())
                    cx = cx_left + cell_size / 2
                    cy = cy_top + cell_size / 2
                    elements.append(
                        f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='{radius:.1f}' "
                        f"fill='{fill}' fill-opacity='{opacity}'/>"
                    )
                elif is_bead(stype):
                    radius = max(2.0, cell_size * bead_radius_factor())
                    cx = cx_left + cell_size / 2
                    cy = cy_top + cell_size / 2
                    elements.append(
                        f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='{radius:.1f}' "
                        f"fill='{fill}' fill-opacity='{opacity}'/>"
                    )
                elif is_partial_stitch(stype):
                    pts = normalized_partial_stitch_shape(stype)
                    if not pts:
                        continue
                    poly = " ".join(
                        f"{cx_left + nx * cell_size:.1f},{cy_top + ny * cell_size:.1f}"
                        for nx, ny in pts
                    )
                    elements.append(
                        f"<polygon points='{poly}' fill='{fill}' "
                        f"fill-opacity='{opacity}' "
                        f"stroke='rgba(0,0,0,0.3)' stroke-width='0.5'/>"
                    )

        return "\n".join(elements)

    def _count_page_colors(
        self, start_x: int, start_y: int, end_x: int, end_y: int
    ) -> dict[int, int]:
        """Zählt die Farben in einem Seitenbereich."""
        if self._cache is not None:
            return self._cache.count_page_colors(start_x, start_y, end_x, end_y)
        return count_page_colors(self.pattern, start_x, start_y, end_x, end_y)

    def _get_page_backstitches(self, start_x: int, start_y: int, end_x: int, end_y: int) -> list:
        """Gibt alle Rückstiche zurück, die auf einer Seite sichtbar sind."""
        if not self.pattern.backstitches:
            return []

        result = []
        for bs in self.pattern.backstitches:
            # Backstitch-Koordinaten sind in halben Stichen
            bs_stitch_x1 = bs.x1 // 2
            bs_stitch_y1 = bs.y1 // 2
            bs_stitch_x2 = bs.x2 // 2
            bs_stitch_y2 = bs.y2 // 2

            # Prüfen ob mindestens ein Endpunkt im Bereich liegt
            in_range_1 = start_x <= bs_stitch_x1 <= end_x and start_y <= bs_stitch_y1 <= end_y
            in_range_2 = start_x <= bs_stitch_x2 <= end_x and start_y <= bs_stitch_y2 <= end_y

            if in_range_1 or in_range_2:
                result.append(bs)

        return result

    def _get_pixel_color(self, x: int, y: int) -> tuple[int, int, int] | None:
        """Gibt die Farbe an einer Position zurück (oberstes sichtbares Layer)."""
        if self._cache is not None:
            return self._cache.get_color(x, y)
        return get_pixel_color(self.pattern, x, y)

    def _get_pixel_symbol(self, x: int, y: int) -> str:
        """Gibt das Symbol an einer Position zurück (oberstes sichtbares Layer)."""
        if self._cache is not None:
            return self._cache.get_symbol(x, y)
        return get_pixel_symbol(self.pattern, x, y)

    def _get_pixel_stitch_type(self, x: int, y: int) -> int:
        """Stitch-Type an einer Position (oberstes sichtbares Layer)."""
        if self._cache is not None:
            return self._cache.get_stitch_type(x, y)
        return get_pixel_stitch_type(self.pattern, x, y)
