# -*- coding: utf-8 -*-
"""Regressionstest (2026-07-18): Zeichnen auf einem Muster ohne Farben (0
color_entries) schrieb bisher trotzdem einen Stich mit ungültigem Farbindex
ins Layer-Grid (PlaceStitchCommand.execute() umgeht Pattern.set_stitch()s
eigene Index-Validierung und ruft layer.set_stitch() direkt auf). Der Stich
zählte zur Stichzahl, wurde aber nirgends gerendert -- 'leere Zeichnung'
trotz steigendem Stich-Zähler in der Info-Leiste."""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def test_stitch_placed_with_no_colors_is_rejected(qtbot):
    from pysticky.core import Pattern
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    pattern = Pattern(name="Leer", width=10, height=10)
    pattern.color_entries.clear()
    w.set_pattern(pattern)
    assert len(w.current_pattern.color_entries) == 0

    w._on_stitch_placed(3, 3, 0)

    layer = w.current_pattern.active_layer
    assert layer.get_stitch(3, 3) is None
    assert w.undo_manager.undo_count == 0


def test_stitch_placed_with_valid_color_still_works(qtbot):
    from pysticky.core import Pattern, Thread
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    pattern = Pattern(name="Farbig", width=10, height=10)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    w.set_pattern(pattern)

    w._on_stitch_placed(3, 3, 0)

    layer = w.current_pattern.active_layer
    assert layer.get_stitch(3, 3) == 0
    assert w.undo_manager.undo_count == 1
