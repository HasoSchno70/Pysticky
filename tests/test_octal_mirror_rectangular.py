# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 24): MirrorMixin.get_mirrored_positions()'s
OCTAL-Zweig (8-fach/Oktagonal) implementierte eine reine x/y-Transposition
um das Zentrum -- geometrisch nur eine echte 45-Grad-Diagonal-Spiegelung
bei einem QUADRATISCHEN Muster. Bei einem rechteckigen Muster (der
Normalfall) fielen die berechneten Diagonal-Positionen entweder
ausserhalb der Musterbreite/-hoehe (stillschweigend verworfen) oder --
in Zentrumsnaehe -- IN das Muster, aber auf eine geometrisch bedeutungslose
Position (kein echter Spiegelpunkt). "8-fach" degradierte dadurch
unbemerkt zu einer Mischung aus fehlenden und falsch platzierten Punkten.

Sichere Zwischenloesung: Oktal faellt bei width != height auf die
bereits korrekte 4-fach-Spiegelung (Quad) zurueck, statt falsche/fehlende
Diagonal-Positionen zu erzeugen.
"""

import pytest

from pysticky.core import Pattern, Thread
from pysticky.ui.canvas import CrossStitchCanvas
from pysticky.ui.canvas.enums import MirrorMode

pytestmark = pytest.mark.usefixtures("qtbot")


def _make_canvas(qtbot, width, height):
    pattern = Pattern(name="Test", width=width, height=height)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(pattern)
    canvas._mirror_mode = MirrorMode.OCTAL
    return canvas


def test_octal_gives_up_to_eight_positions_for_square_pattern(qtbot):
    canvas = _make_canvas(qtbot, 100, 100)

    positions = canvas.get_mirrored_positions(20, 70)

    assert len(positions) <= 8
    assert len(positions) > 4, "Quadratisches Muster muss echte Diagonal-Punkte liefern"
    for x, y in positions:
        assert 0 <= x < 100
        assert 0 <= y < 100


def test_octal_falls_back_to_quad_for_rectangular_pattern(qtbot):
    """Vorher: fuer ein 100x50-Muster in Zentrumsnaehe (48,24) lieferte
    derselbe Aufruf eine zusaetzliche, geometrisch bedeutungslose Position
    (49,23) -- keine echte Spiegelung von irgendetwas, nur ein Artefakt der
    quadrat-spezifischen Transpositionsformel. Jetzt: exakt dieselben
    Positionen wie QUAD (max. 4), niemals eine zusaetzliche falsche."""
    canvas_octal = _make_canvas(qtbot, 100, 50)
    octal_positions = set(canvas_octal.get_mirrored_positions(48, 24))

    canvas_quad = _make_canvas(qtbot, 100, 50)
    canvas_quad._mirror_mode = MirrorMode.QUAD
    quad_positions = set(canvas_quad.get_mirrored_positions(48, 24))

    assert octal_positions == quad_positions
    assert len(octal_positions) <= 4
    assert (49, 23) not in octal_positions, (
        "Regression: (49,23) war die geometrisch bedeutungslose Zusatzposition"
    )


def test_octal_rectangular_never_returns_out_of_bounds_positions(qtbot):
    canvas = _make_canvas(qtbot, 100, 50)

    for x, y in [(20, 10), (48, 24), (5, 45), (95, 5)]:
        positions = canvas.get_mirrored_positions(x, y)
        for px, py in positions:
            assert 0 <= px < 100
            assert 0 <= py < 50
