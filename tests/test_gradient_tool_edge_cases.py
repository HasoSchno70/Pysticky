# -*- coding: utf-8 -*-
"""
Regressionstests (Runde 55, Farbverlauf-Tool-Grenzfaelle-Audit):
src/pysticky/ui/tools/gradient_tool.py::_calculate_gradient()

Bug: Die Schutzklausel `len(ctx.pattern.color_entries) < 2` verhinderte
JEDE Berechnung, sobald ein Muster weniger als 2 Palettenfarben hatte --
auch wenn Start- und Endfarbe (bewusst derselbe, einzige gueltige Index)
laengst gueltig waren. Ein frisches `Pattern()` hat aber per Default GENAU
1 Farbe (siehe pattern.py __post_init__, "Schwarz"), und das
Farbverlauf-Panel (gradient_options_panel.py::_update_combos) befuellt
Start-/End-Combobox auch mit nur 1 Eintrag (nur die automatische
Vorauswahl auf Index 0/1 wird bei <2 Farben uebersprungen -- Qt waehlt
bei Combobox-Befuellung trotzdem Index 0 in beiden Comboboxen). Ergebnis
vor dem Fix: Ziehen einer Verlaufslinie direkt nach dem Anlegen eines
neuen Musters (bevor der Nutzer weitere Farben hinzugefuegt hat) tat
STILLSCHWEIGEND gar nichts -- keine Fehlermeldung, keine Stiche, obwohl
Start=Ende=0 eine voellig gueltige Auswahl war.

Fix: Die `< 2`-Schranke entfaellt ersatzlos. `get_color_entry()` liefert
bei einem ungueltigen Index ohnehin sicher `None` (0 <= index < len-Check),
der bereits vorhandene `if not start_entry or not end_entry: return`-Zweig
faengt echte Fehlkonfigurationen (z.B. Panel zeigt auf einen inzwischen
geloeschten Index) weiterhin ab.

Zusaetzlich verifiziert (bereits korrektes Verhalten, keine Bugs):
- Klick ohne Ziehen (Start==Ende-Position): sinnvoller Fallback (nur
  Startfarbe an der Klickposition), kein Crash bei der Bresenham-Berechnung.
- Verlauf als EINE atomare Undo-Aktion, auch wenn die ueberschriebenen
  Zellen vorher unterschiedliche Original-Farben/leer waren.
- Diamond-Painting-Modus: set_stitch() erzwingt DIAMOND-Stich-Typ pro
  Farbe unabhaengig vom interpolierten RGB-Wert, daher bleibt der Typ auch
  beim Verlauf zwischen zwei verschiedenen Diamond-Farben konsistent.
"""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPoint, Qt

from pysticky.core import Pattern, Thread
from pysticky.core.stitch import StitchType
from pysticky.ui.tools.base_tool import ToolContext
from pysticky.ui.tools.gradient_tool import GradientTool


def _make_ctx(pattern, grid_x: int, grid_y: int, color_index: int = 0) -> ToolContext:
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


def _drag(tool: GradientTool, pattern, start, end):
    x1, y1 = start
    x2, y2 = end
    tool.on_mouse_press(_make_ctx(pattern, x1, y1), _mouse_event())
    tool.on_mouse_move(_make_ctx(pattern, x2, y2), _mouse_event())
    return tool.on_mouse_release(_make_ctx(pattern, x2, y2), _mouse_event())


def test_gradient_with_single_palette_color_still_draws():
    """Frisches Pattern() hat genau 1 Farbe -- Start=Ende=0 (die einzige
    gueltige Wahl) muss trotzdem die Verlaufslinie mit dieser Farbe setzen,
    statt stillschweigend eine leere Aenderungsliste zu liefern."""
    pattern = Pattern(width=5, height=5)
    assert len(pattern.color_entries) == 1

    tool = GradientTool()
    tool.set_start_color(0)
    tool.set_end_color(0)

    changes = _drag(tool, pattern, (0, 0), (3, 3))

    assert changes == [(0, 0, 0), (1, 1, 0), (2, 2, 0), (3, 3, 0)], (
        "Regression: Farbverlauf mit nur 1 Palettenfarbe lieferte frueher "
        "gar keine Aenderungen (Schutzklausel 'len(color_entries) < 2')"
    )


def test_gradient_identical_start_end_color_no_division_by_zero():
    """Identische Start-/Endfarbe (bei >=2 vorhandenen Palettenfarben) darf
    keinen Crash bei der Interpolation ausloesen -- nur eine durchgehende
    Farbe."""
    pattern = Pattern(width=5, height=5)
    pattern.add_color(Thread.from_hex("Weiss", "#ffffff"))
    tool = GradientTool()
    tool.set_start_color(0)
    tool.set_end_color(0)

    changes = _drag(tool, pattern, (0, 0), (4, 0))

    assert all(c[2] == 0 for c in changes)
    assert len(changes) == 5


