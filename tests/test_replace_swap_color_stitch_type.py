# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 30): "Farbe ersetzen" und "Farben tauschen" gaben
Aenderungen als 3-Tuple (x, y, color_index) an canvas._apply_changes()
weiter. Ohne expliziten Stich-Typ (4. Tuple-Element) landet die Aenderung
auf dem stitch_placed-Signal (statt stitch_placed_typed), das ueber
_on_stitch_placed() den GLOBALEN canvas._active_stitch_type einsetzt
(Standard FULL) -- unabhaengig vom tatsaechlichen Stich-Typ der ersetzten
Zelle. Ein Halb- oder Viertelstich wurde dadurch bei "Farbe ersetzen"
oder "Farben tauschen" stillschweigend zu einem Vollstich.
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


def _pattern_with_half_stitch():
    from pysticky.core import Pattern, Thread
    from pysticky.core.stitch import StitchType

    pattern = Pattern(name="Test", width=10, height=10)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.add_color(Thread.from_hex("Blau", "#0000FF"))
    # Halbstich der Farbe 0 (Rot) an (2, 2)
    pattern.set_stitch(2, 2, 0, stitch_type=StitchType.HALF_TL_BR.value)
    return pattern


def test_swap_color_pair_preserves_stitch_type(main_window):
    from pysticky.core.stitch import StitchType

    w = main_window
    w.set_pattern(_pattern_with_half_stitch())

    w._swap_color_pair(0, 1)

    layer = w.current_pattern.active_layer
    assert layer.get_stitch(2, 2) == 1
    assert layer.get_stitch_type(2, 2) == StitchType.HALF_TL_BR.value


def test_replace_color_preserves_stitch_type(main_window, monkeypatch):
    from pysticky.core.stitch import StitchType
    from pysticky.ui import dialogs as dialogs_mod

    w = main_window
    w.set_pattern(_pattern_with_half_stitch())

    monkeypatch.setattr(dialogs_mod.ReplaceColorDialog, "exec", lambda self: True)
    monkeypatch.setattr(dialogs_mod.ReplaceColorDialog, "get_replacements", lambda self: [(0, 1)])

    w._on_replace_color()

    layer = w.current_pattern.active_layer
    assert layer.get_stitch(2, 2) == 1
    assert layer.get_stitch_type(2, 2) == StitchType.HALF_TL_BR.value
