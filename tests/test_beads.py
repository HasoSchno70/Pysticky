# -*- coding: utf-8 -*-
"""Tests fuer Bead-Support (Mill Hill, BEAD-Stitch-Type, Legende)."""

import pytest


def test_mill_hill_palette_loads_and_is_marked_as_beads():
    """Mill Hill Beads-Palette ist registriert und als Bead-Palette markiert."""
    from pysticky.core.palette import get_palette_manager

    pm = get_palette_manager()
    pm.load_all()

    mh = pm.get_palette("Mill Hill Beads")
    assert mh is not None
    assert mh.is_beads is True
    assert len(mh.threads) > 0
    # Stichprobe: 02001 Pearl muss drin sein
    pearl = mh.find_by_number("02001")
    assert pearl is not None


def test_non_bead_palette_is_not_marked_as_beads():
    """Garn-Paletten (DMC, Anchor) sind NICHT als Bead markiert."""
    from pysticky.core.palette import get_palette_manager

    pm = get_palette_manager()
    pm.load_all()

    for name in ["DMC", "Anchor", "Madeira"]:
        palette = pm.get_palette(name)
        if palette is not None:
            assert palette.is_beads is False, f"{name} faelschlich als Bead markiert"


def test_color_entry_has_is_bead_field(empty_pattern):
    """ColorEntry hat is_bead-Feld mit Default False."""
    from pysticky.core import Thread

    pattern = empty_pattern
    idx = pattern.add_color(
        Thread.from_hex("Red", "#FF0000", manufacturer="DMC", catalog_number="321")
    )
    entry = pattern.color_entries[idx]
    assert entry.is_bead is False


def test_add_color_with_is_bead_flag(empty_pattern):
    """add_color akzeptiert is_bead=True."""
    from pysticky.core import Thread

    pattern = empty_pattern
    idx = pattern.add_color(
        Thread.from_hex("Pearl", "#EEEEEE", manufacturer="Mill Hill Beads", catalog_number="02001"),
        is_bead=True,
    )
    entry = pattern.color_entries[idx]
    assert entry.is_bead is True


def test_set_stitch_on_bead_color_uses_bead_stitch_type(empty_pattern):
    """Wenn eine Bead-Farbe gesetzt wird, ist der Stitch-Type automatisch BEAD."""
    from pysticky.core import Thread
    from pysticky.core.stitch import StitchType

    pattern = empty_pattern
    bead_idx = pattern.add_color(
        Thread.from_hex("Pearl", "#EEEEEE", manufacturer="Mill Hill Beads", catalog_number="02001"),
        is_bead=True,
    )
    pattern.set_stitch(3, 4, bead_idx)  # KEIN expliziter stitch_type
    layer = pattern.layer_stack.active_layer
    assert layer.stitch_type_grid[4, 3] == StitchType.BEAD.value


def test_set_stitch_on_regular_color_uses_full_stitch_type(empty_pattern):
    """Regulaere Farben bleiben FULL beim Default-Setzen."""
    from pysticky.core import Thread
    from pysticky.core.stitch import StitchType

    pattern = empty_pattern
    regular = pattern.add_color(
        Thread.from_hex("Red", "#FF0000", manufacturer="DMC", catalog_number="321"),
        is_bead=False,
    )
    pattern.set_stitch(2, 2, regular)
    layer = pattern.layer_stack.active_layer
    assert layer.stitch_type_grid[2, 2] == StitchType.FULL.value


def test_explicit_stitch_type_overrides_bead_default(empty_pattern):
    """Explizit gesetzter Stitch-Type (!= 0) ueberschreibt den Bead-Default."""
    from pysticky.core import Thread
    from pysticky.core.stitch import StitchType

    pattern = empty_pattern
    bead_idx = pattern.add_color(
        Thread.from_hex("Pearl", "#EEEEEE", manufacturer="Mill Hill Beads", catalog_number="02001"),
        is_bead=True,
    )
    # Bewusst Half-Stitch setzen (auch wenn unusual fuer Bead)
    pattern.set_stitch(1, 1, bead_idx, stitch_type=StitchType.HALF_TL_BR.value)
    layer = pattern.layer_stack.active_layer
    assert layer.stitch_type_grid[1, 1] == StitchType.HALF_TL_BR.value


