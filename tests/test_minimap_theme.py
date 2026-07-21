# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 14): MinimapPanel._apply_theme() aktualisierte nur
das Minimap-Widget und das Info-Label, nicht aber das Titel-Label
("ÜBERSICHT") -- dessen Styles.section_header()-Stylesheet (baut auf
THEME.accent_primary auf) wurde nur einmalig in _setup_ui() gesetzt.
Gleiche Bug-Klasse wie tile_preview_panel.py (Runde 12).
"""

import pytest

from pysticky.ui.styles import DARK_THEME, LIGHT_THEME, set_theme

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture(autouse=True)
def _reset_theme():
    yield
    set_theme("dark")


def test_minimap_panel_title_applies_theme_live(qtbot):
    from pysticky.ui.widgets.minimap import MinimapPanel

    set_theme("dark")
    panel = MinimapPanel()
    qtbot.addWidget(panel)

    assert DARK_THEME.accent_primary in panel._title.styleSheet()

    set_theme("light")
    panel._apply_theme()

    assert LIGHT_THEME.accent_primary in panel._title.styleSheet()
