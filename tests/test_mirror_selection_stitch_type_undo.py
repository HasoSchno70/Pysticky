# -*- coding: utf-8 -*-
"""
Regression: `CrossStitchCanvas.mirror_selection_horizontal()`/`_vertical()`
lasen jede Zelle nur ueber `layer.get_stitch()` (Farbindex) und schrieben sie
mit `layer.set_stitch(x, y, color_idx)` zurueck -- ohne `stitch_type`. Jede
gespiegelte Zelle wurde dadurch stillschweigend auf einen vollen Kreuzstich
(FULL) zurueckgesetzt, egal ob die Quellzelle ein Halb-/Viertelstich,
Franzoesischer Knoten oder eine Perle war.

Fix: `layer.get_stitch_type(x, y)` wird mitgelesen und -- ueber
`FLIP_H_MAP`/`FLIP_V_MAP` (core/stitch.py) -- korrekt an die neue
Orientierung angepasst, bevor sie zurueckgeschrieben wird. Diagonale Halb-/
Viertelstiche drehen bei einer Spiegelung ihre Richtung (z.B. "/" -> "\"),
genau wie es das bereits existierende `mirror_horizontal`-Plugin
(plugins/builtin/mirror_horizontal/plugin.py) fuer die ganze-Muster-Variante
schon tut.

Zusaetzlich: `_on_mirror_h`/`_on_mirror_v` (ui/handlers/selection_handlers.py)
riefen `Canvas.mirror_selection_horizontal/_vertical()` direkt auf und
mutierten das Layer, ohne jemals einen Undo-Command zu erzeugen -- Ctrl+Z
konnte eine Spiegelung nie rueckgaengig machen. Fix: beide Handler laufen
jetzt ueber `LayerSnapshotCommand` (wie schon `PluginDialog._on_run` fuer
Plugin-Laeufe), die vor/nach der Operation Grid + stitch_type_grid
snapshotten.
"""

import pytest
from PySide6.QtCore import QRect

from pysticky.core.stitch import StitchType

pytestmark = pytest.mark.usefixtures("qtbot")


def _make_canvas(pattern, qtbot):
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(pattern)
    return canvas


# ---------------------------------------------------------------------------
# Canvas-Ebene: stitch_type-Erhalt
# ---------------------------------------------------------------------------


def test_mirror_horizontal_preserves_and_flips_stitch_type(pattern_with_colors, qtbot):
    """Ein Halbstich "/" (HALF_TL_BR) muss nach horizontaler Spiegelung als
    "\\" (HALF_TR_BL) ankommen -- nicht als FULL (0)."""
    pattern = pattern_with_colors
    pattern.set_stitch(2, 5, 0, stitch_type=StitchType.HALF_TL_BR.value)
    # (3, 5) bleibt leer.

    canvas = _make_canvas(pattern, qtbot)
    canvas._selection = QRect(2, 5, 2, 1)  # deckt (2,5) und (3,5) ab

    assert canvas.mirror_selection_horizontal() is True

    layer = pattern.active_layer
    assert layer.get_stitch(3, 5) == 0
    assert layer.get_stitch_type(3, 5) == StitchType.HALF_TR_BL.value, (
        "Regression: stitch_type ging beim Spiegeln verloren (auf FULL zurueckgesetzt) "
        "statt korrekt geflippt zu werden"
    )


def test_mirror_vertical_preserves_and_flips_stitch_type(pattern_with_colors, qtbot):
    """Analog fuer vertikale Spiegelung: HALF_TL_BR -> HALF_TR_BL (FLIP_V_MAP)."""
    pattern = pattern_with_colors
    pattern.set_stitch(4, 2, 1, stitch_type=StitchType.HALF_TL_BR.value)
    # (4, 3) bleibt leer.

    canvas = _make_canvas(pattern, qtbot)
    canvas._selection = QRect(4, 2, 1, 2)  # deckt (4,2) und (4,3) ab

    assert canvas.mirror_selection_vertical() is True

    layer = pattern.active_layer
    assert layer.get_stitch(4, 3) == 1
    assert layer.get_stitch_type(4, 3) == StitchType.HALF_TR_BL.value, (
        "Regression: stitch_type ging beim Spiegeln verloren (auf FULL zurueckgesetzt) "
        "statt korrekt geflippt zu werden"
    )


def test_mirror_horizontal_preserves_non_directional_stitch_type(pattern_with_colors, qtbot):
    """Ein Franzoesischer Knoten (rotations-/spiegel-invariant) darf beim
    Spiegeln nicht auf FULL zurueckfallen."""
    pattern = pattern_with_colors
    pattern.set_stitch(2, 5, 0, stitch_type=StitchType.FRENCH_KNOT.value)

    canvas = _make_canvas(pattern, qtbot)
    canvas._selection = QRect(2, 5, 2, 1)

    assert canvas.mirror_selection_horizontal() is True

    layer = pattern.active_layer
    assert layer.get_stitch_type(3, 5) == StitchType.FRENCH_KNOT.value


# ---------------------------------------------------------------------------
# Handler-Ebene: Undo-Integration
# ---------------------------------------------------------------------------


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


def test_mirror_h_is_undoable(main_window, qtbot):
    """Regression: Spiegeln umging das Undo-System komplett -- Ctrl+Z konnte
    eine Spiegelung bisher nicht rueckgaengig machen."""
    from pysticky.core import Pattern, Thread

    w = main_window
    pattern = Pattern(name="Test", width=10, height=6)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.set_stitch(2, 3, 0, stitch_type=StitchType.HALF_TL_BR.value)
    w.set_pattern(pattern)

    w.canvas._selection = QRect(2, 3, 2, 1)

    assert w.undo_manager.can_undo is False
    w._on_mirror_h()

    layer = w.current_pattern.active_layer
    assert layer.get_stitch(3, 3) == 0
    assert layer.get_stitch_type(3, 3) == StitchType.HALF_TR_BL.value
    assert w.undo_manager.can_undo is True, (
        "Regression: mirror_selection_horizontal mutierte das Layer direkt, "
        "ohne je einen Undo-Command zu erzeugen"
    )

    w.undo_manager.undo()
    assert layer.get_stitch(2, 3) == 0
    assert layer.get_stitch_type(2, 3) == StitchType.HALF_TL_BR.value
    assert layer.get_stitch(3, 3) is None


def test_mirror_v_is_undoable(main_window, qtbot):
    from pysticky.core import Pattern, Thread

    w = main_window
    pattern = Pattern(name="Test", width=6, height=10)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.set_stitch(3, 2, 0, stitch_type=StitchType.HALF_TL_BR.value)
    w.set_pattern(pattern)

    w.canvas._selection = QRect(3, 2, 1, 2)

    w._on_mirror_v()

    layer = w.current_pattern.active_layer
    assert layer.get_stitch(3, 3) == 0
    assert layer.get_stitch_type(3, 3) == StitchType.HALF_TR_BL.value
    assert w.undo_manager.can_undo is True

    w.undo_manager.undo()
    assert layer.get_stitch(3, 2) == 0
    assert layer.get_stitch(3, 3) is None


def test_mirror_h_without_selection_does_not_touch_undo_stack(main_window, qtbot):
    """Ohne Auswahl darf kein No-Op-Undo-Eintrag entstehen."""
    from pysticky.core import Pattern, Thread

    w = main_window
    pattern = Pattern(name="Test", width=10, height=6)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    w.set_pattern(pattern)

    assert w.canvas._selection is None
    w._on_mirror_h()

    assert w.undo_manager.can_undo is False
