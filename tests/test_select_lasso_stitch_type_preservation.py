# -*- coding: utf-8 -*-
"""Regressionstests (offener Punkt aus dead-code-and-export-gaps.md, Runde 21):
Select/Lasso-Tool verloren den stitch_type (Halb-/Viertelstich etc.) jeder
betroffenen Zelle bei Verschieben/Drehen/Spiegeln/Kopieren-Einfuegen -- die
Werkzeuge lasen nur layer.get_stitch() (Farbindex), nie
layer.get_stitch_type(), und die Change-Tupel (x, y, color_index) hatten
gar keinen Platz fuer einen Stichtyp. undo_handlers.py::_on_stitch_placed()
stempelte jeden ueber das stitch_placed-Signal neu platzierten Stich mit
dem GLOBALEN canvas._active_stitch_type -- ein Halbstich kam nach dem
Verschieben also immer als voller Stich zurueck.

Fix: Change-Tupel werden fuer Select/Lasso auf 4 Elemente erweitert
(x, y, color_index, stitch_type); Canvas._apply_changes() erkennt das und
emittiert ein neues stitch_placed_typed-Signal statt stitch_placed;
undo_handlers.py::_on_stitch_placed_typed() nutzt den mitgelieferten
Stichtyp statt des globalen Fallbacks. Drehen/Spiegeln transformieren den
Stichtyp zusaetzlich per den schon vorhandenen, aber bis dahin nie
genutzten ROTATE_CW_MAP/ROTATE_CCW_MAP/FLIP_H_MAP/FLIP_V_MAP aus
core/stitch.py (die exakt fuer diesen Zweck vorbereitet waren)."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QRect

from pysticky.core.stitch import StitchType
from pysticky.ui.tools.base_tool import ToolContext
from pysticky.ui.tools.lasso_select_tool import LassoSelectTool
from pysticky.ui.tools.select_tool import SelectTool

pytestmark = pytest.mark.usefixtures("qtbot")


def _make_ctx(pattern, grid_x: int, grid_y: int, color_index: int = 0) -> ToolContext:
    canvas = MagicMock()
    canvas.snap_position.side_effect = lambda x, y: (x, y)
    canvas.snap_to_grid = False
    canvas.snap_interval = 1
    return ToolContext(
        canvas=canvas,
        pattern=pattern,
        current_color_index=color_index,
        grid_x=grid_x,
        grid_y=grid_y,
        screen_x=grid_x * 20,
        screen_y=grid_y * 20,
        cell_size=20,
        offset_x=0,
        offset_y=0,
    )


@pytest.fixture
def pattern_with_half_stitch(pattern_with_colors):
    """Ein einzelner Halbstich (HALF_TL_BR, "/") bei (5,5), sonst leer."""
    pattern = pattern_with_colors
    pattern.set_stitch(5, 5, 0, StitchType.HALF_TL_BR.value)
    return pattern


# === SelectTool ===


def test_capture_selection_content_records_stitch_type(pattern_with_half_stitch):
    tool = SelectTool()
    tool._selection = QRect(5, 5, 2, 2)
    ctx = _make_ctx(pattern_with_half_stitch, 5, 5)

    tool._capture_selection_content(ctx)

    entry = next(e for e in tool._selection_content if e[0] == 0 and e[1] == 0)
    assert entry == (0, 0, 0, StitchType.HALF_TL_BR.value)


def test_apply_move_preserves_stitch_type(pattern_with_half_stitch):
    tool = SelectTool()
    ctx = _make_ctx(pattern_with_half_stitch, 5, 5)

    tool._selection = QRect(5, 5, 2, 2)
    tool._original_selection = QRect(5, 5, 2, 2)
    tool._capture_selection_content(ctx)

    tool._selection = QRect(10, 10, 2, 2)
    changes = tool._apply_move(ctx)

    placed = [c for c in changes if c[2] == 0]
    assert placed == [(10, 10, 0, StitchType.HALF_TL_BR.value)], (
        "Regression: Verschieben eines Halbstichs muss dessen Stichtyp bewahren, "
        "nicht auf FULL zuruecksetzen"
    )


def test_copy_paste_preserves_stitch_type(pattern_with_half_stitch):
    tool = SelectTool()
    SelectTool._clipboard = None
    tool._selection = QRect(5, 5, 2, 2)
    ctx = _make_ctx(pattern_with_half_stitch, 5, 5)

    assert tool.copy_selection(ctx) is True
    clip_entry = next(e for e in SelectTool._clipboard if e[0] == 0 and e[1] == 0)
    assert clip_entry == (0, 0, 0, StitchType.HALF_TL_BR.value)

    tool.start_paste(ctx)
    tool._paste_position = (15, 15)
    changes = tool._confirm_paste(ctx)

    placed = [c for c in changes if c[2] == 0]
    assert placed == [(15, 15, 0, StitchType.HALF_TL_BR.value)]


def test_rotate_cw_transforms_half_stitch_orientation(pattern_with_half_stitch):
    """HALF_TL_BR ('/') muss bei 90°-CW-Drehung zu HALF_TR_BL ('\\') werden --
    sonst zeigt der Halbstich nach dem Drehen weiter in die alte Richtung."""
    tool = SelectTool()
    tool._selection = QRect(5, 5, 1, 1)
    ctx = _make_ctx(pattern_with_half_stitch, 5, 5)

    changes = tool.rotate_selection(ctx, clockwise=True)

    placed = [c for c in changes if c[2] is not None]
    assert len(placed) == 1
    assert placed[0][3] == StitchType.HALF_TR_BL.value


def test_flip_horizontal_transforms_half_stitch_orientation(pattern_with_half_stitch):
    tool = SelectTool()
    tool._selection = QRect(5, 5, 1, 1)
    ctx = _make_ctx(pattern_with_half_stitch, 5, 5)

    changes = tool.flip_selection_horizontal(ctx)

    placed = [c for c in changes if c[2] is not None]
    assert len(placed) == 1
    assert placed[0][3] == StitchType.HALF_TR_BL.value


def test_flip_vertical_transforms_half_stitch_orientation(pattern_with_half_stitch):
    tool = SelectTool()
    tool._selection = QRect(5, 5, 1, 1)
    ctx = _make_ctx(pattern_with_half_stitch, 5, 5)

    changes = tool.flip_selection_vertical(ctx)

    placed = [c for c in changes if c[2] is not None]
    assert len(placed) == 1
    assert placed[0][3] == StitchType.HALF_TR_BL.value


def test_fill_selection_still_forces_full_stitch(pattern_with_half_stitch):
    """fill_selection() ist ein bewusster voller Stich, kein Datenverlust-Bug."""
    tool = SelectTool()
    tool._selection = QRect(5, 5, 1, 1)
    ctx = _make_ctx(pattern_with_half_stitch, 5, 5, color_index=1)

    changes = tool.fill_selection(ctx)
    assert changes == [(5, 5, 1, StitchType.FULL.value)]


# === LassoSelectTool ===


def test_lasso_capture_and_move_preserves_stitch_type(pattern_with_half_stitch):
    tool = LassoSelectTool()
    tool._selected_pixels = {(5, 5), (6, 5)}
    tool._selection_bounds = QRect(5, 5, 2, 1)
    ctx = _make_ctx(pattern_with_half_stitch, 5, 5)

    tool._capture_selection_content(ctx)
    entry = next(e for e in tool._selection_content if e[2] == 0)
    assert entry[3] == StitchType.HALF_TL_BR.value

    tool._original_bounds = QRect(5, 5, 2, 1)
    tool._selection_bounds = QRect(10, 10, 2, 1)
    changes = tool._apply_move(ctx)

    placed = [c for c in changes if c[2] == 0]
    assert placed == [(10, 10, 0, StitchType.HALF_TL_BR.value)]


def test_lasso_rotate_transforms_half_stitch_orientation(pattern_with_half_stitch):
    tool = LassoSelectTool()
    tool._selected_pixels = {(5, 5)}
    tool._selection_bounds = QRect(5, 5, 1, 1)
    ctx = _make_ctx(pattern_with_half_stitch, 5, 5)

    changes = tool.rotate_selection(ctx, clockwise=True)

    placed = [c for c in changes if c[2] is not None]
    assert len(placed) == 1
    assert placed[0][3] == StitchType.HALF_TR_BL.value


def test_lasso_flip_horizontal_transforms_half_stitch_orientation(pattern_with_half_stitch):
    tool = LassoSelectTool()
    tool._selected_pixels = {(5, 5)}
    tool._selection_bounds = QRect(5, 5, 1, 1)
    ctx = _make_ctx(pattern_with_half_stitch, 5, 5)

    changes = tool.flip_selection_horizontal(ctx)

    placed = [c for c in changes if c[2] is not None]
    assert len(placed) == 1
    assert placed[0][3] == StitchType.HALF_TR_BL.value


# === Canvas / Undo-Handler Integration ===


def test_apply_changes_routes_4tuple_to_typed_signal(qtbot):
    """Canvas._apply_changes() muss 4-Tuple ueber stitch_placed_typed schicken,
    3-Tuple weiterhin ueber das alte stitch_placed (Rueckwaertskompatibilitaet
    fuer Pencil/Fill/Ellipse/... die den globalen _active_stitch_type nutzen)."""
    from pysticky.core import Pattern
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(Pattern(width=20, height=20))

    typed_calls = []
    plain_calls = []
    canvas.stitch_placed_typed.connect(lambda x, y, c, t: typed_calls.append((x, y, c, t)))
    canvas.stitch_placed.connect(lambda x, y, c: plain_calls.append((x, y, c)))

    canvas._apply_changes([(1, 1, 0, StitchType.HALF_TL_BR.value), (2, 2, 0)])

    assert typed_calls == [(1, 1, 0, StitchType.HALF_TL_BR.value)]
    assert plain_calls == [(2, 2, 0)]


def test_on_stitch_placed_typed_uses_explicit_type_not_global(qtbot):
    """undo_handlers.py::_on_stitch_placed_typed() muss den mitgelieferten
    Stichtyp verwenden, NICHT canvas._active_stitch_type (Regression: vorher
    gab es diesen Pfad gar nicht, jeder Stich lief durch _on_stitch_placed()
    mit dem globalen Fallback)."""
    from pysticky.core import Pattern, Thread
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    pattern = Pattern(name="Test", width=20, height=20)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    w.set_pattern(pattern)

    # Globaler Stichtyp ist FULL -- _on_stitch_placed_typed() soll das ignorieren.
    w.canvas._active_stitch_type = StitchType.FULL.value

    w._on_stitch_placed_typed(3, 3, 0, StitchType.HALF_TR_BL.value)

    layer = w.current_pattern.active_layer
    assert layer.get_stitch_type(3, 3) == StitchType.HALF_TR_BL.value
