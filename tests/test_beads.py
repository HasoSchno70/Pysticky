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
    """MainWindow.add_color_to_pattern setzt is_bead automatisch fuer Mill-Hill-Farben.

    Regression (Test-Qualitaets-Audit): die vorherige Version dieses Tests
    rief add_color_to_pattern() nie tatsaechlich auf, sondern kopierte zwei
    Zeilen der Logik (Palette-Lookup + is_beads-Flag) direkt in den Test und
    pruefte nur diese Kopie. Eine echte Regression in add_color_to_pattern()
    selbst -- z.B. wenn der is_bead=-Kwarg beim add_color()-Aufruf verloren
    ginge -- waere von diesem Test nie bemerkt worden. Jetzt wird die echte
    MainWindow-Methode End-to-End aufgerufen."""
    pytest.importorskip("PySide6")

    from pysticky.core.palette import get_palette_manager
    from pysticky.ui.main_window import MainWindow

    pm = get_palette_manager()
    pm.load_all()

    pearl = pm.get_palette("Mill Hill Beads").find_by_number("02001")
    assert pearl is not None

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    w.current_pattern = empty_pattern

    # pearl ist bereits ein vollstaendiger Thread (aus der Palette geladen)
    index = w.add_color_to_pattern(pearl)

    assert empty_pattern.color_entries[index].is_bead is True


def test_merge_colors_stitches_restamps_moved_cells_to_bead(empty_pattern):
    """Pattern.merge_colors_stitches(): normale Stiche, die in eine Bead-
    Zielfarbe zusammengefuehrt werden, muessen als BEAD-Stitch-Type
    landen -- nicht auf ihrem alten FULL-Typ eingefroren bleiben.

    Regression: Layer.replace_color() (das die alte Merge-Implementierung
    direkt aufrief) kennt nur den Farbindex, nicht is_bead/is_diamond, und
    fasst stitch_type_grid grundsaetzlich nicht an. Ohne Restamping wurde
    eine per "Aehnliche Farben zusammenfuehren" in eine Bead-Farbe
    verschmolzene Zelle weiterhin als Quadrat gerendert und tauchte nicht
    in get_statistics()['bead_count'] auf, obwohl ihre Farbe jetzt is_bead
    ist.
    """
    from pysticky.core import Thread
    from pysticky.core.stitch import StitchType

    pattern = empty_pattern
    normal_idx = pattern.add_color(
        Thread.from_hex("Rot", "#FF0000", manufacturer="DMC", catalog_number="321")
    )
    bead_idx = pattern.add_color(
        Thread.from_hex("Pearl", "#EEEEEE", manufacturer="Mill Hill Beads", catalog_number="02001"),
        is_bead=True,
    )
    pattern.set_stitch(1, 1, normal_idx)

    layer = pattern.layer_stack.active_layer
    assert layer.get_stitch_type(1, 1) == StitchType.FULL.value

    pattern.merge_colors_stitches(normal_idx, bead_idx)

    assert layer.get_stitch(1, 1) == bead_idx
    assert layer.get_stitch_type(1, 1) == StitchType.BEAD.value


def test_merge_colors_stitches_restamps_bead_source_to_full(empty_pattern):
    """Umgekehrter Fall: eine Bead-Farbe wird in eine normale Farbe
    zusammengefuehrt -- die verschobenen Zellen duerfen NICHT auf
    stitch_type=BEAD haengen bleiben (sonst weiterhin als Perle gerendert
    und mitgezaehlt, obwohl die Farbe jetzt eine normale Garnfarbe ist)."""
    from pysticky.core import Thread
    from pysticky.core.stitch import StitchType

    pattern = empty_pattern
    bead_idx = pattern.add_color(
        Thread.from_hex("Pearl", "#EEEEEE", manufacturer="Mill Hill Beads", catalog_number="02001"),
        is_bead=True,
    )
    normal_idx = pattern.add_color(
        Thread.from_hex("Rot", "#FF0000", manufacturer="DMC", catalog_number="321")
    )
    pattern.set_stitch(2, 2, bead_idx)

    layer = pattern.layer_stack.active_layer
    assert layer.get_stitch_type(2, 2) == StitchType.BEAD.value

    pattern.merge_colors_stitches(bead_idx, normal_idx)

    assert layer.get_stitch(2, 2) == normal_idx
    assert layer.get_stitch_type(2, 2) == StitchType.FULL.value


def test_merge_colors_stitches_preserves_half_stitch_for_normal_colors(empty_pattern):
    """Reine Garnfarbe-zu-Garnfarbe-Merges (kein Bead/Diamond beteiligt)
    behalten weiterhin ihre urspruengliche Halbstich-Form (Runde 30) --
    das neue Restamping darf diesen bestehenden Anwendungsfall nicht
    regressieren."""
    from pysticky.core import Thread
    from pysticky.core.stitch import StitchType

    pattern = empty_pattern
    a = pattern.add_color(Thread.from_hex("A", "#FF0000", manufacturer="DMC", catalog_number="321"))
    b = pattern.add_color(Thread.from_hex("B", "#FF0101", manufacturer="DMC", catalog_number="322"))
    pattern.set_stitch(3, 3, a, stitch_type=StitchType.HALF_TL_BR.value)

    pattern.merge_colors_stitches(a, b)

    layer = pattern.layer_stack.active_layer
    assert layer.get_stitch(3, 3) == b
    assert layer.get_stitch_type(3, 3) == StitchType.HALF_TL_BR.value


def test_similar_colors_dialog_merge_restamps_bead_target(qtbot, empty_pattern):
    """End-to-End ueber SimilarColorsDialog._on_merge(): eine Farbe wird in
    eine Bead-Zielfarbe zusammengefuehrt -- der verschmolzene Stich muss
    danach als BEAD gerendert/gezaehlt werden."""
    from pysticky.core import Thread
    from pysticky.core.stitch import StitchType
    from pysticky.ui.color_utils import to_qcolor
    from pysticky.ui.dialogs.similar_colors_dialog import SimilarColorsDialog, _ColorPairRow

    pattern = empty_pattern
    pattern.color_entries.clear()
    bead_idx = pattern.add_color(
        Thread.from_hex("Pearl", "#EEEEEE", manufacturer="Mill Hill Beads", catalog_number="02001"),
        is_bead=True,
    )
    normal_idx = pattern.add_color(
        Thread.from_hex("Fast-Pearl", "#EFEFEF", manufacturer="DMC", catalog_number="B5200")
    )
    pattern.set_stitch(4, 4, normal_idx)

    dialog = SimilarColorsDialog(pattern)
    qtbot.addWidget(dialog)

    entry_bead = pattern.color_entries[bead_idx]
    entry_normal = pattern.color_entries[normal_idx]
    row = _ColorPairRow(
        bead_idx,
        normal_idx,
        entry_bead.thread.name,
        entry_normal.thread.name,
        to_qcolor(entry_bead.thread.color),
        to_qcolor(entry_normal.thread.color),
        distance=1.0,
    )
    row.checkbox.setChecked(True)
    dialog._pair_rows = [row]

    from PySide6.QtWidgets import QMessageBox

    qtbot_monkeypatch_question = QMessageBox.question
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    try:
        dialog._on_merge()
    finally:
        QMessageBox.question = qtbot_monkeypatch_question

    assert len(pattern.color_entries) == 1
    layer = pattern.layer_stack.active_layer
    assert layer.get_stitch(4, 4) == 0  # bead_idx nach Entfernen von normal_idx
    assert layer.get_stitch_type(4, 4) == StitchType.BEAD.value
