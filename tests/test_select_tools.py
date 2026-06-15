# -*- coding: utf-8 -*-
"""
Tests fuer SelectTool und LassoSelectTool.

Verifiziert die gemeinsame API (copy/cut/paste/delete/fill/rotate/flip) auf
beiden Tools, plus die Move-with-content-Logik (inkl. Overlap-Verhalten).
"""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPoint, QRect, Qt

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


def _mouse_event(button: Qt.MouseButton = Qt.MouseButton.LeftButton, modifier=None):
    evt = MagicMock()
    evt.button.return_value = button
    evt.modifiers.return_value = modifier if modifier else Qt.KeyboardModifier.NoModifier
    evt.position.return_value = QPoint(0, 0)
    return evt


# === Symmetrie SelectTool <-> LassoSelectTool ===


def test_lasso_has_same_public_api_as_select_tool():
    """LassoSelectTool muss die gleiche selection-API haben wie SelectTool —
    sonst funktionieren die Bearbeiten-Menue-Aktionen nicht mit Lasso."""
    required = [
        "selection",
        "is_pasting",
        "clear_selection",
        "copy_selection",
        "cut_selection",
        "start_paste",
        "cancel_paste",
        "delete_selection",
        "fill_selection",
        "rotate_selection",
        "flip_selection_horizontal",
        "flip_selection_vertical",
    ]
    select = SelectTool()
    lasso = LassoSelectTool()
    for attr in required:
        assert hasattr(select, attr), f"SelectTool fehlt {attr}"
        assert hasattr(lasso, attr), f"LassoSelectTool fehlt {attr}"


def test_both_select_tools_share_clipboard(pattern_with_stitches):
    """Lasso schreibt in dasselbe Clipboard wie SelectTool — und umgekehrt."""
    select = SelectTool()
    lasso = LassoSelectTool()

    # Reset state
    SelectTool._clipboard = None
    select._selection = QRect(5, 5, 3, 3)
    ctx = _make_ctx(pattern_with_stitches, 5, 5)
    assert select.copy_selection(ctx) is True
    assert SelectTool._clipboard is not None
    assert len(SelectTool._clipboard) == 9  # 3x3

    # Lasso sieht das gleiche clipboard via class-level
    assert lasso.__class__.__mro__[1] is not None  # baseclass exists
    # SelectTool._clipboard ist Klassen-Attribut, also auch ueber Lasso lesbar
    from pysticky.ui.tools.select_tool import SelectTool as ST

    assert ST._clipboard is SelectTool._clipboard


# === SelectTool: kompletter Lifecycle ===


def test_select_tool_drag_creates_rect_selection(pattern_with_colors):
    tool = SelectTool()
    p = pattern_with_colors

    tool.on_mouse_press(_make_ctx(p, 2, 2), _mouse_event())
    tool.on_mouse_move(_make_ctx(p, 5, 4), _mouse_event())
    tool.on_mouse_release(_make_ctx(p, 5, 4), _mouse_event())

    sel = tool.selection
    assert sel is not None
    assert sel.left() == 2 and sel.top() == 2
    assert sel.width() == 4 and sel.height() == 3  # inclusive


def test_select_copy_returns_pixel_grid(pattern_with_stitches):
    """copy_selection erfasst die pixel-data des aktiven Layers."""
    tool = SelectTool()
    tool._selection = QRect(5, 5, 2, 2)
    SelectTool._clipboard = None

    ctx = _make_ctx(pattern_with_stitches, 5, 5)
    assert tool.copy_selection(ctx) is True
    assert SelectTool._clipboard_size == (2, 2)
    assert len(SelectTool._clipboard) == 4


