# -*- coding: utf-8 -*-
"""Regressionstest: große Undo-Batches dürfen die UI nicht einfrieren.

_execute_command rief früher pro Stich _notify_panels("stitch") auf, das die
komplette Muster-Statistik neu berechnet — bei 40.000 Stichen quadratischer
Aufwand und minutenlanger Freeze ("Keine Rückmeldung"). Panel-Updates werden
seitdem während eines Batches gesammelt und am Ende einmal ausgeführt.
"""

import time

import pytest

from pysticky.core import Pattern, Thread


@pytest.fixture
def main_window(qtbot):
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    # Verhindert den modalen "Änderungen speichern?"-Dialog im Teardown
    w._check_save_changes = lambda: True
    return w


def test_large_batch_replace_is_fast(main_window):
    pattern = Pattern(name="Perf", width=200, height=200)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.add_color(Thread.from_hex("Blau", "#0000FF"))
    for y in range(200):
        for x in range(200):
            pattern.set_stitch(x, y, 0)
    main_window.set_pattern(pattern)

    changes = [(x, y, 1) for x, y, ci in pattern.iterate_composite_stitches() if ci == 0]
    assert len(changes) == 40_000

    start = time.perf_counter()
    main_window.canvas.batch_started.emit("Farbe ersetzen")
    for x, y, ci in changes:
        main_window.canvas.stitch_placed.emit(x, y, ci)
    main_window.canvas.batch_ended.emit()
    elapsed = time.perf_counter() - start

    # Lokal ~0.25s; großzügige Schranke gegen CI-Schwankungen. Vor dem Fix
    # lag der Wert im Minutenbereich.
    assert elapsed < 15.0, f"Batch-Ersetzen zu langsam: {elapsed:.1f}s"

    # Ergebnis + ein einziger Undo-Schritt
    assert pattern.color_entries[1].stitch_count == 40_000
    assert main_window.undo_manager.undo()
    assert pattern.color_entries[0].stitch_count == 40_000
