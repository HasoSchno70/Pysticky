# -*- coding: utf-8 -*-
"""
Tests fuer den Composite-Grid-Cache (io/export_cache.py).

Stellt sicher, dass der Cache exakt dieselben Ergebnisse liefert wie die
Per-Pixel-Funktionen in export_common — dass er also ein transparenter
Performance-Layer ist und keine Verhaltens-Aenderung darstellt.
"""

from pysticky.io.export_cache import CompositeGridCache
from pysticky.io.export_common import (
    count_page_colors,
    get_pixel_color,
    get_pixel_stitch_type,
    get_pixel_symbol,
)


def test_cache_matches_per_pixel_color(pattern_with_stitches):
    cache = CompositeGridCache(pattern_with_stitches)
    p = pattern_with_stitches
    for y in range(p.height):
        for x in range(p.width):
            assert cache.get_color(x, y) == get_pixel_color(p, x, y)


def test_cache_matches_per_pixel_symbol(pattern_with_stitches):
    cache = CompositeGridCache(pattern_with_stitches)
    p = pattern_with_stitches
    for y in range(p.height):
        for x in range(p.width):
            assert cache.get_symbol(x, y) == get_pixel_symbol(p, x, y)


def test_cache_matches_per_pixel_stitch_type(pattern_with_stitches):
    cache = CompositeGridCache(pattern_with_stitches)
    p = pattern_with_stitches
    for y in range(p.height):
        for x in range(p.width):
            assert cache.get_stitch_type(x, y) == get_pixel_stitch_type(p, x, y)


def test_cache_count_page_colors_full(pattern_with_stitches):
    p = pattern_with_stitches
    cache = CompositeGridCache(p)
    assert cache.count_page_colors(0, 0, p.width - 1, p.height - 1) == count_page_colors(
        p, 0, 0, p.width - 1, p.height - 1
    )


def test_cache_count_page_colors_subregion(pattern_with_stitches):
    p = pattern_with_stitches
    cache = CompositeGridCache(p)
    assert cache.count_page_colors(6, 6, 8, 8) == count_page_colors(p, 6, 6, 8, 8)


def test_cache_count_page_colors_clamps_out_of_bounds(pattern_with_stitches):
    p = pattern_with_stitches
    cache = CompositeGridCache(p)
    assert cache.count_page_colors(-5, -5, p.width + 5, p.height + 5) == count_page_colors(
        p, -5, -5, p.width + 5, p.height + 5
    )


def test_cache_respects_invisible_layer(pattern_with_colors):
    p = pattern_with_colors
    p.set_stitch(4, 4, 1)
    p.layer_stack.add_layer("Hidden")
    p.layer_stack.active_index = 1
    p.set_stitch(4, 4, 2)
    p.layer_stack.layers[1].visible = False

    cache = CompositeGridCache(p)
    assert cache.get_color(4, 4) == get_pixel_color(p, 4, 4)


def test_cache_out_of_bounds_returns_none(pattern_with_stitches):
    cache = CompositeGridCache(pattern_with_stitches)
    assert cache.get_color(-1, 0) is None
    assert cache.get_color(0, -1) is None
    assert cache.get_color(pattern_with_stitches.width, 0) is None
    assert cache.get_color(0, pattern_with_stitches.height) is None
    assert cache.get_symbol(-1, 0) == ""
    assert cache.get_stitch_type(-1, 0) == 0
