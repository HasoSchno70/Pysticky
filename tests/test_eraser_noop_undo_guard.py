# -*- coding: utf-8 -*-
"""Regressionstest (Clean-Code-Audit Runde 54, Radierer-Grenzfaelle).

_on_stitch_removed() erzeugte bisher IMMER ein RemoveStitchCommand und
fuehrte es aus (bzw. haengte es an den laufenden Batch an) -- auch wenn die
Zelle schon leer war oder die aktive Ebene gesperrt ist. RemoveStitchCommand
selbst ist intern zwar korrekt gegen beide Faelle abgesichert (kein
Grid-Schreibzugriff, keine Stichzahl-Drift), aber das aendert nichts daran,
dass ein komplett wirkungsloser Eintrag auf dem Undo-Stack landete: ein
Radiergummi-Klick (oder -Zug) ueber bereits leere Zellen liess bei Strg+Z
einen Undo-Schritt "verpuffen", ohne dass sich je etwas sichtbar aenderte.
Gleiche Fehlerklasse wie der Lasso-Klick-ohne-Drag-No-Op aus einer
frueheren Audit-Runde (siehe select_tool.py vs. lasso_select_tool.py).
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def _new_window(qtbot):
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    return w


def test_erasing_already_empty_cell_creates_no_undo_entry(qtbot):
    from pysticky.core import Pattern

    w = _new_window(qtbot)
    pattern = Pattern(name="Leer", width=10, height=10)
    w.set_pattern(pattern)

    layer = w.current_pattern.active_layer
    assert layer.get_stitch(3, 3) is None

    w._on_stitch_removed(3, 3)

    assert w.undo_manager.undo_count == 0
    assert layer.get_stitch(3, 3) is None


def test_erasing_locked_layer_creates_no_undo_entry(qtbot):
    from pysticky.core import Pattern

    w = _new_window(qtbot)
    pattern = Pattern(name="Gesperrt", width=10, height=10)
    pattern.active_layer.set_stitch(3, 3, 0)
    pattern.color_entries[0].stitch_count = 1
    pattern.active_layer.locked = True
    w.set_pattern(pattern)

    w._on_stitch_removed(3, 3)

    assert w.undo_manager.undo_count == 0
    # Stich auf der gesperrten Ebene muss unangetastet bleiben.
    assert w.current_pattern.active_layer.get_stitch(3, 3) == 0
    assert w.current_pattern.color_entries[0].stitch_count == 1


def test_erasing_occupied_unlocked_cell_still_creates_undo_entry(qtbot):
    """Der neue Guard darf den regulaeren Radier-Fall nicht mit-blockieren."""
    from pysticky.core import Pattern

    w = _new_window(qtbot)
    pattern = Pattern(name="Stich", width=10, height=10)
    pattern.active_layer.set_stitch(3, 3, 0)
    pattern.color_entries[0].stitch_count = 1
    w.set_pattern(pattern)

    w._on_stitch_removed(3, 3)

    assert w.undo_manager.undo_count == 1
    assert w.current_pattern.active_layer.get_stitch(3, 3) is None

    w.undo_manager.undo()
    assert w.current_pattern.active_layer.get_stitch(3, 3) == 0
