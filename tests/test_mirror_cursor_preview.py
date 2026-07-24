# -*- coding: utf-8 -*-
"""Regressionstest fuer CrossStitchCanvas._draw_cursor()'s gespiegelte
Cursor-Vorschau (rendering_mixin.py).

Bug: `get_mirrored_positions()` baut sein Ergebnis intern ueber ein
`set` auf und gibt `list(positions)` zurueck -- die Original-Position
(grid_x, grid_y) landet dadurch NICHT zuverlaessig an Index 0 der Liste
(Set-Iterationsreihenfolge haengt von den Hashwerten der Tupel ab, nicht
von der Einfuegereihenfolge). `_draw_cursor()` verliess sich vorher auf
`get_mirrored_positions(...)[1:]`, um die Originalzelle beim Zeichnen der
gespiegelten Vorschau-Rahmen zu ueberspringen -- sobald die Originalzelle
NICHT an Index 0 landete, wurde stattdessen eine ECHTE gespiegelte
Position uebersprungen (kein Vorschau-Rahmen dafuer) und die
Originalzelle faelschlich ein zweites Mal (in der Spiegel-Vorschaufarbe)
gezeichnet.

Fix: explizit nach der Originalposition filtern statt sich auf die
Listenreihenfolge zu verlassen.
"""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPoint

pytestmark = pytest.mark.usefixtures("qtbot")


def _make_canvas(qtbot, width, height, mirror_mode):
    from pysticky.core import Pattern, Thread
    from pysticky.ui.canvas import CrossStitchCanvas

    pattern = Pattern(name="Test", width=width, height=height)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(pattern)
    canvas._cell_size = 20
    canvas._offset_x = 0
    canvas._offset_y = 0
    canvas._mirror_mode = mirror_mode
    return canvas


def test_quad_mirror_cursor_preview_draws_every_mirrored_cell_exactly_once(qtbot):
    """Regression: bei QUAD-Spiegelung muss fuer JEDE der vier
    (Original + 3 gespiegelten) Zellen genau ein Vorschau-Rahmen gezeichnet
    werden -- unabhaengig von der (nicht garantierten) Reihenfolge, in der
    get_mirrored_positions() sie zurueckgibt."""
    from pysticky.ui.canvas.enums import MirrorMode

    canvas = _make_canvas(qtbot, width=20, height=20, mirror_mode=MirrorMode.QUAD)

    grid_x, grid_y = 5, 5
    sx, sy = canvas._grid_to_screen(grid_x, grid_y)
    canvas._cursor_pos = QPoint(sx + 2, sy + 2)

    painter = MagicMock()
    canvas._draw_cursor(painter)

    drawn_rects = {(c.args[0], c.args[1]) for c in painter.drawRect.call_args_list}

    positions = canvas.get_mirrored_positions(grid_x, grid_y)
    assert len(positions) == 4, "Testannahme verletzt: QUAD sollte hier 4 Positionen ergeben"
    expected_rects = {canvas._grid_to_screen(mx, my) for mx, my in positions}

    assert drawn_rects == expected_rects, (
        f"Vorschau-Rahmen unvollstaendig/falsch: erwartet {expected_rects}, "
        f"gezeichnet {drawn_rects}"
    )


def test_horizontal_mirror_cursor_preview_draws_both_cells(qtbot):
    """Auch im einfachen Horizontal-Fall (nur 2 Positionen) muss die
    echte gespiegelte Zelle einen Vorschau-Rahmen bekommen."""
    from pysticky.ui.canvas.enums import MirrorMode

    canvas = _make_canvas(qtbot, width=20, height=10, mirror_mode=MirrorMode.HORIZONTAL)

    grid_x, grid_y = 3, 4
    sx, sy = canvas._grid_to_screen(grid_x, grid_y)
    canvas._cursor_pos = QPoint(sx + 2, sy + 2)

    painter = MagicMock()
    canvas._draw_cursor(painter)

    drawn_rects = {(c.args[0], c.args[1]) for c in painter.drawRect.call_args_list}
    positions = canvas.get_mirrored_positions(grid_x, grid_y)
    assert len(positions) == 2
    expected_rects = {canvas._grid_to_screen(mx, my) for mx, my in positions}

    assert drawn_rects == expected_rects
