# -*- coding: utf-8 -*-
"""
Regressionstests für PolygonTool-Grenzfälle (Runde 53 Clean-Code-Audit).

Fokus: Der Scanline-Fuellalgorithmus in ``_fill_polygon`` iterierte vor dem
Fix ueber die ROHEN, unbeschraenkten Klickpunkt-Koordinaten statt ueber den
gueltigen Musterbereich -- bei weit ausserhalb von Pattern.width/height
liegenden Punkten (z.B. bei stark herausgezoomtem/verschobenem Canvas)
erzeugte das potenziell zehntausende bis Millionen nutzloser Zellen, die im
Anschluss in ``on_mouse_press`` ohnehin ueber ``_is_valid_pos`` verworfen
wurden. Der Fix uebernimmt das bereits in
``lasso_select_tool.py::_fill_lasso_polygon`` etablierte Clamping-Muster.
"""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPoint, Qt

from pysticky.core.pattern import Pattern
from pysticky.ui.tools.base_tool import ToolContext
from pysticky.ui.tools.polygon_tool import PolygonTool

pytestmark = pytest.mark.usefixtures("qtbot")


def _make_ctx(pattern: Pattern, grid_x: int, grid_y: int, color_index: int = 0) -> ToolContext:
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


def _click_polygon(tool: PolygonTool, pattern: Pattern, points: list[tuple[int, int]]):
    """Simuliert Linksklicks auf ``points``, dann Rechtsklick zum Schließen."""
    for x, y in points[:-1]:
        tool.on_mouse_press(_make_ctx(pattern, x, y), _mouse_event(Qt.MouseButton.LeftButton))
    last_ctx = _make_ctx(pattern, *points[-1])
    tool.on_mouse_press(last_ctx, _mouse_event(Qt.MouseButton.LeftButton))
    close_ctx = _make_ctx(pattern, *points[-1])
    return tool.on_mouse_press(close_ctx, _mouse_event(Qt.MouseButton.RightButton))


def test_fill_polygon_clamps_scanline_to_pattern_bounds():
    """_fill_polygon darf nur innerhalb von [0, width) x [0, height) scannen,
    selbst wenn die rohen Klickpunkte weit ausserhalb liegen (Regressionstest
    fuer den Round-53-Fix: vorher lief die Scanline ueber den vollen rohen
    Koordinatenbereich, was bei extremen Ausreissern zehntausende bis
    Millionen nutzloser Zellen erzeugte)."""
    pattern = Pattern(width=10, height=10)
    tool = PolygonTool(filled=True)
    tool.activate()
    tool._points = [(-2000, 0), (2000, 0), (0, 5)]

    ctx = _make_ctx(pattern, 0, 5)
    filled = tool._fill_polygon(ctx)

    assert len(filled) < 200, (
        f"Scanline sollte auf den 10x10-Musterbereich begrenzt sein, "
        f"erzeugte aber {len(filled)} Zellen"
    )
    for x, y in filled:
        assert 0 <= x < pattern.width
        assert 0 <= y < pattern.height


def test_fill_polygon_entirely_outside_pattern_yields_empty():
    """Ein Polygon, dessen Punkte komplett ausserhalb des Musters liegen,
    darf keine Zellen erzeugen (statt einer leeren, aber teuren Iteration
    ueber einen weit ausserhalb liegenden Koordinatenbereich)."""
    pattern = Pattern(width=10, height=10)
    tool = PolygonTool(filled=True)
    tool.activate()
    tool._points = [(100, 100), (200, 100), (150, 200)]

    ctx = _make_ctx(pattern, 100, 100)
    filled = tool._fill_polygon(ctx)

    assert filled == set()


