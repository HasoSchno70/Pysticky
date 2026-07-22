# -*- coding: utf-8 -*-
"""Regressionstest (Runde 27): ToolsTab (Einstellungen -> Werkzeuge) rief
.lower() auf dem uebersetzten String t("Stiche") auf, um die Einheit fuer
"Max. Brush-Groesse bei 100% Stift-Druck" als Spinbox-Suffix anzuzeigen --
deutsche Substantive werden aber immer grossgeschrieben, das ergab
"5 stiche" statt "5 Stiche". Jeder andere Spinbox-Suffix in dieser Datei
(t("Minuten") etc.) wird un-lowercased benutzt."""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def test_tablet_max_brush_suffix_is_not_lowercased(qtbot):
    from pysticky.ui.dialogs.settings_tabs.tools_tab import ToolsTab

    tab = ToolsTab()
    qtbot.addWidget(tab)

    assert tab.spin_tablet_max_brush.suffix() == " Stiche"
