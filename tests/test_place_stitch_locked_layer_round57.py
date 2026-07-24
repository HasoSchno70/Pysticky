# -*- coding: utf-8 -*-
"""Reproduktionstest (Clean-Code-Audit Runde 57).

Prueft, ob _place_stitch() (Platzieren-Seite, genutzt von JEDEM Zeichen-
werkzeug ueber das stitch_placed/stitch_placed_typed-Signal: Stift,
Fuellen, Linie, Rechteck, Ellipse, Polygon, Farbverlauf, ...) denselben
wirkungslosen-Undo-Eintrag-Bug hat wie der in Runde 54 gefixte Radierer
(_on_stitch_removed) -- dort NUR auf der Entfernen-Seite gefixt.
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def _new_window(qtbot):
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    return w


def test_placing_on_locked_layer_creates_no_undo_entry(qtbot):
    from pysticky.core import Pattern

    w = _new_window(qtbot)
    pattern = Pattern(name="Gesperrt", width=10, height=10)
    pattern.active_layer.locked = True
    w.set_pattern(pattern)

    w._on_stitch_placed(3, 3, 0)

    assert w.undo_manager.undo_count == 0
    assert w.current_pattern.active_layer.get_stitch(3, 3) is None


def test_placing_on_locked_layer_batch_creates_no_undo_entry(qtbot):
    """Selbe Pruefung im Batch-Pfad (add_to_batch()/end_batch()) -- so laufen
    Drag-Zuege von Stift/Linie/Rechteck/etc. tatsaechlich durch die App."""
    from pysticky.core import Pattern

    w = _new_window(qtbot)
    pattern = Pattern(name="Gesperrt-Batch", width=10, height=10)
    pattern.active_layer.locked = True
    w.set_pattern(pattern)

    w._on_batch_started("Stift")
    w._on_stitch_placed(3, 3, 0)
    w._on_stitch_placed(4, 4, 0)
    w._on_batch_ended()

    assert w.undo_manager.undo_count == 0
    assert w.current_pattern.active_layer.get_stitch(3, 3) is None
    assert w.current_pattern.active_layer.get_stitch(4, 4) is None


def test_placing_on_unlocked_layer_still_creates_undo_entry(qtbot):
    """Der neue Guard darf den regulaeren Zeichen-Fall nicht mit-blockieren."""
    from pysticky.core import Pattern

    w = _new_window(qtbot)
    pattern = Pattern(name="Entsperrt", width=10, height=10)
    w.set_pattern(pattern)

    w._on_stitch_placed(3, 3, 0)

    assert w.undo_manager.undo_count == 1
    assert w.current_pattern.active_layer.get_stitch(3, 3) == 0

    w.undo_manager.undo()
    assert w.current_pattern.active_layer.get_stitch(3, 3) is None


# === End-to-End ueber echte Maus-Events + MainWindow ===


def _press(canvas, x, y):
    from PySide6.QtCore import QPointF, Qt
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
    from PySide6.QtCore import QPointF, Qt
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
    from PySide6.QtCore import QPointF, Qt
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


def test_fill_tool_on_locked_layer_creates_no_undo_entry_e2e(qtbot):
    """Fuelltool auf einer gesperrten Ebene: ein Klick auf eine bereits
    gefuellte (leere) Flaeche wuerde ohne den Guard in _place_stitch()
    potenziell VIELE wirkungslose PlaceStitchCommand-Eintraege in einem
    einzigen Batch erzeugen -- der Batch selbst zaehlt aber weiterhin als
    "nicht leer" (BatchStitchCommand.is_empty prueft nur len(_commands),
    nicht ob ein Sub-Command tatsaechlich etwas geaendert hat)."""
    from pysticky.core import Pattern, Thread
    from pysticky.ui.main_window import MainWindow
    from pysticky.ui.tools.tool_enum import Tool

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    pattern = Pattern(name="Fill-Gesperrt", width=10, height=10)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    w.set_pattern(pattern)

    canvas = w.canvas
    canvas._cell_size = 20
    canvas._offset_x = 0
    canvas._offset_y = 0

    pattern.active_layer.locked = True
    w.tool_bar.select_tool(Tool.FILL)

    _press(canvas, 5 * 20 + 5, 5 * 20 + 5)
    _release(canvas, 5 * 20 + 5, 5 * 20 + 5)

    assert w.undo_manager.undo_count == 0
    for x in range(10):
        for y in range(10):
            assert pattern.active_layer.get_stitch(x, y) is None


def test_rect_tool_drag_on_locked_layer_creates_no_undo_entry_e2e(qtbot):
    """Rechteck-Tool-Drag ueber mehrere Zellen auf gesperrter Ebene: jede
    Zelle des Rechtecks feuert ein eigenes stitch_placed-Signal innerhalb
    EINES Batches -- ohne Guard bliebe ein wirkungsloser Batch-Undo-Eintrag
    zurueck, obwohl das Grid komplett unveraendert ist."""
    from pysticky.core import Pattern, Thread
    from pysticky.ui.main_window import MainWindow
    from pysticky.ui.tools.tool_enum import Tool

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    pattern = Pattern(name="Rect-Gesperrt", width=20, height=20)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    w.set_pattern(pattern)

    canvas = w.canvas
    canvas._cell_size = 20
    canvas._offset_x = 0
    canvas._offset_y = 0

    pattern.active_layer.locked = True
    w.tool_bar.select_tool(Tool.RECT_FILLED)

    _press(canvas, 5 * 20 + 5, 5 * 20 + 5)
    _move(canvas, 10 * 20 + 5, 10 * 20 + 5)
    _release(canvas, 10 * 20 + 5, 10 * 20 + 5)

    assert w.undo_manager.undo_count == 0
    for x in range(5, 11):
        for y in range(5, 11):
            assert pattern.active_layer.get_stitch(x, y) is None
