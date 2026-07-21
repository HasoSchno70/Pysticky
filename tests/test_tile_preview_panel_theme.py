# -*- coding: utf-8 -*-
"""
Tests fuer TilePreviewPanel Live-Theme-Switching.

Regression: _setup_ui() setzte fuer Titel/Info-Label/"Kacheln:"-Label/
Spinboxen/Checkbox individuelle, THEME-abhaengige Stylesheets direkt beim
Aufbau, aber _apply_theme() (aufgerufen von reapply_theme() bei einem
Live-Theme-Wechsel, siehe styles.py) setzte nur den Panel-Hintergrund und
eine Preview-Repaint zurueck -- die Kind-Widgets blieben auf den alten
Theme-Farben haengen (derselbe Bug wie zuvor bei RulerWidget/WelcomeWidget,
siehe test_ruler_theme.py/test_welcome_widget_theme.py).
"""

import pytest

from pysticky.ui.styles import DARK_THEME, LIGHT_THEME, set_theme

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture(autouse=True)
def _reset_theme():
    yield
    set_theme("dark")


def test_tile_preview_panel_applies_theme_live(qtbot):
    from pysticky.ui.panels.tile_preview_panel import TilePreviewPanel

    set_theme("dark")
    panel = TilePreviewPanel()
    qtbot.addWidget(panel)

    assert DARK_THEME.text_secondary in panel._lbl_tiles.styleSheet()
    assert DARK_THEME.bg_dark in panel._spin_x.styleSheet()
    assert DARK_THEME.text_secondary in panel._chk_borders.styleSheet()

    set_theme("light")
    panel._apply_theme()

    assert LIGHT_THEME.text_secondary in panel._lbl_tiles.styleSheet()
    assert LIGHT_THEME.bg_dark in panel._spin_x.styleSheet()
    assert LIGHT_THEME.bg_dark in panel._spin_y.styleSheet()
    assert LIGHT_THEME.text_secondary in panel._chk_borders.styleSheet()
    assert LIGHT_THEME.bg_medium in panel.styleSheet()
