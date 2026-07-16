# -*- coding: utf-8 -*-
"""
Tests fuer WelcomeWidget Live-Theme-Switching.

Regression: der Start-Screen (Header, Untertitel, Action-Kacheln,
"Zuletzt geoeffnet"-Liste) buk THEME-Farben nur einmalig in
setStyleSheet()-Aufrufe bzw. den Kachel-Konstruktor ein und implementierte
kein _apply_theme() -- reapply_theme() ruft _apply_theme() auf allen
Widgets auf, die es haben (siehe styles.py); ohne diese Methode blieb der
Start-Screen nach einem Theme-Wechsel komplett auf den alten Farben
haengen, bis die App neu gestartet wurde.
"""

import pytest

from pysticky.ui.styles import DARK_THEME, LIGHT_THEME, set_theme

# pytest-qt's qtbot-Fixture sorgt fuer eine lebende QApplication
pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture(autouse=True)
def _reset_theme():
    """Ein Themewechsel in diesem Test darf andere Tests nicht
    beeinflussen -- THEME ist globaler, gepatchter Modul-Zustand."""
    yield
    set_theme("dark")


def test_welcome_widget_applies_theme_to_tiles_and_list(qtbot):
    from pysticky.ui.widgets.welcome_widget import WelcomeWidget

    set_theme("dark")
    widget = WelcomeWidget()
    qtbot.addWidget(widget)

    assert widget._new_tile._accent.lower() == DARK_THEME.accent_primary.lower()
    assert DARK_THEME.bg_medium.lower() in widget._recent_list.styleSheet().lower()

    set_theme("light")
    widget._apply_theme()

    assert widget._new_tile._accent.lower() == LIGHT_THEME.accent_primary.lower()
    assert widget._open_tile._accent.lower() == LIGHT_THEME.accent_secondary.lower()
    assert widget._import_tile._accent.lower() == LIGHT_THEME.info.lower()
    assert widget._demo_tile._accent.lower() == LIGHT_THEME.accent_purple.lower()
    assert LIGHT_THEME.bg_medium.lower() in widget._recent_list.styleSheet().lower()
    assert LIGHT_THEME.accent_primary.lower() in widget._header_label.styleSheet().lower()


def test_welcome_widget_rebuilds_recent_items_with_new_theme(qtbot, tmp_path):
    from pysticky.ui.widgets.welcome_widget import WelcomeWidget

    existing_file = tmp_path / "test_pattern.pxs"
    existing_file.write_text("dummy")

    set_theme("dark")
    widget = WelcomeWidget()
    qtbot.addWidget(widget)
    widget.set_recent_files([str(existing_file)])
    assert widget._recent_list.count() == 1

    set_theme("light")
    widget._apply_theme()

    # Liste bleibt nach dem Rebuild inhaltlich unveraendert.
    assert widget._recent_list.count() == 1
    item_widget = widget._recent_list.itemWidget(widget._recent_list.item(0))
    assert item_widget is not None
