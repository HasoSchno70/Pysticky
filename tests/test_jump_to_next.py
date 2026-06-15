# -*- coding: utf-8 -*-
"""Tests fuer die Jump-to-next-stitch-Logik im Canvas (reine Algorithmus-Tests).

Wir testen die Kern-Logik direkt uber eine Mini-Reimplementierung — der
Canvas selbst braucht eine QApplication, was in der Test-Suite ueber
pytest-qt ginge, aber fuer Algorithmus-Tests ist's overkill.

Der Algorithmus ist:
1. composite_grid: numpy-Array mit Color-Indices (-1 = leer)
2. completion: bool-Array, True wo erledigt
3. Reading-order: y * W + x sortiert
4. forward: erste Zelle mit key > current
5. backward: letzte Zelle mit key < current
"""

import numpy as np


def jump_to_next(composite, completion, color_idx, current, width, *, forward=True):
    """Reine Algorithmus-Variante zum Testen — Spiegel der Canvas-Logik."""
    target_mask = (composite == color_idx) & ~completion
    positions = np.argwhere(target_mask)
    if len(positions) == 0:
        return None
    order = positions[:, 0] * width + positions[:, 1]
    order_sorted = np.sort(order)

    if current is None:
        cur_key = -1 if forward else width * 10**6
    else:
        cx, cy = current
        cur_key = cy * width + cx

    if forward:
        mask_next = order_sorted > cur_key
        target_key = int(order_sorted[mask_next][0]) if mask_next.any() else int(order_sorted[0])
    else:
        mask_prev = order_sorted < cur_key
        target_key = int(order_sorted[mask_prev][-1]) if mask_prev.any() else int(order_sorted[-1])
    ty, tx = divmod(target_key, width)
    return (int(tx), int(ty))


def test_jump_finds_first_cell_when_no_cursor():
    grid = np.array(
        [
            [-1, 0, -1],
            [-1, 0, -1],
            [0, -1, -1],
        ]
    )
    completion = np.zeros_like(grid, dtype=bool)
    assert jump_to_next(grid, completion, 0, None, 3, forward=True) == (1, 0)


def test_jump_skips_completed():
    grid = np.array(
        [
            [-1, 0, -1],
            [-1, 0, -1],
            [0, -1, -1],
        ]
    )
    completion = np.zeros_like(grid, dtype=bool)
    completion[0, 1] = True  # erste Zelle abgehakt
    assert jump_to_next(grid, completion, 0, None, 3, forward=True) == (1, 1)


def test_jump_forward_advances_in_reading_order():
    grid = np.array(
        [
            [-1, 0, 0],
            [0, -1, 0],
        ]
    )
    completion = np.zeros_like(grid, dtype=bool)
    cur = (1, 0)  # bei x=1, y=0
    assert jump_to_next(grid, completion, 0, cur, 3, forward=True) == (2, 0)


def test_jump_backward_goes_previous_in_reading_order():
    grid = np.array(
        [
            [-1, 0, 0],
            [0, -1, 0],
        ]
    )
    completion = np.zeros_like(grid, dtype=bool)
    cur = (2, 1)  # letzte
    assert jump_to_next(grid, completion, 0, cur, 3, forward=False) == (0, 1)


def test_jump_wraps_around_at_end():
    grid = np.array([[0, 0, 0]])
    completion = np.zeros_like(grid, dtype=bool)
    cur = (2, 0)  # auf der letzten
    assert jump_to_next(grid, completion, 0, cur, 3, forward=True) == (0, 0)


def test_jump_wraps_around_at_start():
    grid = np.array([[0, 0, 0]])
    completion = np.zeros_like(grid, dtype=bool)
    cur = (0, 0)  # auf der ersten
    assert jump_to_next(grid, completion, 0, cur, 3, forward=False) == (2, 0)


def test_jump_returns_none_when_color_not_present():
    grid = np.array([[-1, -1], [-1, -1]])
    completion = np.zeros_like(grid, dtype=bool)
    assert jump_to_next(grid, completion, 0, None, 2, forward=True) is None


def test_jump_returns_none_when_all_completed():
    grid = np.array([[0, 0]])
    completion = np.array([[True, True]])
    assert jump_to_next(grid, completion, 0, None, 2, forward=True) is None


def test_jump_only_matches_target_color():
    grid = np.array([[1, 0, 1, 0]])
    completion = np.zeros_like(grid, dtype=bool)
    assert jump_to_next(grid, completion, 0, None, 4, forward=True) == (1, 0)
    assert jump_to_next(grid, completion, 0, (1, 0), 4, forward=True) == (3, 0)
    assert jump_to_next(grid, completion, 1, None, 4, forward=True) == (0, 0)
