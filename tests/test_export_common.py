# -*- coding: utf-8 -*-
"""
Tests fuer die gemeinsamen Export-Helfer (io/export_common.py).

Verifiziert "oberstes sichtbares Layer gewinnt"-Logik, Out-of-bounds-
Behandlung und Symbol-Lookup.
"""

from pysticky.io.export_common import (
    count_page_colors,
    get_pixel_color,
    get_pixel_symbol,
    get_watermark,
)


def test_get_pixel_color_returns_none_for_empty_cell(pattern_with_colors):
    assert get_pixel_color(pattern_with_colors, 0, 0) is None


def test_get_pixel_color_returns_rgb_tuple(pattern_with_stitches):
    color = get_pixel_color(pattern_with_stitches, 5, 5)  # schwarzer Rand
    assert color == (0, 0, 0)

    color = get_pixel_color(pattern_with_stitches, 10, 10)  # rote Fuellung
    assert color == (255, 0, 0)


def test_get_pixel_symbol_empty_cell_returns_empty_string(pattern_with_colors):
    assert get_pixel_symbol(pattern_with_colors, 0, 0) == ""


def test_get_pixel_symbol_returns_entrys_symbol(pattern_with_stitches):
    entry = pattern_with_stitches.get_color_entry(0)
    assert get_pixel_symbol(pattern_with_stitches, 5, 5) == entry.symbol


def test_top_visible_layer_wins(pattern_with_colors):
    """Ein zweiter Layer mit Stitch oberhalb ueberlaeuft den unteren."""
    p = pattern_with_colors
    p.set_stitch(3, 3, 1)  # Layer 0: weiss

    p.layer_stack.add_layer("Layer2")
    p.layer_stack.active_index = 1
    p.set_stitch(3, 3, 2)  # Layer 1: rot, oben

    assert get_pixel_color(p, 3, 3) == (255, 0, 0)


def test_invisible_top_layer_falls_through(pattern_with_colors):
    """Ein unsichtbares oberes Layer wird uebersprungen."""
    p = pattern_with_colors
    p.set_stitch(4, 4, 1)  # Layer 0: weiss

    p.layer_stack.add_layer("Hidden")
    p.layer_stack.active_index = 1
    p.set_stitch(4, 4, 2)  # Layer 1: rot, oben
    p.layer_stack.layers[1].visible = False

    assert get_pixel_color(p, 4, 4) == (255, 255, 255)


def test_count_page_colors_counts_each_cell_once(pattern_with_stitches):
    """Zellen mit Stitch auf mehreren Layern werden nur einmal gezaehlt."""
    p = pattern_with_stitches
    counts = count_page_colors(p, 0, 0, p.width - 1, p.height - 1)

    # Rechteck-Rand: 10+10+8+8 = 36 schwarze Stiche (idx 0)
    # Fuellung 8x8 = 64 rote Stiche (idx 2)
    assert counts.get(0) == 36
    assert counts.get(2) == 64


def test_count_page_colors_clamps_out_of_bounds(pattern_with_stitches):
    """Negative oder grosse Koordinaten kraschen nicht und werden ignoriert."""
    p = pattern_with_stitches
    counts_clipped = count_page_colors(p, -5, -5, p.width + 5, p.height + 5)
    counts_full = count_page_colors(p, 0, 0, p.width - 1, p.height - 1)
    assert counts_clipped == counts_full


def test_count_page_colors_subregion(pattern_with_stitches):
    """Subregion zaehlt nur Stiche im Ausschnitt."""
    p = pattern_with_stitches
    counts = count_page_colors(p, 6, 6, 8, 8)  # 3x3 innerhalb der Fuellung
    assert counts == {2: 9}


def test_watermark_returns_pattern_metadata(empty_pattern):
    """Pattern-Metadaten haben Vorrang vor Settings-Defaults."""
    empty_pattern.metadata["author"] = "Anna"
    empty_pattern.metadata["copyright"] = "(c) 2026 Anna"
    author, copyright_ = get_watermark(empty_pattern)
    assert author == "Anna"
    assert copyright_ == "(c) 2026 Anna"


def test_watermark_empty_when_no_metadata_no_settings(empty_pattern, qtbot):
    """Ohne Metadata und ohne Settings-Defaults liefert die Funktion leere Strings.

    Regression (Test-Qualitaets-Audit): die vorherige Version pruefte nur
    `isinstance(..., str)` -- das waere selbst dann wahr gewesen, wenn
    get_watermark() "None", einen Platzhalter oder sonst irgendeinen String
    statt der dokumentierten leeren Strings zurueckgegeben haette. Um das
    ohne Kopplung an zufaellig vorhandene QSettings-Reste testen zu koennen,
    werden die Settings-Defaults hier explizit auf leer gesetzt.
    """
    from PySide6.QtCore import QCoreApplication, QSettings

    app = QCoreApplication.instance()
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    s = QSettings()
    old_author = s.value("default_author", "", type=str)
    old_copyright = s.value("default_copyright", "", type=str)
    s.setValue("default_author", "")
    s.setValue("default_copyright", "")
    s.sync()
    try:
        author, copyright_ = get_watermark(empty_pattern)
        assert author == ""
        assert copyright_ == ""
    finally:
        s.setValue("default_author", old_author)
        s.setValue("default_copyright", old_copyright)
        s.sync()


def test_watermark_strips_whitespace(empty_pattern):
    empty_pattern.metadata["author"] = "  Anna  "
    empty_pattern.metadata["copyright"] = "  © 2026  "
    author, copyright_ = get_watermark(empty_pattern)
    assert author == "Anna"
    assert copyright_ == "© 2026"
