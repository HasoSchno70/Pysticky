# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 21): GradientOptionsPanel._apply_theme() liess
Titel, Info-Text, "Startfarbe:"/"Endfarbe:"-Labels und den "Farben
tauschen"-Button aus -- sie wurden in _setup_ui() nur als lokale
Variablen erzeugt (nicht auf self gespeichert), sodass _apply_theme()
sie gar nicht erreichen konnte. Nach einem Live-Theme-Wechsel blieben
diese Widgets permanent auf der Konstruktions-Theme-Farbe haengen.
"""

import pytest

from pysticky.ui.styles import DARK_THEME, LIGHT_THEME, set_theme

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture(autouse=True)
def _reset_theme():
    yield
    set_theme("dark")


def test_gradient_options_panel_restyles_all_labels_on_theme_switch(qtbot):
    from pysticky.ui.panels.gradient_options_panel import GradientOptionsPanel

    set_theme("dark")
    panel = GradientOptionsPanel()
    qtbot.addWidget(panel)
    assert DARK_THEME.text_muted in panel._info.styleSheet()
    assert DARK_THEME.text_secondary in panel._start_label.styleSheet()
    assert DARK_THEME.text_secondary in panel._end_label.styleSheet()

    set_theme("light")
    panel._apply_theme()

    assert LIGHT_THEME.text_muted in panel._info.styleSheet()
    assert LIGHT_THEME.text_secondary in panel._start_label.styleSheet()
    assert LIGHT_THEME.text_secondary in panel._end_label.styleSheet()
