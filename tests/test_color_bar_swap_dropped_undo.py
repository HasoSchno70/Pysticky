# -*- coding: utf-8 -*-
"""
Runde 69: Untersuchung der ColorBar-Drag&Drop-"Umsortierung".

Ergebnis der Untersuchung: `ColorBar`/`ColorSwatch` (ui/widgets/color_bar.py)
implementieren KEIN Umsortieren der Farb-REIHENFOLGE per Drag & Drop. Das
Drag & Drop dort (SWAP_MIME, `ColorSwatch.dragEnterEvent/dropEvent`,
`ColorBar.color_swap_requested`) loest stattdessen
`MainWindow._on_color_swap_dropped()` -> `_swap_color_pair()` aus, was die
STICH-INHALTE zweier Farb-Indizes kreuzweise vertauscht (wie das Menu
"Bearbeiten > Farben tauschen"). `pattern.color_entries` selbst bleibt in
UNVERAENDERTER Reihenfolge -- es gibt daher keine Objekt-Identitaets-Drift
der aktiven Farbe wie kuerzlich in InfoPanel (Runde 68), weil sich die
Position der aktiven Farbe durch diese Operation nie aendert.

Eine echte Farb-Listen-Umsortierung per Drag & Drop existiert nur in
`ColorManagementDialog._on_order_changed()` (separates Dialog-Widget,
ausserhalb des Fokus dieser Runde).

Diese Tests decken die tatsaechliche Funktion ab, die es in ColorBar GIBT:
- Undo/Redo des Drag&Drop-Farbtauschs muss die Stich-Zuordnung als EIN
  atomarer Schritt wiederherstellen (Batch ueber canvas.batch_started/
  batch_ended, siehe MainWindow._swap_color_pair()).
- Grenzfaelle: Tausch an den Listen-Raendern (Index 0 <-> letzter Index),
  ungueltige/gleiche Indizes aus dem Drop-Signal.
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture
def main_window(qtbot):
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    return w


def _pattern_with_colors(n: int):
    from pysticky.core import Pattern, Thread

    pattern = Pattern(name="Test", width=10, height=10)
    pattern.color_entries.clear()
    for i in range(n):
        pattern.add_color(Thread.from_hex(f"Farbe{i}", f"#{i:02x}{i:02x}{i:02x}"))
    return pattern


def test_color_swap_dropped_undo_restores_stitches_in_one_step(main_window):
    """Drag&Drop-Tausch (ColorBar-Signal color_swap_requested) muss per
    einmaligem undo() vollstaendig rueckgaengig zu machen sein -- die
    komplette Operation laeuft ueber canvas.batch_started/batch_ended als
    EIN Undo-Schritt (MainWindow._swap_color_pair())."""
    w = main_window
    pattern = _pattern_with_colors(3)
    pattern.set_stitch(1, 1, 0)
    pattern.set_stitch(2, 2, 0)
    pattern.set_stitch(3, 3, 1)
    w.set_pattern(pattern)

    layer = w.current_pattern.active_layer
    before = {(x, y): layer.get_stitch(x, y) for x in range(10) for y in range(10)}

    undo_count_before = len(w.undo_manager._undo_stack)

    # Simuliert exakt das, was ColorBar.color_swap_requested (per Signal)
    # ausloest, wenn Swatch 0 auf Swatch 1 fallen gelassen wird.
    w._on_color_swap_dropped(0, 1)

    assert layer.get_stitch(1, 1) == 1
    assert layer.get_stitch(2, 2) == 1
    assert layer.get_stitch(3, 3) == 0

    # Genau EIN neuer Undo-Schritt fuer die gesamte Tausch-Operation.
    assert len(w.undo_manager._undo_stack) == undo_count_before + 1

    assert w.undo_manager.undo() is True
    after = {(x, y): layer.get_stitch(x, y) for x in range(10) for y in range(10)}
    assert after == before


def test_color_swap_dropped_boundary_indices_first_and_last(main_window):
    """Tausch zwischen dem ersten und letzten Farbindex (Rand der Liste)
    darf nicht crashen und muss korrekt tauschen."""
    w = main_window
    n = 5
    pattern = _pattern_with_colors(n)
    pattern.set_stitch(0, 0, 0)
    pattern.set_stitch(1, 1, n - 1)
    w.set_pattern(pattern)

    w._on_color_swap_dropped(0, n - 1)

    layer = w.current_pattern.active_layer
    assert layer.get_stitch(0, 0) == n - 1
    assert layer.get_stitch(1, 1) == 0
    # Farb-Reihenfolge selbst bleibt unangetastet (kein Listen-Reorder).
    assert len(w.current_pattern.color_entries) == n


def test_color_swap_dropped_ignores_out_of_range_indices(main_window):
    """Ein Drop-Signal mit veralteten/ungueltigen Indizes (z.B. Farbe
    zwischenzeitlich geloescht) darf keinen IndexError auswerfen."""
    w = main_window
    pattern = _pattern_with_colors(2)
    w.set_pattern(pattern)

    # src aussernhalb des gueltigen Bereichs
    w._on_color_swap_dropped(5, 0)
    # dst ausserhalb des gueltigen Bereichs
    w._on_color_swap_dropped(0, 5)
    # negative Indizes
    w._on_color_swap_dropped(-1, 0)
    # src == dst (auch von ColorSwatch.dropEvent bereits gefiltert)
    w._on_color_swap_dropped(1, 1)

    # Keine Exception, Farbliste unveraendert.
    assert len(w.current_pattern.color_entries) == 2


def test_color_swap_dropped_with_single_color_pattern(main_window):
    """Mit nur einer Farbe existiert nur ein Swatch -- ein Drop-Signal kann
    dafuer gar nicht real entstehen, aber der Handler darf trotzdem nicht
    crashen, falls er (z.B. durch einen Programmfehler) mit src==dst==0
    aufgerufen wird."""
    w = main_window
    pattern = _pattern_with_colors(1)
    w.set_pattern(pattern)

    w._on_color_swap_dropped(0, 0)

    assert len(w.current_pattern.color_entries) == 1


def test_color_swap_dropped_does_not_move_active_selection(main_window):
    """Da die Operation die Farb-REIHENFOLGE nie aendert (nur Stich-Inhalte),
    bleibt die aktuell in der ColorBar ausgewaehlte Farbe (Index + Objekt-
    Identitaet) durch einen Drag&Drop-Tausch zweier ANDERER Farben
    unveraendert."""
    w = main_window
    pattern = _pattern_with_colors(4)
    w.set_pattern(pattern)

    w.color_bar.select_color(2)
    selected_entry = w.color_bar._current_entry
    assert w.color_bar.current_index == 2

    # Tausch zweier Farben, die NICHT die aktuell ausgewaehlte sind.
    w._on_color_swap_dropped(0, 1)
    w.color_bar.refresh()

    assert w.color_bar.current_index == 2
    assert w.color_bar._current_entry is selected_entry
