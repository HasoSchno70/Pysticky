# -*- coding: utf-8 -*-
"""Regressionstest (Clean-Code-Audit Runde 55, Fortschritts-Werkzeug-Grenzfaelle).

Das Fortschritts-Werkzeug (ProgressTool, ui/tools/progress_tool.py) markiert/
entmarkiert Stiche als erledigt ueber _on_stitch_marked_completed()/
_on_stitch_unmarked_completed() in ui/handlers/undo_handlers.py.

Der urspruengliche Runde-55-Fund schlug vor, Layer.mark_completed()/
unmark_completed() analog zu set_stitch()/clear() gegen gesperrte Ebenen zu
sperren. Nach Ruecksprache mit dem Nutzer ist das aber bewusst NICHT
gewuenscht: "Gesperrt" schuetzt laut UI-Tooltip ("gegen versehentliches
Bearbeiten") gezielt vor Design-Aenderungen (Farbe/Stichtyp) -- Fortschritts-
Markierung ist reines Bookkeeping fuer den Stickfortschritt des Nutzers und
aendert weder Farbe noch Stichtyp. Eine fertig entworfene, gesperrte Ebene
soll beim tatsaechlichen Abstricken trotzdem abgehakt werden koennen (siehe
auch tests/test_file_io_kitchen_sink_roundtrip.py, das genau dieses
Verhalten schon vor Runde 55 als korrekt annahm).

Diese Tests dokumentieren die bestaetigte, gewollte Ausnahme: Fortschritts-
Markierung funktioniert UNABHAENGIG vom Sperr-Status einer Ebene.
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def _new_window(qtbot):
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    return w


def test_layer_mark_completed_works_on_locked_layer():
    """Layer.mark_completed() direkt: gesperrte Ebene blockiert Fortschritt NICHT."""
    from pysticky.core import Layer

    layer = Layer(name="T", width=10, height=10)
    layer.set_stitch(3, 3, 0)
    layer.locked = True

    result = layer.mark_completed(3, 3)

    assert result is True
    assert layer.is_completed(3, 3) is True


def test_layer_unmark_completed_works_on_locked_layer():
    """Layer.unmark_completed() direkt: gesperrte Ebene blockiert Fortschritt NICHT."""
    from pysticky.core import Layer

    layer = Layer(name="T", width=10, height=10)
    layer.set_stitch(3, 3, 0)
    layer.locked = False
    layer.mark_completed(3, 3)
    layer.locked = True

    result = layer.unmark_completed(3, 3)

    assert result is True
    assert layer.is_completed(3, 3) is False


def test_marking_completed_on_locked_layer_still_creates_undo_entry(qtbot):
    from pysticky.core import Pattern

    w = _new_window(qtbot)
    pattern = Pattern(name="Gesperrt", width=10, height=10)
    pattern.active_layer.set_stitch(3, 3, 0)
    pattern.color_entries[0].stitch_count = 1
    pattern.active_layer.locked = True
    w.set_pattern(pattern)

    w._on_stitch_marked_completed(3, 3)

    assert w.undo_manager.undo_count == 1
    assert w.current_pattern.active_layer.is_completed(3, 3) is True

    w.undo_manager.undo()
    assert w.current_pattern.active_layer.is_completed(3, 3) is False


def test_unmarking_completed_on_locked_layer_still_creates_undo_entry(qtbot):
    from pysticky.core import Pattern

    w = _new_window(qtbot)
    pattern = Pattern(name="Gesperrt", width=10, height=10)
    pattern.active_layer.set_stitch(3, 3, 0)
    pattern.color_entries[0].stitch_count = 1
    pattern.active_layer.mark_completed(3, 3)
    pattern.active_layer.locked = True
    w.set_pattern(pattern)

    w._on_stitch_unmarked_completed(3, 3)

    assert w.undo_manager.undo_count == 1
    assert w.current_pattern.active_layer.is_completed(3, 3) is False


def test_marking_completed_on_unlocked_layer_still_works(qtbot):
    """Regulaerer (unlocked) Fall bleibt unveraendert korrekt."""
    from pysticky.core import Pattern

    w = _new_window(qtbot)
    pattern = Pattern(name="Offen", width=10, height=10)
    pattern.active_layer.set_stitch(3, 3, 0)
    pattern.color_entries[0].stitch_count = 1
    w.set_pattern(pattern)

    w._on_stitch_marked_completed(3, 3)

    assert w.undo_manager.undo_count == 1
    assert w.current_pattern.active_layer.is_completed(3, 3) is True

    w.undo_manager.undo()
    assert w.current_pattern.active_layer.is_completed(3, 3) is False


def test_progress_tool_boundary_cells_are_valid():
    """Grenzfall: erste/letzte Zelle des Musters (0,0) und (w-1,h-1) duerfen
    kein Index-/Off-by-one-Problem im Fortschritts-Werkzeug ausloesen."""
    from pysticky.ui.tools.base_tool import ToolContext
    from pysticky.ui.tools.progress_tool import MARK_COMPLETED, ProgressTool

    class DummyPattern:
        width = 10
        height = 10

    tool = ProgressTool()

    for gx, gy in [(0, 0), (9, 9)]:
        ctx = ToolContext(
            canvas=None,
            pattern=DummyPattern(),
            current_color_index=0,
            grid_x=gx,
            grid_y=gy,
            screen_x=0,
            screen_y=0,
            cell_size=10,
            offset_x=0,
            offset_y=0,
        )
        assert tool._is_valid_pos(ctx, gx, gy) is True

    # Direkt ausserhalb des Musters muss ungueltig sein (Off-by-one-Check).
    ctx_out = ToolContext(
        canvas=None,
        pattern=DummyPattern(),
        current_color_index=0,
        grid_x=10,
        grid_y=10,
        screen_x=0,
        screen_y=0,
        cell_size=10,
        offset_x=0,
        offset_y=0,
    )
    assert tool._is_valid_pos(ctx_out, 10, 10) is False
    assert MARK_COMPLETED == -100  # Sentinel unveraendert (Doku-Anker)
