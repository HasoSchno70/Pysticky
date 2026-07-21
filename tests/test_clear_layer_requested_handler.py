# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 16): MainWindow._on_clear_layer_requested() muss
den Aufruf tatsaechlich in einen ClearLayerCommand uebersetzen, der ueber
den UndoManager laeuft -- vorher (layer.clear() direkt aus dem Panel) war
"Ebene leeren" ueberhaupt nicht per Strg+Z rueckgaengig zu machen.
"""

import pytest

from pysticky.core import Pattern, Thread

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


def test_clear_layer_requested_is_undoable(main_window):
    w = main_window
    pattern = Pattern(name="Test", width=10, height=10)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.set_stitch(3, 3, 0)
    pattern.color_entries[0].stitch_count = 1
    w.set_pattern(pattern)

    assert w.current_pattern.active_layer.get_stitch(3, 3) == 0

    w._on_clear_layer_requested(0)

    assert w.current_pattern.active_layer.get_stitch(3, 3) is None
    assert w.current_pattern.color_entries[0].stitch_count == 0
    assert w.undo_manager.can_undo is True

    w.undo_manager.undo()

    assert w.current_pattern.active_layer.get_stitch(3, 3) == 0
    assert w.current_pattern.color_entries[0].stitch_count == 1
