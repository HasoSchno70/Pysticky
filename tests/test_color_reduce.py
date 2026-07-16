# -*- coding: utf-8 -*-
"""Tests für core/color_reduce.py (Vorschläge + Auto-Reduzierung)."""

import pytest

from pysticky.core import Pattern, Thread
from pysticky.core.color_reduce import (
    compute_rare_color_replacements,
    rank_similar_colors,
)


@pytest.fixture
def reduce_pattern():
    """Muster mit klaren Häufigkeits- und Ähnlichkeitsverhältnissen.

    Index 0: Rot      #FF0000 — 50 Stiche (häufig)
    Index 1: Dunkelrot #CC0000 — 2 Stiche (selten, nah an Rot)
    Index 2: Blau     #0000FF — 40 Stiche (häufig)
    Index 3: Hellblau #2020FF — 1 Stich  (selten, nah an Blau)
    Index 4: Grün     #00FF00 — 0 Stiche (unbenutzt)
    """
    pattern = Pattern(name="ReduceTest", width=20, height=20)
    pattern.color_entries.clear()
    colors = [
        ("Rot", "#FF0000"),
        ("Dunkelrot", "#CC0000"),
        ("Blau", "#0000FF"),
        ("Hellblau", "#2020FF"),
        ("Grün", "#00FF00"),
    ]
    for name, hex_color in colors:
        pattern.add_color(Thread.from_hex(name, hex_color))

    # Stiche setzen: 50x Rot, 2x Dunkelrot, 40x Blau, 1x Hellblau
    counts = {0: 50, 1: 2, 2: 40, 3: 1}
    x = y = 0
    for idx, n in counts.items():
        for _ in range(n):
            pattern.set_stitch(x, y, idx)
            x += 1
            if x >= 20:
                x = 0
                y += 1
    return pattern


def test_rank_similar_colors_orders_by_distance(reduce_pattern):
    ranked = rank_similar_colors(reduce_pattern, 0)  # Quelle: Rot

    indices = [i for i, _ in ranked]
    assert 0 not in indices, "Quellfarbe darf nicht vorgeschlagen werden"
    assert len(indices) == 4
    assert indices[0] == 1, "Dunkelrot muss der nächste Nachbar von Rot sein"

    distances = [d for _, d in ranked]
    assert distances == sorted(distances)


def test_rank_similar_colors_invalid_index(reduce_pattern):
    assert rank_similar_colors(reduce_pattern, 99) == []
    assert rank_similar_colors(reduce_pattern, -1) == []


def test_auto_reduce_maps_rare_to_nearest_frequent(reduce_pattern):
    replacements = compute_rare_color_replacements(reduce_pattern, max_stitch_count=5)

    assert dict(replacements) == {1: 0, 3: 2}, (
        "Dunkelrot muss auf Rot, Hellblau auf Blau gemappt werden"
    )


def test_auto_reduce_ignores_unused_colors(reduce_pattern):
    replacements = compute_rare_color_replacements(reduce_pattern, max_stitch_count=5)
    sources = {src for src, _ in replacements}
    assert 4 not in sources, "Unbenutzte Farben (0 Stiche) werden nicht ersetzt"


def test_auto_reduce_never_targets_rare_colors(reduce_pattern):
    replacements = compute_rare_color_replacements(reduce_pattern, max_stitch_count=5)
    targets = {dst for _, dst in replacements}
    assert targets <= {0, 2}, "Ziel darf nur eine häufige Farbe sein"


def test_auto_reduce_without_frequent_colors(reduce_pattern):
    # Schwelle so hoch, dass ALLE benutzten Farben als selten gelten
    assert compute_rare_color_replacements(reduce_pattern, max_stitch_count=1000) == []


def test_auto_reduce_without_rare_colors(reduce_pattern):
    assert compute_rare_color_replacements(reduce_pattern, max_stitch_count=0) == []
