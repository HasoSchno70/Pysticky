# -*- coding: utf-8 -*-
"""
Smoke-Tests fuer die Canvas-Klassen.

Verifiziert grundlegende Eigenschaften und das Verhalten von paintEvent
bei leerem Pattern (frueher: QPainter-Leak via early-return ohne end()).
"""

import pytest

# pytest-qt's qtbot-Fixture sorgt fuer eine lebende QApplication
pytestmark = pytest.mark.usefixtures("qtbot")


def test_canvas_imports():
    """CrossStitchCanvas und Optimized-Variante sind beide importierbar."""
    from pysticky.ui.canvas import CrossStitchCanvas, OptimizedCrossStitchCanvas

    assert issubclass(OptimizedCrossStitchCanvas, CrossStitchCanvas)


def test_canvas_construct_without_pattern(qtbot):
    """Canvas laesst sich ohne Pattern bauen."""
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    assert canvas._pattern is None


def test_canvas_paint_with_no_pattern_does_not_leak_painter(qtbot):
    """
    paintEvent mit None-Pattern darf den Painter nicht haengen lassen.

    Frueher gab es einen early-return zwischen QPainter(self) und impliziter
    Finalisierung. Mit dem try/finally-Pattern muss paintEvent sauber
    durchlaufen.
    """
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.resize(200, 200)
    canvas.show()
    qtbot.waitExposed(canvas)
    canvas.repaint()  # erzwingt synchron einen paintEvent


def test_canvas_set_and_paint_pattern(qtbot, pattern_with_stitches):
    """Mit gesetztem Pattern darf ein Repaint nicht crashen."""
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(pattern_with_stitches)
    canvas.resize(400, 400)
    canvas.show()
    qtbot.waitExposed(canvas)
    canvas.repaint()
    assert canvas._pattern is pattern_with_stitches


def test_optimized_canvas_paint_with_no_pattern(qtbot):
    """Selbiges fuer die optimierte Variante."""
    from pysticky.ui.canvas import OptimizedCrossStitchCanvas

    canvas = OptimizedCrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.resize(200, 200)
    canvas.show()
    qtbot.waitExposed(canvas)
    canvas.repaint()
    assert canvas._pattern is None


def test_optimized_canvas_paint_with_pattern(qtbot, pattern_with_stitches):
    """Optimized-Canvas mit Pattern zeichnet und misst Frame-Zeit."""
    from pysticky.ui.canvas import OptimizedCrossStitchCanvas

    canvas = OptimizedCrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(pattern_with_stitches)
    canvas.resize(400, 400)
    canvas.show()
    qtbot.waitExposed(canvas)
    canvas.repaint()
    # Frame-Timing wird gemessen
    assert canvas._last_frame_time >= 0.0


def test_canvas_zoom_changes_cell_size(qtbot, pattern_with_stitches):
    """zoom_in/out aendert den effektiven cell_size."""
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(pattern_with_stitches)

    initial = canvas._cell_size
    canvas.zoom_in()
    assert canvas._cell_size > initial
    canvas.zoom_out()
    canvas.zoom_out()
    assert canvas._cell_size < initial


def test_canvas_fabric_pixmap_cached_per_cell_size(qtbot):
    """Aida-Textur-Pixmap wird bei gleichem cell_size wiederverwendet."""
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)

    p1 = canvas._get_fabric_pixmap()
    p2 = canvas._get_fabric_pixmap()
    assert p1 is p2, "Bei gleichem cell_size muss derselbe QPixmap geliefert werden"


def test_canvas_fabric_pixmap_invalidated_on_zoom(qtbot, pattern_with_stitches):
    """Nach Zoom-Wechsel wird die Pixmap neu generiert (anderer cell_size)."""
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(pattern_with_stitches)

    p_before = canvas._get_fabric_pixmap()
    cs_before = canvas._fabric_pixmap_cell_size
    canvas.zoom_in()
    p_after = canvas._get_fabric_pixmap()
    assert canvas._fabric_pixmap_cell_size != cs_before
    assert p_after is not p_before


def test_canvas_fabric_texture_toggle(qtbot):
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    assert canvas.show_fabric_texture is True  # Default an

    canvas.show_fabric_texture = False
    assert canvas.show_fabric_texture is False
