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


# =============================================================================
# Runde 59 (Zoom-zu-Cursor-Grenzfaelle-Audit): _update_scrollbars() blockte
# beim Synchronisieren nur setValue() gegen Signal-Rueckkopplung, NICHT
# setRange(). Qt clamped beim setRange()-Aufruf aber automatisch den
# AKTUELLEN (noch unsynchronisierten) Scrollbar-Wert auf die neuen Grenzen
# und feuert dabei ungeblockt valueChanged, wenn der alte Wert ausserhalb
# der neuen Range liegt (typisch beim Herauszoomen am Musterrand: die Range
# schrumpft drastisch, sobald das Muster kleiner als der Viewport wird).
# _on_h_scroll()/_on_v_scroll() haengen an valueChanged und ueberschreiben
# canvas._offset_x/_offset_y direkt -- das ungeblockte Zwischen-Signal
# ueberschrieb damit den gerade erst von Zoom-zu-Cursor korrekt berechneten
# Offset mit einem veralteten, falschen Wert, BEVOR der nachfolgende
# (bereits geblockte) setValue()-Aufruf ueberhaupt zum Zug kam -- das Muster
# sprang beim Herauszoomen unerwartet an eine andere Position, statt dass
# der Punkt unter dem Cursor stabil blieb. Fix: blockSignals() umschliesst
# jetzt setRange() UND setValue().
# =============================================================================


def test_zoom_out_near_pattern_edge_does_not_corrupt_offset(qtbot):
    """Vergleicht denselben Zoom-out-Ablauf auf einem nackten Canvas gegen
    einen in CanvasContainer eingebetteten Canvas -- beide muessen exakt
    denselben Offset berechnen. Der Container darf den von Zoom-zu-Cursor
    berechneten Offset nicht durch seine Scrollbar-Synchronisierung
    verfaelschen."""
    from pysticky.core import Pattern
    from pysticky.ui.canvas import CrossStitchCanvas
    from pysticky.ui.widgets.canvas_container import CanvasContainer

    # Referenz: nackter Canvas ohne Scrollbar-Kopplung.
    ref = CrossStitchCanvas()
    qtbot.addWidget(ref)
    ref.resize(400, 300)
    ref.set_pattern(Pattern(width=50, height=50))
    ref._cell_size = 30
    ref._offset_x = -800
    ref._offset_y = -800

    container = CanvasContainer()
    qtbot.addWidget(container)
    canvas = container.canvas
    canvas.resize(400, 300)
    canvas.set_pattern(Pattern(width=50, height=50))
    canvas._cell_size = 30
    canvas._offset_x = -800
    canvas._offset_y = -800
    # Scrollbar auf diesen (stark reingezoomten) Zustand synchronisieren --
    # wie es nach vorherigen Zoom-/Pan-Schritten im echten Betrieb der Fall
    # waere.
    container._update_scrollbars()

    # Mehrere Zoom-out-Schritte, verankert an der oberen linken Ecke des
    # Viewports: Zellgroesse wird klein genug, dass das Muster kleiner als
    # der Viewport wird -- die Scrollbar-Range schrumpft dadurch drastisch
    # (ggf. bis auf (-50, 0)), was den Bug beim vorherigen Code auslöste.
    for _ in range(15):
        ref.zoom_out(0, 0)
        canvas.zoom_out(0, 0)

    assert (canvas._offset_x, canvas._offset_y) == (ref._offset_x, ref._offset_y), (
        "Regression: CanvasContainer._update_scrollbars() ueberschreibt den "
        "Canvas-Offset mit einem veralteten Wert, weil setRange() den noch "
        "unsynchronisierten Scrollbar-Wert ungeblockt clamped und "
        "valueChanged emittiert"
    )
    # Zusaetzlich: Zellgroesse muss ebenfalls uebereinstimmen (schliesst aus,
    # dass beide zufaellig durch unabhaengige Bugs auf denselben Offset
    # gelandet sind).
    assert canvas._cell_size == ref._cell_size
