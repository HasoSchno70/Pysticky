# -*- coding: utf-8 -*-
"""
Tests fuer MirrorMixin.mirror_selection_horizontal()/_vertical().

Regression fuer einen Absturz: beide Methoden riefen `layer.clear_stitch()`
auf, was auf Layer nicht existiert (richtig waere `remove_stitch()`) --
ausgeloest, sobald eine Spiegelung eine Zelle leeren musste (Quellzelle der
Spiegelung war leer). Reproduzierbar ueber die "Spiegel H"/"Spiegel V"-
Werkzeuge, sobald die Auswahl mindestens eine leere Zelle enthaelt.
"""

import pytest
from PySide6.QtCore import QRect

# pytest-qt's qtbot-Fixture sorgt fuer eine lebende QApplication
pytestmark = pytest.mark.usefixtures("qtbot")


def _make_canvas(pattern, qtbot):
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(pattern)
    return canvas


def test_mirror_horizontal_clears_cell_whose_source_was_empty(pattern_with_colors, qtbot):
    """Eine Zelle, deren gespiegeltes Gegenstueck leer war, muss nach der
    Spiegelung leer sein -- ohne AttributeError auf clear_stitch()."""
    pattern = pattern_with_colors
    pattern.set_stitch(2, 5, 0)
    # (3, 5) bleibt bewusst leer.

    canvas = _make_canvas(pattern, qtbot)
    canvas._selection = QRect(2, 5, 2, 1)  # deckt (2,5) und (3,5) ab

    assert canvas.mirror_selection_horizontal() is True

    layer = pattern.active_layer
    assert layer.get_stitch(2, 5) is None  # Quelle war leer -> jetzt leer
    assert layer.get_stitch(3, 5) == 0  # Farbe ist auf die andere Seite gewandert


def test_mirror_vertical_clears_cell_whose_source_was_empty(pattern_with_colors, qtbot):
    """Analog fuer die vertikale Spiegelung."""
    pattern = pattern_with_colors
    pattern.set_stitch(4, 2, 1)
    # (4, 3) bleibt bewusst leer.

    canvas = _make_canvas(pattern, qtbot)
    canvas._selection = QRect(4, 2, 1, 2)  # deckt (4,2) und (4,3) ab

    assert canvas.mirror_selection_vertical() is True

    layer = pattern.active_layer
    assert layer.get_stitch(4, 2) is None
    assert layer.get_stitch(4, 3) == 1


def test_mirror_horizontal_without_selection_returns_false(pattern_with_colors, qtbot):
    """Ohne aktive Auswahl passiert nichts (kein Crash, kein Effekt)."""
    canvas = _make_canvas(pattern_with_colors, qtbot)
    assert canvas.mirror_selection_horizontal() is False
