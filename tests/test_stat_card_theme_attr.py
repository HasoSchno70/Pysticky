# -*- coding: utf-8 -*-
"""Regressionstest (Runde 26): StatCard (info_panel_widgets.py) baute seine
Icon-Gradient-Farbe (`icon_container`-Stylesheet) und den Rahmen-/Glow-Akzent
(`paintEvent`, ueber `self._color`) einmalig beim Konstruieren aus dem zu
diesem Zeitpunkt aktiven THEME.* -- 6 der 9 Karten in info_panel.py (Stiche,
Farben, Groesse, Masse, Ebenen, Schwierigkeit) uebergeben einen bereits
aufgeloesten THEME.*-Farbwert als `color`-Parameter. `_apply_theme()`
aktualisierte bisher nur die Text-Labels, nie `self._color` selbst oder das
Icon-Gradient -- nach einem Live-Theme-Wechsel blieben Icon-Hintergrund,
Rahmenfarbe und der linke Glow-Streifen dieser 6 Karten dauerhaft auf der
alten Theme-Farbe stehen. Fix: neuer `theme_attr`-Parameter laesst StatCard
die Farbe bei jedem `_apply_theme()`-Aufruf frisch aus THEME nachschlagen;
reine Hex-Literal-Karten (Stickzeit/Garnbedarf/Fortschritt) bleiben bewusst
unveraendert (dekorative Farben, siehe MEMORY.md)."""

import pytest

from pysticky.ui.styles import DARK_THEME, LIGHT_THEME, set_theme

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture(autouse=True)
def _reset_theme():
    yield
    set_theme("dark")


def test_stat_card_with_theme_attr_refreshes_color_on_apply_theme(qtbot):
    from pysticky.ui.panels.info_panel_widgets import StatCard

    set_theme("dark")
    card = StatCard("✦", "Test", theme_attr="accent_primary")
    qtbot.addWidget(card)

    assert card._color.name().lower() == DARK_THEME.accent_primary.lower()
    assert DARK_THEME.accent_primary.lower() in card.icon_container.styleSheet().lower()

    set_theme("light")
    card._apply_theme()

    assert card._color.name().lower() == LIGHT_THEME.accent_primary.lower()
    assert LIGHT_THEME.accent_primary.lower() in card.icon_container.styleSheet().lower()


def test_stat_card_with_literal_hex_color_stays_unchanged_on_apply_theme(qtbot):
    """Dekorative Hex-Literal-Karten (z.B. Stickzeit "#40c8b0") duerfen sich
    NICHT mit dem Theme aendern -- das war schon immer beabsichtigt."""
    from pysticky.ui.panels.info_panel_widgets import StatCard

    set_theme("dark")
    card = StatCard("⏱", "Test", "#40c8b0")
    qtbot.addWidget(card)

    assert card._color.name().lower() == "#40c8b0"

    set_theme("light")
    card._apply_theme()

    assert card._color.name().lower() == "#40c8b0"


def test_info_panel_theme_cards_refresh_icon_color(qtbot):
    from pysticky.ui.panels.info_panel import InfoPanel

    set_theme("dark")
    panel = InfoPanel()
    qtbot.addWidget(panel)
    icon_style = panel.card_stitches.icon_container.styleSheet().lower()
    assert DARK_THEME.accent_primary.lower() in icon_style

    set_theme("light")
    panel._apply_theme()

    icon_style = panel.card_stitches.icon_container.styleSheet().lower()
    assert LIGHT_THEME.accent_primary.lower() in icon_style
