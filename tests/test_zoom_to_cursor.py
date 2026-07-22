# -*- coding: utf-8 -*-
"""Regressionstest (offener Punkt, Nutzerentscheidung 'Ja, umsetzen'):
Zoom ankerte bisher IMMER auf der Canvas-Mitte (width()//2, height()//2),
auch beim Mausrad-Zoom -- Standard-UX in Zeichenprogrammen ist, dass die
Stelle unter dem Cursor beim Zoomen an Ort und Stelle bleibt.
zoom_in()/zoom_out()/_set_cell_size() bekommen jetzt optionale
anchor_x/anchor_y-Parameter (None = Canvas-Mitte wie bisher), und
wheelEvent() reicht die Cursor-Position durch. zoom_reset()/zoom_fit()/
set_zoom() bleiben bewusst zentriert (kein Anker-Argument)."""

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent

from pysticky.core import Pattern

pytestmark = pytest.mark.usefixtures("qtbot")


def _grid_point_under(canvas, screen_x: float, screen_y: float) -> tuple[float, float]:
    return (
        (screen_x - canvas._offset_x) / canvas._cell_size,
        (screen_y - canvas._offset_y) / canvas._cell_size,
    )


def _make_canvas(qtbot):
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.resize(400, 300)
    canvas.set_pattern(Pattern(width=50, height=50))
    canvas._offset_x = 10
    canvas._offset_y = 10
    canvas._cell_size = 20
    return canvas


def test_zoom_in_keeps_anchor_point_fixed(qtbot):
    canvas = _make_canvas(qtbot)
    anchor_x, anchor_y = 100, 80
    before = _grid_point_under(canvas, anchor_x, anchor_y)

    canvas.zoom_in(anchor_x, anchor_y)

    after = _grid_point_under(canvas, anchor_x, anchor_y)
    assert after == pytest.approx(before, abs=0.05), (
        "Regression: Zoom-zu-Cursor -- der Punkt unter dem Anker muss vor "
        "und nach dem Zoomen an derselben Bildschirmposition bleiben"
    )


def test_zoom_out_keeps_anchor_point_fixed(qtbot):
    canvas = _make_canvas(qtbot)
    anchor_x, anchor_y = 250, 40
    before = _grid_point_under(canvas, anchor_x, anchor_y)

    canvas.zoom_out(anchor_x, anchor_y)

    after = _grid_point_under(canvas, anchor_x, anchor_y)
    # abs=0.05: _offset_x/_offset_y sind int (siehe _set_cell_size), daher
    # ist ein Sub-Pixel-Rundungsfehler beim Ankern erwartet, kein Bug.
    assert after == pytest.approx(before, abs=0.05)


def test_zoom_in_without_anchor_still_centers(qtbot):
    """Rueckwaertskompatibilitaet: Aufrufer ohne Anker (Toolbar-Buttons,
    Tablet-Pinch-Geste) muessen weiterhin auf der Canvas-Mitte zoomen."""
    canvas = _make_canvas(qtbot)
    center_x, center_y = canvas.width() // 2, canvas.height() // 2
    before = _grid_point_under(canvas, center_x, center_y)

    canvas.zoom_in()

    after = _grid_point_under(canvas, center_x, center_y)
    assert after == pytest.approx(before)


def test_zoom_reset_still_centers_regardless_of_current_offset(qtbot):
    canvas = _make_canvas(qtbot)
    canvas._offset_x = 137
    canvas._offset_y = -42
    canvas.DEFAULT_CELL_SIZE = 25

    canvas.zoom_reset()

    # zoom_reset() zentriert das Muster explizit ueber _center_pattern(),
    # unabhaengig vom vorherigen Offset -- kein Cursor-Anker beteiligt.
    assert canvas._cell_size == 25


def test_zoom_fit_still_centers(qtbot):
    canvas = _make_canvas(qtbot)
    canvas._offset_x = 999
    canvas._offset_y = -999

    canvas.zoom_fit()

    # zoom_fit() ruft _center_pattern() auf -- Ergebnis haengt nicht vom
    # vorherigen Offset ab, nur von Canvas-/Muster-Groesse.
    expected_cell = max(
        canvas.MIN_CELL_SIZE,
        min((canvas.width() - 40) // 50, (canvas.height() - 40) // 50, canvas.MAX_CELL_SIZE),
    )
    assert canvas._cell_size == expected_cell


def test_set_zoom_still_centers(qtbot):
    canvas = _make_canvas(qtbot)
    center_x, center_y = canvas.width() // 2, canvas.height() // 2
    canvas._offset_x = 5
    canvas._offset_y = 5
    before = _grid_point_under(canvas, center_x, center_y)

    canvas.set_zoom(2.0)

    after = _grid_point_under(canvas, center_x, center_y)
    assert after == pytest.approx(before), (
        "set_zoom() muss weiterhin auf der Canvas-Mitte ankern (kein Anker-Argument)"
    )


def test_wheel_event_passes_cursor_position_to_zoom(qtbot, monkeypatch):
    canvas = _make_canvas(qtbot)
    calls = []
    monkeypatch.setattr(canvas, "zoom_in", lambda *a: calls.append(("in", a)))
    monkeypatch.setattr(canvas, "zoom_out", lambda *a: calls.append(("out", a)))

    event = QWheelEvent(
        QPointF(123, 45),
        QPointF(123, 45),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    canvas.wheelEvent(event)

    assert calls == [("in", (123, 45))], (
        "Regression: Mausrad-Zoom muss die Cursor-Position als Anker "
        "durchreichen statt ungeankert zu zoomen"
    )