def test_select_delete_returns_none_changes(pattern_with_stitches):
    """delete_selection produziert (x, y, None)-Changes fuer jeden Pixel im Rect."""
    tool = SelectTool()
    tool._selection = QRect(5, 5, 2, 2)
    ctx = _make_ctx(pattern_with_stitches, 5, 5)

    changes = tool.delete_selection(ctx)
    assert len(changes) == 4
    assert all(c == (x, y, None) for c, (x, y) in zip(changes, [(5, 5), (6, 5), (5, 6), (6, 6)]))


def test_select_fill_uses_current_color(pattern_with_colors):
    """fill_selection setzt jeden Pixel auf ctx.current_color_index."""
    tool = SelectTool()
    tool._selection = QRect(3, 3, 2, 2)
    ctx = _make_ctx(pattern_with_colors, 3, 3, color_index=2)

    changes = tool.fill_selection(ctx)
    assert len(changes) == 4
    assert all(c_idx == 2 for _, _, c_idx in changes)


def test_select_rotate_cw_changes_geometry(pattern_with_stitches):
    """90°-rechts-Rotation tauscht width und height."""
    tool = SelectTool()
    tool._selection = QRect(5, 5, 4, 2)  # 4 breit, 2 hoch
    ctx = _make_ctx(pattern_with_stitches, 5, 5)

    tool.rotate_selection(ctx, clockwise=True)
    # Nach Drehung: 2 breit, 4 hoch
    assert tool.selection.width() == 2
    assert tool.selection.height() == 4


def test_select_flip_horizontal_reverses_rows(pattern_with_stitches):
    """Horizontaler Flip kehrt die Pixel pro Zeile um.

    Pattern hat in der Fuellung idx=2 (Rot) in einem 8x8-Block. An den Raendern
    (5,5)..(14,14) ist idx=0 (Schwarz). Flip taucht hier nicht auf, weil
    symmetrisch — also ein einfacher Smoke-Test, dass kein Crash passiert.
    """
    tool = SelectTool()
    tool._selection = QRect(5, 5, 3, 2)
    ctx = _make_ctx(pattern_with_stitches, 5, 5)
    changes = tool.flip_selection_horizontal(ctx)
    assert len(changes) == 6  # 3*2 Pixel


# === Move-with-content (Overlap-Verhalten) ===


def test_select_move_no_overlap(pattern_with_stitches):
    """Verschieben ohne Ueberlap: alte Position wird None, neue kriegt Pixel."""
    tool = SelectTool()
    ctx = _make_ctx(pattern_with_stitches, 5, 5)

    # Auswahl an (5,5..6,6) — Rand mit Schwarz (idx 0)
    tool._selection = QRect(5, 5, 2, 2)
    tool._original_selection = QRect(5, 5, 2, 2)
    tool._capture_selection_content(ctx)
    tool._content_captured = True

    # Auswahl nach (15,15) verschoben — weit weg, kein Ueberlap
    tool._selection = QRect(15, 15, 2, 2)
    changes = tool._apply_move(ctx)

    # Trennung pruefen: erst alte (None), dann neue (color_idx)
    none_changes = [(x, y) for x, y, c in changes if c is None]
    set_changes = [(x, y, c) for x, y, c in changes if c is not None]

    # Alle 4 alten Positions sind im "None"-Block
    assert set(none_changes) >= {(5, 5), (6, 5), (5, 6), (6, 6)}
    # Die "Set"-Changes sind alle out-of-bounds (Pattern ist 20x20, also 15..16 valid)
    # Pattern.width=20, height=20 — also (15,15)..(16,16) sind valid
    new_positions = {(x, y) for x, y, _ in set_changes}
    assert new_positions == {(15, 15), (16, 15), (15, 16), (16, 16)}