def test_polygon_out_of_bounds_close_produces_only_valid_changes():
    """Klickpunkte ausserhalb des Musterrands fuehren zu sauberem Clipping
    beim Schliessen ueber Rechtsklick, kein Crash, keine ungueltigen Zellen."""
    pattern = Pattern(width=10, height=10)
    tool = PolygonTool(filled=True)
    tool.activate()

    changes = _click_polygon(tool, pattern, [(-5, -5), (15, -5), (5, 15)])

    assert len(changes) > 0
    for x, y, _color in changes:
        assert 0 <= x < pattern.width
        assert 0 <= y < pattern.height


def test_polygon_close_with_one_point_is_noop():
    """Schliessen (Rechtsklick) nach nur einem einzigen Klickpunkt bricht
    sauber ab (kein Crash, leeres Ergebnis, Werkzeugzustand zurückgesetzt)."""
    pattern = Pattern(width=20, height=20)
    tool = PolygonTool(filled=False)
    tool.activate()

    tool.on_mouse_press(_make_ctx(pattern, 5, 5), _mouse_event(Qt.MouseButton.LeftButton))
    changes = tool.on_mouse_press(
        _make_ctx(pattern, 5, 5), _mouse_event(Qt.MouseButton.RightButton)
    )

    assert changes == []
    assert tool._points == []
    assert tool._active is False


def test_polygon_close_with_two_points_is_noop():
    """Zwei Punkte reichen nicht für eine Fläche -- Schliessen bricht ab
    statt z.B. eine einzelne Linie zu erzeugen (dokumentiertes Verhalten:
    ein Polygon braucht mindestens 3 Punkte)."""
    pattern = Pattern(width=20, height=20)
    tool = PolygonTool(filled=False)
    tool.activate()

    tool.on_mouse_press(_make_ctx(pattern, 5, 5), _mouse_event(Qt.MouseButton.LeftButton))
    tool.on_mouse_press(_make_ctx(pattern, 10, 5), _mouse_event(Qt.MouseButton.LeftButton))
    changes = tool.on_mouse_press(
        _make_ctx(pattern, 10, 5), _mouse_event(Qt.MouseButton.RightButton)
    )

    assert changes == []
    assert tool._points == []


def test_fill_polygon_self_intersecting_bowtie_uses_even_odd_rule():
    """Ein selbstüberschneidendes Polygon (Schmetterlings-/Bowtie-Form) wird
    per Even-Odd-Regel gefüllt: beide Dreieck-Lappen gefüllt, die "Taille"
    (Bereiche außerhalb beider Lappen) bleibt leer."""
    pattern = Pattern(width=20, height=20)
    tool = PolygonTool(filled=True)
    tool.activate()
    tool._points = [(0, 0), (10, 10), (0, 10), (10, 0)]

    ctx = _make_ctx(pattern, 0, 0)
    filled = tool._fill_polygon(ctx)

    # Innerhalb beider Dreieck-Lappen
    assert (5, 9) in filled
    assert (5, 1) in filled
    # Außerhalb der Form (in der "Taille" links/rechts der Kreuzung)
    assert (1, 5) not in filled
    assert (9, 5) not in filled


def test_escape_during_polygon_leaves_no_state():
    """Escape mitten im Klicken bricht sauber ab, ohne Restzustand
    (kein reservierter, nie ausgeführter Undo-Batch -- das Werkzeug selbst
    öffnet ohnehin keinen Batch, bevor das Polygon fertig geschlossen ist)."""
    pattern = Pattern(width=20, height=20)
    tool = PolygonTool(filled=False)
    tool.activate()

    tool.on_mouse_press(_make_ctx(pattern, 2, 2), _mouse_event(Qt.MouseButton.LeftButton))
    tool.on_mouse_press(_make_ctx(pattern, 8, 2), _mouse_event(Qt.MouseButton.LeftButton))

    escape_event = MagicMock()
    escape_event.key.return_value = Qt.Key.Key_Escape
    handled = tool.on_key_press(_make_ctx(pattern, 8, 2), escape_event)

    assert handled is True
    assert tool._points == []
    assert tool._active is False
