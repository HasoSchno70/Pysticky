# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 24): colors_tab.py's Skip-Markierung
"(nicht sticken)" und overview_tab.py's "Farben"-Karten-Suffix
"übersp." waren nie durch t() geschickt -- im Englisch-Modus zeigten
beide dauerhaft deutschen Text.
"""

import pytest

from pysticky.core.i18n import set_language


@pytest.fixture
def english_language():
    set_language("en")
    try:
        yield
    finally:
        set_language("de")


def test_colors_tab_skip_marker_is_translated(qtbot, english_language):
    from pysticky.core import Pattern, Thread
    from pysticky.ui.dialogs.statistics_tabs.colors_tab import ColorsTab

    pattern = Pattern(width=10, height=10)
    pattern.color_entries.clear()
    idx = pattern.add_color(Thread.from_hex("Stoff", "#EEEEEE"))
    pattern.color_entries[idx].skip_stitching = True
    pattern.set_stitch(0, 0, idx)

    tab = ColorsTab()
    qtbot.addWidget(tab)
    tab.update_stats(pattern, pattern.get_statistics())

    name_item = tab._colors_table.item(0, 2)
    assert "nicht sticken" not in name_item.text()


def test_overview_tab_skipped_suffix_is_translated(qtbot, english_language):
    from pysticky.core import Pattern, Thread
    from pysticky.ui.dialogs.statistics_tabs.overview_tab import OverviewTab

    pattern = Pattern(width=10, height=10)
    pattern.color_entries.clear()
    idx_used = pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    idx_fabric = pattern.add_color(Thread.from_hex("Stoff", "#EEEEEE"))
    pattern.color_entries[idx_fabric].skip_stitching = True
    pattern.set_stitch(0, 0, idx_used)
    pattern.set_stitch(1, 1, idx_fabric)

    tab = OverviewTab()
    qtbot.addWidget(tab)
    tab.update_stats(pattern, pattern.get_statistics())

    assert "übersp" not in tab._card_colors._value_label.text()
