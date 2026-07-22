# -*- coding: utf-8 -*-
"""Regressionstest (offener Punkt, Nutzerentscheidung 'Garnverbrauch-
Konvention'): PatternStatisticsDialog._calculate_statistics() reicht den
Verschnitt-Zuschlag (waste_percent) des Garnverbrauch-Tabs jetzt an den
Einkaufsliste-Tab durch, statt dass Letzterer mit einer eigenen, fest
codierten Formel rechnet."""

import math

import pytest

from pysticky.core import Pattern, Thread
from pysticky.core.inventory import Inventory, compute_shopping_list
from pysticky.ui.dialogs.statistics_dialog import PatternStatisticsDialog
from pysticky.ui.dialogs.statistics_tabs._constants import STITCHES_PER_SKEIN
from pysticky.ui.dialogs.statistics_tabs.shopping_tab import ShoppingTab

pytestmark = pytest.mark.usefixtures("qtbot")


def _pattern_with_stitch_count(count: int) -> Pattern:
    pattern = Pattern(name="Test", width=100, height=100, fabric_count=14)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.set_stitch(0, 0, 0)
    pattern.color_entries[0].stitch_count = count
    return pattern


def test_statistics_dialog_passes_thread_tab_waste_percent_to_shopping_tab(qtbot, monkeypatch):
    """Verdrahtungstest: _calculate_statistics() muss den Verschnitt-
    Zuschlag aus ThreadTab.calculator_settings() an
    ShoppingTab.update_stats() weiterreichen (Default 20%)."""
    pattern = _pattern_with_stitch_count(1234)

    captured = {}
    orig_update_stats = ShoppingTab.update_stats

    def spy(self, pattern_arg, stats, waste_percent=20.0):
        captured["waste_percent"] = waste_percent
        return orig_update_stats(self, pattern_arg, stats, waste_percent)

    monkeypatch.setattr(ShoppingTab, "update_stats", spy)

    dialog = PatternStatisticsDialog(pattern)
    qtbot.addWidget(dialog)

    assert captured["waste_percent"] == dialog._thread_tab.calculator_settings()[1]
    assert captured["waste_percent"] == 20.0


def test_shopping_tab_table_reflects_waste_percent_formula(qtbot, tmp_path):
    """Direkter Unit-Test von ShoppingTab.update_stats() mit einem vom
    Default abweichenden Verschnitt-Zuschlag."""
    pattern = _pattern_with_stitch_count(1234)

    tab = ShoppingTab()
    qtbot.addWidget(tab)
    tab.update_stats(pattern, {}, waste_percent=35.0)

    exact_skeins = 1234 / STITCHES_PER_SKEIN.get(14, 500)
    expected_needed = math.ceil(exact_skeins * 1.35)

    table = tab._layout.itemAt(1).widget()
    shown = int(table.item(0, 3).text())
    assert shown == expected_needed

    # Gegenprobe direkt gegen die core-Funktion.
    expected_items = compute_shopping_list(
        pattern, Inventory(tmp_path / "inv.json"), STITCHES_PER_SKEIN, waste_percent=35.0
    )
    assert expected_items[0]["needed_skeins"] == expected_needed
