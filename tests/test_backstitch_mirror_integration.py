# -*- coding: utf-8 -*-
"""Integrationstest: das Rückstich-Werkzeug erzeugt bei aktivem Spiegel-
Modus jetzt mehrere Rückstiche pro Klick (analog jedem anderen
Zeichenwerkzeug) UND fasst sie als EINE Undo-Aktion zusammen -- vorher
wurde der Spiegel-Modus komplett ignoriert."""

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


def test_backstitch_with_mirror_creates_multiple_lines_as_one_undo(main_window):
    from pysticky.core import Pattern, Thread
    from pysticky.ui.canvas.enums import MirrorMode
    from pysticky.ui.tools.tool_enum import Tool

    w = main_window
    pattern = Pattern(name="Test", width=10, height=6)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    w.set_pattern(pattern)

    canvas = w.canvas
    canvas._cell_size = 20
    canvas._offset_x = 0
    canvas._offset_y = 0
    canvas._mirror_mode = MirrorMode.HORIZONTAL

    w.tool_bar.select_tool(Tool.BACKSTITCH)
    backstitch_tool = canvas._tool_manager.get_backstitch_tool()
    backstitch_tool.snap_to_grid = False

    # Zwei Klicks: Startpunkt (Zelle 1,1 -> half-stitch 2,2), dann Endpunkt
    # (Zelle 2,2 -> half-stitch 4,4) -- ergibt eine Linie (2,2)-(4,4).
    _press(canvas, 25, 25)
    _press(canvas, 45, 45)

    assert len(pattern.backstitches) == 2, (
        "Regression: Spiegel-Modus wurde beim Rueckstich-Werkzeug ignoriert "
        "-- es haette eine gespiegelte zusaetzliche Linie geben muessen"
    )

    coords = {(bs.x1, bs.y1, bs.x2, bs.y2) for bs in pattern.backstitches}
    assert (2, 2, 4, 4) in coords
    assert (18, 2, 16, 4) in coords  # gespiegelt: max_x = 2*10 = 20

    assert w.undo_manager.undo_count == 1, (
        "Regression: die zwei gespiegelten Rueckstiche wurden als ZWEI "
        "getrennte Undo-Schritte erfasst statt als einer"
    )

    w.undo_manager.undo()
    assert len(pattern.backstitches) == 0, (
        "Ein einzelnes Undo muss BEIDE gespiegelten Linien entfernen"
    )
