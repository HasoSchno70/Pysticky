# -*- coding: utf-8 -*-
"""Regressionstest (Runde 25): OptimizedCrossStitchCanvas._paint() deaktivierte
den Chunk-Cache komplett, sobald should_skip_details() 'use_simplified'
zurückgab (cell_size < 6) -- genau der Zoom-Stufe, bei der am meisten Zellen
gleichzeitig sichtbar sind. Es gibt aber gar keinen tatsächlich vereinfachten
Rendering-Pfad: _draw_all_cells ist exakt derselbe teure Pro-Zelle-Renderer
wie sonst auch. Bei einem großen Muster (Performance-Modus aktiv) und
weit rausgezoomter Ansicht (cell_size < 6) fiel das Rendering dadurch auf den
ungecachten O(Breite×Höhe)-Pfad zurück -- eine Performance-Klippe genau
umgekehrt zur Absicht des Chunk-Cache-Systems."""

import pytest
from PySide6.QtGui import QPainter, QPixmap

from pysticky.core import Pattern, Thread

pytestmark = pytest.mark.usefixtures("qtbot")


def _large_pattern() -> Pattern:
    pattern = Pattern(name="Gross", width=210, height=210)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    return pattern


def test_chunk_cache_stays_active_at_very_small_cell_size(qtbot):
    from pysticky.ui.canvas import OptimizedCrossStitchCanvas

    canvas = OptimizedCrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(_large_pattern())
    assert canvas._perf_manager.enabled

    canvas._cell_size = 3  # < 6 -> should_skip_details() liefert use_simplified=True
    canvas.resize(400, 400)

    calls = {"chunked": 0, "direct": 0}
    orig_chunked = canvas._draw_cells_chunked
    orig_direct = canvas._draw_all_cells

    def _spy_chunked(*args, **kwargs):
        calls["chunked"] += 1
        return orig_chunked(*args, **kwargs)

    def _spy_direct(*args, **kwargs):
        calls["direct"] += 1
        return orig_direct(*args, **kwargs)

    canvas._draw_cells_chunked = _spy_chunked
    canvas._draw_all_cells = _spy_direct

    # Direkter _paint()-Aufruf auf einem QPixmap statt repaint()/paintEvent
    # ueber die Fenster-Ereignisschleife -- unabhaengig von Fenster-
    # Sichtbarkeit/Fokus-Timing, das sich innerhalb der vollen Testsuite
    # (viele andere Widgets/Fenster) als unzuverlaessig erwiesen hat.
    pixmap = QPixmap(canvas.width(), canvas.height())
    painter = QPainter(pixmap)
    try:
        canvas._paint(painter)
    finally:
        painter.end()

    assert calls["chunked"] == 1, (
        "Regression: bei cell_size < 6 wurde der Chunk-Cache umgangen und "
        "stattdessen der ungecachte Direkt-Renderer benutzt"
    )
    assert calls["direct"] == 0
