# -*- coding: utf-8 -*-
"""
Regressionstests (Runde 12) für NewProjectDialog:

1. Der Stoffart-Combo verwendete currentIndex() als Position in
   COMMON_FABRIC_COUNTS -- die Combo-Liste hatte 6 Eintraege ohne "22",
   COMMON_FABRIC_COUNTS aber 7 Eintraege MIT "22" dazwischen. Ab "Evenweave
   28" (Index 4) griff dadurch der falsche Wert (22 statt 28), "Leinen 32"
   bekam 28 statt 32.
2. _dp_mode_selected blieb True haengen, wenn nach Auswahl eines
   Diamond-Painting-Presets zu einer normalen Kategorie/Template
   gewechselt wurde -- get_settings() meldete dann faelschlich
   dp_mode=True fuer ein gewoehnliches Kreuzstich-Template.
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def test_fabric_combo_returns_correct_count_for_all_entries(qtbot):
    from pysticky.ui.dialogs.new_project_dialog import NewProjectDialog

    dlg = NewProjectDialog()
    qtbot.addWidget(dlg)

    expected = [11, 14, 16, 18, 28, 32]
    for index, count in enumerate(expected):
        dlg._fabric_combo.setCurrentIndex(index)
        assert dlg._fabric_combo.currentData() == count
        assert dlg.get_settings()["fabric_count"] == count


def test_dp_preset_flag_resets_when_switching_to_normal_category(qtbot):
    from pysticky.ui.dialogs.new_project_dialog import NewProjectDialog

    dlg = NewProjectDialog()
    qtbot.addWidget(dlg)

    # Ein echtes DP-Preset auswaehlen (Index 0 ist "Keine Auswahl", also
    # das erste DP-Preset mit gesetzten w/h suchen).
    dp_index = next(
        i for i, (label, w, h, is_dp) in enumerate(dlg._DP_PRESETS) if is_dp and w is not None
    )
    dlg._dp_preset_combo.setCurrentIndex(dp_index)
    assert dlg.get_settings()["dp_mode"] is True

    # Zu "Benutzerdefiniert" (Kategorie-Button-ID 0) wechseln.
    dlg._on_category_changed(0)
    assert dlg.get_settings()["dp_mode"] is False
