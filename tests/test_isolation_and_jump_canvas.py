# -*- coding: utf-8 -*-
"""Integration: Canvas + Pattern fuer Isolation und Jump.

Braucht eine QApplication — pytest-qt liefert die ueber das `qtbot`-Fixture.
"""

import pytest


@pytest.fixture
def patterned_canvas(qtbot, pattern_with_stitches):
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(pattern_with_stitches)
    canvas.resize(800, 600)
    return canvas, pattern_with_stitches


def test_isolation_state_default_none(patterned_canvas):
    canvas, _ = patterned_canvas
    assert canvas.isolate_color_index is None


def test_set_isolate_color_persists_and_clears(patterned_canvas):
    canvas, _ = patterned_canvas
    canvas.set_isolate_color(2)
    assert canvas.isolate_color_index == 2
    canvas.set_isolate_color(None)
    assert canvas.isolate_color_index is None


def test_set_pattern_resets_isolation(patterned_canvas, empty_pattern):
    canvas, _ = patterned_canvas
    canvas.set_isolate_color(2)
    canvas.set_pattern(empty_pattern)
    assert canvas.isolate_color_index is None
    assert canvas.stitch_cursor is None


def test_jump_finds_red_stitch(patterned_canvas):
    """pattern_with_stitches hat innerhalb (6..13, 6..13) Rot (idx 2)."""
    canvas, _ = patterned_canvas
    canvas.set_current_color(2)  # Rot
    found = canvas.jump_to_next_stitch(forward=True)
    assert found is True
    assert canvas.stitch_cursor is not None
    cx, cy = canvas.stitch_cursor
    # Erste Rot-Zelle in Reading-Order ist (6, 6)
    assert (cx, cy) == (6, 6)


def test_jump_advances(patterned_canvas):
    canvas, _ = patterned_canvas
    canvas.set_current_color(2)
    canvas.jump_to_next_stitch(forward=True)
    first = canvas.stitch_cursor
    canvas.jump_to_next_stitch(forward=True)
    second = canvas.stitch_cursor
    assert first != second
    # Reading-order: zweite Zelle ist (7, 6)
    assert second == (7, 6)


def test_jump_returns_false_on_unused_color(patterned_canvas, pattern_with_stitches):
    canvas, _ = patterned_canvas
    # Farbe idx 3 (Gruen) ist im pattern_with_stitches nicht gesetzt
    canvas.set_current_color(3)
    assert canvas.jump_to_next_stitch(forward=True) is False
    assert canvas.stitch_cursor is None


def test_jump_does_not_skip_cell_completed_only_on_hidden_lower_layer(qtbot, pattern_with_colors):
    """Regressionstest fuer Runde 25/45-Fund in jump_to_next_stitch().

    Zwei Layer, gleiche Farbe an derselben Position (5, 5):
    - Layer A (oben, sichtbar): Farbe Rot, NICHT erledigt.
    - Layer B (unten, verdeckt): Farbe Rot, ERLEDIGT markiert.

    Das Composite zeigt/braucht Layer A's Stich (oberste Ebene gewinnt) —
    der ist nicht erledigt. Die alte OR-ueber-alle-Layer-Logik haette die
    Zelle faelschlich als "erledigt" behandelt und uebersprungen.
    """
    from pysticky.ui.canvas import CrossStitchCanvas

    pattern = pattern_with_colors  # 20x20, leer

    # Unteres Layer (Hintergrund, bereits vorhanden): Stich setzen + erledigt.
    lower = pattern.layer_stack[0]
    pattern.set_stitch(5, 5, 2)  # Rot auf aktivem (unterem) Layer
    assert pattern.mark_stitch_completed(5, 5, 0) is True
    assert lower.completion_grid[5, 5]

    # Oberes Layer hinzufuegen, gleiche Farbe an derselben Position, NICHT erledigt.
    pattern.layer_stack.add_layer("Oben")
    upper_index = len(pattern.layer_stack) - 1
    pattern.layer_stack.active_index = upper_index
    pattern.set_stitch(5, 5, 2)
    assert pattern.layer_stack[upper_index].completion_grid[5, 5] == False  # noqa: E712

    # Composite an (5, 5) muss Layer A's (oberstes) Rot zeigen.
    assert pattern.layer_stack.get_composite_stitch(5, 5) == 2

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(pattern)
    canvas.resize(800, 600)
    canvas.set_current_color(2)  # Rot

    found = canvas.jump_to_next_stitch(forward=True)
    assert found is True
    assert canvas.stitch_cursor == (5, 5)


def test_isolation_dim_render_does_not_crash(patterned_canvas, qtbot):
    """Smoke: paintEvent mit Isolation darf nicht crashen."""
    from PySide6.QtGui import QPixmap

    canvas, _ = patterned_canvas
    canvas.set_isolate_color(2)
    pm = QPixmap(canvas.size())
    canvas.render(pm)  # triggert paintEvent
    # Wenn wir hier ankommen, hat alles geklappt
    assert not pm.isNull()
