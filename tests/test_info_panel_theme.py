# -*- coding: utf-8 -*-
"""
Regressionstests (Runde 21) fuer InfoPanel-Theme-Staleness:

1. `SectionHeader` (info_panel_widgets.py) hatte gar keine `_apply_theme()`
   -- die Akzentfarbe der "STOFFZÄHLUNG"/"FARBÜBERSICHT"-Header blieb nach
   einem Live-Theme-Wechsel permanent auf der beim Konstruieren aktiven
   Farbe haengen.
2. `_ColorListItem.update_entry()` (der Incremental-Update-Pfad, der bei
   unveraenderter Farbanzahl statt eines Voll-Rebuilds laeuft) aktualisierte
   nur Text, nie die Swatch-Rahmenfarbe / Nummer- / Namen-Stylesheets --
   diese blieben nach einem Theme-Wechsel ohne Farb-Hinzufuegen/-Entfernen
   auf der alten Farbe haengen.

Gleiches Testmuster wie test_tile_preview_panel_theme.py/test_ruler_theme.py.
"""

import pytest

from pysticky.ui.styles import DARK_THEME, LIGHT_THEME, set_theme

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture(autouse=True)
def _reset_theme():
    yield
    set_theme("dark")


def test_section_header_applies_theme_live(qtbot):
    from pysticky.ui.panels.info_panel_widgets import SectionHeader

    set_theme("dark")
    header = SectionHeader("📋", "Test", DARK_THEME.info)
    qtbot.addWidget(header)

    assert DARK_THEME.info in header._title_label.styleSheet()

    set_theme("light")
    header._apply_theme(LIGHT_THEME.info)

    assert LIGHT_THEME.info in header._title_label.styleSheet()
    assert LIGHT_THEME.info in header._icon_label.styleSheet()


def test_info_panel_section_headers_restyle_on_theme_switch(qtbot):
    from pysticky.ui.panels.info_panel import InfoPanel

    set_theme("dark")
    panel = InfoPanel()
    qtbot.addWidget(panel)

    set_theme("light")
    panel._apply_theme()

    assert LIGHT_THEME.accent_primary in panel._section_fabric._title_label.styleSheet()
    assert LIGHT_THEME.info in panel._section_colors._title_label.styleSheet()


def test_color_list_item_update_entry_restyles_swatch_and_labels(qtbot, pattern_with_colors):
    """Simuliert den Incremental-Update-Pfad (_update_colors_list()'s
    'same_structure'-Fast-Path bei unveraenderter Farbanzahl): swatch/
    lbl_num/lbl_name muessen nach update_entry() die AKTUELLE Theme-Farbe
    zeigen, nicht die beim Konstruieren aktive."""
    from pysticky.ui.panels.info_panel_widgets import _ColorListItem

    set_theme("dark")
    entry = pattern_with_colors.color_entries[0]
    entry.stitch_count = 5

    def calc_thread(stitch_count, fabric_count, mode="stitch"):
        return "1.0m"

    item = _ColorListItem(0, entry, 14, calc_thread)
    qtbot.addWidget(item)
    assert DARK_THEME.border_light in item.swatch.styleSheet()
    assert DARK_THEME.text_muted in item.lbl_num.styleSheet()
    assert DARK_THEME.text_secondary in item.lbl_name.styleSheet()

    set_theme("light")
    item.update_entry(entry, 14, calc_thread)

    assert LIGHT_THEME.border_light in item.swatch.styleSheet()
    assert LIGHT_THEME.text_muted in item.lbl_num.styleSheet()
    assert LIGHT_THEME.text_secondary in item.lbl_name.styleSheet()
