# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 21): GradientTool._find_closest_color() nutzte
rohe RGB-Euklid-Distanz statt CIEDE2000 (delta_e) -- inkonsistent mit
jeder anderen perzeptuellen Farbabgleich-Stelle im Code (fill_tool.py,
palette_conversion_dialog.py, similar_colors_dialog.py, ...) und konnte
bei einem Farbverlauf sichtbar falsche Zwischenfarben waehlen, da RGB-
Distanz Helligkeits- vs. Farbton-Unterschiede anders gewichtet als die
menschliche Wahrnehmung.
"""

from unittest.mock import patch

from pysticky.core import Pattern, Thread
from pysticky.ui.tools.gradient_tool import GradientTool


def _make_pattern_with_colors():
    pattern = Pattern(width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("A", "#101010"))
    pattern.add_color(Thread.from_hex("B", "#808080"))
    pattern.add_color(Thread.from_hex("C", "#f0f0f0"))
    return pattern


def test_find_closest_color_uses_delta_e():
    from pysticky.core.color_math import delta_e as real_delta_e

    pattern = _make_pattern_with_colors()
    tool = GradientTool()

    with patch("pysticky.ui.tools.gradient_tool.delta_e", side_effect=real_delta_e) as mock_delta_e:
        tool._find_closest_color(pattern, 128, 128, 128)

        assert mock_delta_e.call_count == len(pattern.color_entries)


def test_find_closest_color_picks_perceptually_nearest():
    pattern = _make_pattern_with_colors()
    tool = GradientTool()

    idx = tool._find_closest_color(pattern, 128, 128, 128)
    assert pattern.color_entries[idx].thread.name == "B"

    idx_dark = tool._find_closest_color(pattern, 20, 20, 20)
    assert pattern.color_entries[idx_dark].thread.name == "A"

    idx_light = tool._find_closest_color(pattern, 235, 235, 235)
    assert pattern.color_entries[idx_light].thread.name == "C"
