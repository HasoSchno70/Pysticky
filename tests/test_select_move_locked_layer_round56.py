# -*- coding: utf-8 -*-
"""Regressionstest (Clean-Code-Audit Runde 56, Auswahl-Verschieben-Grenzfaelle).

Wenn die aktive Ebene gesperrt ist (oder waehrend eines laufenden Drags
gesperrt wird), lehnen layer.set_stitch()/remove_stitch() jeden
Schreibzugriff ab (siehe layer.py) -- das Verschieben einer Auswahl landet
dann als kompletter No-Op auf dem Grid. Vorher haben SelectTool._apply_move()
und LassoSelectTool._apply_move() trotzdem bedingungslos akzeptiert, dass sich
die Auswahl visuell zur neuen Position bewegt hat (self._selection bzw.
self._selection_bounds/_selected_pixels blieben auf der neuen, in Wahrheit
leeren Position stehen). Ergebnis: die Auswahl "log" -- sie markierte leere
Zellen, waehrend der echte Inhalt unveraendert an der alten Position lag,
fuer den Nutzer nicht mehr als ausgewaehlt erkennbar. Ein Klick auf
Loeschen/Fuellen danach haette die FALSCHEN (leeren) Zellen getroffen statt
den eigentlichen Auswahlinhalt.

Fix: on_mouse_release() prueft jetzt vor dem Akzeptieren eines Moves, ob die
aktive Ebene gesperrt ist. Falls ja, springt die Auswahl zurueck auf ihre
urspruengliche Position (kein Change erzeugt, kein Undo-Eintrag) --
identisches Prinzip zum bereits gefixten Radierer-/Fortschritt-Guard, nur auf
der "Verschieben"-Seite von Select/Lasso.
"""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPoint, QRect, Qt

from pysticky.ui.tools.base_tool import ToolContext
from pysticky.ui.tools.lasso_select_tool import LassoSelectTool
from pysticky.ui.tools.select_tool import SelectTool

pytestmark = pytest.mark.usefixtures("qtbot")


def _make_ctx(pattern, grid_x: int, grid_y: int, color_index: int = 0) -> ToolContext:
    canvas = MagicMock()
    canvas.snap_position.side_effect = lambda x, y: (x, y)
    canvas.snap_to_grid = False
    canvas.snap_interval = 1
    return ToolContext(
        canvas=canvas,
        pattern=pattern,
        current_color_index=color_index,
        grid_x=grid_x,
        grid_y=grid_y,
        screen_x=grid_x * 20,
        screen_y=grid_y * 20,
        cell_size=20,
        offset_x=0,
        offset_y=0,
    )


def _mouse_event(button: Qt.MouseButton = Qt.MouseButton.LeftButton, modifier=None):
    evt = MagicMock()
    evt.button.return_value = button
    evt.modifiers.return_value = modifier if modifier else Qt.KeyboardModifier.NoModifier
    evt.position.return_value = QPoint(0, 0)
    return evt


def test_select_move_onto_locked_layer_reverts_selection(pattern_with_stitches):
    """SelectTool: Verschieben bei gesperrter Ebene erzeugt keine Changes UND
    die Auswahl springt zurueck auf ihre urspruengliche Position -- sonst
    zeigt sie auf leere Zellen, obwohl der echte Inhalt woanders liegt."""
    tool = SelectTool()
    p = pattern_with_stitches
    ctx = _make_ctx(p, 6, 6)

    tool._selection = QRect(6, 6, 3, 3)
    tool._original_selection = QRect(6, 6, 3, 3)
    tool._capture_selection_content(ctx)
    tool._content_captured = True
    tool._is_moving = True
    tool._move_start = (6, 6)

    p.active_layer.locked = True

    # Drag weit weg
    tool.on_mouse_move(_make_ctx(p, 12, 6), _mouse_event())
    changes = tool.on_mouse_release(_make_ctx(p, 12, 6), _mouse_event())

    assert changes == [], "Gesperrte Ebene darf keine Changes erzeugen"
    assert tool.selection == QRect(6, 6, 3, 3), (
        "Auswahl muss bei gesperrter Ebene auf der urspruenglichen Position "
        "bleiben, sonst zeigt sie auf leere Zellen"
    )
    # Inhalt an der urspruenglichen Position unveraendert (Layer war eh
    # gesperrt, aber sicherstellen dass nichts geloescht wurde).
    assert p.active_layer.get_stitch(6, 6) is not None


def test_select_move_onto_unlocked_layer_still_works(pattern_with_stitches):
    """Regulaerer (ungesperrter) Fall bleibt unveraendert korrekt -- der neue
    Guard darf normales Verschieben nicht blockieren."""
    tool = SelectTool()
    p = pattern_with_stitches
    ctx = _make_ctx(p, 6, 6)

    tool._selection = QRect(6, 6, 3, 3)
    tool._original_selection = QRect(6, 6, 3, 3)
    tool._capture_selection_content(ctx)
    tool._content_captured = True
    tool._is_moving = True
    tool._move_start = (6, 6)

    tool.on_mouse_move(_make_ctx(p, 12, 6), _mouse_event())
    changes = tool.on_mouse_release(_make_ctx(p, 12, 6), _mouse_event())

    assert changes != []
    assert tool.selection == QRect(12, 6, 3, 3)


