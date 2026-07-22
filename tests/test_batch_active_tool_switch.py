# -*- coding: utf-8 -*-
"""Regressionstest (Runde 25): CrossStitchCanvas._batch_active blieb fuer
immer haengen, wenn der Nutzer waehrend eines gehaltenen Mausklicks per
Tastenkuerzel das Werkzeug wechselte. mousePressEvent oeffnet den Undo-Batch
nur, wenn das damals aktive Werkzeug NICHT Select/Polygon/Backstitch ist;
mouseReleaseEvent las das aktuelle Werkzeug aber zum Loslass-Zeitpunkt neu
aus (mixins/mouse_events_mixin.py) -- wechselte der Nutzer zwischen Press und
Release z.B. von Pencil zu Select, griff die Schliessen-Bedingung
"not is_select_tool" nicht mehr, der Batch blieb offen und JEDE folgende
Aktion oeffnete nie wieder einen eigenen Undo-Batch (das Start-Gate prueft
"not self._batch_active").

Fix: canvas.py speichert jetzt _batch_opened_by_polygon_tool/
_batch_opened_by_select_tool zum Press-Zeitpunkt; mouseReleaseEvent schliesst
den Batch anhand dieser gespeicherten Werte, nicht anhand des aktuellen
Werkzeugs."""

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent

from pysticky.core import Pattern, Thread
from pysticky.ui.canvas import CrossStitchCanvas
from pysticky.ui.tools.tool_enum import Tool

pytestmark = pytest.mark.usefixtures("qtbot")


def _make_canvas(qtbot):
    pattern = Pattern(name="Test", width=20, height=20)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(pattern)
    return canvas


def _press_event():
    return QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(5, 5),
        QPointF(5, 5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


def _release_event():
    return QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(5, 5),
        QPointF(5, 5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )


def test_batch_closes_when_tool_switches_to_select_mid_drag(qtbot):
    canvas = _make_canvas(qtbot)
    canvas.set_tool(Tool.PENCIL)

    canvas.mousePressEvent(_press_event())
    assert canvas._batch_active, "Pencil-Press haette einen Batch oeffnen muessen"

    # Waehrend die Maustaste noch gehalten wird, wechselt der Nutzer per
    # Tastenkuerzel auf Select.
    canvas.set_tool(Tool.SELECT)

    canvas.mouseReleaseEvent(_release_event())

    assert not canvas._batch_active, (
        "Regression: _batch_active blieb haengen, weil das Loslassen anhand "
        "des NEUEN (Select-)Werkzeugs statt des Press-Zeitpunkt-Werkzeugs "
        "entschieden wurde"
    )


def test_batch_closes_when_tool_switches_to_polygon_mid_drag(qtbot):
    canvas = _make_canvas(qtbot)
    canvas.set_tool(Tool.PENCIL)

    canvas.mousePressEvent(_press_event())
    assert canvas._batch_active

    canvas.set_tool(Tool.POLYGON)
    canvas.mouseReleaseEvent(_release_event())

    assert not canvas._batch_active


def test_next_batch_opens_normally_after_tool_switch_release(qtbot):
    """Direkte Folgeprüfung des eigentlichen Symptoms: nach dem Vorfall muss
    ein ganz normaler Pencil-Stich wieder einen EIGENEN, NEUEN Batch oeffnen
    -- zaehlt batch_started-Emissionen statt nur den (bei haengengebliebenem
    Batch trivial immer "True" bleibenden) _batch_active-Flag zu pruefen."""
    canvas = _make_canvas(qtbot)
    starts = []
    canvas.batch_started.connect(starts.append)

    canvas.set_tool(Tool.PENCIL)
    canvas.mousePressEvent(_press_event())
    canvas.set_tool(Tool.SELECT)
    canvas.mouseReleaseEvent(_release_event())
    assert len(starts) == 1

    canvas.set_tool(Tool.PENCIL)
    canvas.mousePressEvent(_press_event())
    assert len(starts) == 2, (
        "Nach dem haengengebliebenen Batch oeffnete keine weitere Aktion "
        "mehr einen eigenen Undo-Batch (batch_started feuerte nicht erneut)"
    )
    canvas.mouseReleaseEvent(_release_event())
    assert not canvas._batch_active
