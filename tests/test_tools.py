# -*- coding: utf-8 -*-
"""
Smoke-Tests fuer Zeichenwerkzeuge.

Verifiziert ToolManager-Setup und das grundlegende press/move/release-Protokoll
ohne echte Canvas — mit einem minimalen Mock-Context.
"""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPoint, Qt

from pysticky.ui.tools.base_tool import ToolContext
from pysticky.ui.tools.eraser_tool import EraserTool
from pysticky.ui.tools.fill_tool import FillTool
from pysticky.ui.tools.pencil_tool import PencilTool
from pysticky.ui.tools.tool_enum import Tool
from pysticky.ui.tools.tool_manager import ToolManager

pytestmark = pytest.mark.usefixtures("qtbot")


def _make_ctx(pattern, grid_x: int, grid_y: int, color_index: int = 0) -> ToolContext:
    """Baut einen ToolContext mit einer Mock-Canvas."""
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


def _mouse_event(button: Qt.MouseButton = Qt.MouseButton.LeftButton) -> MagicMock:
    evt = MagicMock()
    evt.button.return_value = button
    evt.buttons.return_value = button
    evt.position.return_value = QPoint(0, 0)
    return evt


# MIRROR_H/V sind Aktionen, keine Werkzeuge — sie fuehren beim Klick eine
# Transformation auf der ganzen Auswahl durch und werden nicht als Tool aktiv.
_ACTION_ONLY_TOOLS = {Tool.MIRROR_H, Tool.MIRROR_V}


def test_tool_manager_registers_all_drawing_tools():
    """Alle Zeichenwerkzeuge (inkl. MOVE) sind im Manager hinterlegt."""
    mgr = ToolManager()
    for tool in Tool:
        if tool in _ACTION_ONLY_TOOLS:
            continue
        assert mgr.get_tool(tool) is not None, f"{tool} fehlt im Manager"


def test_move_tool_returns_open_hand_cursor():
    """Bewegen-Werkzeug zeigt OpenHand-Cursor und ignoriert Klicks."""
    from PySide6.QtCore import Qt

    from pysticky.ui.tools.move_tool import MoveTool

    tool = MoveTool()
    assert tool.get_cursor() == Qt.CursorShape.OpenHandCursor


def test_tool_manager_default_is_pencil():
    mgr = ToolManager()
    assert mgr.current_tool == Tool.PENCIL


def test_tool_manager_switch_activates_and_deactivates():
    """Beim Wechsel wird das alte Tool deaktiviert, das neue aktiviert."""
    mgr = ToolManager()
    pencil = mgr.get_tool(Tool.PENCIL)
    fill = mgr.get_tool(Tool.FILL)

    pencil._active = True  # simulierter Zeichenzustand
    mgr.current_tool = Tool.FILL
    assert pencil._active is False
    assert mgr.current_tool == Tool.FILL
    assert mgr.get_active_tool() is fill


def test_pencil_press_sets_stitch(pattern_with_colors):
    tool = PencilTool()
    ctx = _make_ctx(pattern_with_colors, 3, 4, color_index=2)
    changes = tool.on_mouse_press(ctx, _mouse_event())
    assert changes == [(3, 4, 2)]
    assert tool.is_active is True


def test_pencil_release_clears_active(pattern_with_colors):
    tool = PencilTool()
    tool.on_mouse_press(_make_ctx(pattern_with_colors, 1, 1), _mouse_event())
    tool.on_mouse_release(_make_ctx(pattern_with_colors, 1, 1), _mouse_event())
    assert tool.is_active is False


def test_pencil_drag_interpolates_line(pattern_with_colors):
    """Beim Drag von (0,0) zu (3,0) entsteht eine horizontale Linie."""
    tool = PencilTool()
    tool.on_mouse_press(_make_ctx(pattern_with_colors, 0, 0, 2), _mouse_event())
    changes = tool.on_mouse_move(_make_ctx(pattern_with_colors, 3, 0, 2), _mouse_event())
    coords = {(x, y) for x, y, _ in changes}
    assert (1, 0) in coords and (2, 0) in coords and (3, 0) in coords


def test_pencil_ignores_right_click(pattern_with_colors):
    tool = PencilTool()
    changes = tool.on_mouse_press(
        _make_ctx(pattern_with_colors, 1, 1), _mouse_event(Qt.MouseButton.RightButton)
    )
    assert changes == []
    assert tool.is_active is False


