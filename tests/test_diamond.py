# -*- coding: utf-8 -*-
"""Tests fuer Diamond-Painting-Support (DP-Paletten, DIAMOND-Stitch-Type,
Auto-Mapping, Roundtrip durch .pxs)."""

import json

import pytest

# ---------------------------------------------------------------------------
# Paletten-Erkennung
# ---------------------------------------------------------------------------


def test_dmc_diamond_painting_palette_loads_and_is_marked_as_diamond():
    """Die mitgelieferte DMC-DP-Palette wird als is_diamond=True erkannt."""
    from pysticky.core.palette import get_palette_manager

    pm = get_palette_manager()
    pm.load_all()

    dp = pm.get_palette("DMC Diamond Painting")
    assert dp is not None
    assert dp.is_diamond is True
    assert dp.is_beads is False  # Diamond und Bead schliessen sich aus
    assert len(dp.threads) > 0


def test_dac_skeleton_palette_loads_and_is_marked_as_diamond():
    """Skelett-Palette fuer Diamond Art Club wird ebenfalls erkannt."""
    from pysticky.core.palette import get_palette_manager

    pm = get_palette_manager()
    pm.load_all()

    dac = pm.get_palette("Diamond Art Club Diamond Painting")
    assert dac is not None
    assert dac.is_diamond is True
    # Stichprobe: DAC-001 (Pure White) ist drin
    assert dac.find_by_number("DAC-001") is not None


def test_diamond_dotz_skeleton_palette_loads_and_is_marked_as_diamond():
    """Skelett-Palette fuer Diamond Dotz wird ebenfalls erkannt."""
    from pysticky.core.palette import get_palette_manager

    pm = get_palette_manager()
    pm.load_all()

    dd = pm.get_palette("Diamond Dotz Diamond Painting")
    assert dd is not None
    assert dd.is_diamond is True
    assert dd.find_by_number("DD-001") is not None


def test_regular_palettes_are_not_marked_as_diamond():
    """Garn-/Bead-Paletten sind NICHT als Diamond markiert."""
    from pysticky.core.palette import get_palette_manager

    pm = get_palette_manager()
    pm.load_all()

    for name in ["DMC", "Anchor", "Madeira", "Mill Hill Beads"]:
        palette = pm.get_palette(name)
        if palette is not None:
            assert palette.is_diamond is False, f"{name} faelschlich als Diamond markiert"


# ---------------------------------------------------------------------------
# ColorEntry + Pattern.set_stitch
# ---------------------------------------------------------------------------


def test_color_entry_has_is_diamond_field(empty_pattern):
    """ColorEntry hat is_diamond-Feld mit Default False."""
    from pysticky.core import Thread

    pattern = empty_pattern
    idx = pattern.add_color(
        Thread.from_hex("Red", "#FF0000", manufacturer="DMC", catalog_number="321")
    )
    entry = pattern.color_entries[idx]
    assert entry.is_diamond is False


def test_add_color_with_is_diamond_flag(empty_pattern):
    """add_color akzeptiert is_diamond=True."""
    from pysticky.core import Thread

    pattern = empty_pattern
    idx = pattern.add_color(
        Thread.from_hex(
            "Dusty Rose",
            "#AB0249",
            manufacturer="DMC Diamond Painting",
            catalog_number="150",
        ),
        is_diamond=True,
    )
    entry = pattern.color_entries[idx]
    assert entry.is_diamond is True


def test_set_stitch_on_diamond_color_uses_diamond_stitch_type(empty_pattern):
    """Wenn eine DP-Farbe gesetzt wird, ist der Stitch-Type automatisch DIAMOND."""
    from pysticky.core import Thread
    from pysticky.core.stitch import StitchType

    pattern = empty_pattern
    dp_idx = pattern.add_color(
        Thread.from_hex(
            "Dusty Rose",
            "#AB0249",
            manufacturer="DMC Diamond Painting",
            catalog_number="150",
        ),
        is_diamond=True,
    )
    pattern.set_stitch(2, 3, dp_idx)  # KEIN expliziter stitch_type
    layer = pattern.layer_stack.active_layer
    assert layer.stitch_type_grid[3, 2] == StitchType.DIAMOND.value


def test_diamond_and_bead_are_mutually_exclusive(empty_pattern):
    """Eine Farbe kann nicht gleichzeitig Bead UND Diamond sein —
    die Auto-Mapping-Logik bevorzugt Bead (entspricht dem Code-Pfad)."""
    from pysticky.core import Thread
    from pysticky.core.stitch import StitchType

    pattern = empty_pattern
    # Sollte in der Praxis nie auftreten (Paletten-Erkennung schliesst es
    # aus), aber wenn jemand manuell beide setzt: Bead gewinnt.
    idx = pattern.add_color(
        Thread.from_hex("X", "#888888"),
        is_bead=True,
        is_diamond=True,
    )
    pattern.set_stitch(0, 0, idx)
    layer = pattern.layer_stack.active_layer
    assert layer.stitch_type_grid[0, 0] == StitchType.BEAD.value


# ---------------------------------------------------------------------------
# Stitch-Type-Transformationen
# ---------------------------------------------------------------------------


def test_diamond_is_invariant_under_flip_and_rotate():
    """DIAMOND-Stitches sind rotations-/spiegel-invariant (wie BEAD)."""
    from pysticky.core.stitch import (
        FLIP_H_MAP,
        FLIP_V_MAP,
        ROTATE_CCW_MAP,
        ROTATE_CW_MAP,
        StitchType,
    )

    d = StitchType.DIAMOND.value
    assert FLIP_H_MAP[d] == d
    assert FLIP_V_MAP[d] == d
    assert ROTATE_CW_MAP[d] == d
    assert ROTATE_CCW_MAP[d] == d


# ---------------------------------------------------------------------------
# .pxs-Roundtrip
# ---------------------------------------------------------------------------


