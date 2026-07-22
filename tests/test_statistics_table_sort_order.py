# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 24): mehrere Statistik-Tabs (colors_tab.py,
progress_tab.py, thread_tab.py) setzten fuer Prozent-/Kosten-Spalten
Qt.ItemDataRole.UserRole auf den Zahlenwert, in der Annahme,
setSortingEnabled(True) wuerde danach numerisch sortieren -- Qt's
QTableWidgetItem.operator<() vergleicht aber nur Qt.ItemDataRole.
DisplayRole (den angezeigten Text), UserRole wird fuer die Klick-auf-
Spaltenkopf-Sortierung schlicht ignoriert. "45.3%" sortierte dadurch
lexikographisch VOR "9.5%".
"""

from pysticky.ui.dialogs.statistics_tabs._table_helpers import (
    sortable_decimal_item,
    sortable_percent_item,
)


def test_percent_items_sort_numerically_not_lexicographically():
    items = [sortable_percent_item(v) for v in [45.3, 9.5, 100.0, 2.1]]
    items_sorted = sorted(items)
    values_sorted = [item.text() for item in items_sorted]

    assert values_sorted == ["2.1%", "9.5%", "45.3%", "100.0%"]


def test_decimal_items_sort_numerically_not_lexicographically():
    items = [sortable_decimal_item(v, " €") for v in [12.00, 4.80, 100.50, 0.99]]
    items_sorted = sorted(items)
    values_sorted = [item.text() for item in items_sorted]

    assert values_sorted == ["0.99 €", "4.80 €", "12.00 €", "100.50 €"]


def test_percent_item_display_text_is_formatted():
    item = sortable_percent_item(45.3)
    assert item.text() == "45.3%"


def test_decimal_item_display_text_is_formatted():
    item = sortable_decimal_item(12.0, " €")
    assert item.text() == "12.00 €"
