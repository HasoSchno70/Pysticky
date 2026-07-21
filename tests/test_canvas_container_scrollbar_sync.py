# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 14): CanvasContainer._on_h_scroll()/_on_v_scroll()
setzten den Canvas-Offset direkt, ohne canvas.offset_changed zu emittieren
-- im Gegensatz zu JEDEM anderen Offset-aendernden Pfad (Ruler-Klick,
Zentrieren-Button, Maus-/Pfeiltasten-Pan, Minimap-Klick-Navigation).
MainWindow haengt _update_minimap_viewport() ausschliesslich an dieses
Signal (mw_signals_mixin.py) -- beim Ziehen der Canvas-Scrollbar blieb die
Minimap-Viewport-Markierung dadurch an der alten Position stehen, bis eine
unabhaengige Aktion sie zufaellig mit-synchronisierte.
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def test_h_scroll_emits_offset_changed(qtbot):
    from pysticky.ui.widgets.canvas_container import CanvasContainer

    container = CanvasContainer()
    qtbot.addWidget(container)

    received = []
    container._canvas.offset_changed.connect(lambda x, y: received.append((x, y)))

    container._on_h_scroll(50)

    assert received == [(-50, container._canvas._offset_y)]


def test_v_scroll_emits_offset_changed(qtbot):
    from pysticky.ui.widgets.canvas_container import CanvasContainer

    container = CanvasContainer()
    qtbot.addWidget(container)

    received = []
    container._canvas.offset_changed.connect(lambda x, y: received.append((x, y)))

    container._on_v_scroll(30)

    assert received == [(container._canvas._offset_x, -30)]
