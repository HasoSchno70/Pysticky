# -*- coding: utf-8 -*-
"""
Tests fuer Live-Theme-Switching der oberen Icon-Toolbar (mw_toolbar_mixin.py).

Regression: ``combo_stitch_type_label`` (Stichtyp-Picker-Beschriftung),
``_mode_switch_label`` ("Modus:"-Beschriftung), ``_symmetry_icon_label``
(Symmetrie-Icon) und die per ``_add_section_divider`` erzeugten
Section-Trennlinien sind reine ``QLabel``/``QFrame``-Instanzen ohne eigene
``_apply_theme()``-Methode. ``_reapply_all_widget_styles()``
(misc_handlers.py) ruft nach einem Theme-Wechsel zwar ``_apply_theme()`` auf
allen Widgets auf, die es implementieren, aber diese Widgets hatten keins --
sie blieben nach einem Live-Theme-Wechsel dauerhaft auf den Farben des
Themes haengen, unter dem die Toolbar urspruenglich gebaut wurde (gleiche
Bugklasse wie zuvor bei RulerWidget/WelcomeWidget/TilePreviewPanel, siehe
test_ruler_theme.py/test_welcome_widget_theme.py/test_tile_preview_panel_theme.py).
"""

import pytest

from pysticky.ui.styles import DARK_THEME, LIGHT_THEME, set_theme

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture(autouse=True)
def _reset_theme():
    yield
    set_theme("dark")


def _make_main_window(qtbot):
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    return w


def test_toolbar_stitch_label_applies_theme_live(qtbot):
    set_theme("dark")
    w = _make_main_window(qtbot)

    assert DARK_THEME.text_muted in w.combo_stitch_type_label.styleSheet()

    set_theme("light")
    w._apply_toolbar_theme_colors()

    assert LIGHT_THEME.text_muted in w.combo_stitch_type_label.styleSheet()
    assert DARK_THEME.text_muted not in w.combo_stitch_type_label.styleSheet()


def test_toolbar_mode_switch_label_applies_theme_live(qtbot):
    set_theme("dark")
    w = _make_main_window(qtbot)

    assert DARK_THEME.text_primary in w._mode_switch_label.styleSheet()

    set_theme("light")
    w._apply_toolbar_theme_colors()

    assert LIGHT_THEME.text_primary in w._mode_switch_label.styleSheet()


def test_toolbar_symmetry_icon_label_applies_theme_live(qtbot):
    set_theme("dark")
    w = _make_main_window(qtbot)

    assert DARK_THEME.text_muted in w._symmetry_icon_label.styleSheet()

    set_theme("light")
    w._apply_toolbar_theme_colors()

    assert LIGHT_THEME.text_muted in w._symmetry_icon_label.styleSheet()


def test_toolbar_section_dividers_apply_theme_live(qtbot):
    set_theme("dark")
    w = _make_main_window(qtbot)

    assert len(w._toolbar_dividers) > 0
    for line, color_attr in w._toolbar_dividers:
        expected = getattr(DARK_THEME, color_attr)
        assert expected in line.styleSheet()

    set_theme("light")
    w._apply_toolbar_theme_colors()

    for line, color_attr in w._toolbar_dividers:
        expected = getattr(LIGHT_THEME, color_attr)
        assert expected in line.styleSheet()


def test_toolbar_theme_colors_wired_into_full_reapply(qtbot):
    """_reapply_all_widget_styles() (die echte Live-Theme-Wechsel-Methode)
    muss _apply_toolbar_theme_colors() mit aufrufen -- nicht nur der direkte
    Methodenaufruf in den Tests oben."""
    set_theme("dark")
    w = _make_main_window(qtbot)

    set_theme("light")
    w._reapply_all_widget_styles()

    assert LIGHT_THEME.text_muted in w.combo_stitch_type_label.styleSheet()
    for line, color_attr in w._toolbar_dividers:
        expected = getattr(LIGHT_THEME, color_attr)
        assert expected in line.styleSheet()
