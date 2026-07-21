# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 16): SettingsDialog bleibt bei "Anwenden" (im
Gegensatz zu den meisten anderen Dialogen dieser Codebase) offen, waehrend
ein Live-Theme-Wechsel passieren kann (_apply_settings() -> settings_changed
-> misc_handlers.py::_apply_settings_from_dialog() -> set_theme()/
reapply_theme()) -- die "modale exec()-Dialoge brauchen kein
_apply_theme()"-Ausnahme gilt hier also NICHT. Drei Tab-Widgets/Sub-
Widgets hatten trotzdem keins: ColorsTab (Symbol-Vorschau-Rahmen+Label),
ColorButton (in canvas_tab.py 4x verwendet), ShortcutsTab (Info-Label).
Gleiche Bug-Klasse wie ruler.py/welcome_widget.py/tile_preview_panel.py/
minimap.py aus fruehreren Runden.
"""

import pytest

from pysticky.ui.styles import DARK_THEME, LIGHT_THEME, set_theme

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture(autouse=True)
def _reset_theme():
    yield
    set_theme("dark")


def test_colors_tab_symbol_preview_applies_theme_live(qtbot):
    from pysticky.ui.dialogs.settings_tabs.colors_tab import ColorsTab

    set_theme("dark")
    tab = ColorsTab()
    qtbot.addWidget(tab)

    assert DARK_THEME.bg_dark in tab._symbol_preview_frame.styleSheet()
    assert DARK_THEME.text_primary in tab.label_symbol_preview.styleSheet()

    set_theme("light")
    tab._apply_theme()

    assert LIGHT_THEME.bg_dark in tab._symbol_preview_frame.styleSheet()
    assert LIGHT_THEME.text_primary in tab.label_symbol_preview.styleSheet()


def test_color_button_applies_theme_live(qtbot):
    from pysticky.ui.dialogs.settings_tabs.color_button import ColorButton

    set_theme("dark")
    btn = ColorButton("#112233")
    qtbot.addWidget(btn)

    assert DARK_THEME.border_medium in btn.styleSheet()
    assert DARK_THEME.text_secondary in btn.styleSheet()

    set_theme("light")
    btn._apply_theme()

    assert LIGHT_THEME.border_medium in btn.styleSheet()
    assert LIGHT_THEME.text_secondary in btn.styleSheet()
    # Die gewaehlte Farbe selbst (THEME-unabhaengig) bleibt erhalten.
    assert "#112233" in btn.styleSheet()


def test_shortcuts_tab_info_label_applies_theme_live(qtbot):
    from pysticky.ui.dialogs.settings_tabs.shortcuts_tab import ShortcutsTab

    set_theme("dark")
    tab = ShortcutsTab(registry=None)
    qtbot.addWidget(tab)

    assert DARK_THEME.text_muted in tab._info_label.styleSheet()

    set_theme("light")
    tab._apply_theme()

    assert LIGHT_THEME.text_muted in tab._info_label.styleSheet()
