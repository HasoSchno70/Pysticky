# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 24): TabletGestureMixin._tablet_in_use/
_tablet_pressure wurden nur bei QEvent.Type.TabletRelease zurueckgesetzt.
Verlaesst der Stift den Erkennungsbereich abrupt (Fokuswechsel waehrend
gedrueckt, Stift kippt aus dem Sensorbereich) OHNE dass ein passendes
TabletRelease folgt, blieb der Zustand haengen -- ein spaeterer normaler
Maus-Klick wurde faelschlich als druckbasierter (Brush-)Stich interpretiert.
"""

import pytest
from PySide6.QtCore import QEvent

pytestmark = pytest.mark.usefixtures("qtbot")


def test_tablet_leave_proximity_resets_stale_pressure_state(qtbot):
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)

    # Simuliert einen laufenden, nie sauber beendeten Stift-Strich.
    canvas._tablet_in_use = True
    canvas._tablet_pressure = 0.8

    proximity_event = QEvent(QEvent.Type.TabletLeaveProximity)
    canvas.event(proximity_event)

    assert canvas._tablet_in_use is False
    assert canvas._tablet_pressure == 0.0


def test_unrelated_events_do_not_reset_tablet_state(qtbot):
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)

    canvas._tablet_in_use = True
    canvas._tablet_pressure = 0.5

    unrelated_event = QEvent(QEvent.Type.Show)
    canvas.event(unrelated_event)

    assert canvas._tablet_in_use is True
    assert canvas._tablet_pressure == 0.5
