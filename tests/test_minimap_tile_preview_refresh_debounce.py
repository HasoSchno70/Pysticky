# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 63): _on_batch_ended() haengte bei JEDEM Aufruf
bedingungslos je einen neuen QTimer.singleShot(100, minimap_panel.refresh)
und QTimer.singleShot(100, tile_preview_panel.refresh) an, ohne jede
Deduplizierung. Bei mehreren schnell aufeinanderfolgenden Batches (z.B. eine
Serie von Undo/Redo-Schritten oder mehrere Fuellungen kurz hintereinander)
stapelten sich dadurch mehrere redundante Refreshes, die alle denselben
(zum Feuerzeitpunkt aktuellen) Zustand neu rendern.

Für ein nahezu maximal grosses Muster (MAX_PATTERN_SIZE = 1000x1000, siehe
core/constants.py) dauert ein einzelner MinimapWidget._rebuild_cache()-Aufruf
messbar >1s (voller Python-Pixel-Loop ueber jeden Stich) -- N redundante
Rebuilds hintereinander summieren sich zu einem mehrsekuendigen UI-Freeze,
obwohl am Ende ohnehin nur das Ergebnis des letzten Rebuilds sichtbar bleibt.

Fix: _on_batch_ended() plant hoechstens einen ausstehenden Refresh pro Panel
(Guard-Flag, das beim Feuern des Timers zurueckgesetzt wird).
"""

import pytest

from pysticky.core import Pattern


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


def test_rapid_batches_coalesce_minimap_and_tile_preview_refresh(main_window, qtbot):
    pattern = Pattern(name="P", width=20, height=20)
    main_window.set_pattern(pattern)

    minimap_calls = []
    tile_calls = []
    main_window.minimap_panel.refresh = lambda: minimap_calls.append(1)
    main_window.tile_preview_panel.refresh = lambda: tile_calls.append(1)

    # Fünf Batches unmittelbar hintereinander, wie bei einer schnellen
    # Undo/Redo-Serie oder mehreren Füllungen kurz nacheinander.
    for _ in range(5):
        main_window.canvas.batch_started.emit("x")
        main_window.canvas.batch_ended.emit()

    # Genug warten, dass alle QTimer.singleShot(100, ...)-Aufrufe feuern.
    qtbot.wait(250)

    assert minimap_calls == [1], (
        f"Minimap-Refresh sollte pro Rapid-Fire-Serie genau einmal feuern, "
        f"nicht {len(minimap_calls)}x"
    )
    assert tile_calls == [1], (
        f"Tile-Preview-Refresh sollte pro Rapid-Fire-Serie genau einmal feuern, "
        f"nicht {len(tile_calls)}x"
    )


def test_batch_ended_still_refreshes_after_previous_refresh_fired(main_window, qtbot):
    """Nach einem abgeschlossenen Refresh-Zyklus muss ein neuer Batch wieder
    einen neuen Refresh anstossen -- die Dedup-Guard darf nicht dauerhaft
    blockieren."""
    pattern = Pattern(name="P", width=20, height=20)
    main_window.set_pattern(pattern)

    minimap_calls = []
    main_window.minimap_panel.refresh = lambda: minimap_calls.append(1)

    main_window.canvas.batch_started.emit("x")
    main_window.canvas.batch_ended.emit()
    qtbot.wait(150)
    assert len(minimap_calls) == 1

    main_window.canvas.batch_started.emit("y")
    main_window.canvas.batch_ended.emit()
    qtbot.wait(150)
    assert len(minimap_calls) == 2