def test_is_diamond_survives_pxs_roundtrip(tmp_path):
    """is_diamond + DIAMOND-Stitch-Type ueberlebt save/load."""
    from pysticky.core import Pattern, Thread
    from pysticky.core.file_io import load_pattern, save_pattern
    from pysticky.core.stitch import StitchType

    pattern = Pattern(name="DP", width=5, height=5)
    pattern.color_entries.clear()
    idx = pattern.add_color(
        Thread.from_hex(
            "Dusty Rose",
            "#AB0249",
            manufacturer="DMC Diamond Painting",
            catalog_number="150",
        ),
        is_diamond=True,
    )
    pattern.set_stitch(2, 2, idx)

    path = tmp_path / "dp.pxs"
    save_pattern(pattern, str(path))

    loaded = load_pattern(str(path))
    assert loaded.color_entries[idx].is_diamond is True
    layer = loaded.layer_stack.active_layer
    assert layer.stitch_type_grid[2, 2] == StitchType.DIAMOND.value


# ---------------------------------------------------------------------------
# stitch_shapes Helper
# ---------------------------------------------------------------------------


def test_stitch_shapes_is_diamond_helper():
    """is_diamond(stitch_type)-Helper liefert True nur fuer DIAMOND."""
    from pysticky.core.stitch import StitchType
    from pysticky.core.stitch_shapes import is_diamond

    assert is_diamond(StitchType.DIAMOND.value) is True
    assert is_diamond(StitchType.FULL.value) is False
    assert is_diamond(StitchType.BEAD.value) is False


def test_diamond_inset_factor_is_sensible():
    """Inset-Faktor liegt im erwarteten Bereich (kein Drill bedeckt die ganze Zelle)."""
    from pysticky.core.stitch_shapes import diamond_inset_factor

    factor = diamond_inset_factor()
    assert 0.0 < factor < 0.25  # Mehr als 25% Inset waere zu klein


# ---------------------------------------------------------------------------
# Canvas Diamond-View-Property
# ---------------------------------------------------------------------------


def test_canvas_diamond_view_default_off(qtbot):
    """Canvas startet mit diamond_view=False."""
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    assert canvas.diamond_view is False


def test_canvas_diamond_view_toggle_triggers_update(qtbot, pattern_with_stitches):
    """diamond_view-Property aendert State und triggert kein Crash beim Repaint."""
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(pattern_with_stitches)
    canvas.resize(400, 300)

    canvas.diamond_view = True
    assert canvas.diamond_view is True
    canvas.repaint()  # darf nicht crashen

    canvas.diamond_view = False
    assert canvas.diamond_view is False
    canvas.repaint()


def test_canvas_renders_diamond_stitch_type_without_crash(qtbot, empty_pattern):
    """Pattern mit DIAMOND-Stiches rendert sauber — Drill-Pfad wird durchlaufen."""
    from pysticky.core import Thread
    from pysticky.ui.canvas import CrossStitchCanvas

    pattern = empty_pattern
    idx = pattern.add_color(
        Thread.from_hex(
            "Dusty Rose",
            "#AB0249",
            manufacturer="DMC Diamond Painting",
            catalog_number="150",
        ),
        is_diamond=True,
    )
    pattern.set_stitch(2, 3, idx)  # wird als DIAMOND platziert (auto)

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(pattern)
    canvas.resize(400, 300)
    canvas.repaint()  # Drill-Renderer wird aufgerufen


# ---------------------------------------------------------------------------
# Pattern.mode
# ---------------------------------------------------------------------------


def test_pattern_mode_defaults_to_stitch(empty_pattern):
    """Neue Patterns sind standardmaessig im Stick-Modus."""
    assert empty_pattern.mode == "stitch"


def test_pattern_mode_persists_through_pxs_roundtrip(tmp_path, empty_pattern):
    """Pattern.mode='diamond' ueberlebt save/load."""
    from pysticky.core.file_io import load_pattern, save_pattern

    empty_pattern.mode = "diamond"
    path = tmp_path / "dp.pxs"
    save_pattern(empty_pattern, str(path))
    loaded = load_pattern(str(path))
    assert loaded.mode == "diamond"


def test_pattern_mode_invalid_value_falls_back_to_stitch(tmp_path, empty_pattern):
    """Beim Laden wird ein unbekannter Mode auf 'stitch' gemappt."""
    from pysticky.core.file_io import load_pattern, save_pattern

    path = tmp_path / "broken.pxs"
    save_pattern(empty_pattern, str(path))
    # Mode auf Junk-Wert manipulieren
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["mode"] = "ufo"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    loaded = load_pattern(str(path))
    assert loaded.mode == "stitch"


def test_old_pxs_files_without_mode_field_default_to_stitch(tmp_path, empty_pattern):
    """Aeltere .pxs-Dateien (vor v1.5) ohne mode-Feld werden als 'stitch' geladen."""
    from pysticky.core.file_io import load_pattern, save_pattern

    path = tmp_path / "old.pxs"
    save_pattern(empty_pattern, str(path))
    # mode-Feld aus den Daten entfernen (simuliert alte Datei)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["pattern"].pop("mode", None)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    loaded = load_pattern(str(path))
    assert loaded.mode == "stitch"


# ---------------------------------------------------------------------------
# InfoPanel mode-spezifische Labels
# ---------------------------------------------------------------------------


def test_info_panel_default_mode_is_stitch(qtbot):
    """InfoPanel startet im Stick-Modus mit Stoff-Auswahl."""
    from pysticky.ui.panels.info_panel import InfoPanel

    panel = InfoPanel()
    qtbot.addWidget(panel)
    assert panel._mode == "stitch"
    # Combo-Inhalt: Aida-Eintraege
    assert "Aida" in panel.combo_fabric.itemText(0)


def test_info_panel_diamond_mode_swaps_labels(qtbot):
    """set_mode('diamond') ersetzt Labels und Combo-Inhalt."""
    from pysticky.ui.panels.info_panel import InfoPanel

    panel = InfoPanel()
    qtbot.addWidget(panel)
    panel.set_mode("diamond")

    assert panel._mode == "diamond"
    # Stat-Card-Label umgestellt
    assert panel.card_stitches._label == "Drills"
    assert panel.card_time._label == "Klebezeit"
    assert panel.card_thread._label == "Drill-Bedarf"
    # Combo zeigt Drill-Groessen
    assert "Square" in panel.combo_fabric.itemText(0) or "mm" in panel.combo_fabric.itemText(0)


