# -*- coding: utf-8 -*-
"""Regressionstests für den Werkzeuge-Settings-Tab (2026-07-18): 8 von 13
Einstellungen waren totes UI (default_tool, remember_tool, pipette_behavior,
pipette_show_info, fill_diagonal, marching_ants, backstitch_width,
backstitch_snap). select_mode wurde entfernt -- Auswahl ist aktuell ein
einzelnes QRect, "Hinzufügen"/"Subtrahieren" sind damit nicht darstellbar
ohne eine grundlegende Umstellung auf eine Masken-Repräsentation."""

from PySide6.QtCore import QSettings


def _qsettings_with_scope():
    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    return QSettings()


def test_default_tool_selected_at_startup(qtbot):
    from pysticky.ui.main_window import MainWindow
    from pysticky.ui.tools.tool_enum import Tool

    s = _qsettings_with_scope()
    old_default = s.value("default_tool")
    old_remember = s.value("remember_tool")
    old_last = s.value("last_tool")
    try:
        s.setValue("default_tool", Tool.FILL.name)
        s.setValue("remember_tool", False)
        s.remove("last_tool")
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()
        assert w.tool_bar.current_tool == Tool.FILL
    finally:
        for key, old in (
            ("default_tool", old_default),
            ("remember_tool", old_remember),
            ("last_tool", old_last),
        ):
            if old is None:
                s.remove(key)
            else:
                s.setValue(key, old)


def test_remember_tool_overrides_default_tool(qtbot):
    from pysticky.ui.main_window import MainWindow
    from pysticky.ui.tools.tool_enum import Tool

    s = _qsettings_with_scope()
    old_default = s.value("default_tool")
    old_remember = s.value("remember_tool")
    old_last = s.value("last_tool")
    try:
        s.setValue("default_tool", Tool.PENCIL.name)
        s.setValue("remember_tool", True)
        s.setValue("last_tool", Tool.RECT.name)
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()
        assert w.tool_bar.current_tool == Tool.RECT
    finally:
        for key, old in (
            ("default_tool", old_default),
            ("remember_tool", old_remember),
            ("last_tool", old_last),
        ):
            if old is None:
                s.remove(key)
            else:
                s.setValue(key, old)


def test_tool_change_persists_last_tool_only_when_remember_enabled(qtbot):
    from pysticky.ui.main_window import MainWindow
    from pysticky.ui.tools.tool_enum import Tool

    s = _qsettings_with_scope()
    old_remember = s.value("remember_tool")
    old_last = s.value("last_tool")
    try:
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()

        s.setValue("remember_tool", False)
        s.remove("last_tool")
        w._on_tool_changed(Tool.ERASER)
        assert s.value("last_tool") is None

        s.setValue("remember_tool", True)
        w._on_tool_changed(Tool.LINE)
        assert s.value("last_tool") == Tool.LINE.name
    finally:
        for key, old in (("remember_tool", old_remember), ("last_tool", old_last)):
            if old is None:
                s.remove(key)
            else:
                s.setValue(key, old)


def test_marching_ants_timer_follows_setting(qtbot):
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old = s.value("marching_ants")
    try:
        s.setValue("marching_ants", False)
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()
        assert w.canvas.marching_ants_enabled is False
        assert not w.canvas._marching_ants_timer.isActive()

        s.setValue("marching_ants", True)
        w._apply_settings_from_dialog()
        assert w.canvas.marching_ants_enabled is True
        assert w.canvas._marching_ants_timer.isActive()
    finally:
        if old is None:
            s.remove("marching_ants")
        else:
            s.setValue("marching_ants", old)


def test_backstitch_snap_applied_to_live_tool(qtbot):
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old = s.value("backstitch_snap")
    try:
        s.setValue("backstitch_snap", False)
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()
        tool = w.canvas._tool_manager.get_backstitch_tool()
        assert tool.snap_to_grid is False
    finally:
        if old is None:
            s.remove("backstitch_snap")
        else:
            s.setValue("backstitch_snap", old)


def test_backstitch_width_offset_applied(qtbot):
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old = s.value("backstitch_width")
    try:
        s.setValue("backstitch_width", 5)
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()
        assert w.canvas.backstitch_width_offset == 3  # 5 - 2 (Default)
    finally:
        if old is None:
            s.remove("backstitch_width")
        else:
            s.setValue("backstitch_width", old)


def test_fill_diagonal_reaches_diagonal_neighbor():
    """Ein rein diagonal verbundener Bereich darf nur bei fill_diagonal=True
    komplett gefuellt werden -- der Standard-Scanline-Algorithmus ist
    4-fach verbunden und wuerde diagonale Nachbarn nicht erreichen."""
    from pysticky.core import Pattern, Thread
    from pysticky.ui.tools.base_tool import ToolContext
    from pysticky.ui.tools.fill_tool import FillTool

    pattern = Pattern(width=2, height=2)
    pattern.color_entries.clear()
    idx_a = pattern.add_color(Thread.from_hex("A", "#FF0000"))
    idx_b = pattern.add_color(Thread.from_hex("B", "#00FF00"))
    # Schachbrett: (0,0) und (1,1) sind Farbe A, nur diagonal verbunden.
    pattern.set_stitch(0, 0, idx_a)
    pattern.set_stitch(1, 1, idx_a)
    pattern.set_stitch(1, 0, idx_b)
    pattern.set_stitch(0, 1, idx_b)

    tool = FillTool()
    ctx = ToolContext(
        canvas=None,
        pattern=pattern,
        current_color_index=idx_b,
        grid_x=0,
        grid_y=0,
        screen_x=0,
        screen_y=0,
        cell_size=20,
        offset_x=0,
        offset_y=0,
    )

    scanline_changes = tool._scanline_fill(ctx, 0, 0, idx_b)
    assert len(scanline_changes) == 1  # nur (0,0), (1,1) ist nicht 4-fach erreichbar

    diagonal_changes = tool._diagonal_fill(ctx, 0, 0, idx_b)
    assert len(diagonal_changes) == 2  # (0,0) UND (1,1) ueber die Diagonale erreicht
