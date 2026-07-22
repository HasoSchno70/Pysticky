# -*- coding: utf-8 -*-
"""Tests fuer Smart-Resize (bilineare Stitch-Redistribution)."""

import numpy as np
import pytest


def test_smart_resize_changes_dimensions(pattern_with_stitches):
    """Smart-Resize aendert width/height des Patterns."""
    from pysticky.core.smart_resize import smart_resize

    smart_resize(pattern_with_stitches, 40, 30)
    assert pattern_with_stitches.width == 40
    assert pattern_with_stitches.height == 30


def test_smart_resize_changes_layer_dimensions(pattern_with_stitches):
    """Alle Layer haben die neuen Dimensionen."""
    from pysticky.core.smart_resize import smart_resize

    smart_resize(pattern_with_stitches, 30, 30)
    for layer in pattern_with_stitches.layer_stack:
        assert layer.width == 30
        assert layer.height == 30
        assert layer.grid.shape == (30, 30)
        assert layer.stitch_type_grid.shape == (30, 30)
        assert layer.completion_grid.shape == (30, 30)


def test_smart_resize_doubles_pattern_keeps_stitches(empty_pattern):
    """Hochskalieren 10x10 -> 20x20 erhaelt die Stiche (jetzt 4x soviele).

    Regression (Test-Qualitaets-Audit): `>= 3` (die Ausgangs-Stichzahl)
    haette der Docstring-Behauptung ("jetzt 4x soviele") widersprochen, aber
    auch dann noch gepasst, wenn smart_resize() das Grid beim Hochskalieren
    ueberhaupt nicht neu abgetastet, sondern die alten 3 Stiche einfach
    unveraendert kopiert haette (z.B. bei einem Shape-Mismatch-Bug, der
    still verschluckt wird). Nearest-Neighbor bei exaktem Faktor 2 macht aus
    jedem Alt-Stich einen exakten 2x2-Block -- bei 3 nicht ueberlappenden
    Quell-Stichen ergibt das exakt 12.
    """
    from pysticky.core import Thread
    from pysticky.core.layer import NO_STITCH
    from pysticky.core.smart_resize import smart_resize

    pattern = empty_pattern
    pattern.add_color(Thread.from_hex("Red", "#FF0000"))
    pattern.set_stitch(0, 0, 0)
    pattern.set_stitch(5, 5, 0)
    pattern.set_stitch(9, 9, 0)

    smart_resize(pattern, 20, 20)
    layer = pattern.layer_stack.active_layer
    n_stitches = int(np.sum(layer.grid != NO_STITCH))
    assert n_stitches == 12, "3 Quell-Stiche * 2x2-Block (Faktor 2) = 12"
    # Im Bereich (0,0) muss ein Stich sein (Skalierungs-Faktor 2)
    assert layer.get_stitch(0, 0) is not None


def test_smart_resize_halves_pattern_reduces_stitches(empty_pattern):
    """Runterskalieren 10x10 -> 5x5 reduziert Stiche."""
    from pysticky.core import Thread
    from pysticky.core.layer import NO_STITCH
    from pysticky.core.smart_resize import smart_resize

    pattern = empty_pattern
    pattern.add_color(Thread.from_hex("Red", "#FF0000"))
    for y in range(10):
        for x in range(10):
            pattern.set_stitch(x, y, 0)

    before = int(np.sum(pattern.layer_stack.active_layer.grid != NO_STITCH))
    smart_resize(pattern, 5, 5)
    after = int(np.sum(pattern.layer_stack.active_layer.grid != NO_STITCH))
    assert after < before
    assert after == 25  # 5x5 voll


def test_smart_resize_no_op_when_dimensions_unchanged(pattern_with_stitches):
    """Wenn neue Dimensionen gleich alten sind, passiert nichts."""
    import copy

    from pysticky.core.smart_resize import smart_resize

    snapshot = copy.deepcopy(pattern_with_stitches.layer_stack.active_layer.grid)
    smart_resize(pattern_with_stitches, pattern_with_stitches.width, pattern_with_stitches.height)
    after = pattern_with_stitches.layer_stack.active_layer.grid
    assert np.array_equal(snapshot, after)