def test_info_panel_back_to_stitch_restores_labels(qtbot):
    """set_mode('stitch') stellt die Stick-Labels wieder her."""
    from pysticky.ui.panels.info_panel import InfoPanel

    panel = InfoPanel()
    qtbot.addWidget(panel)
    panel.set_mode("diamond")
    panel.set_mode("stitch")

    assert panel.card_stitches._label == "Stiche"
    assert panel.card_time._label == "Stickzeit"
    assert panel.card_thread._label == "Garnbedarf"


def test_info_panel_diamond_time_is_faster_than_stitch(qtbot):
    """Klebezeit < Stickzeit fuer gleiche Stueckzahl."""
    from pysticky.ui.panels.info_panel import InfoPanel

    panel = InfoPanel()
    qtbot.addWidget(panel)

    panel.set_mode("stitch")
    stitch_time = panel._calculate_stitch_time(1000)

    panel.set_mode("diamond")
    diamond_time = panel._calculate_stitch_time(1000)

    # Heuristik: 1000 Stiche * 20s = 333 min vs. 1000 Drills * 3s = 50 min
    assert "5" in stitch_time  # ~5 Stunden
    assert "5" in diamond_time and "h" not in diamond_time  # ~50 Min


def test_info_panel_unknown_mode_is_ignored(qtbot):
    """set_mode('foo') aendert nichts."""
    from pysticky.ui.panels.info_panel import InfoPanel

    panel = InfoPanel()
    qtbot.addWidget(panel)
    panel.set_mode("foo")
    assert panel._mode == "stitch"


# ---------------------------------------------------------------------------
# ColorBar + InfoPanel-Mode
# ---------------------------------------------------------------------------


def test_color_bar_set_mode_propagates_to_swatches(qtbot, pattern_with_colors):
    """ColorBar.set_mode setzt den Modus auf alle bestehenden Swatches."""
    from pysticky.ui.widgets.color_bar import ColorBar

    bar = ColorBar()
    qtbot.addWidget(bar)
    bar.set_pattern(pattern_with_colors)
    bar.set_mode("diamond")
    assert all(s._mode == "diamond" for s in bar._swatches)
    bar.set_mode("stitch")
    assert all(s._mode == "stitch" for s in bar._swatches)


def test_color_bar_unknown_mode_is_ignored(qtbot, pattern_with_colors):
    from pysticky.ui.widgets.color_bar import ColorBar

    bar = ColorBar()
    qtbot.addWidget(bar)
    bar.set_pattern(pattern_with_colors)
    bar.set_mode("invalid")
    assert bar._mode == "stitch"


def test_info_panel_color_item_hides_symbol_in_diamond_mode(qtbot, pattern_with_colors):
    """Im DP-Modus wird die Symbol-Spalte in der Farbuebersicht versteckt."""
    from pysticky.ui.panels.info_panel import InfoPanel

    panel = InfoPanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.set_mode("diamond")
    panel.update_info(pattern_with_colors)
    # Mindestens ein _ColorListItem sollte da sein
    from pysticky.ui.panels.info_panel import _ColorListItem

    items = [it for it in panel._color_items if isinstance(it, _ColorListItem)]
    assert len(items) > 0
    for it in items:
        assert it._mode == "diamond"
        assert it.lbl_symbol.isHidden() is True


def test_palette_panel_dropdown_uses_icon_prefix(qtbot):
    """Combo-Items haben Typ-Icons im Anzeigetext, userData=reiner Name."""
    from pysticky.ui.panels.palette_panel import PalettePanel

    panel = PalettePanel()
    qtbot.addWidget(panel)
    combo = panel.combo_palette
    # Mindestens je ein Garn- und ein DP-Eintrag
    texts = [combo.itemText(i) for i in range(combo.count())]
    datas = [combo.itemData(i) for i in range(combo.count())]
    assert any(t.startswith("🧵") for t in texts), "Garn-Praefix fehlt"
    assert any(t.startswith("💎") for t in texts), "Diamond-Praefix fehlt"
    # userData enthaelt KEINEN Icon-Prefix
    assert any(d == "DMC" for d in datas)
    assert any(d == "DMC Diamond Painting" for d in datas)


def test_palette_panel_find_palette_index_works_with_icon_text(qtbot):
    """_find_palette_index sucht ueber userData, nicht ueber Text."""
    from pysticky.ui.panels.palette_panel import PalettePanel

    panel = PalettePanel()
    qtbot.addWidget(panel)
    idx = panel._find_palette_index("DMC Diamond Painting")
    assert idx >= 0
    panel.combo_palette.setCurrentIndex(idx)
    assert panel.current_palette_name() == "DMC Diamond Painting"


def test_palette_panel_set_mode_switches_header_label(qtbot):
    """set_mode aendert Header-Label und Icon."""
    from pysticky.ui.panels.palette_panel import PalettePanel

    panel = PalettePanel()
    qtbot.addWidget(panel)
    panel.set_mode("diamond")
    assert panel.palette_icon.text() == "💎"
    assert "DIAMOND" in panel.palette_label.text()
    panel.set_mode("stitch")
    assert panel.palette_icon.text() == "🎨"
    assert "GARN" in panel.palette_label.text()


# ---------------------------------------------------------------------------
# Pattern.convert_to_mode
# ---------------------------------------------------------------------------


def test_convert_to_mode_remaps_to_dmc_dp(empty_pattern):
    """Stick-Farben werden auf nächstgelegene DMC-DP-Codes gemappt."""
    from pysticky.core import Thread

    pattern = empty_pattern
    pattern.color_entries.clear()
    pattern.add_color(
        Thread.from_hex(
            "White",
            "#FFFFFF",
            manufacturer="Anchor",
            catalog_number="1",
        )
    )

    changed = pattern.convert_to_mode("diamond")

    assert changed is True
    assert pattern.mode == "diamond"
    entry = pattern.color_entries[0]
    assert entry.thread.manufacturer == "DMC Diamond Painting"
    assert entry.thread.catalog_number is not None
    assert entry.is_diamond is True


def test_convert_to_mode_back_to_stitch_uses_backup(empty_pattern):
    """Stick→Diamond→Stick stellt die Original-Anchor-Codes wieder her.

    Ohne Backup würde Diamond→Stick via DMC-Default eine Drift produzieren
    (Anchor White → DMC-DP 3865 → DMC 3865, nicht zurück zu Anchor 1).
    """
    from pysticky.core import Thread

    pattern = empty_pattern
    pattern.color_entries.clear()
    pattern.add_color(
        Thread.from_hex(
            "White",
            "#FFFFFF",
            manufacturer="Anchor",
            catalog_number="1",
        )
    )

    pattern.convert_to_mode("diamond")
    pattern.convert_to_mode("stitch")

    entry = pattern.color_entries[0]
    assert entry.thread.manufacturer == "Anchor"
    assert entry.thread.catalog_number == "1"
    assert entry.is_diamond is False
    assert pattern.mode == "stitch"


