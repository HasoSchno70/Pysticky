# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 12): _draw_backstitches() wendete keine
Farbblindheits-Simulation an, obwohl der Zellen-Renderpfad
(_draw_layer_cells in derselben Datei) das schon lange tut. Mit aktivem
colorblind_mode blieben Rueckstich-Konturlinien in ihrer echten (potenziell
nicht unterscheidbaren) Farbe -- der Modus wirkte auf Konturen schlicht
nicht.
"""

import pytest
from PySide6.QtGui import QImage, QPainter

from pysticky.core import Pattern, Thread
from pysticky.core.color_blindness import ColorBlindType, simulate_color

pytestmark = pytest.mark.usefixtures("qtbot")


def test_backstitch_color_is_colorblind_simulated(qtbot):
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)

    pattern = Pattern(name="BS-Test", width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    canvas.set_pattern(pattern)
    canvas._set_cell_size(40)

    pattern.add_backstitch(0, 0, 4, 0, 0)  # horizontale Linie oben, Farbe 0
    canvas.colorblind_mode = ColorBlindType.PROTANOPIA

    img = QImage(canvas.width(), canvas.height(), QImage.Format.Format_ARGB32)
    img.fill(0)
    painter = QPainter(img)
    canvas._draw_backstitches(painter)
    painter.end()

    half_cell = canvas._cell_size // 2
    x = 2 * half_cell + canvas._offset_x
    y = 0 * half_cell + canvas._offset_y
    pixel = img.pixelColor(x, y)

    expected_r, expected_g, expected_b = simulate_color(255, 0, 0, ColorBlindType.PROTANOPIA)

    # Nicht exakt pruefen (Antialiasing/Schatten-Overlay an der Linienmitte
    # koennten leicht abweichen) -- aber die simulierte Farbe darf NICHT
    # mehr die rohe, nicht-simulierte Rot-Zielfarbe sein.
    assert (pixel.red(), pixel.green(), pixel.blue()) != (255, 0, 0)
    assert abs(pixel.red() - expected_r) <= 5
    assert abs(pixel.green() - expected_g) <= 5
    assert abs(pixel.blue() - expected_b) <= 5


def test_backstitch_color_unsimulated_when_colorblind_off(qtbot):
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)

    pattern = Pattern(name="BS-Test", width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    canvas.set_pattern(pattern)
    canvas._set_cell_size(40)
    pattern.add_backstitch(0, 0, 4, 0, 0)
    canvas.colorblind_mode = ColorBlindType.NONE

    img = QImage(canvas.width(), canvas.height(), QImage.Format.Format_ARGB32)
    img.fill(0)
    painter = QPainter(img)
    canvas._draw_backstitches(painter)
    painter.end()

    half_cell = canvas._cell_size // 2
    x = 2 * half_cell + canvas._offset_x
    y = 0 * half_cell + canvas._offset_y
    pixel = img.pixelColor(x, y)

    assert (pixel.red(), pixel.green(), pixel.blue()) == (255, 0, 0)
