# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 24): OverviewTab.update_stats()'s "Farben"-Karte
zeigte bei skipped_colors == 0 stats["color_count"] -- das ist IMMER die
volle Palettengroesse (len(color_entries)), nicht die Anzahl tatsaechlich
gemalter Farben. Ein Muster mit ungenutzten Palettenfarben (z.B. manuell
hinzugefuegt, nie gemalt) zeigte dadurch eine zu hohe Zahl, sobald
skipped_colors zufaellig 0 war -- die angezeigte Bedeutung der Karte
kippte abhaengig von einem voellig unabhaengigen Flag.
"""

import pytest

from pysticky.core import Pattern, Thread

pytestmark = pytest.mark.usefixtures("qtbot")


def test_color_count_excludes_unused_palette_entries_even_without_skip(qtbot):
    from pysticky.ui.dialogs.statistics_tabs.overview_tab import OverviewTab

    pattern = Pattern(width=10, height=10)
    pattern.color_entries.clear()
    idx_used = pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.add_color(Thread.from_hex("Nie gemalt", "#00FF00"))  # bleibt ungenutzt
    pattern.set_stitch(0, 0, idx_used)

    tab = OverviewTab()
    qtbot.addWidget(tab)
    tab.update_stats(pattern, pattern.get_statistics())

    assert tab._card_colors._value_label.text() == "1"


def test_color_count_matches_used_minus_skipped_when_skip_present(qtbot):
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

    assert "1" in tab._card_colors._value_label.text()
    assert "übersp" in tab._card_colors._value_label.text()
