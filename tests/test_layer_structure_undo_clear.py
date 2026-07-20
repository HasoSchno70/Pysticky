# -*- coding: utf-8 -*-
"""
Regressionstests: Ebene hinzufuegen/entfernen/duplizieren/verschieben/
vereinen aenderte frueher die Layer-Indizes im Stack, ohne den Undo-Stack
zu leeren. Bereits ausgefuehrte Commands (PlaceStitchCommand etc.) halten
einen fest eingebrannten `layer_index` -- ein spaeteres Undo/Redo haette
entweder mit IndexError gecrasht (Ebene entfernt/vereint -> Stack kuerzer)
oder lautlos die falsche Ebene mutiert (Ebene hinzugefuegt/verschoben).

Fix: `LayerPanel.layer_structure_changed`-Signal (separat von
`layers_changed`, das auch fuer harmlose Property-Aenderungen wie
Deckkraft/Notiz feuert) -> MainWindow._on_layer_structure_changed() leert
den Undo-Stack, analog zu misc_handlers.py::_on_flatten_layers.
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
    # Siehe test_save_error_handling.py::main_window fuer die Begruendung.
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    # Ein headless konstruiertes MainWindow durchlaeuft _perform_start_action()
    # (Welcome-Screen-Dismiss etc.) nicht wie im echten App-Start -- Layer-
    # Panel explizit an das aktuelle Pattern binden, sonst no-opt
    # _on_add_layer()/_on_remove_layer() sonst still (oder _on_remove_layer
    # zeigt eine echte, ungemockte Warnung -- Test-Hang-Risiko).
    w.layer_panel.set_layer_stack(w.current_pattern.layer_stack)
    return w


def _give_undo_history(main_window):
    from pysticky.core import PlaceStitchCommand

    cmd = PlaceStitchCommand(main_window.current_pattern, 0, 0, 0, 0)
    main_window.undo_manager.execute(cmd)
    assert main_window.undo_manager.can_undo is True


def test_layer_structure_changed_clears_undo_history(main_window):
    _give_undo_history(main_window)

    main_window.layer_panel.layer_structure_changed.emit()

    assert main_window.undo_manager.can_undo is False


def test_plain_layers_changed_does_not_clear_undo_history(main_window):
    """Deckkraft/Notiz/Sichtbarkeit-Aenderungen aendern KEINE Layer-Indizes
    -- das generische layers_changed-Signal darf die Undo-Historie nicht
    anfassen (sonst waere jede Deckkraft-Aenderung ein versehentlicher
    Undo-Reset)."""
    _give_undo_history(main_window)

    main_window.layer_panel.layers_changed.emit()

    assert main_window.undo_manager.can_undo is True


def test_add_layer_emits_structure_changed_and_clears_undo(main_window, monkeypatch):
    from PySide6.QtWidgets import QInputDialog

    _give_undo_history(main_window)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Neue Ebene", True))

    main_window.layer_panel._on_add_layer()

    assert main_window.undo_manager.can_undo is False


def test_remove_layer_emits_structure_changed_and_clears_undo(main_window, monkeypatch):
    from PySide6.QtWidgets import QInputDialog, QMessageBox

    # Zweite Ebene noetig, da _on_remove_layer bei nur einer Ebene ablehnt.
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Ebene 2", True))
    main_window.layer_panel._on_add_layer()

    _give_undo_history(main_window)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)

    main_window.layer_panel.list_widget.setCurrentRow(0)
    main_window.layer_panel._on_remove_layer()

    assert main_window.undo_manager.can_undo is False
