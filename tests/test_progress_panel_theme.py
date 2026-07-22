# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 21): ProgressPanel._apply_theme() restylte nie den
"Sticken-Modus"-Hauptbutton -- _apply_stitch_mode_btn_style() wurde bisher
nur bei tatsaechlichen Zustandswechseln (set_stitch_mode_active()) gerufen,
nicht bei einem reinen Theme-Wechsel. Gleiches Testmuster wie
test_tile_preview_panel_theme.py.
"""

import pytest

from pysticky.ui.styles import DARK_THEME, LIGHT_THEME, set_theme

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture(autouse=True)
def _reset_theme():
    yield
    set_theme("dark")


def test_stitch_mode_button_restyles_on_theme_switch(qtbot):
    from pysticky.ui.panels.progress_panel import ProgressPanel

    set_theme("dark")
    panel = ProgressPanel()
    qtbot.addWidget(panel)
    assert DARK_THEME.bg_medium in panel.btn_stitch_mode.styleSheet()

    set_theme("light")
    panel._apply_theme()

    assert LIGHT_THEME.bg_medium in panel.btn_stitch_mode.styleSheet()
