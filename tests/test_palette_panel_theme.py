# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 21): PalettePanel._apply_theme() rief nie
_refresh_color_list() auf -- bereits gerenderte Swatch-Icons backen
THEME.accent_primary/border_light in ein Raster-QPixmap
(_create_color_icon), das nach einem Live-Theme-Wechsel auf der alten
Theme-Farbe haengen blieb, bis der Nutzer die Liste ohnehin durch Suche
oder Palettenwechsel neu aufbaute.
"""

from unittest.mock import patch

import pytest

from pysticky.ui.styles import set_theme

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture(autouse=True)
def _reset_theme():
    yield
    set_theme("dark")


def test_apply_theme_refreshes_color_list(qtbot):
    from pysticky.ui.panels.palette_panel import PalettePanel

    panel = PalettePanel()
    qtbot.addWidget(panel)

    with patch.object(panel, "_refresh_color_list") as mock_refresh:
        panel._apply_theme()
        mock_refresh.assert_called_once()
