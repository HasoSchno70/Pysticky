# -*- coding: utf-8 -*-
"""
Regressionstests (Runde 29): zwei Bugs in GradientTool.on_mouse_press()/
on_mouse_release() (src/pysticky/ui/tools/gradient_tool.py).

1. is_active-Luecke: on_mouse_press() setzte nie self._active = True. Da
   ToolManager.draw_preview() fuer alle Werkzeuge ausser Select/Lasso nur bei
   tool.is_active zeichnet (siehe tool_manager.py::draw_preview), war die
   komplette draw_preview()-Implementierung dieses Tools damit toter Code --
   waehrend des Ziehens erschien keinerlei Live-Vorschau (Start-/End-Markierung,
   interpolierte Zwischenfarben), obwohl _calculate_gradient() bei jeder
   Mausbewegung korrekt _preview_points fuellte.

2. Start-Farbe-Ueberschreibung: on_mouse_press() setzte bedingungslos
   self._start_color_index = ctx.current_color_index. gradient_options_panel.py
   hat aber eigene, von der globalen Farbleiste unabhaengige Start-/Endfarbe-
   Comboboxen (start_color_changed/end_color_changed -> set_start_color()/
   set_end_color()). Waehlt der Nutzer im Panel eine andere Startfarbe als die
   aktuell in der Farbleiste aktive Farbe, wurde diese Auswahl bei jedem Klick
   still durch ctx.current_color_index ersetzt -- end_color_index war von
   diesem Bug nicht betroffen (asymmetrisch, ein klares Zeichen fuer einen
   vergessenen Uebergangs-Code-Rest).
"""

from unittest.mock import MagicMock

from PySide6.QtCore import QPoint, Qt

from pysticky.core import Pattern, Thread
from pysticky.ui.tools.base_tool import ToolContext
from pysticky.ui.tools.gradient_tool import GradientTool


def _make_pattern_with_colors():
    pattern = Pattern(width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("A", "#ff0000"))
    pattern.add_color(Thread.from_hex("B", "#00ff00"))
    pattern.add_color(Thread.from_hex("C", "#0000ff"))
    return pattern


def _make_ctx(pattern, grid_x: int, grid_y: int, color_index: int) -> ToolContext:
    return ToolContext(
        canvas=None,
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
    evt.position.return_value = QPoint(0, 0)
    return evt


def test_gradient_tool_is_active_during_drag():
    """is_active muss True sein, sobald der Nutzer zu ziehen beginnt --
    sonst zeichnet ToolManager.draw_preview() nie die Live-Vorschau (siehe
    tool_manager.py: `isinstance(tool, (SelectTool, LassoSelectTool)) or
    tool.is_active`)."""
    pattern = _make_pattern_with_colors()
    tool = GradientTool()

    assert not tool.is_active

    ctx = _make_ctx(pattern, 1, 1, color_index=0)
    tool.on_mouse_press(ctx, _mouse_event())

    assert tool.is_active, "GradientTool muss waehrend des Ziehens is_active=True melden"

    ctx_move = _make_ctx(pattern, 3, 3, color_index=0)
    tool.on_mouse_move(ctx_move, _mouse_event())
    assert tool.is_active

    tool.on_mouse_release(ctx_move, _mouse_event())
    assert not tool.is_active, "Nach dem Loslassen darf das Tool nicht mehr aktiv sein"


def test_gradient_tool_press_preserves_panel_selected_start_color():
    """Der Panel-Startfarbe-Combobox (set_start_color) darf nicht durch die
    global aktive Farbleisten-Farbe (ctx.current_color_index) ueberschrieben
    werden, sobald der Nutzer klickt."""
    pattern = _make_pattern_with_colors()
    tool = GradientTool()

    # Nutzer waehlt im Farbverlauf-Panel Startfarbe = 2, unabhaengig davon,
    # welche Farbe gerade in der globalen Farbleiste aktiv ist.
    tool.set_start_color(2)
    assert tool.start_color_index == 2

    # Globale Farbleiste zeigt weiterhin Farbe 0 (unveraendert) -- Klick zum
    # Ziehen einer Linie darf die Panel-Auswahl nicht verwerfen.
    ctx = _make_ctx(pattern, 1, 1, color_index=0)
    tool.on_mouse_press(ctx, _mouse_event())

    assert tool.start_color_index == 2, (
        "on_mouse_press() hat die Panel-Startfarbe still durch ctx.current_color_index ersetzt"
    )
