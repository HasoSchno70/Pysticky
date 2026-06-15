# -*- coding: utf-8 -*-
"""Tests fuer Confetti-Reduction beim Bildimport."""

import numpy as np

from pysticky.core.confetti_reduction import NO_STITCH, reduce_confetti


def test_no_op_with_min_run_size_1():
    """min_run_size=1 ist No-Op."""
    grid = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=np.int16)
    result = reduce_confetti(grid, min_run_size=1)
    assert np.array_equal(result, grid)


def test_no_op_with_min_run_size_0():
    """min_run_size=0 ist auch No-Op (defensive)."""
    grid = np.array([[0, 1], [1, 0]], dtype=np.int16)
    result = reduce_confetti(grid, min_run_size=0)
    assert np.array_equal(result, grid)


def test_isolated_pixel_gets_absorbed():
    """Einzelner Pixel mit anderer Farbe wird zur dominanten Nachbarfarbe."""
    # 5x5 alle Farbe 0, ein Pixel in der Mitte = Farbe 1
    grid = np.zeros((5, 5), dtype=np.int16)
    grid[2, 2] = 1

    result = reduce_confetti(grid, min_run_size=2)
    assert result[2, 2] == 0
    assert np.all(result == 0)


def test_large_cluster_is_preserved():
    """Cluster groesser als min_run_size bleibt erhalten."""
    # 5x5 alle Farbe 0, 2x2-Block in der Mitte = Farbe 1
    grid = np.zeros((5, 5), dtype=np.int16)
    grid[1:3, 1:3] = 1

    result = reduce_confetti(grid, min_run_size=3)
    # 2x2-Block hat size=4, also > min_run_size=3 -> bleibt
    assert np.array_equal(result[1:3, 1:3], np.ones((2, 2), dtype=np.int16))


def test_cluster_below_threshold_is_absorbed():
    """Cluster mit size < min_run_size wird absorbiert."""
    grid = np.zeros((5, 5), dtype=np.int16)
    grid[1:3, 1:3] = 1  # 2x2 = 4 Pixel

    result = reduce_confetti(grid, min_run_size=5)
    # 4 < 5 -> absorbiert
    assert np.all(result == 0)


def test_no_stitch_pixels_are_preserved():
    """NO_STITCH-Zellen werden nicht angefasst."""
    grid = np.full((3, 3), NO_STITCH, dtype=np.int16)
    grid[0, 0] = 0
    grid[1, 1] = 1  # isolated, surrounded by NO_STITCH

    result = reduce_confetti(grid, min_run_size=2)
    # Pixel (1,1) hat keine farbige Nachbarn -> bleibt (kein Fallback-Move)
    # Wichtig: NO_STITCH-Pixel sollen NO_STITCH bleiben
    assert result[0, 1] == NO_STITCH
    assert result[2, 2] == NO_STITCH


def test_isolated_pixel_with_no_neighbor_stays_unchanged():
    """Wenn ein kleiner Cluster keinen Nachbarn anderer Farbe hat, bleibt er."""
    grid = np.full((3, 3), NO_STITCH, dtype=np.int16)
    grid[1, 1] = 5

    result = reduce_confetti(grid, min_run_size=2)
    # Kein anderer Cluster zum Anschliessen -> bleibt
    assert result[1, 1] == 5


def test_two_colors_isolated_pixels_swap_correctly():
    """Bei zwei Farben mit isolierten Pixeln gewinnt der dominante Nachbar."""
    # 5x5: Linke Haelfte Farbe 0, rechte Haelfte Farbe 1, ein 1-Pixel in der
    # 0-Region.
    grid = np.zeros((5, 5), dtype=np.int16)
    grid[:, 3:] = 1
    grid[2, 1] = 1  # Confetti in der 0-Region

    result = reduce_confetti(grid, min_run_size=2)
    assert result[2, 1] == 0  # Confetti wird zu 0


def test_iterative_merging():
    """Nach erstem Reduce-Pass entstehende kleine Cluster werden in der
    naechsten Iteration auch reduziert."""
    # Aufbau: Zwei isolierte Confetti-Pixel der Farbe 1 nebeneinander
    # in einem 0er-Feld. Zusammen waeren sie 2 Pixel — beim min_run=3
    # wuerden beide reduziert (nicht zu einem 2-Cluster gemerged, sondern
    # weil sie auch nach Reassign-Pass kleiner sind).
    grid = np.zeros((5, 5), dtype=np.int16)
    grid[2, 1] = 1
    grid[2, 3] = 1  # NICHT direkt benachbart (zwischen ihnen ist 0)

    result = reduce_confetti(grid, min_run_size=3)
    assert np.all(result == 0)


def test_empty_grid():
    """Leeres Grid (alle NO_STITCH) bleibt unveraendert."""
    grid = np.full((3, 3), NO_STITCH, dtype=np.int16)
    result = reduce_confetti(grid, min_run_size=2)
    assert np.array_equal(result, grid)


def test_zero_size_grid():
    """Edge-Case: 0x0-Grid."""
    grid = np.zeros((0, 0), dtype=np.int16)
    result = reduce_confetti(grid, min_run_size=2)
    assert result.shape == (0, 0)


def test_original_grid_not_mutated():
    """Original-Grid wird nicht modifiziert."""
    grid = np.zeros((3, 3), dtype=np.int16)
    grid[1, 1] = 1
    grid_copy = grid.copy()

    reduce_confetti(grid, min_run_size=2)
    assert np.array_equal(grid, grid_copy)


def test_realistic_photo_pattern():
    """Realistischer Fall: Foto-aehnliches Pattern mit vielen Einzelpixeln."""
    # 10x10 mit Streumuster
    np.random.seed(42)
    grid = np.zeros((10, 10), dtype=np.int16)
    # 20 zufaellige Einzelpixel der Farbe 1
    for _ in range(20):
        y = np.random.randint(0, 10)
        x = np.random.randint(0, 10)
        grid[y, x] = 1

    # Vor: viele Confetti-Pixel
    confetti_before = int(np.sum(grid == 1))

    result = reduce_confetti(grid, min_run_size=3)
    confetti_after = int(np.sum(result == 1))

    # Nach: weniger Farbe-1-Pixel (Confetti reduziert)
    assert confetti_after < confetti_before


def test_integration_with_image_import_settings():
    """ImportSettings akzeptiert confetti_min_run_size-Parameter."""
    from pysticky.core.image_import import ImportSettings

    s = ImportSettings(confetti_min_run_size=3)
    assert s.confetti_min_run_size == 3

    # Default ist 1 (aus)
    s_default = ImportSettings()
    assert s_default.confetti_min_run_size == 1
