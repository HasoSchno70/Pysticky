# -*- coding: utf-8 -*-
"""Regressionstest (Runde 26): BackstitchOptionsPanel's "Vorschau:"-Label
setzt sein eigenes explizites setStyleSheet() beim Konstruieren --
_apply_theme() rief bisher nur _apply_styles() (ein blanket QWidget-QSS)
auf, das laut Qt-Stylesheet-Kaskade NICHT gegen das explizit gesetzte
Label-Stylesheet gewinnt. Das Label blieb nach einem Live-Theme-Wechsel auf
der alten Textfarbe stehen, waehrend jedes andere Label im selben Panel
(nur ueber das blanket QSS gestylt) korrekt mitzog."""

import pytest

from pysticky.ui.styles import DARK_THEME, LIGHT_THEME, set_theme

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture(autouse=True)
def _reset_theme():
    yield
    set_theme("dark")


def test_preview_label_restyles_on_theme_switch(qtbot):
    from pysticky.ui.panels.backstitch_options_panel import BackstitchOptionsPanel

    set_theme("dark")
    panel = BackstitchOptionsPanel()
    qtbot.addWidget(panel)
    assert DARK_THEME.text_muted in panel._preview_label.styleSheet()

    set_theme("light")
    panel._apply_theme()

    assert LIGHT_THEME.text_muted in panel._preview_label.styleSheet()