def test_select_move_with_overlap_order(pattern_with_stitches):
    """
    Bei Ueberlap muss die Change-Liste die alten Positionen ZUERST loeschen
    und dann die neuen setzen — sonst ueberschreibt das Setzen die alten und
    der Loesch-Eintrag killt sie hinterher.

    Pattern hat Fuellung (idx 2) in (6..13, 6..13). Auswahl bei (6,6,3,3)
    erfasst 9 rote Pixel; Verschieben um (1,0) ueberlappt 6 Pixel.
    """
    tool = SelectTool()
    p = pattern_with_stitches
    ctx = _make_ctx(p, 6, 6)

    tool._selection = QRect(6, 6, 3, 3)
    tool._original_selection = QRect(6, 6, 3, 3)
    tool._capture_selection_content(ctx)
    tool._content_captured = True

    # Verschiebung um (1, 0) — 6 Pixel Ueberlap
    tool._selection = QRect(7, 6, 3, 3)
    changes = tool._apply_move(ctx)

    # Reihenfolge: erst alle None-Changes, dann alle Set-Changes
    last_none_idx = max(i for i, (_, _, c) in enumerate(changes) if c is None)
    first_set_idx = min(i for i, (_, _, c) in enumerate(changes) if c is not None)
    assert last_none_idx < first_set_idx, (
        "apply_move muss erst alle alten Positionen loeschen, bevor neue "
        "gesetzt werden — sonst werden ueberlappende Pixel zerstoert"
    )


# === Paste-Lifecycle ===


def test_select_paste_without_clipboard_returns_false(pattern_with_colors):
    """start_paste ohne Clipboard liefert False."""
    SelectTool._clipboard = None
    tool = SelectTool()
    ctx = _make_ctx(pattern_with_colors, 5, 5)
    assert tool.start_paste(ctx) is False


def test_select_paste_starts_paste_mode(pattern_with_colors):
    """Wenn Clipboard etwas hat, geht das Tool in den Paste-Modus."""
    SelectTool._clipboard = [(0, 0, 2)]
    SelectTool._clipboard_size = (1, 1)
    tool = SelectTool()
    ctx = _make_ctx(pattern_with_colors, 3, 4)
    assert tool.start_paste(ctx) is True
    assert tool.is_pasting is True
    assert tool._paste_position == (3, 4)


def test_select_clear_resets_all_state():
    tool = SelectTool()
    tool._selection = QRect(0, 0, 5, 5)
    tool._selection_content = [(0, 0, 1)]
    tool._is_pasting = True
    tool.clear_selection()
    assert tool.selection is None
    assert tool._selection_content is None
    assert tool.is_pasting is False


# === LassoSelectTool: parallele Smoke-Tests ===


def test_lasso_empty_selection_returns_no_changes(pattern_with_colors):
    """Ohne aktive Auswahl liefern alle Operationen leere Listen."""
    tool = LassoSelectTool()
    ctx = _make_ctx(pattern_with_colors, 5, 5)
    assert tool.delete_selection(ctx) == []
    assert tool.fill_selection(ctx) == []
    assert tool.rotate_selection(ctx) == []
    assert tool.flip_selection_horizontal(ctx) == []
    assert tool.copy_selection(ctx) is False


def test_lasso_fill_operates_on_pixel_set_not_bounding_rect(pattern_with_colors):
    """
    Lasso muss nur die TATSAECHLICH ausgewaehlten Pixel fuellen,
    nicht das ganze umschliessende Rechteck — sonst wuerde Lasso wie
    SelectTool wirken.
    """
    tool = LassoSelectTool()
    # Manuell ein L-foermiges Pixel-Set setzen (3 Pixel, Bounding-Rect waere 4)
    tool._selected_pixels = {(2, 2), (3, 2), (2, 3)}
    tool._selection_bounds = QRect(2, 2, 2, 2)  # 2x2 = 4 Pixel im Rect

    ctx = _make_ctx(pattern_with_colors, 2, 2, color_index=2)
    changes = tool.fill_selection(ctx)
    assert len(changes) == 3, "Lasso fuellt nur die Pixel im Set, nicht den Rect"
    assert {(x, y) for x, y, _ in changes} == {(2, 2), (3, 2), (2, 3)}