def test_smart_resize_rejects_invalid_dimensions(empty_pattern):
    """Negative/Null-Dimensionen werfen ValueError."""
    from pysticky.core.smart_resize import smart_resize

    with pytest.raises(ValueError):
        smart_resize(empty_pattern, 0, 10)
    with pytest.raises(ValueError):
        smart_resize(empty_pattern, 10, 0)


def test_smart_resize_preserves_stitch_types(empty_pattern):
    """Stitch-Type-Grid wird mit nearest-neighbor uebernommen."""
    from pysticky.core import Thread
    from pysticky.core.smart_resize import smart_resize
    from pysticky.core.stitch import StitchType

    pattern = empty_pattern
    pattern.add_color(Thread.from_hex("Red", "#FF0000"))
    pattern.set_stitch(3, 3, 0, stitch_type=StitchType.HALF_TL_BR.value)

    smart_resize(pattern, 20, 20)  # 2x hochskaliert
    layer = pattern.layer_stack.active_layer
    # Position (3,3) im Original mappt auf (6,6) im neuen
    assert layer.stitch_type_grid[6, 6] == StitchType.HALF_TL_BR.value


def test_smart_resize_scales_backstitches(empty_pattern):
    """Backstitches werden proportional skaliert."""
    from pysticky.core import Thread
    from pysticky.core.smart_resize import smart_resize

    pattern = empty_pattern
    pattern.add_color(Thread.from_hex("Black", "#000000"))
    pattern.add_backstitch(2, 2, 4, 4, 0)

    smart_resize(pattern, 20, 20)  # 2x
    bs = pattern.backstitch_manager.backstitches
    assert len(bs) == 1
    # Skalierung mit Faktor 2: (2,2)->(4,4), (4,4)->(8,8)
    assert bs[0].x1 == 4
    assert bs[0].y1 == 4
    assert bs[0].x2 == 8
    assert bs[0].y2 == 8


def test_smart_resize_recalculates_stitch_counts(empty_pattern):
    """Stitch-Counts in color_entries werden nach Resize neu berechnet.

    Regression (Test-Qualitaets-Audit): die vorherige Version setzte Stiche
    mit color_index=0 (dem Default-Schwarz aus Pattern.__post_init__),
    pruefte aber stitch_count von color_entries[-1] (der frisch
    hinzugefuegten, nie benutzten Rot-Farbe) -- die geprueften stitch_count
    blieb dadurch vorher UND nachher bei 0, `after >= before` (0 >= 0) war
    also unabhaengig davon wahr, ob recalculate_stitch_counts() ueberhaupt
    aufgerufen wird. Jetzt wird explizit die Farbe geprueft, mit der auch
    tatsaechlich gezeichnet wurde.
    """
    from pysticky.core import Thread
    from pysticky.core.smart_resize import smart_resize

    pattern = empty_pattern
    red_idx = pattern.add_color(Thread.from_hex("Red", "#FF0000"))
    pattern.set_stitch(1, 1, red_idx)
    pattern.set_stitch(2, 2, red_idx)

    before = pattern.color_entries[red_idx].stitch_count
    assert before == 2
    smart_resize(pattern, 20, 20)
    after = pattern.color_entries[red_idx].stitch_count

    # 2x-Hochskalierung: 2 nicht ueberlappende Quell-Stiche -> je ein
    # 2x2-Block -> exakt 8.
    assert after == 8


def test_smart_resize_aspect_ratio_change(empty_pattern):
    """Smart-Resize kann das Aspect-Ratio aendern (10x10 -> 20x5)."""
    from pysticky.core import Thread
    from pysticky.core.smart_resize import smart_resize

    pattern = empty_pattern  # 10x10
    pattern.add_color(Thread.from_hex("Red", "#FF0000"))
    pattern.set_stitch(5, 5, 0)

    smart_resize(pattern, 20, 5)
    assert pattern.width == 20
    assert pattern.height == 5