def test_convert_to_mode_roundtrip_preserves_diamond_codes(empty_pattern):
    """Diamond→Stick→Diamond findet dieselben DP-Codes wieder (kein Drift)."""
    from pysticky.core import Thread

    pattern = empty_pattern
    pattern.color_entries.clear()
    pattern.add_color(
        Thread.from_hex(
            "Red",
            "#FF0000",
            manufacturer="Anchor",
            catalog_number="47",
        )
    )

    pattern.convert_to_mode("diamond")
    first_dp_code = pattern.color_entries[0].thread.catalog_number
    pattern.convert_to_mode("stitch")
    pattern.convert_to_mode("diamond")
    second_dp_code = pattern.color_entries[0].thread.catalog_number

    assert first_dp_code == second_dp_code


def test_convert_to_mode_skips_beads(empty_pattern):
    """Bead-Farben werden bei der Modus-Konvertierung NICHT angefasst."""
    from pysticky.core import Thread

    pattern = empty_pattern
    pattern.color_entries.clear()
    pattern.add_color(
        Thread.from_hex(
            "Pearl",
            "#EEEEEE",
            manufacturer="Mill Hill Beads",
            catalog_number="02001",
        ),
        is_bead=True,
    )
    pattern.add_color(
        Thread.from_hex(
            "Red",
            "#FF0000",
            manufacturer="Anchor",
            catalog_number="47",
        )
    )

    pattern.convert_to_mode("diamond")

    # Bead bleibt unveraendert
    assert pattern.color_entries[0].thread.manufacturer == "Mill Hill Beads"
    assert pattern.color_entries[0].is_bead is True
    # Stick-Farbe wurde konvertiert
    assert pattern.color_entries[1].thread.manufacturer == "DMC Diamond Painting"


def test_convert_to_mode_noop_when_already_target(empty_pattern):
    """convert_to_mode mit selbem Modus ist ein No-Op (returns False)."""
    pattern = empty_pattern
    assert pattern.mode == "stitch"
    assert pattern.convert_to_mode("stitch") is False


def test_convert_to_mode_empty_pattern_just_flips_mode(empty_pattern):
    """Bei leerem Pattern wird nur der Mode-String gesetzt, kein Mapping."""
    pattern = empty_pattern
    pattern.color_entries.clear()
    result = pattern.convert_to_mode("diamond")
    # Pattern.mode wurde gesetzt
    assert pattern.mode == "diamond"
    # `changed=True` weil sich der Mode geaendert hat (selbst wenn keine
    # Farben da waren, ist es ein Wechsel).
    assert result is True


def test_convert_to_mode_persists_backup_through_pxs(tmp_path, empty_pattern):
    """Mode-Backups landen in pattern.metadata und ueberleben .pxs-Roundtrip."""
    from pysticky.core import Thread
    from pysticky.core.file_io import load_pattern, save_pattern

    pattern = empty_pattern
    pattern.color_entries.clear()
    pattern.add_color(
        Thread.from_hex(
            "White",
            "#FFFFFF",
            manufacturer="Anchor",
            catalog_number="1",
        )
    )
    pattern.convert_to_mode("diamond")

    # Backup fuer stitch-Modus liegt in metadata
    assert "mode_backups" in pattern.metadata
    assert "stitch" in pattern.metadata["mode_backups"]

    path = tmp_path / "dp.pxs"
    save_pattern(pattern, str(path))
    loaded = load_pattern(str(path))

    # Roundtrip: Backup ist da, Rueckweg funktioniert
    loaded.convert_to_mode("stitch")
    assert loaded.color_entries[0].thread.manufacturer == "Anchor"
    assert loaded.color_entries[0].thread.catalog_number == "1"


# ---------------------------------------------------------------------------
# Export-Terminologie + Inhalt
# ---------------------------------------------------------------------------


def test_terms_for_returns_diamond_set_when_pattern_is_diamond(empty_pattern):
    """``terms_for`` liefert das DP-Terms-Dict fuer ein DP-Pattern."""
    from pysticky.io.export_common import terms_for

    empty_pattern.mode = "diamond"
    terms = terms_for(empty_pattern)
    assert terms["unit_plural"] == "Drills"
    assert terms["time_label"] == "Klebezeit"
    assert terms["supply_label"] == "Drill-Bedarf"


def test_terms_for_falls_back_to_stitch(empty_pattern):
    """Default-Pattern liefert das Stick-Terms-Dict."""
    from pysticky.io.export_common import terms_for

    terms = terms_for(empty_pattern)
    assert terms["unit_plural"] == "Stiche"
    assert terms["time_label"] == "Stickzeit"


def test_fabric_label_for_returns_drill_pitch_in_dp(empty_pattern):
    """fabric_label_for liefert mm-Angabe im DP-Modus."""
    from pysticky.io.export_common import fabric_label_for

    empty_pattern.mode = "diamond"
    empty_pattern.fabric_count = 10
    assert "2.5 mm" in fabric_label_for(empty_pattern)


def test_html_export_diamond_pattern_uses_drill_terminology(tmp_path, pattern_with_stitches):
    """HTML-Export eines DP-Patterns enthaelt 'Drills', nicht 'Stiche'."""
    from pysticky.io.html_export import HTMLExporter

    pattern_with_stitches.mode = "diamond"
    output = tmp_path / "out.html"
    exporter = HTMLExporter(pattern_with_stitches)
    exporter.export(str(output))

    html = output.read_text(encoding="utf-8")
    assert "Drills" in html
    assert "DIAMOND-PAINTING-VORLAGE" in html
    assert "Drill-Legende" in html
    # Standard-Stickzeit-Begriffe sollten NICHT vorkommen
    assert "Garn-Legende" not in html


