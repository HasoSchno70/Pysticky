# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 17): PatternPropertiesDialog zeigte die Stoff-
Information hart-codiert als "{fabric_count} ct Aida" an -- im Diamond-
Painting-Modus ergibt eine Aida-Stoffzaehlung keinen Sinn (DP nutzt eine
Drill-Pitch-Bezeichnung wie "2.5 mm Square"). io/export_common.py::
fabric_label_for() loest genau das schon fuer PDF-/HTML-Export und
info_panel korrekt -- dieser Dialog wurde nie darauf umgestellt.
"""

import pytest

from pysticky.core import Pattern

pytestmark = pytest.mark.usefixtures("qtbot")


def test_fabric_label_shows_drill_pitch_in_diamond_mode(qtbot):
    from pysticky.ui.dialogs.pattern_properties_dialog import PatternPropertiesDialog

    pattern = Pattern(name="DP-Test", width=20, height=20, fabric_count=10)
    pattern.mode = "diamond"

    dlg = PatternPropertiesDialog(pattern)
    qtbot.addWidget(dlg)

    assert "Aida" not in dlg._fabric_label.text()
    assert "2.5 mm Square" in dlg._fabric_label.text()


def test_fabric_label_shows_aida_ct_in_stitch_mode(qtbot):
    from pysticky.ui.dialogs.pattern_properties_dialog import PatternPropertiesDialog

    pattern = Pattern(name="Stitch-Test", width=20, height=20, fabric_count=16)
    assert pattern.mode == "stitch"

    dlg = PatternPropertiesDialog(pattern)
    qtbot.addWidget(dlg)

    assert "Aida" in dlg._fabric_label.text()
    assert "16" in dlg._fabric_label.text()
