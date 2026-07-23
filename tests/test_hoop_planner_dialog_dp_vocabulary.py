# -*- coding: utf-8 -*-
"""
Regressionstest (Nachfolge-Runde zu Runde 25): HoopPlannerDialog verwendete
durchgehend "Stiche"-Vokabular unabhaengig vom Pattern-Modus. Fuer
Diamond-Painting-Muster (pattern.mode == "diamond") soll stattdessen
"Drills" angezeigt werden -- in Spinbox-Suffixen, Tabellen-Header,
Intro-Text, Zusammenfassung und Ueberlappungs-Tooltip.

Die "Stickrahmen"-Terminologie selbst (Dialogtitel, "Rahmen-Breite" etc.)
bleibt bewusst modus-unabhaengig und wird hier NICHT geprueft.
"""

import pytest

from pysticky.core import Pattern

pytestmark = pytest.mark.usefixtures("qtbot")


def test_stitch_mode_uses_stiche_vocabulary(qtbot):
    from pysticky.ui.dialogs.hoop_planner_dialog import HoopPlannerDialog

    pattern = Pattern(width=200, height=200, fabric_count=14, mode="stitch")
    dialog = HoopPlannerDialog(pattern)
    qtbot.addWidget(dialog)

    assert dialog._diamond is False
    assert dialog.spin_w.suffix() == " Stiche"
    assert dialog.spin_h.suffix() == " Stiche"
    assert dialog.spin_overlap.suffix() == " Stiche"
    assert dialog.table.horizontalHeaderItem(4).text() == "Stiche"
    assert "Stiche" in dialog.summary_label.text() or "Rahmen" in dialog.summary_label.text()
    assert "Anzahl Stiche" in dialog.spin_overlap.toolTip()


def test_diamond_mode_uses_drills_vocabulary(qtbot):
    from pysticky.ui.dialogs.hoop_planner_dialog import HoopPlannerDialog

    pattern = Pattern(width=200, height=200, fabric_count=14, mode="diamond")
    dialog = HoopPlannerDialog(pattern)
    qtbot.addWidget(dialog)

    assert dialog._diamond is True
    assert dialog.spin_w.suffix() == " Drills"
    assert dialog.spin_h.suffix() == " Drills"
    assert dialog.spin_overlap.suffix() == " Drills"
    assert dialog.table.horizontalHeaderItem(4).text() == "Drills"
    assert "Anzahl Drills" in dialog.spin_overlap.toolTip()
    assert "Stiche" not in dialog.spin_overlap.toolTip()


def test_diamond_mode_intro_text_says_drills(qtbot):
    """Intro-Label ('Pattern-Groesse: N x N Stiche/Drills') soll im
    Diamond-Modus 'Drills' statt 'Stiche' sagen."""
    from pysticky.ui.dialogs.hoop_planner_dialog import HoopPlannerDialog

    pattern = Pattern(width=200, height=200, fabric_count=14, mode="diamond")
    dialog = HoopPlannerDialog(pattern)
    qtbot.addWidget(dialog)

    intro_labels = [
        w for w in dialog.findChildren(type(dialog.summary_label)) if "Pattern-Größe" in w.text()
    ]
    assert intro_labels, "Intro-Label nicht gefunden"
    assert "Drills" in intro_labels[0].text()
    assert "Stiche" not in intro_labels[0].text()


def test_diamond_mode_summary_label_says_drills_when_multi_sector(qtbot):
    """Bei mehreren Sektoren nennt die Zusammenfassung die Ueberlappung in
    der modusabhaengigen Einheit."""
    from pysticky.ui.dialogs.hoop_planner_dialog import HoopPlannerDialog

    pattern = Pattern(width=300, height=300, fabric_count=14, mode="diamond")
    dialog = HoopPlannerDialog(pattern)
    qtbot.addWidget(dialog)

    # Kleinen Rahmen erzwingen, damit mehrere Sektoren entstehen.
    dialog.spin_w.setValue(50)
    dialog.spin_h.setValue(50)

    text = dialog.summary_label.text()
    assert "Überlappung" in text
    assert "Drills" in text
    assert "Stiche" not in text


def test_stitch_word_matches_dialog_word_for_word_spinbox(qtbot):
    """dialog._stitch_word/_stitch_word_suffix bleiben intern konsistent
    mit den tatsaechlich angezeigten Widget-Texten."""
    from pysticky.ui.dialogs.hoop_planner_dialog import HoopPlannerDialog

    for mode, expected in (("stitch", "Stiche"), ("diamond", "Drills")):
        pattern = Pattern(width=150, height=150, fabric_count=14, mode=mode)
        dialog = HoopPlannerDialog(pattern)
        qtbot.addWidget(dialog)

        assert dialog._stitch_word == expected
        assert dialog._stitch_word_suffix == f" {expected}"