def test_html_export_stick_pattern_keeps_stitch_terminology(tmp_path, pattern_with_stitches):
    """Regression: Stick-Pattern aenderten sich nicht durch DP-Features."""
    from pysticky.io.html_export import HTMLExporter

    output = tmp_path / "stick.html"
    HTMLExporter(pattern_with_stitches).export(str(output))

    html = output.read_text(encoding="utf-8")
    assert "Stiche" in html
    assert "KREUZSTICH-MUSTER" in html
    assert "Stoffempfehlung" in html
    assert "DIAMOND-PAINTING-VORLAGE" not in html


def test_svg_drill_shape_emits_four_facets():
    """svg_drill_shape rendert vier Facetten + Kantenrand."""
    from pysticky.io.export_common import svg_drill_shape

    svg = svg_drill_shape(0, 0, 20, 20, (200, 50, 50))
    # Vier <polygon>-Elemente fuer die Facetten
    assert svg.count("<polygon") == 4
    # Ein Rect mit stroke fuer den Kantenrand
    assert "stroke" in svg


def test_shade_rgb_lighten_and_darken():
    """_shade_rgb: factor>100 hellt auf, factor<100 dunkelt ab."""
    from pysticky.io.export_common import _shade_rgb

    base = (100, 100, 100)
    lighter = _shade_rgb(base, 150)
    darker = _shade_rgb(base, 50)
    assert all(l > b for l, b in zip(lighter, base))
    assert all(d < b for d, b in zip(darker, base))
    # Identitaet bei 100
    assert _shade_rgb(base, 100) == base


def test_svg_shape_for_stitch_renders_drill_when_as_diamond(empty_pattern):
    """as_diamond=True macht FULL-Stiche zu Drill-Polygonen."""
    from pysticky.io.export_common import svg_shape_for_stitch

    # Stitch-Type 0 (FULL) — als Drill rendern
    svg = svg_shape_for_stitch(0, 0, 0, 20, 20, (200, 50, 50), as_diamond=True)
    assert "<polygon" in svg
    # Background-Rect fuer den Klebegrund
    assert "#ebe8dc" in svg


def test_svg_shape_for_stitch_diamond_type_always_renders_drill():
    """StitchType.DIAMOND (11) wird immer als Drill gerendert, auch ohne as_diamond."""
    from pysticky.io.export_common import svg_shape_for_stitch

    svg = svg_shape_for_stitch(11, 0, 0, 20, 20, (200, 50, 50), as_diamond=False)
    assert "<polygon" in svg


def test_svg_shape_for_stitch_stick_mode_keeps_rect(empty_pattern):
    """Stick-Modus (as_diamond=False, stype=FULL) bleibt einfache Rechteck-Fuellung."""
    from pysticky.io.export_common import svg_shape_for_stitch

    svg = svg_shape_for_stitch(0, 0, 0, 20, 20, (200, 50, 50), as_diamond=False)
    assert "<rect" in svg
    # KEIN Drill-Polygon
    assert "<polygon" not in svg


def test_html_export_diamond_pattern_renders_drills_in_svg(tmp_path, pattern_with_stitches):
    """HTML-Vorschau enthaelt mehrere <polygon>-Drills im DP-Modus."""
    from pysticky.io.html_export import HTMLExporter

    pattern_with_stitches.mode = "diamond"
    output = tmp_path / "drill.html"
    HTMLExporter(pattern_with_stitches).export(str(output))
    html = output.read_text(encoding="utf-8")

    # Pro Stich vier Polygone -> bei einem Pattern mit vielen Stichen gibt's
    # mehrere Hundert Polygone in der Cover-/Preview-Vorschau.
    assert html.count("<polygon") > 20


# ---------------------------------------------------------------------------
# Preview-Render-Engine im DP-Modus
# ---------------------------------------------------------------------------


def test_preview_engine_renders_diamond_pattern_without_crash(qtbot, empty_pattern):
    """PreviewRenderEngine rendert ein DP-Pattern (FULL-Stiche -> Drill-Pfad)."""
    from pysticky.core import Thread
    from pysticky.ui.rendering import PreviewRenderEngine

    pattern = empty_pattern
    pattern.mode = "diamond"
    pattern.color_entries.clear()
    pattern.add_color(
        Thread.from_hex(
            "Red", "#FF0000", manufacturer="DMC Diamond Painting", catalog_number="321"
        ),
        is_diamond=True,
    )
    pattern.set_stitch(2, 2, 0)  # wird als DIAMOND-Type platziert (auto)
    pattern.set_stitch(3, 3, 0)

    engine = PreviewRenderEngine(pattern)
    img = engine.render(cell_size=12)
    assert not img.isNull()


def test_preview_engine_renders_stick_pattern_keeps_cross_stitch(qtbot, pattern_with_stitches):
    """Stick-Pattern bleibt mit Kreuzstich-Renderer (Regression-Schutz)."""
    from pysticky.ui.rendering import PreviewRenderEngine

    assert pattern_with_stitches.mode == "stitch"
    engine = PreviewRenderEngine(pattern_with_stitches)
    img = engine.render(cell_size=12)
    assert not img.isNull()


# ---------------------------------------------------------------------------
# Drill-Nummern an show_symbols
# ---------------------------------------------------------------------------


def test_drill_labels_tied_to_show_symbols(qtbot, empty_pattern):
    """Im DP-Modus wird das Drill-Label nur gezeichnet wenn show_symbols=True ist."""
    from pysticky.core import Thread
    from pysticky.ui.canvas import CrossStitchCanvas

    pattern = empty_pattern
    pattern.add_color(
        Thread.from_hex(
            "Red",
            "#FF0000",
            manufacturer="DMC Diamond Painting",
            catalog_number="321",
        ),
        is_diamond=True,
    )
    pattern.set_stitch(2, 2, 0)

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(pattern)
    canvas.diamond_view = True
    canvas.resize(800, 600)

    # show_symbols=False -> Drill-Labels sollten NICHT gezeichnet werden
    canvas._show_symbols = False
    canvas.repaint()
    # show_symbols=True -> Drill-Labels werden gezeichnet
    canvas._show_symbols = True
    canvas.repaint()
    # Beide Pfade laufen ohne Crash durch (eigentliche Pixel-Pruefung ist
    # zu fragil — wir verlassen uns auf die Render-Logik in _draw_layer_cells).


# ---------------------------------------------------------------------------
# PatternPreviewDialog DP-aware
# ---------------------------------------------------------------------------


