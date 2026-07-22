# -*- coding: utf-8 -*-
"""Regressionstest (offener Punkt, Nutzerentscheidung 'Ja, angleichen'):
statistics_tabs/time_tab.py hatte KEINERLEI Diamond-Painting-Anpassung --
zeigte durchgehend Kreuzstich-Vokabular ("Stiche pro Stunde", "Bei
täglichem Sticken", Spalten-Header "Stiche") auch fuer DP-Muster, und
skalierte die Zeitschaetzung weiterhin nach Kreuzstich-Erfahrungsstufe
(2-8s/Stich) statt der bereits etablierten DP-Konvention aus
info_panel.py::_calculate_stitch_time() (3.0s/Diamant, feste Rate ohne
Skill-Abstufung -- Diamond Painting ist Hand-Tool-Tempo, keine
Erfahrungsstufen)."""

import pytest

from pysticky.core import Pattern, Thread

pytestmark = pytest.mark.usefixtures("qtbot")


def _pattern(mode: str, stitch_count: int = 300) -> Pattern:
    pattern = Pattern(name="Test", width=50, height=50, mode=mode)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.set_stitch(0, 0, 0)
    pattern.color_entries[0].stitch_count = stitch_count
    return pattern


def test_diamond_pattern_uses_fixed_rate_not_skill_level(qtbot):
    from pysticky.ui.dialogs.statistics_tabs.time_tab import TimeTab

    tab = TimeTab()
    qtbot.addWidget(tab)
    tab.update_stats(_pattern("diamond", 300), {})

    # 300 Drills * 3.0s = 900s = 15 min, unabhaengig vom Skill-Combo-Wert.
    assert "15 " in tab._card_total_time._value_label.text()


def test_diamond_pattern_disables_skill_combo(qtbot):
    from pysticky.ui.dialogs.statistics_tabs.time_tab import TimeTab

    tab = TimeTab()
    qtbot.addWidget(tab)
    assert tab._skill_combo.isEnabled()

    tab.update_stats(_pattern("diamond"), {})
    assert not tab._skill_combo.isEnabled(), (
        "Regression: Skill-Combo bleibt im DP-Modus anklickbar, obwohl sie keine Wirkung mehr hat"
    )

    tab.update_stats(_pattern("stitch"), {})
    assert tab._skill_combo.isEnabled()


def test_diamond_pattern_swaps_vocabulary(qtbot):
    from pysticky.ui.dialogs.statistics_tabs.time_tab import TimeTab

    tab = TimeTab()
    qtbot.addWidget(tab)
    tab.update_stats(_pattern("diamond"), {})

    assert tab._card_speed._title_label.text() == "Drills pro Stunde"
    assert tab._time_table.horizontalHeaderItem(2).text() == "Drills"

    tab.update_stats(_pattern("stitch"), {})
    assert tab._card_speed._title_label.text() == "Stiche pro Stunde"
    assert tab._time_table.horizontalHeaderItem(2).text() == "Stiche"


def test_stitch_pattern_still_uses_skill_level(qtbot):
    """Kreuzstich-Verhalten muss unveraendert bleiben (Skill-Skalierung)."""
    from pysticky.ui.dialogs.statistics_tabs.time_tab import TimeTab

    tab = TimeTab()
    qtbot.addWidget(tab)
    tab._skill_combo.setCurrentIndex(0)  # "Anfänger" = 8s/Stich
    tab.update_stats(_pattern("stitch", 300), {})

    # 300 Stiche * 8s = 2400s = 40 min
    assert "40 " in tab._card_total_time._value_label.text()