def test_lasso_move_onto_locked_layer_reverts_selection(pattern_with_stitches):
    """LassoSelectTool: gleiches Prinzip wie bei SelectTool, nur ueber das
    Pixel-Set statt ein Rechteck."""
    tool = LassoSelectTool()
    p = pattern_with_stitches
    ctx = _make_ctx(p, 6, 6)

    tool._selected_pixels = {(6, 6), (7, 6), (6, 7)}
    tool._update_bounds()
    tool._original_bounds = QRect(tool._selection_bounds)
    tool._capture_selection_content(ctx)
    tool._content_captured = True
    tool._is_moving = True
    tool._move_start = (6, 6)

    p.active_layer.locked = True

    tool.on_mouse_move(_make_ctx(p, 12, 6), _mouse_event())
    changes = tool.on_mouse_release(_make_ctx(p, 12, 6), _mouse_event())

    assert changes == []
    assert tool._selected_pixels == {(6, 6), (7, 6), (6, 7)}, (
        "Pixel-Set muss bei gesperrter Ebene auf die urspruengliche Position zurueckspringen"
    )


def test_lasso_move_onto_unlocked_layer_still_works(pattern_with_stitches):
    tool = LassoSelectTool()
    p = pattern_with_stitches
    ctx = _make_ctx(p, 6, 6)

    tool._selected_pixels = {(6, 6), (7, 6), (6, 7)}
    tool._update_bounds()
    tool._original_bounds = QRect(tool._selection_bounds)
    tool._capture_selection_content(ctx)
    tool._content_captured = True
    tool._is_moving = True
    tool._move_start = (6, 6)

    tool.on_mouse_move(_make_ctx(p, 12, 6), _mouse_event())
    changes = tool.on_mouse_release(_make_ctx(p, 12, 6), _mouse_event())

    assert changes != []
    assert tool._selected_pixels == {(12, 6), (13, 6), (12, 7)}


# === End-to-End ueber MainWindow: kein wirkungsloser Undo-Eintrag ===


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


def _press(canvas, x, y):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent

    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(event)


def _move(canvas, x, y):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent

    event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseMoveEvent(event)


def _release(canvas, x, y):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent

    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseReleaseEvent(event)


def test_select_move_onto_locked_layer_creates_no_undo_entry_e2e(qtbot, main_window):
    """End-to-End ueber echte Maus-Events + MainWindow: kein wirkungsloser
    Undo-Eintrag, Auswahl bleibt an der urspruenglichen Position, Inhalt
    bleibt an der urspruenglichen Position stehen."""
    from pysticky.core import Pattern, Thread
    from pysticky.ui.tools.tool_enum import Tool

    w = main_window
    pattern = Pattern(name="Test", width=20, height=20)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    w.set_pattern(pattern)

    canvas = w.canvas
    canvas._cell_size = 20
    canvas._offset_x = 0
    canvas._offset_y = 0

    layer = pattern.active_layer
    for x in range(5, 8):
        for y in range(5, 8):
            layer.set_stitch(x, y, 0)
    pattern.color_entries[0].stitch_count = 9

    w.tool_bar.select_tool(Tool.SELECT)
    select_tool = canvas._tool_manager.get_active_select_tool()

    _press(canvas, 5 * 20 + 5, 5 * 20 + 5)
    _move(canvas, 7 * 20 + 5, 7 * 20 + 5)
    _release(canvas, 7 * 20 + 5, 7 * 20 + 5)
    assert select_tool.selection == QRect(5, 5, 3, 3)

    undo_count_before = w.undo_manager.undo_count
    layer.locked = True

    _press(canvas, 6 * 20 + 5, 6 * 20 + 5)  # Klick in Auswahl -> Move-Start
    _move(canvas, 10 * 20 + 5, 10 * 20 + 5)
    _release(canvas, 10 * 20 + 5, 10 * 20 + 5)

    assert w.undo_manager.undo_count == undo_count_before, (
        "Verschieben auf eine gesperrte Ebene darf keinen Undo-Eintrag erzeugen"
    )
    assert select_tool.selection == QRect(5, 5, 3, 3), (
        "Auswahl darf bei gesperrter Ebene nicht zur neuen (leeren) Position springen"
    )
    assert layer.get_stitch(5, 5) == 0, "Inhalt muss unveraendert an der alten Position bleiben"
    assert layer.get_stitch(10, 10) is None, "Neue Position darf nichts erhalten haben"
