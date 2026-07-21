# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 12): PatternPreviewDialog._update_info() las den
Stoffzaehlungswert per Positions-Index aus COMMON_FABRIC_COUNTS -- die
sichtbare Combo-Liste hatte 6 Eintraege ohne "22", COMMON_FABRIC_COUNTS
aber 7 Eintraege MIT "22" dazwischen. Ab "Evenweave 28" (Index 4) griff
dadurch der falsche Wert (22 statt 28), "Leinen 32" bekam 28 statt 32 --
verfaelschte die berechnete physische Muster-Groesse in cm.
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def test_fabric_combo_returns_correct_count_for_all_entries(qtbot, pattern_with_stitches):
    from pysticky.ui.dialogs.pattern_preview_dialog import PatternPreviewDialog

    dialog = PatternPreviewDialog(pattern_with_stitches)
    qtbot.addWidget(dialog)

    expected = [11, 14, 16, 18, 28, 32]
    for index, count in enumerate(expected):
        dialog._fabric_combo.setCurrentIndex(index)
        assert dialog._fabric_combo.currentData() == count
