# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 14): ColorsTab.combo_default_palette hatte eine
hart-codierte 13-Eintraege-Liste, die dem tatsaechlichen Paletten-Bestand
hinterherhinkte -- z.B. fehlten "DMC Diamant" und "DMC Light Effects",
obwohl beides normale Garn-Paletten sind (nicht is_diamond/is_beads),
waehrend files_tab.py's Cross-Reference-Liste und der Bildimport-Dialog
ihre Paletten-Listen schon immer dynamisch aus dem PaletteManager
aufbauen. Jetzt baut auch dieser Combo dynamisch auf, gefiltert auf
"regulaere" (nicht Bead-/Diamond-only) Paletten.
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def test_default_palette_combo_includes_previously_missing_regular_palettes(qtbot):
    from pysticky.ui.dialogs.settings_tabs.colors_tab import ColorsTab

    tab = ColorsTab()
    qtbot.addWidget(tab)

    combo = tab.combo_default_palette
    items = [combo.itemText(i) for i in range(combo.count())]

    assert "DMC Diamant" in items
    assert "DMC Light Effects" in items
    # Weiterhin die schon immer korrekten Kern-Paletten enthalten.
    assert "DMC" in items
    assert "Anchor" in items


def test_default_palette_combo_excludes_bead_and_diamond_only_palettes(qtbot):
    from pysticky.ui.dialogs.settings_tabs.colors_tab import ColorsTab

    tab = ColorsTab()
    qtbot.addWidget(tab)

    combo = tab.combo_default_palette
    items = [combo.itemText(i) for i in range(combo.count())]

    assert "Mill Hill Beads" not in items
    assert "DMC Diamond Painting" not in items
