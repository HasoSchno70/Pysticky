# -*- coding: utf-8 -*-
"""
Tests fuer RulerWidget/RulerCorner Live-Theme-Switching.

Regression: beide Widgets cachten ihre Theme-Farben nur im __init__,
ohne _apply_theme() zu implementieren. reapply_theme() ruft _apply_theme()
auf allen Widgets auf, die es implementieren (siehe styles.py) -- ohne
diese Methode blieb das Lineal nach einem Theme-Wechsel bei den alten
Farben haengen, bis die App neu gestartet wurde.
"""

import pytest

from pysticky.ui.styles import DARK_THEME, LIGHT_THEME, set_theme

# pytest-qt's qtbot-Fixture sorgt fuer eine lebende QApplication
pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture(autouse=True)
def _reset_theme():
    """Stellt sicher, dass ein Themewechsel in diesem Test andere Tests
    nicht beeinflusst -- THEME ist globaler, gepatchter Modul-Zustand."""
    yield
    set_theme("dark")


def test_ruler_widget_applies_theme_live(qtbot):
    from PySide6.QtCore import Qt

    from pysticky.ui.widgets.ruler import RulerWidget

    set_theme("dark")
    ruler = RulerWidget(Qt.Orientation.Horizontal)
    qtbot.addWidget(ruler)

    assert ruler._bg_color.name().lower() == DARK_THEME.bg_light.lower()

    set_theme("light")
    ruler._apply_theme()

    assert ruler._bg_color.name().lower() == LIGHT_THEME.bg_light.lower()
    assert ruler._major_color.name().lower() == LIGHT_THEME.accent_primary.lower()


def test_ruler_corner_applies_theme_live(qtbot):
    from pysticky.ui.widgets.ruler import RulerCorner

    set_theme("dark")
    corner = RulerCorner()
    qtbot.addWidget(corner)

    set_theme("light")
    corner._apply_theme()

    assert corner._bg_color.name().lower() == LIGHT_THEME.bg_light.lower()