def test_preview_dialog_dp_mode_hides_fabric_controls(qtbot, pattern_with_stitches):
    """Im DP-Modus sind Stoff-, Farb-, Rueckstiche-, Fortschritts-Controls weg."""
    from pysticky.ui.dialogs.pattern_preview_dialog import PatternPreviewDialog

    pattern_with_stitches.mode = "diamond"
    dialog = PatternPreviewDialog(pattern_with_stitches)
    qtbot.addWidget(dialog)
    dialog.show()

    # Stoff- und Farb-Combo + Rueckstiche/Fortschritt versteckt
    assert dialog._fabric_combo.isHidden() is True
    assert dialog._color_combo.isHidden() is True
    assert dialog._cb_backstitches.isHidden() is True
    assert dialog._cb_completion.isHidden() is True
    # Modus-Combo hat nur 2 Eintraege (Drill + Pixel)
    assert dialog._mode_combo.count() == 2
    # Titel enthaelt "Vorlagen-Vorschau"
    assert "Vorlagen" in dialog.windowTitle()


def test_preview_dialog_stick_mode_shows_fabric_controls(qtbot, pattern_with_stitches):
    """Regression: Stick-Modus zeigt weiterhin alle Controls."""
    from pysticky.ui.dialogs.pattern_preview_dialog import PatternPreviewDialog

    assert pattern_with_stitches.mode == "stitch"
    dialog = PatternPreviewDialog(pattern_with_stitches)
    qtbot.addWidget(dialog)
    dialog.show()

    assert dialog._fabric_combo.isHidden() is False
    assert dialog._cb_backstitches.isHidden() is False
    # 3 Modi: Stoff / Pixel / Symbol
    assert dialog._mode_combo.count() == 3
    assert "Muster-Vorschau" in dialog.windowTitle()


def test_preview_dialog_dp_info_bar_shows_drills(qtbot, pattern_with_stitches):
    """Info-Bar zeigt 'Drills' statt 'Stiche' im DP-Modus."""
    from pysticky.ui.dialogs.pattern_preview_dialog import PatternPreviewDialog

    pattern_with_stitches.mode = "diamond"
    dialog = PatternPreviewDialog(pattern_with_stitches)
    qtbot.addWidget(dialog)

    assert "Drills" in dialog._label_stitches.text()


# ---------------------------------------------------------------------------
# Adaptive Drill-Inset
# ---------------------------------------------------------------------------


def test_diamond_inset_pixels_zero_for_small_cells():
    """Bei kleinen Zellgroessen (<12px) ist der Inset 0 — Drills beruehren sich."""
    from pysticky.core.stitch_shapes import diamond_inset_pixels

    assert diamond_inset_pixels(2) == 0.0
    assert diamond_inset_pixels(8) == 0.0
    assert diamond_inset_pixels(11) == 0.0
    # Ab 12 -> sichtbarer Inset
    assert diamond_inset_pixels(12) > 0
    assert diamond_inset_pixels(20) > 1.0


def test_diamond_edge_only_for_larger_cells():
    """Edge-Rand nur bei cell_size >= 14 (sonst frisst er die Hauptfarbe)."""
    from pysticky.core.stitch_shapes import diamond_should_draw_edge

    assert diamond_should_draw_edge(8) is False
    assert diamond_should_draw_edge(13) is False
    assert diamond_should_draw_edge(14) is True


def test_svg_drill_shape_no_gap_at_small_cells():
    """SVG-Drill rendert bei kleiner Zelle ohne Rand-Gap.

    Das war die Ursache der ausgewaschen-weissen DP-Vorschauen: ein
    konstanter 1px-Inset liess die Drills isoliert wirken.
    """
    from pysticky.io.export_common import svg_drill_shape

    svg = svg_drill_shape(0, 0, 4, 4, (200, 50, 50))
    # Bei size=4 sollte das erste Polygon bei (0,0) starten — kein Inset.
    assert "0.00,0.00" in svg
    # KEIN Kantenrand-Rect bei kleiner Zelle
    assert "stroke='rgba(0,0,0,0.4)" not in svg


def test_svg_drill_shape_has_edge_at_large_cells():
    """Bei groesserer Zelle (>=14) wird der Kantenrand gerendert."""
    from pysticky.io.export_common import svg_drill_shape

    svg = svg_drill_shape(0, 0, 20, 20, (200, 50, 50))
    # Bei size=20 ist der Inset >0, Polygon startet nicht mehr exakt bei (0,0).
    assert "0.00,0.00" not in svg
    # Kantenrand vorhanden
    assert "stroke='rgba(0,0,0,0.4)" in svg


# ---------------------------------------------------------------------------
# 1:1-Druck-Massstab im DP-Export
# ---------------------------------------------------------------------------


def test_drill_pitch_mm_mapping(empty_pattern):
    """drill_pitch_mm liefert die fabric_count-mm-Mapping-Werte."""
    from pysticky.io.export_common import drill_pitch_mm

    empty_pattern.mode = "diamond"
    empty_pattern.fabric_count = 10
    assert drill_pitch_mm(empty_pattern) == 2.5
    empty_pattern.fabric_count = 9
    assert drill_pitch_mm(empty_pattern) == 2.8
    empty_pattern.fabric_count = 8
    assert drill_pitch_mm(empty_pattern) == 3.0
    # Fallback fuer unbekannten Count
    empty_pattern.fabric_count = 14
    assert drill_pitch_mm(empty_pattern) == 2.5


def test_pdf_exporter_dp_mode_uses_drill_pitch(empty_pattern):
    """PDFExporter berechnet STITCHES_PER_PAGE und Cell-Size dynamisch im DP."""
    pytest.importorskip("reportlab")
    from pysticky.io.pdf_export import PDFExporter

    empty_pattern.mode = "diamond"
    empty_pattern.fabric_count = 10

    exp = PDFExporter(empty_pattern)
    # Cell-Size ist exakt 2.5mm in reportlab-Pt (1mm ≈ 2.835pt)
    assert exp._dp_cell_size is not None
    assert abs(exp._dp_cell_size - 2.5 * 2.83464567) < 0.001
    # Mehr Drills pro Seite als die Standard-40 (bei 2.5mm passt mehr rein)
    assert exp.STITCHES_PER_PAGE_X > 40


