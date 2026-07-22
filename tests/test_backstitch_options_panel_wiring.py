# -*- coding: utf-8 -*-
"""Regressionstest: BackstitchOptionsPanel war seit langem fertig
implementiert (~600 Zeilen, Signale fuer Dicke/Linienart/Endstil/Snap),
hatte aber KEIN Dock-Widget und wurde nie angezeigt -- anders als Text-
und Gradient-Werkzeug, die je ein eigenes Dock bekommen. Ausserdem
schlugen sich seine Signale nirgends auf die tatsaechliche Canvas-
Rueckstich-Darstellung durch (Linienart/Endstil waren im Renderer immer
hart auf Solid/Round codiert)."""

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
    w.show()
    return w


def test_backstitch_options_dock_exists_and_toggles_with_tool(main_window):
    from pysticky.ui.tools.tool_enum import Tool

    w = main_window
    assert hasattr(w, "backstitch_options_dock")
    assert w.backstitch_options_dock.objectName() == "dock_backstitch_options"

    w.tool_bar.select_tool(Tool.BACKSTITCH)
    assert w.backstitch_options_dock.isVisible()

    w.tool_bar.select_tool(Tool.PENCIL)
    assert not w.backstitch_options_dock.isVisible()


def test_panel_style_signals_reach_canvas_rendering_state(main_window):
    from PySide6.QtCore import Qt

    from pysticky.ui.tools.tool_enum import Tool

    w = main_window
    w.tool_bar.select_tool(Tool.BACKSTITCH)
    panel = w.backstitch_options_panel

    panel._style_combo.setCurrentIndex(1)  # "Gestrichelt" -> DashLine
    assert w.canvas._backstitch_line_style == Qt.PenStyle.DashLine

    panel._cap_combo.setCurrentIndex(1)  # "Eckig" -> SquareCap
    assert w.canvas._backstitch_cap_style == Qt.PenCapStyle.SquareCap

    panel._thickness_slider.setValue(5)
    assert w.canvas._backstitch_width_offset == 5

    panel._snap_check.setChecked(False)
    backstitch_tool = w.canvas._tool_manager.get_backstitch_tool()
    assert backstitch_tool.snap_to_grid is False
