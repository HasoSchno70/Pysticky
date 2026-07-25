# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 81): NewProjectDialog ignorierte die in einem
eigenen (benutzerdefinierten) Template gespeicherte Stoffzaehlung.

SaveTemplateDialog speichert die zum Speicherzeitpunkt aktive Stoffzaehlung
in UserTemplate.fabric_count (user_template_dialog.py:44/314). Waehlt man
danach in "Neues Projekt" -> "Eigene Templates" genau dieses Template aus,
liest _on_user_templates_selected() diesen Wert zwar in das Karten-Dict
ein (new_project_dialog.py:746/767), aber _on_template_selected() setzt
davon nur Breite/Hoehe -- die Stoffart-Combo bleibt unangetastet auf ihrem
bisherigen Wert (Standard: Aida 14). Sowohl die im Dialog angezeigte
"Fertige Groesse" (cm) als auch das an file_handlers.py::_on_new()
zurueckgegebene fabric_count passen dadurch nicht mehr zu der Stoffzaehlung,
mit der das Template urspruenglich gespeichert wurde.
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def test_selecting_user_template_applies_its_stored_fabric_count(qtbot, monkeypatch):
    from pysticky.ui.dialogs import new_project_dialog
    from pysticky.ui.dialogs.user_template_dialog import UserTemplate

    saved_template = UserTemplate(
        name="Mein Kissen",
        width=90,
        height=90,
        fabric_count=18,  # bewusst != Dialog-Standard (Aida 14)
        description="",
        category="Eigene",
    )
    monkeypatch.setattr(new_project_dialog, "load_user_templates", lambda: [saved_template])

    dlg = new_project_dialog.NewProjectDialog()
    qtbot.addWidget(dlg)

    # Fabric-Combo steht auf dem Dialog-Standard (Aida 14, Index 1).
    assert dlg._fabric_combo.currentData() == 14

    # "Eigene Templates" (Kategorie-Button-ID 1) waehlen -> laedt und
    # selektiert automatisch das erste (einzige) eigene Template.
    dlg._on_category_changed(1)

    settings = dlg.get_settings()
    assert settings["width"] == 90
    assert settings["height"] == 90
    # Die im Template gespeicherte Stoffzaehlung (18) muss uebernommen
    # werden -- vorher blieb faelschlich der Dialog-Standard (14) haengen.
    assert settings["fabric_count"] == 18
    assert dlg._fabric_combo.currentData() == 18
