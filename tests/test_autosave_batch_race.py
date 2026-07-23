# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 47, Autosave-Timing-Audit): Autosave-Timer vs. offene
Undo-Batch.

_execute_command() rief _mark_unsaved() nur im Nicht-Batch-Zweig auf --
waehrend einer offenen Batch (begin_batch()...end_batch(), z.B. ein Drag-
Zeichnen ueber mehrere Maus-Move-Events) wurde die Panel-Benachrichtigung
bewusst aufgeschoben (siehe _pending_batch_scopes-Kommentar), aber
_mark_unsaved() wurde dabei versehentlich GANZ WEGGELASSEN statt nur
aufgeschoben. Jedes Maus-Move-Event ist ein eigener Event-Loop-Durchlauf --
der QTimer fuer Autosave KANN dazwischen feuern (Qt ist single-threaded,
aber eine mehrere Events umspannende Batch ist keine atomare Operation).

War der aktuell offene Drag die ERSTE Aenderung seit dem letzten Speichern/
Laden, blieb _unsaved_changes waehrend der gesamten Batch False, obwohl die
Sub-Commands (add_to_batch() fuehrt sofort aus) ihre Mutationen laengst im
Pattern-Grid haben. _on_autosave() gibt bei _unsaved_changes==False sofort
auf (kein Datei-Schreiben) -- ein Absturz genau in dieser Luecke (z.B. eine
sehr grosse Fuellen/Farbe-ersetzen-Batch) verlor die bereits ausgefuehrten
Aenderungen komplett, ohne dass je eine Autosave-Datei existierte, aus der
serviert werden koennte.
"""

import pytest


@pytest.fixture
def main_window(qtbot):
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    # Siehe testing-gotchas.md: modaler "Aenderungen speichern?"-Dialog beim
    # Teardown sowie der echte periodische Autosave-Timer muessen fuer
    # Tests mit echtem MainWindow() stillgelegt werden.
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    return w


def test_autosave_during_open_batch_captures_already_applied_stitches(main_window, tmp_path):
    """Autosave darf waehrend einer offenen Batch nicht komplett aussetzen,
    wenn die Batch bereits echte Grid-Mutationen ausgefuehrt hat."""
    from pysticky.core.undo import PlaceStitchCommand

    main_window.current_file = tmp_path / "test.pxs"
    assert main_window._unsaved_changes is False

    main_window._on_batch_started("Linie zeichnen")
    cmd = PlaceStitchCommand(main_window.current_pattern, 0, 0, 0, 0)
    main_window._execute_command(cmd, scope="stitch")

    # Der Stich ist bereits im Pattern-Grid (Command.execute() lief sofort
    # innerhalb von add_to_batch()) -- die Batch ist aber noch NICHT beendet.
    layer = main_window.current_pattern.layer_stack[0]
    assert layer.get_stitch(0, 0) == 0
    assert main_window.undo_manager.in_batch is True

    # Kernbehauptung: eine bereits ausgefuehrte Mutation muss den
    # ungespeichert-Zustand sofort markieren, nicht erst bei Batch-Ende.
    assert main_window._unsaved_changes is True, (
        "_mark_unsaved() muss auch waehrend einer offenen Batch beim ersten "
        "add_to_batch()-Aufruf feuern -- sonst verpasst ein zwischenzeitlich "
        "feuernder Autosave-Timer bereits angewendete Grid-Mutationen."
    )

    autosave_path = main_window.current_file.with_suffix(".pxs.autosave")
    main_window._on_autosave()
    assert autosave_path.exists(), (
        "Autosave darf waehrend einer offenen Batch nicht wegen "
        "_unsaved_changes==False komplett aussetzen, obwohl der Stich "
        "bereits im Pattern-Grid liegt."
    )

    from pysticky.core import load_pattern

    recovered = load_pattern(str(autosave_path))
    assert recovered.layer_stack[0].get_stitch(0, 0) == 0

    # Batch sauber abschliessen (Aufraeumen fuer den Test).
    main_window._on_batch_ended()
    assert main_window.undo_manager.in_batch is False


def test_execute_command_without_batch_still_marks_unsaved_immediately(main_window, tmp_path):
    """Regressionsschutz: der normale Nicht-Batch-Pfad darf durch den Fix
    nicht doppelt/anders markieren."""
    from pysticky.core.undo import PlaceStitchCommand

    assert main_window.undo_manager.in_batch is False
    assert main_window._unsaved_changes is False

    cmd = PlaceStitchCommand(main_window.current_pattern, 1, 1, 0, 0)
    main_window._execute_command(cmd, scope="stitch")

    assert main_window._unsaved_changes is True
