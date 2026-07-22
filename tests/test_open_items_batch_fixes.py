# -*- coding: utf-8 -*-
"""Regressionstests fuer die "Kleinere sichere Fixes"-Sammlung aus dem
Open-Items-Backlog (dead-code-and-export-gaps.md), 2026-07-22:

1. PaletteManager.get_palette() war case-sensitiv, inkonsistent zu
   thread_cross_ref.find_equivalent()'s eigenem case-insensitiven Check.
2. Pattern.fill_rectangle(...,None) crashte mit TypeError (None in ein
   int16-numpy-Array zugewiesen) statt wie set_stitch(x,y,None) zu loeschen.
3. PerformanceManager.invalidate_region() markierte einen Chunk zu viel als
   dirty (Off-by-one, aktuell toter Pfad ohne echten Aufrufer).
4. HoopPlannerDialog zeigte immer "Stiche"-Vokabular, unabhaengig vom
   Diamond-Painting-Modus.
5. ToolButton/ToggleToolButton-Tooltips buken THEME.accent_primary/text_muted
   fest in den Tooltip-HTML-String ein, ohne bei einem Theme-Wechsel
   aktualisiert zu werden (reapply_styles() rief nur _apply_base_style(),
   nie eine Tooltip-Neuerstellung)."""

from PySide6.QtCore import QRect

from pysticky.core import Pattern, Thread
from pysticky.core.palette import PaletteManager, ThreadPalette


def test_get_palette_case_insensitive_fallback():
    pm = PaletteManager()
    pm._palettes["Anchor"] = ThreadPalette(name="Anchor", manufacturer="Anchor", threads=[])

    assert pm.get_palette("Anchor") is not None
    assert pm.get_palette("anchor") is not None, (
        "Regression: get_palette() muss case-insensitiv matchen, analog "
        "thread_cross_ref.find_equivalent()'s eigenem Vergleich"
    )
    assert pm.get_palette("ANCHOR") is not None
    assert pm.get_palette("Nichtvorhanden") is None


def test_fill_rectangle_none_erases_region_instead_of_crashing():
    pattern = Pattern(name="Test", width=10, height=10)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.fill_rectangle(0, 0, 4, 4, 0)
    assert pattern.get_stitch(2, 2) == 0

    # Vorher: TypeError beim Zuweisen von None in layer.grid (int16-Array).
    pattern.fill_rectangle(0, 0, 4, 4, None)

    assert pattern.get_stitch(2, 2) is None
    assert pattern.color_entries[0].stitch_count == 0


def test_invalidate_region_marks_correct_chunk_range(qtbot):
    from pysticky.ui.canvas import OptimizedCrossStitchCanvas

    canvas = OptimizedCrossStitchCanvas()
    qtbot.addWidget(canvas)
    perf = canvas._perf_manager
    perf._enabled = True
    chunk_size = perf._chunk_size

    # Rechteck das vollstaendig innerhalb von Chunk (0,0) liegt (chunk_size=64).
    perf.invalidate_region(QRect(0, 0, 5, 5))
    assert perf._dirty_chunks == {(0, 0)}, (
        "Regression: invalidate_region() markierte eine Chunk-Reihe/Spalte "
        "zu viel als dirty (Off-by-one bei rect.right()/bottom())"
    )

    perf._dirty_chunks.clear()
    # Rechteck das genau bis zur letzten Zelle von Chunk (0,0) reicht
    # (rect.right() ist inklusiv in Qt) -- darf NICHT Chunk (1,0) beruehren.
    perf.invalidate_region(QRect(0, 0, chunk_size, chunk_size))
    assert perf._dirty_chunks == {(0, 0)}

    perf._dirty_chunks.clear()
    # Rechteck das genau EINE Zelle in den naechsten Chunk hineinreicht.
    perf.invalidate_region(QRect(0, 0, chunk_size + 1, chunk_size + 1))
    assert perf._dirty_chunks == {(0, 0), (1, 0), (0, 1), (1, 1)}


def _diamond_pattern() -> Pattern:
    return Pattern(name="DP", width=20, height=20, mode="diamond")


def test_hoop_planner_dialog_uses_drill_vocabulary_for_diamond_patterns(qtbot):
    from pysticky.ui.dialogs.hoop_planner_dialog import HoopPlannerDialog

    dialog = HoopPlannerDialog(_diamond_pattern())
    qtbot.addWidget(dialog)

    assert dialog.spin_w.suffix() == " Drills"
    assert dialog.table.horizontalHeaderItem(4).text() == "Drills"


def test_hoop_planner_dialog_uses_stitch_vocabulary_for_stitch_patterns(qtbot):
    from pysticky.ui.dialogs.hoop_planner_dialog import HoopPlannerDialog

    pattern = Pattern(name="Stitch", width=20, height=20, mode="stitch")
    dialog = HoopPlannerDialog(pattern)
    qtbot.addWidget(dialog)

    assert dialog.spin_w.suffix() == " Stiche"
    assert dialog.table.horizontalHeaderItem(4).text() == "Stiche"


def test_tool_button_tooltip_refreshes_after_theme_switch(qtbot):
    # set_theme() patcht THEME in ALLEN Modulen die es importiert haben
    # (sys.modules-Iteration) -- ein naives `styles.THEME = ...` wuerde nur
    # das styles-Modul selbst umbiegen, nicht tool_bar.py's eigene
    # `from ..styles import THEME`-Kopie der Referenz.
    from pysticky.ui import styles
    from pysticky.ui.tools.tool_enum import Tool
    from pysticky.ui.widgets.tool_bar import ToolButton

    original_theme_name = styles._current_theme_name
    try:
        styles.set_theme("dark")
        btn = ToolButton(Tool.PENCIL, "P", "Stift", "P")
        qtbot.addWidget(btn)
        assert styles.DARK_THEME.accent_primary in btn.toolTip()

        styles.set_theme("light")
        btn._apply_stylesheet()

        assert styles.LIGHT_THEME.accent_primary in btn.toolTip(), (
            "Regression: Tool-Button-Tooltip behielt die alte THEME-Farbe "
            "nach einem Theme-Wechsel, weil reapply_styles() den Tooltip "
            "nie neu aufgebaut hat"
        )
        assert styles.DARK_THEME.accent_primary not in btn.toolTip()
    finally:
        styles.set_theme(original_theme_name)


def test_toggle_tool_button_tooltip_refreshes_after_theme_switch(qtbot):
    from pysticky.ui import styles
    from pysticky.ui.tools.tool_enum import Tool
    from pysticky.ui.widgets.tool_bar import ToggleToolButton

    original_theme_name = styles._current_theme_name
    try:
        styles.set_theme("dark")
        btn = ToggleToolButton(
            Tool.RECT, Tool.RECT_FILLED, "□", "■", "Rechteck", "Rechteck gefuellt", "R"
        )
        qtbot.addWidget(btn)

        styles.set_theme("light")
        btn._apply_stylesheet()

        assert styles.LIGHT_THEME.accent_primary in btn.toolTip()
        assert styles.LIGHT_THEME.text_muted in btn.toolTip()
        assert styles.DARK_THEME.accent_primary not in btn.toolTip()
    finally:
        styles.set_theme(original_theme_name)
