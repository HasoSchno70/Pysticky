"""
Gemeinsame Hilfsfunktionen fuer HTML- und PDF-Export.

Die Funktionen kapseln die "Top-Visible-Layer"-Logik, die in beiden
Exporter-Varianten identisch gebraucht wird: pro Pattern-Position wird
das oberste sichtbare Layer befragt, das einen Stitch eingetragen hat.

Zusaetzlich exportiert dieses Modul die modus-spezifische Terminologie
fuer HTML- und PDF-Export. Statt im Template-Code "Stiche" oder "Drills"
hartcodieren, holt sich der Renderer die passenden Begriffe aus
``terms_for(pattern)`` und kann denselben Template-Code in beiden Modi
nutzen.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.pattern import ColorEntry, Pattern


# Modus-spezifische Begriffe fuer Export-Templates. Pro Mode ein Dict
# mit derselben Key-Struktur, damit der Template-Code modus-blind ist.
_MODE_TERMS: dict[str, dict[str, str]] = {
    "stitch": {
        "unit_plural": "Stiche",
        "unit_singular": "Stich",
        "time_label": "Stickzeit",
        "supply_label": "Garnbedarf",
        "supply_unit": "Stränge",
        "supply_unit_short": "Str.",
        "supply_icon": "&#129525;",  # 🧵
        "fabric_label": "Stoffempfehlung",
        "fabric_format": "Aida {count}",
        "fabric_count_label": "ct Aida",
        "legend_title": "Garn-Legende",
        "code_header": "Garnnummer",
        "preview_caption": "Vorschau des fertigen Musters",
        "cover_title_suffix": "Kreuzstich-Muster",
        "size_unit_template": "{w} × {h} Stiche",
        "totals_template": "{n} Kreuze",
        "doc_subtitle": "Kreuzstich-Anleitung",
    },
    "diamond": {
        "unit_plural": "Drills",
        "unit_singular": "Drill",
        "time_label": "Klebezeit",
        "supply_label": "Drill-Bedarf",
        "supply_unit": "Drills",
        "supply_unit_short": "Dr.",
        "supply_icon": "&#128142;",  # 💎
        "fabric_label": "Drill-Raster",
        "fabric_format": "{count}",  # wird im Renderer mit fertigem Label gefuellt
        "fabric_count_label": "Drill-Pitch",
        "legend_title": "Drill-Legende",
        "code_header": "Drill-Code",
        "preview_caption": "Vorschau der fertigen Vorlage",
        "cover_title_suffix": "Diamond-Painting-Vorlage",
        "size_unit_template": "{w} × {h} Drills",
        "totals_template": "{n} Drills",
        "doc_subtitle": "Diamond-Painting-Anleitung",
    },
}


def terms_for(pattern: "Pattern") -> dict[str, str]:
    """Liefert die modus-spezifischen Begriffe fuer den Export.

    Uebersetzt bei JEDEM Aufruf frisch in der aktuell aktiven UI-Sprache
    (statt einmalig zur Modul-Importzeit), damit ein Sprachwechsel zur
    Laufzeit auch fuer PDF-/HTML-Exports sofort wirkt.
    """
    from ..core.i18n import t

    mode = getattr(pattern, "mode", "stitch")
    raw = _MODE_TERMS.get(mode, _MODE_TERMS["stitch"])
    return {k: t(v) for k, v in raw.items()}


def is_diamond_mode(pattern: "Pattern") -> bool:
    """Convenience-Predicate fuer Templates."""
    return getattr(pattern, "mode", "stitch") == "diamond"


def fabric_label_for(pattern: "Pattern") -> str:
    """Stoff/Drill-Raster-Bezeichnung. Im DP-Modus haengt der Text vom
    fabric_count ab (siehe info_panel: 10≈2.5mm, 9≈2.8mm, 8≈3.0mm)."""
    from ..core.i18n import t

    if is_diamond_mode(pattern):
        mapping = {10: t("2.5 mm Square"), 9: t("2.8 mm Round"), 8: t("3.0 mm Round")}
        fallback = t("{count} (Drill-Pitch)").format(count=pattern.fabric_count)
        return mapping.get(pattern.fabric_count, fallback)
    return f"Aida {pattern.fabric_count}"


# Drill-Pitch-Mapping (fabric_count -> Pitch in Millimetern).
# fabric_count im DP-Modus wird vom info_panel aus dem Combo gesetzt:
# 10 = 2.5 mm Square (Standard), 9 = 2.8 mm Round, 8 = 3.0 mm Round.
_DRILL_PITCH_MM: dict[int, float] = {10: 2.5, 9: 2.8, 8: 3.0}


def drill_pitch_mm(pattern: "Pattern") -> float:
    """Drill-Kanten-Laenge in Millimetern (nur im DP-Modus sinnvoll).

    Wird beim 1:1-Druck als physische Cell-Size benutzt: ein Drill auf
    der ausgedruckten Vorlage muss exakt diese Kanten-Laenge haben, sonst
    passt der physische Drill nicht in die Klebezelle. Ein DP-Pattern bei
    200x200 Drills mit 2.5mm Pitch ergibt 500x500mm = 50x50cm fertige
    Klebefolie.

    Fallback: 2.5mm fuer unbekannte fabric_count-Werte (Standard-Drill).
    """
    return _DRILL_PITCH_MM.get(pattern.fabric_count, 2.5)


# Papier-Formate fuer die DP-Format-Empfehlung. Reihenfolge: klein -> gross.
# Werte sind die NUTZBAREN Innenmasse (Papier minus typischer Margin), in
# Millimetern. Das ist die Flaeche, in die das Drill-Raster wirklich rein
# muss — sonst gibt's reportlab-LayoutErrors.
_PAPER_USABLE_MM = (
    # (Name, nutzbare Breite mm, nutzbare Hoehe mm)
    ("A4", 180.0, 247.0),  # 210x297 minus 15mm Margin + ~50mm Header/Footer-Reserve
    ("A3", 267.0, 354.0),  # 297x420 - 15mm Margin - 50mm Reserve
    ("A2", 380.0, 504.0),  # 420x594 - 20mm Margin - 50mm Reserve
    ("A1", 544.0, 691.0),  # 594x841 - 20mm Margin - 100mm Reserve
    ("A0", 781.0, 989.0),  # 841x1189 - 25mm Margin - 150mm Reserve
)


def recommend_paper_format_for_dp(pattern: "Pattern", max_pages: int = 2) -> str:
    """Empfiehlt das kleinste Papierformat, in das ein DP-Pattern bei
    1:1-Druck mit max ``max_pages`` Seiten passt.

    Beispiel: 200x200-Drill-Pattern bei 2.5mm Pitch ist 500x500mm fertige
    Klebefolie. A4 (nutzbar 180x247mm) braucht 3x3 = 9 Seiten — zu viel.
    A1 (544x691mm) passt auf 1 Seite — empfohlen.

    Args:
        pattern: Das DP-Pattern (mode='diamond').
        max_pages: Wie viele Seiten der Druck maximal haben darf, damit
            ein Format als "passend" gilt. Default 2 — bei groesseren
            Patterns wird A0 empfohlen, weil mehr Seiten unhandlich sind.

    Returns:
        Format-Name aus PAGE_FORMATS, oder "A4" fuer Nicht-DP-Pattern.
    """
    if not is_diamond_mode(pattern):
        return "A4"

    pitch = drill_pitch_mm(pattern)
    pattern_w_mm = pattern.width * pitch
    pattern_h_mm = pattern.height * pitch

    import math

    for name, usable_w, usable_h in _PAPER_USABLE_MM:
        pages_x = math.ceil(pattern_w_mm / usable_w)
        pages_y = math.ceil(pattern_h_mm / usable_h)
        if pages_x * pages_y <= max_pages:
            return name
    # Wenn nichts in max_pages passt → groesstes Format als Default.
    return _PAPER_USABLE_MM[-1][0]


def _top_color_entry(pattern: "Pattern", x: int, y: int) -> "ColorEntry | None":
    """Liefert den ColorEntry des obersten sichtbaren Stitches an (x, y)."""
    for layer in reversed(pattern.layer_stack.layers):
        if not layer.visible:
            continue
        color_idx = layer.get_stitch(x, y)
        if color_idx is not None:
            return pattern.get_color_entry(color_idx)
    return None


def get_pixel_color(pattern: "Pattern", x: int, y: int) -> tuple[int, int, int] | None:
    """RGB des obersten sichtbaren Stitches, oder None wenn leer."""
    entry = _top_color_entry(pattern, x, y)
    if entry is None:
        return None
    color = entry.thread.color
    return (color.r, color.g, color.b)


def get_pixel_symbol(pattern: "Pattern", x: int, y: int) -> str:
    """Symbol des obersten sichtbaren Stitches, oder Leerstring."""
    entry = _top_color_entry(pattern, x, y)
    return entry.symbol if entry is not None else ""


def get_pixel_stitch_type(pattern: "Pattern", x: int, y: int) -> int:
    """
    Stitch-Type des obersten sichtbaren Stitches an (x, y).

    0 = FULL (oder leere Zelle — der Aufrufer prueft `get_pixel_color`
    separat). 1-7 = Halbe/Viertel-Stiche. 8/9 = Backstitch/French-Knot.
    """
    for layer in reversed(pattern.layer_stack.layers):
        if not layer.visible:
            continue
        color_idx = layer.get_stitch(x, y)
        if color_idx is not None:
            if layer.stitch_type_grid is not None:
                return int(layer.stitch_type_grid[y, x])
            return 0
    return 0


# ---------------------------------------------------------------------------
# Drill-Optik fuer Diamond-Painting-Export
# ---------------------------------------------------------------------------

# Inset des Drills relativ zur Zelle. Der Rand zur Nachbarzelle macht die
# Drill-Optik plastisch und entspricht dem echten DP-Klebegrund zwischen den
# Drills. Konsistent zur Canvas-Drill-Darstellung (siehe stitch_shapes.py:
# diamond_inset_factor()).
_DRILL_INSET = 0.08


def _shade_rgb(rgb: tuple[int, int, int], factor: int) -> tuple[int, int, int]:
    """Heller (factor>100) oder dunkler (factor<100) Variante einer Farbe.

    Analog zu QColor.lighter()/darker() — factor=100 ist Identitaet,
    factor=150 ist 50% heller, factor=70 ist 30% dunkler.
    """
    r, g, b = rgb
    if factor >= 100:
        amt = (factor - 100) / 100.0
        return (
            int(r + (255 - r) * amt),
            int(g + (255 - g) * amt),
            int(b + (255 - b) * amt),
        )
    amt = factor / 100.0
    return (int(r * amt), int(g * amt), int(b * amt))


def svg_drill_shape(
    x: float,
    y: float,
    cell_w: float,
    cell_h: float,
    color: tuple[int, int, int],
) -> str:
    """Liefert einen SVG-Snippet fuer einen Diamond-Painting-Drill.

    Vier dreieckige Facetten: oben hell (Glanz), unten dunkel (Schatten),
    seitlich mittel. Bei kleiner Zelle (<12) entfaellt der Inset, damit
    benachbarte Drills sich nahtlos beruehren — sonst wirkt die Vorlage
    in der Cover-/Mini-Vorschau ausgewaschen weiss. Bei groesserer Zelle
    zusaetzlich ein dunkler Kantenrand fuer Trennschaerfe. Konsistent zur
    Canvas-Drill-Optik (siehe rendering_mixin._draw_diamond_drill).
    """
    from ..core.stitch_shapes import diamond_inset_pixels, diamond_should_draw_edge

    min_side = min(cell_w, cell_h)
    inset = diamond_inset_pixels(min_side)
    x0, y0 = x + inset, y + inset
    x1, y1 = x + cell_w - inset, y + cell_h - inset
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0

    c_top = "rgb({},{},{})".format(*_shade_rgb(color, 145))
    c_right = "rgb({},{},{})".format(*_shade_rgb(color, 110))
    c_left = "rgb({},{},{})".format(*_shade_rgb(color, 95))
    c_bottom = "rgb({},{},{})".format(*_shade_rgb(color, 70))

    def poly(pts, fill):
        coords = " ".join(f"{px:.2f},{py:.2f}" for px, py in pts)
        return f"<polygon points='{coords}' fill='{fill}'/>"

    facets = (
        poly([(x0, y0), (x1, y0), (cx, cy)], c_top)
        + poly([(x1, y0), (x1, y1), (cx, cy)], c_right)
        + poly([(x1, y1), (x0, y1), (cx, cy)], c_bottom)
        + poly([(x0, y1), (x0, y0), (cx, cy)], c_left)
    )

    if diamond_should_draw_edge(min_side):
        facets += (
            f"<rect x='{x0:.2f}' y='{y0:.2f}' "
            f"width='{x1 - x0:.2f}' height='{y1 - y0:.2f}' "
            f"fill='none' stroke='rgba(0,0,0,0.4)' stroke-width='0.5'/>"
        )
    return facets


def svg_shape_for_stitch(
    stitch_type: int,
    x: float,
    y: float,
    cell_w: float,
    cell_h: float,
    color: tuple[int, int, int],
    overdraw: float = 0.5,
    as_diamond: bool = False,
) -> str:
    """
    Liefert ein SVG-Snippet (rect oder polygon) fuer einen Stich.

    Args:
        stitch_type: 0 = voll (Rechteck), 1-7 = Polygon
        x, y: linke obere Ecke der Zelle in SVG-Pixeln
        cell_w, cell_h: Zellgroesse
        color: (R, G, B) 0-255
        overdraw: Pixel-Ueberlappung, damit keine Luecken zwischen Zellen sichtbar werden

    Returns:
        SVG-String mit dem entsprechenden Element.
    """
    from ..core.stitch_shapes import (
        bead_radius_factor,
        french_knot_radius_factor,
        is_bead,
        is_diamond,
        is_french_knot,
        is_partial_stitch,
        normalized_partial_stitch_shape,
    )

    fill = f"rgb({color[0]},{color[1]},{color[2]})"

    # DIAMOND-Stitch-Type ODER (FULL-Stitch im DP-Modus): facettierter Drill.
    # Stoff-Background unter dem Drill, damit der Inset sichtbar bleibt.
    if is_diamond(stitch_type) or (as_diamond and stitch_type == 0):
        return (
            f"<rect x='{x:.2f}' y='{y:.2f}' "
            f"width='{cell_w + overdraw:.2f}' height='{cell_h + overdraw:.2f}' "
            f"fill='#ebe8dc'/>" + svg_drill_shape(x, y, cell_w, cell_h, color)
        )

    if is_french_knot(stitch_type):
        # Stoff-Hintergrund + Kreis-Punkt — als SVG-Gruppe damit die Reihenfolge stimmt
        radius = max(0.5, min(cell_w, cell_h) * french_knot_radius_factor())
        cx = x + cell_w / 2.0
        cy = y + cell_h / 2.0
        return (
            f"<rect x='{x:.2f}' y='{y:.2f}' "
            f"width='{cell_w + overdraw:.2f}' height='{cell_h + overdraw:.2f}' "
            f"fill='#fafafa'/>"
            f"<circle cx='{cx:.2f}' cy='{cy:.2f}' r='{radius:.2f}' fill='{fill}'/>"
        )

    if is_bead(stitch_type):
        # Perle: Stoff-Hintergrund + grosse Kugel mit Glanzpunkt fuer 3D-Effekt
        radius = max(1.0, min(cell_w, cell_h) * bead_radius_factor())
        cx = x + cell_w / 2.0
        cy = y + cell_h / 2.0
        h_r = radius / 3.0
        h_cx = cx - radius / 2.5
        h_cy = cy - radius / 2.5
        # Highlight-Farbe: 50% mit Weiss aufgehellt
        hr = min(255, color[0] + (255 - color[0]) // 2)
        hg = min(255, color[1] + (255 - color[1]) // 2)
        hb = min(255, color[2] + (255 - color[2]) // 2)
        return (
            f"<rect x='{x:.2f}' y='{y:.2f}' "
            f"width='{cell_w + overdraw:.2f}' height='{cell_h + overdraw:.2f}' "
            f"fill='#fafafa'/>"
            f"<circle cx='{cx:.2f}' cy='{cy:.2f}' r='{radius:.2f}' fill='{fill}'/>"
            f"<circle cx='{h_cx:.2f}' cy='{h_cy:.2f}' r='{h_r:.2f}' "
            f"fill='rgb({hr},{hg},{hb})' opacity='0.85'/>"
        )

    if not is_partial_stitch(stitch_type):
        return (
            f"<rect x='{x:.2f}' y='{y:.2f}' "
            f"width='{cell_w + overdraw:.2f}' height='{cell_h + overdraw:.2f}' "
            f"fill='{fill}'/>"
        )

    pts = normalized_partial_stitch_shape(stitch_type)
    coords = " ".join(f"{x + nx * cell_w:.2f},{y + ny * cell_h:.2f}" for nx, ny in pts)
    return f"<polygon points='{coords}' fill='{fill}'/>"


def get_watermark(pattern: "Pattern") -> tuple[str, str]:
    """
    Liefert (author, copyright) fuer Export-Footer.

    Reihenfolge der Quellen:
    1. `pattern.metadata['author' / 'copyright']` — pattern-spezifisch
    2. QSettings `default_author` / `default_copyright` — globale Defaults
    3. Leerer String wenn beides fehlt
    """
    author = pattern.metadata.get("author", "") or ""
    copyright_ = pattern.metadata.get("copyright", "") or ""

    if not author or not copyright_:
        try:
            from PySide6.QtCore import QSettings

            settings = QSettings()
            if not author:
                author = settings.value("default_author", "", type=str)
            if not copyright_:
                copyright_ = settings.value("default_copyright", "", type=str)
        except Exception:  # noqa: BLE001 - QSettings darf in Test-Env fehlen
            pass

    return author.strip(), copyright_.strip()


def count_page_colors(
    pattern: "Pattern",
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
) -> dict[int, int]:
    """
    Zaehlt Farb-Indizes auf einem rechteckigen Seitenausschnitt.

    Out-of-bounds-Koordinaten werden uebersprungen. Pro Zelle wird nur das
    oberste sichtbare Layer gezaehlt.
    """
    counts: dict[int, int] = {}
    width = pattern.width
    height = pattern.height
    for y in range(start_y, end_y + 1):
        if y < 0 or y >= height:
            continue
        for x in range(start_x, end_x + 1):
            if x < 0 or x >= width:
                continue
            for layer in reversed(pattern.layer_stack.layers):
                if not layer.visible:
                    continue
                idx = layer.get_stitch(x, y)
                if idx is not None:
                    counts[idx] = counts.get(idx, 0) + 1
                    break
    return counts
