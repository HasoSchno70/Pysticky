# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 21): BackstitchTool._to_half_stitch() validierte nie
gegen die Musterbreite/-hoehe -- anders als jedes andere Tool (die alle
_is_valid_pos() vor dem Zurueckgeben pruefen). Ein Klick im Canvas-Rand
ausserhalb des Musters (z.B. bei Zoom < 100% oder direkt an Zeile/Spalte 0)
lieferte unbegrenzte, teils negative Halb-Stich-Koordinaten -- ein dauerhaft
ausserhalb des Musters liegender Rueckstich landete unbemerkt im Pattern.
"""

from pysticky.core import Pattern
from pysticky.ui.tools.backstitch_tool import BackstitchTool
from pysticky.ui.tools.base_tool import ToolContext


def _make_ctx(pattern, screen_x=0, screen_y=0):
    return ToolContext(
        canvas=None,
        pattern=pattern,
        current_color_index=0,
        grid_x=0,
        grid_y=0,
        screen_x=screen_x,
        screen_y=screen_y,
        cell_size=12,
        offset_x=0,
        offset_y=0,
    )


def test_to_half_stitch_clamps_negative_coordinates():
    pattern = Pattern(width=5, height=5)
    tool = BackstitchTool()
    ctx = _make_ctx(pattern)

    half_x, half_y = tool._to_half_stitch(-500, -500, ctx)

    assert half_x == 0
    assert half_y == 0


def test_to_half_stitch_clamps_coordinates_past_pattern_end():
    pattern = Pattern(width=5, height=5)
    tool = BackstitchTool()
    ctx = _make_ctx(pattern)

    half_x, half_y = tool._to_half_stitch(10_000, 10_000, ctx)

    assert half_x == pattern.width * 2
    assert half_y == pattern.height * 2


def test_to_half_stitch_within_bounds_is_unaffected():
    pattern = Pattern(width=5, height=5)
    tool = BackstitchTool()
    ctx = _make_ctx(pattern)

    # Zelle (2,2), Zentrum -> (5, 5) in halben Stichen
    half_x, half_y = tool._to_half_stitch(2 * 12 + 6, 2 * 12 + 6, ctx)

    assert 0 <= half_x <= pattern.width * 2
    assert 0 <= half_y <= pattern.height * 2
