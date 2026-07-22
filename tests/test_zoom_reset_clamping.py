# -*- coding: utf-8 -*-
"""Regressionstest (Runde 27): ZoomMixin.zoom_reset() setzte die Zellgroesse
direkt auf DEFAULT_CELL_SIZE zurueck, OHNE gegen MIN_CELL_SIZE/MAX_CELL_SIZE
zu clampen -- anders als zoom_in()/zoom_out()/set_zoom(), die das alle
korrekt tun. Einstellungen -> Canvas -> Zoom erlaubt MIN/MAX/DEFAULT jeweils
unabhaengig voneinander zu konfigurieren (kein Cross-Validation); ist
DEFAULT_CELL_SIZE ausserhalb der konfigurierten Min/Max-Grenzen (z.B.
DEFAULT=60, MAX=30), ueberschritt Zoom-Reset (100%) die Grenze still, bis
der naechste zoom_in()/zoom_out()-Schritt sie wieder korrekt clampte."""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def test_zoom_reset_clamps_to_max_cell_size(qtbot):
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)

    canvas.DEFAULT_CELL_SIZE = 60
    canvas.MAX_CELL_SIZE = 30

    canvas.zoom_reset()

    assert canvas._cell_size == 30, (
        "Regression: zoom_reset() ueberschritt MAX_CELL_SIZE, weil es "
        "DEFAULT_CELL_SIZE ungeclampt uebernahm"
    )


def test_zoom_reset_clamps_to_min_cell_size(qtbot):
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)

    canvas.DEFAULT_CELL_SIZE = 4
    canvas.MIN_CELL_SIZE = 20

    canvas.zoom_reset()

    assert canvas._cell_size == 20
