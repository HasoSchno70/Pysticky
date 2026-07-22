# -*- coding: utf-8 -*-
"""
Tests für den StitchPathOptimizer.
"""

import pytest

from pysticky.core import (
    OptimizationStrategy,
    Pattern,
    StitchPathOptimizer,
    Thread,
    compare_strategies,
)


@pytest.fixture
def pattern_with_stitches():
    """Pattern mit Stichen für Optimierung."""
    p = Pattern(width=20, height=20)
    p.color_entries.clear()
    p.add_color(Thread.from_hex("Rot", "#FF0000"))
    p.add_color(Thread.from_hex("Blau", "#0000FF"))

    # Rot: Diagonale
    for i in range(10):
        p.set_stitch(i, i, 0)
    # Blau: Reihe
    for x in range(10):
        p.set_stitch(x, 15, 1)

    return p


class TestStitchPathOptimizer:
    """Tests für den Optimizer."""

    def test_row_by_row(self, pattern_with_stitches):
        """Test: Zeilenweise Optimierung."""
        optimizer = StitchPathOptimizer(pattern_with_stitches)
        result = optimizer.optimize(OptimizationStrategy.ROW_BY_ROW)
        assert result is not None
        assert result.total_stitches == 20

    def test_nearest_neighbor(self, pattern_with_stitches):
        """Test: Nearest-Neighbor Optimierung."""
        optimizer = StitchPathOptimizer(pattern_with_stitches)
        result = optimizer.optimize(OptimizationStrategy.NEAREST_NEIGHBOR)
        assert result is not None
        assert result.total_stitches == 20

    def test_danish_method(self, pattern_with_stitches):
        """Test: Danish Method."""
        optimizer = StitchPathOptimizer(pattern_with_stitches)
        result = optimizer.optimize(OptimizationStrategy.DANISH_METHOD)
        assert result is not None
        assert result.total_stitches == 20

    def test_column_by_column(self, pattern_with_stitches):
        """Test: Spaltenweise.

        Regression (Test-Qualitaets-Audit): anders als alle Schwester-Tests
        (row_by_row, nearest_neighbor, danish_method) fehlte hier die
        total_stitches-Pruefung -- ein Bug, der fuer diese Strategie
        speziell Stiche verliert (z.B. Off-by-one in der Spalten-Traversal),
        waere durch `result is not None` allein nie aufgefallen.
        """
        optimizer = StitchPathOptimizer(pattern_with_stitches)
        result = optimizer.optimize(OptimizationStrategy.COLUMN_BY_COLUMN)
        assert result is not None
        assert result.total_stitches == 20

    def test_diagonal(self, pattern_with_stitches):
        """Test: Diagonal.

        Regression (Test-Qualitaets-Audit): siehe test_column_by_column --
        gleiche fehlende total_stitches-Pruefung."""
        optimizer = StitchPathOptimizer(pattern_with_stitches)
        result = optimizer.optimize(OptimizationStrategy.DIAGONAL)
        assert result is not None
        assert result.total_stitches == 20

    def test_empty_pattern(self):
        """Test: Leeres Pattern."""
        p = Pattern(width=10, height=10)
        p.color_entries.clear()
        optimizer = StitchPathOptimizer(p)
        result = optimizer.optimize()
        assert result is not None
        assert result.total_stitches == 0

    def test_cancellation(self, pattern_with_stitches):
        """Test: Abbruch der Optimierung."""
        optimizer = StitchPathOptimizer(pattern_with_stitches, cancel_check=lambda: True)
        result = optimizer.optimize()
        assert result is None

    def test_progress_callback(self, pattern_with_stitches):
        """Test: Progress-Callback."""
        progress_values = []

        def on_progress(current, total, message):
            progress_values.append((current, total, message))

        optimizer = StitchPathOptimizer(pattern_with_stitches, progress_callback=on_progress)
        result = optimizer.optimize()
        assert result is not None
        assert len(progress_values) > 0

    def test_statistics(self, pattern_with_stitches):
        """Test: Statistiken abrufen."""
        optimizer = StitchPathOptimizer(pattern_with_stitches)
        result = optimizer.optimize()
        stats = optimizer.get_statistics(result)
        assert stats["total_stitches"] == 20
        assert stats["total_colors"] == 2

    def test_color_paths(self, pattern_with_stitches):
        """Test: Farbpfade."""
        optimizer = StitchPathOptimizer(pattern_with_stitches)
        result = optimizer.optimize()
        assert len(result.color_paths) == 2
        # Jeder Pfad sollte Stiche haben
        for path in result.color_paths:
            assert path.stitch_count > 0
            assert len(path.steps) == path.stitch_count


class TestNearestNeighborGridCorrectness:
    """Regression: die Grid-beschleunigte Ring-Suche in
    `_optimize_nearest_neighbor_fast` (>100 Punkte) verglich frueher ein
    quadriertes `nearest_dist` mit einem linearen Ring-Radius -- der
    Abbruch-Check griff dadurch faktisch nie, was die Grid-Optimierung fuer
    genau den grossen/verstreuten Fall aushebelte, fuer den sie gedacht ist.
    Ergebnis blieb dabei zufaellig korrekt (nur langsamer), aber der Fix an
    der Ring-Abbruchbedingung koennte das leicht kaputt machen -- daher hier
    explizit gegen den bewusst ungekuerzten `_simple`-Bruteforce auf
    identischen, verstreuten Punkten verglichen (gleiche Gesamtdistanz =
    beide finden denselben optimalen Greedy-Pfad)."""

    def _scattered_positions(self, count: int) -> list[tuple[int, int]]:
        import random

        rng = random.Random(42)
        return [(rng.randint(0, 5000), rng.randint(0, 5000)) for _ in range(count)]

    def test_fast_grid_matches_bruteforce_on_scattered_points(self, empty_pattern):
        optimizer = StitchPathOptimizer(empty_pattern)
        positions = self._scattered_positions(150)  # > 100 -> Grid-Pfad

        fast_result = optimizer._optimize_nearest_neighbor_fast(positions)
        simple_result = optimizer._optimize_nearest_neighbor_simple(positions)

        assert set(fast_result) == set(positions)  # keine Punkte verloren/dupliziert

        def total_distance(ordered):
            return sum(
                optimizer._distance_fast(x1, y1, x2, y2)
                for (x1, y1), (x2, y2) in zip(ordered, ordered[1:])
            )

        assert total_distance(fast_result) == pytest.approx(total_distance(simple_result))


class TestCompareStrategies:
    """Tests für Strategievergleich."""

    def test_compare_all(self, pattern_with_stitches):
        """Test: Alle Strategien vergleichen."""
        results = compare_strategies(pattern_with_stitches)
        assert results is not None
        assert len(results) == len(OptimizationStrategy)

    def test_compare_cancel(self, pattern_with_stitches):
        """Test: Vergleich abbrechen."""
        results = compare_strategies(pattern_with_stitches, cancel_check=lambda: True)
        assert results is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