def test_gradient_click_without_drag_falls_back_to_start_color():
    """Start==Ende-Position (Klick ohne Ziehen) darf bei der Bresenham-/
    Richtungsberechnung nicht crashen -- sinnvoller Fallback ist ein
    einzelner Punkt mit der Startfarbe."""
    pattern = Pattern(width=5, height=5)
    pattern.add_color(Thread.from_hex("Weiss", "#ffffff"))
    tool = GradientTool()
    tool.set_start_color(0)
    tool.set_end_color(1)

    ctx = _make_ctx(pattern, 2, 2)
    tool.on_mouse_press(ctx, _mouse_event())
    changes = tool.on_mouse_release(ctx, _mouse_event())

    assert changes == [(2, 2, 0)]


# ---------------------------------------------------------------------------
# Integrationstests: Undo-Atomaritaet + Diamond-Modus (echtes MainWindow,
# damit set_stitch()/execute_command() ueber den echten Pfad laufen -- siehe
# test_batch_performance.py fuer dasselbe main_window-Fixture-Muster).
# ---------------------------------------------------------------------------


@pytest.fixture
def main_window(qtbot):
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    return w


def _apply_gradient_changes_as_batch(main_window, changes):
    main_window.canvas.batch_started.emit("Farbverlauf")
    for x, y, color_idx in changes:
        main_window.canvas.stitch_placed.emit(x, y, color_idx)
    main_window.canvas.batch_ended.emit()


def test_gradient_apply_is_one_atomic_undo_step_with_varied_originals(main_window):
    """Der Verlauf ueberschreibt Zellen mit UNTERSCHIEDLICHEN Original-
    Zustaenden (verschiedene Farben + eine leere Zelle). Ein einziges Undo
    muss jede Zelle exakt auf ihren jeweiligen Vorzustand zuruecksetzen,
    nicht nur die zuletzt ueberschriebene."""
    pattern = Pattern(name="Grad", width=6, height=6)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#ff0000"))
    pattern.add_color(Thread.from_hex("Gruen", "#00ff00"))
    pattern.add_color(Thread.from_hex("Blau", "#0000ff"))

    # Unterschiedliche Ausgangszustaende entlang der geplanten Linie (0,0)-(3,3).
    pattern.set_stitch(0, 0, 2)
    pattern.set_stitch(1, 1, None)
    pattern.set_stitch(2, 2, 0)
    pattern.set_stitch(3, 3, 1)

    main_window.set_pattern(pattern)

    tool = main_window.canvas._tool_manager.get_gradient_tool()
    assert tool is not None
    tool.set_start_color(0)
    tool.set_end_color(1)

    changes = _drag(tool, pattern, (0, 0), (3, 3))
    assert len(changes) == 4

    _apply_gradient_changes_as_batch(main_window, changes)

    # Verlauf wurde angewendet: (0,0) und (3,3) sind jetzt Start-/Endfarbe.
    assert pattern.get_stitch(0, 0) == 0
    assert pattern.get_stitch(3, 3) == 1

    assert main_window.undo_manager.undo(), (
        "Ein einziges Undo muss den gesamten Verlauf zuruecknehmen"
    )

    assert pattern.get_stitch(0, 0) == 2, (
        "Zelle (0,0) muss ihre urspruengliche Farbe (2) zurueckerhalten"
    )
    assert pattern.get_stitch(1, 1) is None, "Zelle (1,1) muss wieder leer sein"
    assert pattern.get_stitch(2, 2) == 0, (
        "Zelle (2,2) muss ihre urspruengliche Farbe (0) zurueckerhalten"
    )
    assert pattern.get_stitch(3, 3) == 1, (
        "Zelle (3,3) muss ihre urspruengliche Farbe (1) zurueckerhalten"
    )


def test_gradient_between_diamond_colors_keeps_diamond_stitch_type(main_window):
    """Verlauf zwischen zwei Diamond-Painting-Farben muss jede platzierte
    Zelle als DIAMOND-Stich markieren (set_stitch() erzwingt das anhand von
    entry.is_diamond) -- unabhaengig davon, dass die Interpolation
    zwischendurch andere RGB-Werte/Farbindizes waehlt."""
    pattern = Pattern(name="DP", width=6, height=6, mode="diamond")
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("DP-Rot", "#ff0000"), is_diamond=True)
    pattern.add_color(Thread.from_hex("DP-Blau", "#0000ff"), is_diamond=True)

    main_window.set_pattern(pattern)

    tool = main_window.canvas._tool_manager.get_gradient_tool()
    assert tool is not None
    tool.set_start_color(0)
    tool.set_end_color(1)

    changes = _drag(tool, pattern, (0, 0), (4, 0))
    assert len(changes) == 5

    _apply_gradient_changes_as_batch(main_window, changes)

    for x, _y, color_idx in changes:
        assert pattern.get_stitch(x, 0) == color_idx
        assert pattern.active_layer.get_stitch_type(x, 0) == StitchType.DIAMOND.value, (
            f"Zelle ({x},0) wurde nicht als DIAMOND-Stich platziert"
        )
