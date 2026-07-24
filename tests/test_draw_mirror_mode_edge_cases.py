# -*- coding: utf-8 -*-
"""Regressionstests fuer den Zeichen-Spiegelmodus (get_mirrored_positions()
+ _apply_changes_with_mirror()) in Grenzfaellen:

- ungerade Musterbreite/-hoehe: die exakte Mittelspalte/-zeile darf nur
  EINMAL gezeichnet werden, nicht als Original+Spiegel-Duplikat
- 4-fach-Symmetrie (QUAD) bei ungeradem Muster: die exakte Mittelzelle
  (auf BEIDEN Achsen gleichzeitig) darf nur einmal gezeichnet werden
- ein kompletter Zeichen-Drag (Press+Move+Release) mit aktivem Spiegel-
  Modus muss als EINE Undo-Aktion erfasst werden (analog zum bereits
  gefixten Rueckstich-Pendant in test_backstitch_mirror_integration.py)
- Diamond-Modus: der gespiegelte Stich muss denselben stitch_type
  bekommen wie das Original (beide haengen am globalen
  canvas._active_stitch_type, nicht an einem per-Stich Wert)
"""

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent

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


def _press(canvas, x, y):
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
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseReleaseEvent(event)


def _setup(main_window, width, height):
    from pysticky.core import Pattern, Thread
    from pysticky.ui.tools.tool_enum import Tool

    w = main_window
    pattern = Pattern(name="Test", width=width, height=height)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    w.set_pattern(pattern)

    canvas = w.canvas
    canvas._cell_size = 20
    canvas._offset_x = 0
    canvas._offset_y = 0
    w.tool_bar.select_tool(Tool.PENCIL)
    return w, pattern, canvas


def test_odd_width_center_column_draws_once_horizontal_mirror(main_window):
    """Bei ungerader Breite (21) liegt Spalte 10 exakt auf der Spiegelachse
    -- ein Klick dort darf nur EINEN Stich erzeugen, nicht Original+Spiegel
    auf derselben Zelle (was harmlos waere, aber trotzdem als Doppel-Undo-
    Eintrag auftauchen koennte)."""
    from pysticky.ui.canvas.enums import MirrorMode

    w, pattern, canvas = _setup(main_window, width=21, height=6)
    canvas._mirror_mode = MirrorMode.HORIZONTAL

    positions = canvas.get_mirrored_positions(10, 3)
    assert positions == [(10, 3)], (
        f"Mittelspalte bei ungerader Breite muss auf genau eine Position "
        f"kollabieren, bekam aber {positions}"
    )

    _press(canvas, 10 * 20 + 5, 3 * 20 + 5)
    _release(canvas, 10 * 20 + 5, 3 * 20 + 5)

    layer = pattern.active_layer
    assert layer.get_stitch(10, 3) == 0
    assert w.undo_manager.undo_count == 1


def test_quad_mirror_odd_pattern_center_cell_draws_once(main_window):
    """4-fach-Symmetrie bei ungeradem Muster (21x15): die exakte
    Mittelzelle (10, 7) liegt auf BEIDEN Achsen gleichzeitig -- darf nur
    einmal in der Positionsliste auftauchen, sonst wuerde sie beim
    Zeichnen ueberfluessig mehrfach (und damit potenziell mehrfach im
    Undo) gesetzt."""
    from pysticky.ui.canvas.enums import MirrorMode

    w, pattern, canvas = _setup(main_window, width=21, height=15)
    canvas._mirror_mode = MirrorMode.QUAD

    positions = canvas.get_mirrored_positions(10, 7)
    assert positions == [(10, 7)]

    _press(canvas, 10 * 20 + 5, 7 * 20 + 5)
    _release(canvas, 10 * 20 + 5, 7 * 20 + 5)

    layer = pattern.active_layer
    assert layer.get_stitch(10, 7) == 0
    assert w.undo_manager.undo_count == 1


def test_quad_mirror_drag_is_one_undo_action(main_window):
    """Ein Zeichen-Drag (Press+Move+Release) mit QUAD-Spiegelung muss als
    EINE Undo-Aktion erfasst werden -- ein einzelnes Undo muss alle
    gespiegelten Zellen wieder entfernen."""
    from pysticky.ui.canvas.enums import MirrorMode

    w, pattern, canvas = _setup(main_window, width=20, height=20)
    canvas._mirror_mode = MirrorMode.QUAD

    _press(canvas, 2 * 20 + 5, 2 * 20 + 5)
    _move(canvas, 3 * 20 + 5, 2 * 20 + 5)
    _release(canvas, 3 * 20 + 5, 2 * 20 + 5)

    layer = pattern.active_layer
    # Original + horizontal + vertikal + diagonal fuer beide besuchten Zellen
    placed = [(x, y) for x in range(20) for y in range(20) if layer.get_stitch(x, y) is not None]
    assert len(placed) == 8, f"Erwartet 8 gespiegelte Zellen, bekam {placed}"

    assert w.undo_manager.undo_count == 1, (
        "Ein Zeichen-Drag mit aktivem Spiegel-Modus muss EINE Undo-Aktion "
        "sein, egal wie viele gespiegelte Zellen dabei gesetzt wurden"
    )

    w.undo_manager.undo()
    placed_after_undo = [
        (x, y) for x in range(20) for y in range(20) if layer.get_stitch(x, y) is not None
    ]
    assert placed_after_undo == [], "Ein einzelnes Undo muss ALLE gespiegelten Zellen entfernen"


def test_diamond_mode_mirrored_stitch_gets_same_stitch_type(main_window):
    """Im Diamond-Modus muss der gespiegelte Stich denselben stitch_type
    (DIAMOND) bekommen wie das Original -- beide haengen am globalen
    canvas._active_stitch_type."""
    from pysticky.core.stitch import StitchType
    from pysticky.ui.canvas.enums import MirrorMode

    w, pattern, canvas = _setup(main_window, width=20, height=10)
    canvas._mirror_mode = MirrorMode.HORIZONTAL
    canvas._active_stitch_type = StitchType.DIAMOND.value

    _press(canvas, 2 * 20 + 5, 3 * 20 + 5)
    _release(canvas, 2 * 20 + 5, 3 * 20 + 5)

    layer = pattern.active_layer
    assert layer.get_stitch(2, 3) == 0
    assert layer.get_stitch_type(2, 3) == StitchType.DIAMOND.value
    mirror_x = 20 - 2 - 1
    assert layer.get_stitch(mirror_x, 3) == 0
    assert layer.get_stitch_type(mirror_x, 3) == StitchType.DIAMOND.value
    assert w.undo_manager.undo_count == 1
