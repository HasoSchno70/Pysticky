# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 81): NewProjectDialog liess den Namen und die
Dimensionen des zuvor ausgewaehlten Templates hängen, wenn danach ein
Diamond-Painting-Preset gewaehlt wurde.

Szenario: Nutzer waehlt zuerst ein normales Kreuzstich-Template (z.B.
"Untersetzer Rund", 40x40 Stiche) und wechselt danach -- ohne die Kategorie
zu verlassen -- im DP-Preset-Dropdown auf ein Diamond-Painting-Preset (z.B.
"DP A4 quadratisch", 60x60). _on_dp_preset_changed() setzt zwar Breite/Hoehe
und dp_mode korrekt, loescht aber NICHT self._selected_template. Dadurch
meldet get_settings() weiterhin template_name="Untersetzer Rund", obwohl
Breite/Hoehe/dp_mode laengst auf das DP-Preset zeigen -- file_handlers.py
uebernimmt diesen Namen 1:1 als Pattern.name, das entstehende Diamond-
Painting-Muster heisst also faelschlich wie das urspruengliche
Kreuzstich-Template.
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def test_dp_preset_after_template_selection_clears_stale_template_name(qtbot):
    from pysticky.ui.dialogs.new_project_dialog import NewProjectDialog

    dlg = NewProjectDialog()
    qtbot.addWidget(dlg)

    # Kategorie "Lesezeichen" waehlen (ID 2, da 0=Benutzerdefiniert,
    # 1=Eigene Templates, Kategorien ab 2 in TEMPLATES-Reihenfolge).
    dlg._on_category_changed(2)
    assert dlg._selected_template is not None
    assert dlg._selected_template["name"] == "Lesezeichen Klein"
    assert dlg.get_settings()["width"] == 25
    assert dlg.get_settings()["height"] == 80

    # Jetzt ein echtes DP-Preset waehlen, ohne die Kategorie zu wechseln.
    dp_index = next(
        i for i, (label, w, h, is_dp) in enumerate(dlg._DP_PRESETS) if is_dp and w is not None
    )
    dlg._dp_preset_combo.setCurrentIndex(dp_index)

    settings = dlg.get_settings()
    assert settings["dp_mode"] is True
    assert settings["width"] == dlg._DP_PRESETS[dp_index][1]
    assert settings["height"] == dlg._DP_PRESETS[dp_index][2]

    # Kein Template mehr aktiv -- vorher blieb hier faelschlich
    # "Lesezeichen Klein" haengen, obwohl laengst ein DP-Preset gewaehlt ist.
    assert settings["template_name"] is None
    assert dlg._selected_template is None
    assert all(not card.selected for card in dlg._template_cards)