def test_pdf_exporter_stick_mode_keeps_default_pages(empty_pattern):
    """Regression: Stick-Modus benutzt weiterhin die festen 40-Drills-Vorgaben."""
    pytest.importorskip("reportlab")
    from pysticky.io.pdf_export import PDFExporter

    assert empty_pattern.mode == "stitch"
    exp = PDFExporter(empty_pattern)
    assert exp._dp_cell_size is None
    assert exp.STITCHES_PER_PAGE_X == 40
    assert exp.STITCHES_PER_PAGE_Y == 40


def test_html_exporter_dp_mode_emits_mm_print_css(tmp_path, pattern_with_stitches):
    """HTML-Export im DP-Modus enthaelt @media print mit mm-Cell-Sizes."""
    from pysticky.io.html_export import HTMLExporter

    pattern_with_stitches.mode = "diamond"
    pattern_with_stitches.fabric_count = 10
    out = tmp_path / "dp.html"
    HTMLExporter(pattern_with_stitches).export(out)
    html = out.read_text(encoding="utf-8")
    assert "width: 2.5mm !important" in html
    assert "height: 2.5mm !important" in html


def test_html_exporter_stick_mode_no_mm_print_css(tmp_path, pattern_with_stitches):
    """Regression: Stick-Pattern hat kein mm-Print-CSS."""
    from pysticky.io.html_export import HTMLExporter

    assert pattern_with_stitches.mode == "stitch"
    out = tmp_path / "stick.html"
    HTMLExporter(pattern_with_stitches).export(out)
    html = out.read_text(encoding="utf-8")
    assert "2.5mm !important" not in html


# ---------------------------------------------------------------------------
# Papier-Format-Empfehlung fuer DP-1:1-Druck
# ---------------------------------------------------------------------------


def test_recommend_paper_format_small_dp_fits_a4(empty_pattern):
    """Kleines 50x50-Drill-Pattern bei 2.5mm passt in A4."""
    from pysticky.io.export_common import recommend_paper_format_for_dp

    empty_pattern.width = 50
    empty_pattern.height = 50
    empty_pattern.mode = "diamond"
    empty_pattern.fabric_count = 10
    assert recommend_paper_format_for_dp(empty_pattern) == "A4"


def test_recommend_paper_format_medium_dp_fits_a2(empty_pattern):
    """200x200 Drills (50x50 cm bei 2.5mm) wird auf A2 empfohlen."""
    from pysticky.io.export_common import recommend_paper_format_for_dp

    empty_pattern.width = 200
    empty_pattern.height = 200
    empty_pattern.mode = "diamond"
    empty_pattern.fabric_count = 10
    assert recommend_paper_format_for_dp(empty_pattern) == "A2"


def test_recommend_paper_format_large_dp_picks_a0(empty_pattern):
    """Sehr grosses 400x400-Pattern (100x100 cm) faellt auf A0 (groesstes)."""
    from pysticky.io.export_common import recommend_paper_format_for_dp

    empty_pattern.width = 400
    empty_pattern.height = 400
    empty_pattern.mode = "diamond"
    empty_pattern.fabric_count = 10
    assert recommend_paper_format_for_dp(empty_pattern) == "A0"


def test_recommend_paper_format_stick_mode_returns_a4(empty_pattern):
    """Stick-Pattern: keine DP-spezifische Empfehlung, Default A4."""
    from pysticky.io.export_common import recommend_paper_format_for_dp

    assert empty_pattern.mode == "stitch"
    assert recommend_paper_format_for_dp(empty_pattern) == "A4"


def test_pdf_exporter_supports_a1_and_a0():
    """PAGE_FORMATS enthaelt jetzt A1 und A0 fuer grosse DP-Vorlagen."""
    pytest.importorskip("reportlab")
    from pysticky.io.pdf_export import PDFExporter

    assert "A1" in PDFExporter.PAGE_FORMATS
    assert "A0" in PDFExporter.PAGE_FORMATS


# ---------------------------------------------------------------------------
# DP-Cells im Export farbig statt Symbol-Text
# ---------------------------------------------------------------------------


def test_html_export_dp_pages_use_colored_cells(tmp_path, empty_pattern):
    """Im DP-Modus haben die Page-Cells eine Hintergrundfarbe (kein Symbol-Text).

    Das ist der Kern: Bei DP ist die ausgedruckte Vorlage die Klebefolie
    selbst — der User muss die Drill-Farbe direkt erkennen koennen, nicht
    erst eine Symbol-Legende abgleichen.
    """
    from pysticky.core import Thread
    from pysticky.io.html_export import HTMLExporter

    p = empty_pattern
    p.mode = "diamond"
    p.fabric_count = 10
    p.color_entries.clear()
    p.add_color(
        Thread.from_hex("Red", "#FF0000", manufacturer="DMC DP", catalog_number="321"),
        is_diamond=True,
    )
    p.set_stitch(0, 0, 0)
    p.set_stitch(5, 5, 0)

    out = tmp_path / "dp.html"
    HTMLExporter(p).export(out)
    html = out.read_text(encoding="utf-8")
    # Pattern-Page enthaelt cells mit `background:rgb(...)` Style
    assert "background:rgb(255,0,0)" in html


def test_html_export_stick_pages_still_use_symbols(tmp_path, pattern_with_stitches):
    """Regression: Stick-Pattern haben weiterhin Symbol-Text-Cells."""
    from pysticky.io.html_export import HTMLExporter

    assert pattern_with_stitches.mode == "stitch"
    out = tmp_path / "stick.html"
    HTMLExporter(pattern_with_stitches).export(out)
    html = out.read_text(encoding="utf-8")
    # Pattern-Cells haben KEINE Drill-Background-Farben.
    # (Die Cover-Vorschau hat Farben — wir suchen explizit nach
    # background:rgb innerhalb von <td> der grid-table.)
    import re

    td_with_bg = re.findall(r"<td[^>]*style='background:rgb\(", html)
    assert len(td_with_bg) == 0, "Stick-Pages sollten keine farbigen Cells haben"


