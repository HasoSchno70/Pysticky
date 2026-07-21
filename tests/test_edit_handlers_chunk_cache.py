# -*- coding: utf-8 -*-
"""
Regressionstests (Runde 13): Farbe-ersetzen, Farben-tauschen und
Text-Tool-Bestaetigen aenderten Stiche ueber einen manuellen
`canvas.stitch_placed.emit(...)`-Loop statt ueber `canvas._apply_changes()`
-- dabei wird `invalidate_cell()` NICHT aufgerufen. Auf Mustern ueber dem
Chunk-Cache-Schwellwert (>200x200 Zellen, `OptimizedCrossStitchCanvas`)
blieb der betroffene Chunk-Pixmap dadurch beim alten Bild haengen, bis eine
unabhaengige Aktion (Zoom, Undo, ein weiterer Edit) den Cache zufaellig
mitinvalidierte -- exakt dieselbe Bug-Klasse, die Runde 4 fuer
Selection-Operationen (`selection_handlers.py::_run_selection_op`) schon
einmal gefixt hat.
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


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


def _large_pattern_with_two_colors():
    from pysticky.core import Pattern, Thread

    pattern = Pattern(name="Gross", width=210, height=210)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.add_color(Thread.from_hex("Blau", "#0000FF"))
    pattern.set_stitch(3, 3, 0)
    return pattern


def _cache_dummy_chunk_at(canvas, x, y):
    from PySide6.QtGui import QPixmap

    chunk_size = canvas._perf_manager._chunk_size
    chunk = (x // chunk_size, y // chunk_size)
    canvas._perf_manager.cache_chunk(
        *chunk, QPixmap(1, 1), canvas._cell_size, True, True, False, False
    )
    return chunk


def test_swap_color_pair_invalidates_chunk_cache(main_window):
    w = main_window
    w.set_pattern(_large_pattern_with_two_colors())
    assert w.canvas._perf_manager.enabled

    chunk = _cache_dummy_chunk_at(w.canvas, 3, 3)
    assert chunk in w.canvas._perf_manager._chunk_cache

    w._swap_color_pair(0, 1)

    # get_cached_chunk() ist die massgebliche Anfrage, die der naechste
    # paintEvent stellt -- muss None liefern (Neu-Rendern erzwingen).
    assert (
        w.canvas._perf_manager.get_cached_chunk(
            *chunk, w.canvas._pattern, w.canvas._cell_size, True, True, False, False
        )
        is None
    )


def test_replace_color_invalidates_chunk_cache(main_window, monkeypatch):
    w = main_window
    w.set_pattern(_large_pattern_with_two_colors())
    chunk = _cache_dummy_chunk_at(w.canvas, 3, 3)

    from pysticky.ui import dialogs as dialogs_mod

    monkeypatch.setattr(dialogs_mod.ReplaceColorDialog, "exec", lambda self: True)
    monkeypatch.setattr(dialogs_mod.ReplaceColorDialog, "get_replacements", lambda self: [(0, 1)])

    w._on_replace_color()

    assert (
        w.canvas._perf_manager.get_cached_chunk(
            *chunk, w.canvas._pattern, w.canvas._cell_size, True, True, False, False
        )
        is None
    )


def test_text_confirm_invalidates_chunk_cache(main_window, monkeypatch):
    w = main_window
    w.set_pattern(_large_pattern_with_two_colors())
    chunk = _cache_dummy_chunk_at(w.canvas, 3, 3)

    class _FakeTextTool:
        has_preview = True

        def confirm_text(self, ctx):
            return [(3, 3, 1)]

    monkeypatch.setattr(w.canvas._tool_manager, "get_text_tool", lambda: _FakeTextTool())

    w._on_text_confirm()

    assert (
        w.canvas._perf_manager.get_cached_chunk(
            *chunk, w.canvas._pattern, w.canvas._cell_size, True, True, False, False
        )
        is None
    )
