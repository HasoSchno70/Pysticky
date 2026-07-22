# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 20): HoopPlannerDialog.COMMON_HOOPS war fest auf
Aida 14 ct kalibriert (~5.5 Stiche/cm) und wurde nie mit pattern.fabric_count
skaliert -- fuer jede andere Stoffzaehlung (11/16/18/22/28/32 ct) ergaben die
Preset-Buttons (z.B. "8 Zoll (20 cm)") einen Rahmen, der real eine andere
physische Groesse als die Beschriftung hatte.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from pysticky.core import Pattern

pytestmark = pytest.mark.usefixtures("qtbot")


def _preset_button(dialog, hoop_w_expected_14ct: int) -> QPushButton:
    """Findet den Preset-Button, dessen 14ct-Basiswert `hoop_w_expected_14ct`
    entspricht -- Buttons werden zur Laufzeit erzeugt, keine Attribute."""
    for btn in dialog.findChildren(QPushButton):
        w = btn.property("hoop_w")
        if w is not None and round(w / dialog._hoop_scale) == hoop_w_expected_14ct:
            return btn
    raise AssertionError(f"Kein Preset-Button mit 14ct-Basiswert {hoop_w_expected_14ct} gefunden")


def test_hoop_scale_is_one_at_baseline_fabric_count(qtbot):
    from pysticky.ui.dialogs.hoop_planner_dialog import HoopPlannerDialog

    pattern = Pattern(width=200, height=200, fabric_count=14)
    dialog = HoopPlannerDialog(pattern)
    qtbot.addWidget(dialog)

    assert dialog._hoop_scale == pytest.approx(1.0)


def test_hoop_scale_doubles_at_double_fabric_count(qtbot):
    from pysticky.ui.dialogs.hoop_planner_dialog import HoopPlannerDialog

    pattern = Pattern(width=200, height=200, fabric_count=28)
    dialog = HoopPlannerDialog(pattern)
    qtbot.addWidget(dialog)

    assert dialog._hoop_scale == pytest.approx(2.0)


def test_preset_button_values_scale_with_fabric_count(qtbot):
    from pysticky.ui.dialogs.hoop_planner_dialog import HoopPlannerDialog

    pattern_14ct = Pattern(width=200, height=200, fabric_count=14)
    dialog_14 = HoopPlannerDialog(pattern_14ct)
    qtbot.addWidget(dialog_14)
    btn_14 = _preset_button(dialog_14, 110)  # "8 Zoll (20 cm)"
    assert btn_14.property("hoop_w") == 110

    pattern_18ct = Pattern(width=200, height=200, fabric_count=18)
    dialog_18 = HoopPlannerDialog(pattern_18ct)
    qtbot.addWidget(dialog_18)
    btn_18 = _preset_button(dialog_18, 110)
    expected = round(110 * 18 / 14)
    assert btn_18.property("hoop_w") == expected
    assert btn_18.property("hoop_w") != 110


def test_clicking_preset_applies_scaled_value(qtbot):
    from pysticky.ui.dialogs.hoop_planner_dialog import HoopPlannerDialog

    pattern = Pattern(width=200, height=200, fabric_count=18)
    dialog = HoopPlannerDialog(pattern)
    qtbot.addWidget(dialog)

    btn = _preset_button(dialog, 110)  # "8 Zoll (20 cm)"
    qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)

    assert dialog.spin_w.value() == round(110 * 18 / 14)
    assert dialog.spin_h.value() == round(110 * 18 / 14)


def test_default_hoop_size_scales_with_fabric_count(qtbot):
    from pysticky.ui.dialogs.hoop_planner_dialog import HoopPlannerDialog

    pattern_14ct = Pattern(width=200, height=200, fabric_count=14)
    dialog_14 = HoopPlannerDialog(pattern_14ct)
    qtbot.addWidget(dialog_14)
    assert dialog_14.spin_w.value() == 82

    pattern_22ct = Pattern(width=200, height=200, fabric_count=22)
    dialog_22 = HoopPlannerDialog(pattern_22ct)
    qtbot.addWidget(dialog_22)
    assert dialog_22.spin_w.value() == round(82 * 22 / 14)
