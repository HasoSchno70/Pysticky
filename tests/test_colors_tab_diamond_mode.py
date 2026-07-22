# -*- coding: utf-8 -*-
"""Regressionstest (offener Punkt, Nachtrag zur TimeTab-DP-Angleichung
2026-07-22): colors_tab.py (statistics_tabs) hatte dieselbe DP-Vokabular-
Luecke wie TimeTab -- Spalten-Header "Stiche" und der "(nicht sticken)"-
Skip-Marker blieben Kreuzstich-Vokabular auch fuer Diamond-Painting-Muster,
obwohl pdf_export_sections.py bereits eine etablierte DP-Variante
("nicht kleben") fuer denselben Marker kennt."""

import pytest

from pysticky.core import Pattern, Thread

pytestmark = pytest.mark.usefixtures("qtbot")


def _pattern(mode: str) -> Pattern:
    pattern = Pattern(name="Test", width=10, height=10, mode=mode)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.color_entries[0].stitch_count = 50
    pattern.add_color(Thread.from_hex("Blau", "#0000FF"))
    pattern.color_entries[1].stitch_count = 10
    pattern.color_entries[1].skip_stitching = True
    return pattern


def test_diamond_pattern_uses_drill_column_header(qtbot):
    from pysticky.ui.dialogs.statistics_tabs.colors_tab import ColorsTab

    tab = ColorsTab()
    qtbot.addWidget(tab)
    tab.update_stats(_pattern("diamond"), {})

    assert tab._colors_table.horizontalHeaderItem(5).text() == "Drills"


def test_diamond_pattern_uses_nicht_kleben_skip_label(qtbot):
    from pysticky.ui.dialogs.statistics_tabs.colors_tab import ColorsTab

    tab = ColorsTab()
    qtbot.addWidget(tab)
    tab.update_stats(_pattern("diamond"), {})

    skip_name = tab._colors_table.item(1, 2).text()
    assert "nicht kleben" in skip_name
    assert "nicht sticken" not in skip_name


def test_stitch_pattern_still_uses_stiche_vocabulary(qtbot):
    """Kreuzstich-Verhalten muss unveraendert bleiben (Regressionsschutz)."""
    from pysticky.ui.dialogs.statistics_tabs.colors_tab import ColorsTab

    tab = ColorsTab()
    qtbot.addWidget(tab)
    tab.update_stats(_pattern("stitch"), {})

    assert tab._colors_table.horizontalHeaderItem(5).text() == "Stiche"
    skip_name = tab._colors_table.item(1, 2).text()
    assert "nicht sticken" in skip_name


def test_switching_from_diamond_back_to_stitch_restores_vocabulary(qtbot):
    from pysticky.ui.dialogs.statistics_tabs.colors_tab import ColorsTab

    tab = ColorsTab()
    qtbot.addWidget(tab)
    tab.update_stats(_pattern("diamond"), {})
    assert tab._colors_table.horizontalHeaderItem(5).text() == "Drills"

    tab.update_stats(_pattern("stitch"), {})
    assert tab._colors_table.horizontalHeaderItem(5).text() == "Stiche"
