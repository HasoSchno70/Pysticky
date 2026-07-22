# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 12): ThreadTab (Statistik-Dialog -> Garnverbrauch)
las den Stoffzaehlungswert per Positions-Index aus COMMON_FABRIC_COUNTS --
die sichtbare Combo-Liste hatte 6 Eintraege ohne "22", COMMON_FABRIC_COUNTS
aber 7 Eintraege MIT "22" dazwischen. Ab "Evenweave 28" (Index 4) griff
dadurch der falsche Wert (22 statt 28) fuer sowohl die
Garnverbrauch-Berechnung als auch calculator_settings() (das den
CSV-Export speist).
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def test_fabric_combo_returns_correct_count_for_all_entries(qtbot, pattern_with_stitches):
    from pysticky.ui.dialogs.statistics_tabs.thread_tab import ThreadTab

    tab = ThreadTab()
    qtbot.addWidget(tab)
    tab.update_stats(pattern_with_stitches, {})

    expected = [11, 14, 16, 18, 28, 32]
    for index, count in enumerate(expected):
        tab._fabric_combo.setCurrentIndex(index)
        assert tab._fabric_combo.currentData() == count
        fabric_count, _waste, _price = tab.calculator_settings()
        assert fabric_count == count


def test_update_stats_syncs_combo_to_pattern_fabric_count(qtbot):
    """Regression (Runde 24): die Stoffart-Combobox blieb immer auf dem
    hart-codierten Default "Aida 14" stehen, unabhaengig vom tatsaechlichen
    pattern.fabric_count -- der Tab oeffnete sich fuer ein Aida-18- oder
    Evenweave-28-Muster mit einer falschen Stoffzaehlung und berechnete
    Straenge/Kosten dementsprechend falsch, bis der Nutzer es manuell
    bemerkte und umstellte."""
    from pysticky.core import Pattern, Thread
    from pysticky.ui.dialogs.statistics_tabs.thread_tab import ThreadTab

    pattern = Pattern(width=10, height=10, fabric_count=28)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.set_stitch(0, 0, 0)

    tab = ThreadTab()
    qtbot.addWidget(tab)
    tab.update_stats(pattern, {})

    assert tab._fabric_combo.currentData() == 28


def test_calculator_settings_evenweave_28_not_confused_with_22(qtbot, pattern_with_stitches):
    """Konkreter Repro-Fall aus dem Audit: 'Evenweave 28' (Combo-Index 4)
    darf NICHT den Stiche-pro-Strang-Wert von 22ct liefern."""
    from pysticky.core.constants import STITCHES_PER_SKEIN
    from pysticky.ui.dialogs.statistics_tabs.thread_tab import ThreadTab

    tab = ThreadTab()
    qtbot.addWidget(tab)
    tab.update_stats(pattern_with_stitches, {})

    tab._fabric_combo.setCurrentIndex(4)  # "Evenweave 28 (11 St/cm)"
    fabric_count, _waste, _price = tab.calculator_settings()
    assert fabric_count == 28
    assert STITCHES_PER_SKEIN[fabric_count] == 190