def test_html_export_dp_mini_legend_uses_codes_not_symbols(tmp_path, empty_pattern):
    """Im DP-Modus zeigt die Mini-Legende den Drill-Code (fett), KEIN Symbol."""
    from pysticky.core import Thread
    from pysticky.io.html_export import HTMLExporter

    p = empty_pattern
    p.mode = "diamond"
    p.fabric_count = 10
    p.color_entries.clear()
    p.add_color(
        Thread.from_hex("Red", "#FF0000", manufacturer="DMC DP", catalog_number="321"),
        is_diamond=True,
    )
    for y in range(20):
        for x in range(20):
            p.set_stitch(x, y, 0)

    out = tmp_path / "dp.html"
    HTMLExporter(p).export(out)
    html = out.read_text(encoding="utf-8")
    # Code prominent in <b>-Tag
    assert "<b>321</b>" in html
    # KEIN Symbol=Code-Pattern (z.B. "●=321" oder "■=321")
    # Wir checken konservativ: das alte Format "{symbol}={code}" fehlt.
    import re

    # Suche nach "X=321" wo X kein <b ist (also Symbol-Pattern aus dem Stick-Modus)
    matches = re.findall(r"[●■▲▼◆]=321", html)
    assert len(matches) == 0


def test_html_export_dp_legend_code_column_no_overlap(tmp_path, empty_pattern):
    """Im DP zeigt die Legenden-Code-Spalte NUR den Drill-Code, nicht den
    vollen Manufacturer-Namen — sonst ueberlappt der Text mit der Name-Spalte.
    """
    from pysticky.core import Thread
    from pysticky.io.html_export import HTMLExporter

    p = empty_pattern
    p.mode = "diamond"
    p.fabric_count = 10
    p.color_entries.clear()
    p.add_color(
        Thread.from_hex(
            "Pewter light",
            "#888888",
            manufacturer="DMC Diamond Painting",
            catalog_number="169",
        ),
        is_diamond=True,
    )
    p.set_stitch(0, 0, 0)

    out = tmp_path / "dp.html"
    HTMLExporter(p).export(out)
    html = out.read_text(encoding="utf-8")
    # Garn-Label in der Hauptlegende sollte NICHT den langen Manufacturer-String
    # enthalten — sonst sprengt er die Spalte und ueberlappt den Farbnamen.
    # In der Hauptlegende-Zeile (<td><b>...</b></td>) suchen wir nach
    # "<b>DMC Diamond Painting 169</b>" — sollte nicht da sein.
    assert "<b>DMC Diamond Painting 169</b>" not in html
    # Stattdessen: nur der Code als fetter Eintrag
    assert "<b>169</b>" in html


def test_new_project_dialog_dp_preset_sets_size_and_mode(qtbot):
    """Auswahl eines DP-Presets im New-Pattern-Dialog setzt Groesse + DP-Flag."""
    from pysticky.ui.dialogs.new_project_dialog import NewProjectDialog

    dlg = NewProjectDialog()
    qtbot.addWidget(dlg)

    # Default: keine DP-Auswahl
    s0 = dlg.get_settings()
    assert s0["dp_mode"] is False

    # "DP A2 (150×150)" → Index 6
    dlg._dp_preset_combo.setCurrentIndex(6)
    s1 = dlg.get_settings()
    assert s1["width"] == 150
    assert s1["height"] == 150
    assert s1["dp_mode"] is True

    # "DP A1 quer (280×200)" → Index 9
    dlg._dp_preset_combo.setCurrentIndex(9)
    s2 = dlg.get_settings()
    assert s2["width"] == 280
    assert s2["height"] == 200
    assert s2["dp_mode"] is True

    # Zurueck auf "Keine Auswahl"
    dlg._dp_preset_combo.setCurrentIndex(0)
    s3 = dlg.get_settings()
    assert s3["dp_mode"] is False


def test_image_import_dp_palette_sets_pattern_mode(tmp_path):
    """Bild-Import mit DP-Palette laesst Pattern direkt im Diamond-Modus landen."""
    pytest.importorskip("PIL")
    import numpy as np
    from PIL import Image

    from pysticky.core.image_import import ImportSettings, import_image

    img_path = tmp_path / "test.png"
    img = Image.fromarray(np.random.randint(0, 255, (40, 40, 3), dtype=np.uint8))
    img.save(img_path)

    s = ImportSettings(
        width=40,
        height=40,
        max_colors=10,
        palette_name="DMC Diamond Painting",
    )
    p = import_image(img_path, s)

    assert p.mode == "diamond"
    assert p.fabric_count == 10  # Standard-Drill-Pitch 2.5mm
    assert len(p.color_entries) > 0
    assert all(e.is_diamond for e in p.color_entries)


def test_image_import_stick_palette_keeps_stitch_mode(tmp_path):
    """Bild-Import mit Garn-Palette bleibt im Stick-Modus (Regression)."""
    pytest.importorskip("PIL")
    import numpy as np
    from PIL import Image

    from pysticky.core.image_import import ImportSettings, import_image

    img_path = tmp_path / "test.png"
    img = Image.fromarray(np.random.randint(0, 255, (40, 40, 3), dtype=np.uint8))
    img.save(img_path)

    s = ImportSettings(width=40, height=40, max_colors=10, palette_name="DMC")
    p = import_image(img_path, s)

    assert p.mode == "stitch"
    assert p.fabric_count == 14  # Aida-Standard
    assert len(p.color_entries) > 0
    assert all(not e.is_diamond for e in p.color_entries)


def test_image_import_dp_presets_in_builtin_list():
    """BUILTIN_PRESETS enthaelt jetzt DP-Varianten mit palette + dp_mode."""
    from pysticky.ui.dialogs.image_import_presets import BUILTIN_PRESETS

    dp_presets = [p for p in BUILTIN_PRESETS if p.get("dp_mode")]
    assert len(dp_presets) >= 5  # mindestens A4-A0
    for p in dp_presets:
        assert p.get("palette") == "DMC Diamond Painting"
        assert "DP" in p["name"]


def test_canvas_diamond_view_renders_full_stitches_as_drills(qtbot, pattern_with_stitches):
    """Im Diamond-View werden auch FULL-Stiche durch den Drill-Pfad gerendert.

    Smoke-Test: das Pattern enthaelt nur FULL-Stiche; mit diamond_view=True
    laeuft der Diamond-Render-Pfad und darf nicht crashen.
    """
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(pattern_with_stitches)
    canvas.resize(400, 300)
    canvas.diamond_view = True
    canvas.repaint()
