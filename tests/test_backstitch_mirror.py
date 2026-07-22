# -*- coding: utf-8 -*-
"""Regressionstest: das Rückstich-Werkzeug ignorierte den aktiven
Spiegel-Modus komplett, waehrend jedes andere Zeichenwerkzeug ihn ueber
`get_mirrored_positions()`/`_apply_changes_with_mirror()` respektiert (seit
laengerem als offener Punkt dokumentiert, ungeklaert ob Absicht). Rueckstich-
Koordinaten sind in halben Stichen -- der Spiegel-Mittelpunkt liegt bei
pattern.width/height (nicht /2), beide Endpunkte einer Linie muessen IMMER
mit derselben Transformation gespiegelt werden (nie unabhaengig), sonst
entsteht ein verdrehtes Liniensegment statt eines echten Spiegelbilds."""

import pytest

from pysticky.core import Pattern, Thread
from pysticky.ui.canvas import CrossStitchCanvas
from pysticky.ui.canvas.enums import MirrorMode

pytestmark = pytest.mark.usefixtures("qtbot")


def _make_canvas(qtbot, width=10, height=6):
    pattern = Pattern(name="Test", width=width, height=height)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(pattern)
    return canvas


def test_no_mirror_returns_only_original_line(qtbot):
    canvas = _make_canvas(qtbot)
    canvas._mirror_mode = MirrorMode.NONE

    lines = canvas.get_mirrored_backstitch_lines(2, 2, 4, 4)

    assert lines == [(2, 2, 4, 4)]


def test_horizontal_mirror_flips_both_endpoints_together(qtbot):
    # width=10 -> max_x = 2*10 = 20
    canvas = _make_canvas(qtbot, width=10, height=6)
    canvas._mirror_mode = MirrorMode.HORIZONTAL

    lines = set(canvas.get_mirrored_backstitch_lines(2, 2, 4, 4))

    assert (2, 2, 4, 4) in lines
    assert (18, 2, 16, 4) in lines
    assert len(lines) == 2


def test_vertical_mirror_flips_both_endpoints_together(qtbot):
    # height=6 -> max_y = 2*6 = 12
    canvas = _make_canvas(qtbot, width=10, height=6)
    canvas._mirror_mode = MirrorMode.VERTICAL

    lines = set(canvas.get_mirrored_backstitch_lines(2, 2, 4, 4))

    assert (2, 2, 4, 4) in lines
    assert (2, 10, 4, 8) in lines
    assert len(lines) == 2


def test_quad_mirror_produces_four_consistent_lines(qtbot):
    canvas = _make_canvas(qtbot, width=10, height=6)
    canvas._mirror_mode = MirrorMode.QUAD

    lines = set(canvas.get_mirrored_backstitch_lines(2, 2, 4, 4))

    assert lines == {
        (2, 2, 4, 4),
        (18, 2, 16, 4),
        (2, 10, 4, 8),
        (18, 10, 16, 8),
    }


def test_octal_falls_back_to_quad_for_lines(qtbot):
    """Diagonal-Spiegelung fuer Linien ist bewusst nicht implementiert
    (haerteres Geometrie-Problem als bei Punkten) -- Oktal degradiert wie
    beim Punkt-Pendant auf Quad."""
    canvas = _make_canvas(qtbot, width=10, height=6)
    canvas._mirror_mode = MirrorMode.OCTAL

    octal_lines = set(canvas.get_mirrored_backstitch_lines(2, 2, 4, 4))
    canvas._mirror_mode = MirrorMode.QUAD
    quad_lines = set(canvas.get_mirrored_backstitch_lines(2, 2, 4, 4))

    assert octal_lines == quad_lines


def test_out_of_bounds_mirrored_line_is_dropped(qtbot):
    """Eine gespiegelte Linie, die (teilweise) ausserhalb des Musters
    landen wuerde, wird verworfen statt mit Koordinaten ausserhalb des
    gueltigen Bereichs erzeugt zu werden."""
    canvas = _make_canvas(qtbot, width=10, height=6)
    canvas._mirror_mode = MirrorMode.HORIZONTAL

    # x2=25 liegt bereits ausserhalb (max_x=20) -- Original bleibt drin,
    # aber die gespiegelte Variante haette x2 < 0 und muss fehlen.
    lines = canvas.get_mirrored_backstitch_lines(2, 2, 25, 4)

    assert lines == [(2, 2, 25, 4)]
