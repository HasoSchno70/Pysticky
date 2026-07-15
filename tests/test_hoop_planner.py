# -*- coding: utf-8 -*-
"""Tests fuer die Rahmenaufteilung (core/hoop_planner.py)."""

import pytest

from pysticky.core.hoop_planner import plan_hoops


def test_pattern_fits_single_hoop(pattern_with_stitches):
    p = pattern_with_stitches
    plan = plan_hoops(p, hoop_width=p.width + 10, hoop_height=p.height + 10)
    assert plan.fits_single_hoop
    assert plan.total_sectors == 1
    assert plan.sectors[0].x_start == 0
    assert plan.sectors[0].y_start == 0


def test_two_by_two_split(pattern_with_stitches):
    """Pattern 20x20, Hoop 12x12 → 2x2 Sektoren noetig."""
    p = pattern_with_stitches
    assert p.width == 20 and p.height == 20
    plan = plan_hoops(p, hoop_width=12, hoop_height=12, overlap=0)
    assert plan.rows == 2 and plan.cols == 2
    assert plan.total_sectors == 4


def test_overlap_reduces_step(pattern_with_stitches):
    """Mit Overlap 2: Hoop 12, Schritt 10 — Pattern 20: 2 Sektoren pro Achse."""
    p = pattern_with_stitches
    plan = plan_hoops(p, hoop_width=12, hoop_height=12, overlap=2)
    # Step = 12 - 2 = 10. (20 - 2) / 10 = 1.8 -> ceil 2 Spalten
    assert plan.cols == 2
    assert plan.rows == 2


def test_sectors_cover_entire_pattern(pattern_with_stitches):
    """Jede Pattern-Zelle muss in mindestens einem Sektor liegen."""
    p = pattern_with_stitches
    plan = plan_hoops(p, hoop_width=12, hoop_height=12, overlap=2)
    covered = [[False] * p.width for _ in range(p.height)]
    for s in plan.sectors:
        for y in range(s.y_start, s.y_end):
            for x in range(s.x_start, s.x_end):
                covered[y][x] = True
    for row in covered:
        assert all(row), "Es gibt unbedeckte Zellen im Pattern"


def test_stitch_count_in_sectors_sums_at_least_total(pattern_with_stitches):
    """Mit Overlap koennen Stiche doppelt gezaehlt werden (eine Zelle in
    mehreren Sektoren), aber die Gesamt-Summe darf nie unter dem
    Pattern-Total liegen."""
    p = pattern_with_stitches
    plan = plan_hoops(p, hoop_width=12, hoop_height=12, overlap=2)
    total_in_sectors = sum(s.stitch_count for s in plan.sectors)
    assert total_in_sectors >= p.total_stitches


def test_invalid_hoop_size_raises():
    from pysticky.core import Pattern

    p = Pattern()
    with pytest.raises(ValueError):
        plan_hoops(p, hoop_width=0, hoop_height=10)
    with pytest.raises(ValueError):
        plan_hoops(p, hoop_width=10, hoop_height=10, overlap=10)


def test_sector_dimensions_at_pattern_edges(pattern_with_stitches):
    """Last sector am Rand sollte zurueckgeschoben sein, damit volle Hoop-Groesse genutzt wird."""
    p = pattern_with_stitches  # 20x20
    plan = plan_hoops(p, hoop_width=15, hoop_height=15, overlap=0)
    # 15 + Step 15 — sector 0 deckt 0..15, sector 1 deckt 15..20 — wird zurueckgeschoben auf 5..20
    last_col_sectors = [s for s in plan.sectors if s.col == plan.cols - 1]
    for s in last_col_sectors:
        assert s.width == 15  # voll genutzt
        assert s.x_end == p.width


def test_sectors_indexed_row_major(pattern_with_stitches):
    p = pattern_with_stitches
    plan = plan_hoops(p, hoop_width=10, hoop_height=10)
    for i, s in enumerate(plan.sectors):
        assert s.index == i
    # Erster Sektor ist (0,0)
    assert plan.sectors[0].row == 0
    assert plan.sectors[0].col == 0