def test_pencil_clips_out_of_bounds(pattern_with_colors):
    """Press auf Position ausserhalb des Patterns liefert keine Changes."""
    tool = PencilTool()
    ctx = _make_ctx(pattern_with_colors, -1, 5)
    changes = tool.on_mouse_press(ctx, _mouse_event())
    assert changes == []


def test_eraser_emits_none_color(pattern_with_colors):
    """Radierer setzt color_index=None."""
    tool = EraserTool()
    ctx = _make_ctx(pattern_with_colors, 5, 5)
    changes = tool.on_mouse_press(ctx, _mouse_event())
    assert changes == [(5, 5, None)]


def test_fill_tool_fills_empty_region(pattern_with_colors):
    """Flood-Fill auf leerem 20x20 Pattern fuellt die ganze Flaeche."""
    tool = FillTool()
    ctx = _make_ctx(pattern_with_colors, 0, 0, color_index=2)
    changes = tool.on_mouse_press(ctx, _mouse_event())
    expected_cells = pattern_with_colors.width * pattern_with_colors.height
    assert len(changes) == expected_cells
    # alle Changes setzen Farbe 2
    assert all(c == 2 for _, _, c in changes)


def test_fill_tool_no_op_when_color_matches(pattern_with_stitches):
    """Klick auf Zelle, die bereits die Zielfarbe hat -> keine Changes."""
    tool = FillTool()
    # (10, 10) ist rot (idx 2) im Fixture
    ctx = _make_ctx(pattern_with_stitches, 10, 10, color_index=2)
    changes = tool.on_mouse_press(ctx, _mouse_event())
    assert changes == []


def _qsettings_with_scope():
    """QSettings() braucht Org/App-Name auf der QCoreApplication, sonst
    landen setValue()-Aufrufe im Leeren (siehe test_tablet_pressure.py)."""
    from PySide6.QtCore import QCoreApplication, QSettings

    app = QCoreApplication.instance()
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    return QSettings()


def test_fill_tool_zero_tolerance_default_exact_match_only():
    """Ohne Toleranz-Setting (Default 0) wird nur exakt gleiche Farbe gefuellt."""
    from pysticky.core import Pattern, Thread

    pattern = Pattern(width=3, height=1)
    pattern.color_entries.clear()
    idx_red = pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    idx_near = pattern.add_color(Thread.from_hex("Nahrot", "#FA0A0A"))
    idx_new = pattern.add_color(Thread.from_hex("Neu", "#0000FF"))
    pattern.set_stitch(0, 0, idx_red)
    pattern.set_stitch(1, 0, idx_near)

    s = _qsettings_with_scope()
    old = s.value("fill_tolerance", 0, type=int)
    s.setValue("fill_tolerance", 0)
    try:
        tool = FillTool()
        ctx = _make_ctx(pattern, 0, 0, color_index=idx_new)
        changes = tool.on_mouse_press(ctx, _mouse_event())
        assert changes == [(0, 0, idx_new)]
    finally:
        s.setValue("fill_tolerance", old)


def test_fill_tool_tolerance_includes_similar_neighbor_color():
    """Toleranz > 0 fuellt auch farblich aehnliche (nicht exakt gleiche) Nachbarn.

    #FF0000 und #FA0A0A liegen nah beieinander (kleines Delta-E), #00FF00
    ist weit weg und darf nicht mit erfasst werden.
    """
    from pysticky.core import Pattern, Thread

    pattern = Pattern(width=3, height=1)
    pattern.color_entries.clear()
    idx_red = pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    idx_near = pattern.add_color(Thread.from_hex("Nahrot", "#FA0A0A"))
    idx_green = pattern.add_color(Thread.from_hex("Gruen", "#00FF00"))
    idx_new = pattern.add_color(Thread.from_hex("Neu", "#0000FF"))
    pattern.set_stitch(0, 0, idx_red)
    pattern.set_stitch(1, 0, idx_near)
    pattern.set_stitch(2, 0, idx_green)

    s = _qsettings_with_scope()
    old = s.value("fill_tolerance", 0, type=int)
    s.setValue("fill_tolerance", 100)  # entspricht max. 50 Delta-E
    try:
        tool = FillTool()
        ctx = _make_ctx(pattern, 0, 0, color_index=idx_new)
        changes = tool.on_mouse_press(ctx, _mouse_event())
        assert dict((x, c) for x, _, c in changes) == {0: idx_new, 1: idx_new}
    finally:
        s.setValue("fill_tolerance", old)