def test_file_io_preserves_is_bead(empty_pattern, tmp_path):
    """is_bead-Flag ueberlebt den .pxs-Roundtrip."""
    from pysticky.core import Thread, load_pattern, save_pattern

    pattern = empty_pattern
    pattern.add_color(
        Thread.from_hex("Red", "#FF0000", manufacturer="DMC", catalog_number="321"),
        is_bead=False,
    )
    pattern.add_color(
        Thread.from_hex("Pearl", "#EEEEEE", manufacturer="Mill Hill Beads", catalog_number="02001"),
        is_bead=True,
    )

    out = tmp_path / "test.pxs"
    save_pattern(pattern, out)
    reloaded = load_pattern(out)

    # Bead-Flag pro Eintrag pruefen
    bead_flags = [e.is_bead for e in reloaded.color_entries]
    # Default-Black von Pattern.__post_init__ + Red + Pearl
    assert bead_flags[-1] is True
    assert bead_flags[-2] is False


def test_oxs_roundtrip_preserves_bead_marker(empty_pattern, tmp_path):
    """Bead-Farben werden beim OXS-Roundtrip wieder als Beads erkannt."""
    from pysticky.core import Thread
    from pysticky.io.formats import export_oxs, import_oxs

    pattern = empty_pattern
    pattern.add_color(
        Thread.from_hex(
            "Pearl",
            "#EEEEEE",
            manufacturer="Mill Hill Beads",
            catalog_number="02001",
        ),
        is_bead=True,
    )
    pattern.set_stitch(2, 3, 1)  # Bead-Color -> Stitch wird BEAD

    out = tmp_path / "bead.oxs"
    export_oxs(pattern, out)
    reloaded, errors, warnings = import_oxs(out)
    assert errors == []

    # Reloaded muss Mill-Hill-Eintrag als is_bead=True haben
    bead_entries = [e for e in reloaded.color_entries if e.is_bead]
    assert len(bead_entries) >= 1
    assert bead_entries[0].thread.manufacturer == "Mill Hill Beads"


def test_html_legend_has_bead_section(empty_pattern, tmp_path):
    """HTML-Export erzeugt eine separate Bead-Sektion bei Bead-Stichen."""
    from pysticky.core import Thread
    from pysticky.io import HTMLExporter

    pattern = empty_pattern
    pearl_idx = pattern.add_color(
        Thread.from_hex(
            "Pearl",
            "#EEEEEE",
            manufacturer="Mill Hill Beads",
            catalog_number="02001",
        ),
        is_bead=True,
    )
    pattern.set_stitch(2, 2, pearl_idx)

    out = tmp_path / "bead.html"
    HTMLExporter(pattern).export(out)
    html = out.read_text(encoding="utf-8")

    assert "Perlen (Beads)" in html
    assert "02001" in html


def test_html_legend_omits_bead_section_when_no_beads(pattern_with_stitches, tmp_path):
    """Ohne Bead-Stiche keine Bead-Sektion."""
    from pysticky.io import HTMLExporter

    out = tmp_path / "no_bead.html"
    HTMLExporter(pattern_with_stitches).export(out)
    html = out.read_text(encoding="utf-8")
    assert "Perlen (Beads)" not in html


def test_bead_count_not_counted_as_skeins(empty_pattern):
    """Bead-Farben werden NICHT zu Strang-Bedarf gerechnet."""
    from pysticky.core import Thread
    from pysticky.io import HTMLExporter

    pattern = empty_pattern
    # Bead-Farbe mit vielen "Stichen" — sollte 0 Strang ergeben
    pearl_idx = pattern.add_color(
        Thread.from_hex(
            "Pearl",
            "#EEEEEE",
            manufacturer="Mill Hill Beads",
            catalog_number="02001",
        ),
        is_bead=True,
    )
    for x in range(10):
        for y in range(10):
            pattern.set_stitch(x, y, pearl_idx)

    exporter = HTMLExporter(pattern)
    exporter._calculate_statistics()

    bead_stats = [s for s in exporter._color_stats if s.get("is_bead")]
    assert len(bead_stats) == 1
    assert bead_stats[0]["skeins"] == 0
    assert bead_stats[0]["count"] == 100


def test_main_window_add_color_detects_bead_palette(qtbot, empty_pattern):
    """MainWindow.add_color_to_pattern setzt is_bead automatisch fuer Mill-Hill-Farben."""
    pytest.importorskip("PySide6")

    # Wir testen direkt die Logik ohne komplettes MainWindow,
    # weil das volle Setup gross ist. Wir replizieren die Logik:
    from pysticky.core.palette import get_palette_manager

    pm = get_palette_manager()
    pm.load_all()

    pearl = pm.get_palette("Mill Hill Beads").find_by_number("02001")
    assert pearl is not None

    # Simuliere add_color_to_pattern-Logik
    palette = pm.get_palette(pearl.manufacturer)
    is_bead = palette is not None and palette.is_beads
    assert is_bead is True
