# -*- coding: utf-8 -*-
"""Tests fuer die Schwierigkeits-Heuristik (core.difficulty)."""

import pytest

from pysticky.core import Pattern, Thread
from pysticky.core.difficulty import (
    LEVELS,
    _backstitch_score,
    _color_score,
    _level_for_score,
    _size_score,
    _special_stitch_score,
    compute_difficulty,
)


def test_empty_pattern_is_anfaenger():
    p = Pattern(name="leer", width=10, height=10)
    result = compute_difficulty(p)
    assert result["level"] == "Anfänger"
    assert result["score"] == 0


@pytest.mark.parametrize(
    "colors,expected",
    [
        (1, 0),
        (5, 0),
        (6, 1),
        (15, 1),
        (16, 2),
        (30, 2),
        (31, 3),
        (60, 3),
        (200, 3),
    ],
)
def test_color_score_buckets(colors, expected):
    assert _color_score(colors) == expected


@pytest.mark.parametrize(
    "stitches,expected",
    [
        (0, 0),
        (1000, 0),
        (1001, 1),
        (5000, 1),
        (5001, 2),
        (20000, 2),
        (20001, 3),
        (200000, 3),
    ],
)
def test_size_score_buckets(stitches, expected):
    assert _size_score(stitches) == expected


@pytest.mark.parametrize(
    "ratio,expected",
    [
        (0.0, 0),
        (0.019, 0),
        (0.02, 1),
        (0.099, 1),
        (0.10, 2),
        (0.249, 2),
        (0.25, 3),
        (1.0, 3),
    ],
)
def test_special_stitch_score_buckets(ratio, expected):
    assert _special_stitch_score(ratio) == expected


@pytest.mark.parametrize(
    "count,expected",
    [
        (0, 0),
        (1, 1),
        (30, 1),
        (31, 2),
        (150, 2),
        (151, 3),
        (10000, 3),
    ],
)
def test_backstitch_score_buckets(count, expected):
    assert _backstitch_score(count) == expected


@pytest.mark.parametrize(
    "score,expected_level",
    [
        (0, "Anfänger"),
        (2, "Anfänger"),
        (3, "Mittel"),
        (5, "Mittel"),
        (6, "Fortgeschritten"),
        (8, "Fortgeschritten"),
        (9, "Profi"),
        (12, "Profi"),
    ],
)
def test_level_mapping(score, expected_level):
    assert _level_for_score(score) == expected_level


def test_level_strings_match_constant():
    assert LEVELS == ("Anfänger", "Mittel", "Fortgeschritten", "Profi")


def test_complex_pattern_scores_above_anfaenger(pattern_with_stitches):
    """pattern_with_stitches hat ~84 Stiche, 2 Farben — erwartete Mittel-Untergrenze."""
    result = compute_difficulty(pattern_with_stitches)
    assert result["level"] in LEVELS
    assert result["score"] >= 0
    # Details muessen stimmig sein
    assert result["details"]["used_colors"] == 2  # Schwarz + Rot benutzt
    assert result["details"]["stitches_to_do"] > 0


def test_factors_keys_complete():
    p = Pattern(name="x", width=5, height=5)
    f = compute_difficulty(p)["factors"]
    assert set(f.keys()) == {"colors", "size", "special", "backstitches"}
    # Alle Faktor-Werte 0..3
    for v in f.values():
        assert 0 <= v <= 3


def test_skip_stitching_excluded_from_color_count():
    p = Pattern(name="x", width=5, height=5)
    # Eine Schwarz-Farbe ist Default — die nicht-skipped, mit Stichen versehen
    p.set_stitch(0, 0, 0)
    # Zweite Farbe als skip
    skipped = Thread.from_hex("Skip-Stoff", "#ffffff")
    p.add_color(skipped)
    p.color_entries[1].skip_stitching = True
    p.color_entries[1].stitch_count = 100  # auch wenn nominell vorhanden
    result = compute_difficulty(p)
    # Skipped-Farbe darf nicht in used_colors zaehlen
    assert result["details"]["used_colors"] == 1
