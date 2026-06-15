# -*- coding: utf-8 -*-
"""
Tests fuer den BEAD-Stichtyp (Perlen).
"""

from pysticky.core.stitch import FLIP_H_MAP, FLIP_V_MAP, ROTATE_CCW_MAP, ROTATE_CW_MAP, StitchType
from pysticky.core.stitch_shapes import (
    bead_radius_factor,
    is_bead,
    is_french_knot,
    is_partial_stitch,
)
from pysticky.io.export_common import svg_shape_for_stitch


def test_bead_enum_value_is_10():
    assert StitchType.BEAD.value == 10


def test_is_bead_returns_true_only_for_10():
    assert is_bead(10) is True
    for other in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9):
        assert is_bead(other) is False


def test_is_bead_distinct_from_french_knot():
    # Perle und French Knot sind unterschiedliche Konzepte
    assert is_bead(10) and not is_french_knot(10)
    assert is_french_knot(9) and not is_bead(9)


def test_bead_is_not_a_partial_stitch():
    # Perlen sind keine Teil-Stiche (Polygone)
    assert is_partial_stitch(10) is False


def test_bead_radius_factor_in_valid_range():
    # Sollte deutlich groesser sein als French-Knot (0.18) aber unter 0.5
    factor = bead_radius_factor()
    assert 0.2 < factor < 0.5


def test_bead_invariant_under_flip_and_rotate():
    """Perlen sind rund — Spiegeln/Rotation aendern sie nicht."""
    assert FLIP_H_MAP[10] == 10
    assert FLIP_V_MAP[10] == 10
    assert ROTATE_CW_MAP[10] == 10
    assert ROTATE_CCW_MAP[10] == 10


def test_svg_shape_for_bead_contains_circles():
    """SVG-Output fuer BEAD enthaelt Hintergrund + Hauptkugel + Glanzpunkt."""
    svg = svg_shape_for_stitch(10, 0.0, 0.0, 10.0, 10.0, (128, 64, 200))
    # Hintergrund (Rect) + Hauptkreis + Glanzkreis = 3 Elemente
    assert svg.count("<circle") == 2
    assert "<rect" in svg
    assert "rgb(128,64,200)" in svg


def test_bead_count_in_pattern_statistics(pattern_with_colors):
    """get_statistics()['bead_count'] zaehlt Perlen separat von Stichen."""
    p = pattern_with_colors
    # Drei Perlen, zwei volle Stiche setzen
    p.set_stitch(1, 1, 1, stitch_type=10)
    p.set_stitch(2, 2, 1, stitch_type=10)
    p.set_stitch(3, 3, 1, stitch_type=10)
    p.set_stitch(5, 5, 2, stitch_type=0)
    p.set_stitch(6, 6, 2, stitch_type=0)
    stats = p.get_statistics()
    assert stats["bead_count"] == 3
    # Volle Stiche bleiben in total_stitches drin
    assert stats["total_stitches"] >= 2


def test_bead_count_ignores_invisible_layers(pattern_with_colors):
    """Unsichtbare Layer beeinflussen die Perlen-Zaehlung nicht."""
    p = pattern_with_colors
    p.set_stitch(0, 0, 1, stitch_type=10)
    p.layer_stack.add_layer("Hidden")
    p.layer_stack.active_index = 1
    p.set_stitch(1, 1, 1, stitch_type=10)
    p.layer_stack.add_layer("Visible")  # wieder sichtbar — dritte
    p.layer_stack.active_index = 2
    p.set_stitch(2, 2, 1, stitch_type=10)
    p.layer_stack.layers[1].visible = False  # mittlere unsichtbar

    stats = p.get_statistics()
    # Layer 0 (1) + Layer 2 (1) sichtbar — Layer 1 (1) unsichtbar
    assert stats["bead_count"] == 2
