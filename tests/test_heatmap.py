# -*- coding: utf-8 -*-
"""
Tests fuer die Heatmap-Algorithmen (ui/dialogs/heatmap_dialog.py).

Nur die reinen Helfer ohne Qt-Abhaengigkeit werden getestet.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np

from pysticky.ui.dialogs.heatmap_dialog import (
    _color_variety_heatmap,
    _density_heatmap,
    _intensity_to_rgb,
)


def test_density_heatmap_empty_grid():
    comp = np.full((10, 10), -1, dtype=np.int32)
    out = _density_heatmap(comp, 4)
    # 10/4 -> ceil = 3 Bloecke pro Dimension
    assert out.shape == (3, 3)
    assert float(out.max()) == 0.0


def test_density_heatmap_full_grid():
    comp = np.zeros((8, 8), dtype=np.int32)  # alle Zellen mit Farbidx 0
    out = _density_heatmap(comp, 4)
    assert out.shape == (2, 2)
    assert np.all(out == 1.0)


def test_density_heatmap_partial_block_normalized():
    comp = np.full((4, 4), -1, dtype=np.int32)
    # Nur ein Stich gesetzt — einziger Block, Dichte = max = 1.0
    comp[0, 0] = 0
    out = _density_heatmap(comp, 4)
    assert out.shape == (1, 1)
    assert float(out[0, 0]) == 1.0


def test_density_heatmap_relative_intensity():
    comp = np.full((4, 8), -1, dtype=np.int32)
    # linker Block 4x4: 4 Stiche; rechter Block 4x4: 1 Stich
    comp[0:2, 0:2] = 0  # 4 Stiche
    comp[0, 4] = 0  # 1 Stich
    out = _density_heatmap(comp, 4)
    assert out.shape == (1, 2)
    assert float(out[0, 0]) == 1.0
    assert float(out[0, 1]) == 0.25


def test_color_variety_heatmap_counts_distinct():
    comp = np.full((4, 4), -1, dtype=np.int32)
    comp[0, 0] = 0
    comp[0, 1] = 1
    comp[1, 0] = 2
    comp[1, 1] = 2  # dup
    out = _color_variety_heatmap(comp, 4)
    assert out.shape == (1, 1)
    # 3 verschiedene Farben, max = 3, normalisiert auf 1.0
    assert float(out[0, 0]) == 1.0


def test_color_variety_heatmap_empty_block_zero():
    comp = np.full((4, 4), -1, dtype=np.int32)
    out = _color_variety_heatmap(comp, 4)
    assert out.shape == (1, 1)
    assert float(out[0, 0]) == 0.0


def test_intensity_to_rgb_bounds():
    # Leerer Block hat eigene "fast-schwarz"-Farbe
    assert _intensity_to_rgb(0.0) == (20, 20, 60)
    # Mitte und Ende liegen im Standard-Gradient
    r1, g1, b1 = _intensity_to_rgb(0.5)
    assert (r1, g1, b1) == (0, 255, 0)  # Gruen genau bei 0.5
    r2, g2, b2 = _intensity_to_rgb(1.0)
    assert r2 == 255 and g2 == 0 and b2 == 0


def test_intensity_to_rgb_clamps_out_of_range():
    assert _intensity_to_rgb(-1.0) == (20, 20, 60)
    r, g, b = _intensity_to_rgb(1.5)
    assert (r, g, b) == (255, 0, 0)
