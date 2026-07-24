# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 60): der Rahmenaufteilung-Dialog hatte keine obere
Grenze fuer die Sektor-Anzahl. Ein winziger Rahmen (Minimum 10x10 ueber die
Spinboxen) kombiniert mit einer fast rahmengrossen Ueberlappung (bis 9, per
Dialog-eigenem Auto-Clamp erlaubt -- siehe overlap-Clamp in _recalculate())
ergibt eine Schrittweite von nur 1 Stich. Bei einem groesseren, aber
vollkommen normalen Muster (z.B. 500x500) fuehrte das zu >240000 Sektoren:
plan_hoops() (inkl. Stich-Zaehlung pro Sektor) UND die anschliessende
Tabellen-/Vorschau-Befuellung laufen synchron auf dem GUI-Thread, was den
Dialog fuer viele Sekunden bis Minuten einfrieren liess -- ganz ohne
Fehlermeldung oder jegliches Feedback fuer den Nutzer.

Reine Spinbox-Bedienung (keine Tastatur-Tricks noetig) reicht, um das
auszuloesen: Rahmen-Breite/-Hoehe auf Minimum (10) stellen, dann
Ueberlappung so hoch wie moeglich (wird automatisch auf max(hw,hh)-1 = 9
geklemmt).

Fix: `core/hoop_planner.py::estimate_sector_grid()` berechnet nur
(rows, cols) OHNE die teure Sektor-Liste zu bauen; der Dialog ruft das vor
jeder vollen Neuberechnung auf und bricht mit einer Warnung ab, statt
einzufrieren, wenn `rows * cols` die (dialog-lokale)
`HoopPlannerDialog.MAX_REASONABLE_SECTORS`-Grenze ueberschreitet.
"""

import time

import pytest

from pysticky.core import Pattern
from pysticky.core.hoop_planner import estimate_sector_grid, plan_hoops

pytestmark = pytest.mark.usefixtures("qtbot")


def test_estimate_sector_grid_matches_plan_hoops_rows_cols(pattern_with_stitches):
    """estimate_sector_grid() ist die single source of truth, die
    plan_hoops() jetzt intern verwendet -- beide muessen fuer dieselben
    Eingaben dasselbe (rows, cols) liefern."""
    p = pattern_with_stitches  # 20x20
    rows, cols = estimate_sector_grid(p.width, p.height, 12, 12, overlap=2)
    plan = plan_hoops(p, hoop_width=12, hoop_height=12, overlap=2)
    assert (rows, cols) == (plan.rows, plan.cols)


def test_estimate_sector_grid_raises_same_errors_as_plan_hoops():
    with pytest.raises(ValueError):
        estimate_sector_grid(100, 100, hoop_width=0, hoop_height=10)
    with pytest.raises(ValueError):
        estimate_sector_grid(100, 100, hoop_width=10, hoop_height=10, overlap=10)


def test_pathological_overlap_estimate_is_huge_but_cheap():
    """Die reine Schaetzung (ohne Sektor-Liste/Stich-Zaehlung) muss auch
    fuer die pathologische Kombination (Rahmen 10x10, Overlap 9, grosses
    Muster) sofort zurueckkommen -- das ist der ganze Sinn von
    estimate_sector_grid()."""
    t0 = time.perf_counter()
    rows, cols = estimate_sector_grid(500, 500, hoop_width=10, hoop_height=10, overlap=9)
    elapsed = time.perf_counter() - t0
    assert rows * cols > 200_000  # bestaetigt: das waere tatsaechlich pathologisch
    assert elapsed < 0.5


def test_dialog_blocks_pathological_sector_count_instead_of_freezing(qtbot):
    """Kern-Regressionstest: kleiner Rahmen + hohe Ueberlappung auf einem
    normalen 500x500-Muster darf den Dialog NICHT fuer Sekunden einfrieren
    -- _recalculate() muss den Guard treffen und frueh abbrechen."""
    from pysticky.ui.dialogs.hoop_planner_dialog import HoopPlannerDialog

    pattern = Pattern(width=500, height=500, fabric_count=14)
    dialog = HoopPlannerDialog(pattern)
    qtbot.addWidget(dialog)

    dialog.spin_w.setValue(10)
    dialog.spin_h.setValue(10)

    t0 = time.perf_counter()
    dialog.spin_overlap.setValue(50)  # wird intern auf 9 geklemmt (Overlap-Clamp)
    elapsed = time.perf_counter() - t0

    assert dialog.spin_overlap.value() == 9  # bestaetigt bestehenden Overlap-Clamp
    assert elapsed < 1.0, f"_recalculate() dauerte {elapsed:.2f}s -- Guard hat nicht gegriffen"
    assert "⚠" in dialog.summary_label.text()
    assert dialog.table.rowCount() == 0


def test_dialog_still_works_for_100_sectors(qtbot):
    """Die im Audit-Auftrag explizit genannte 10x10=100-Sektoren-Situation
    (grosse, aber legitime Aufteilung) darf vom neuen Guard NICHT
    blockiert werden."""
    from pysticky.ui.dialogs.hoop_planner_dialog import HoopPlannerDialog

    pattern = Pattern(width=1000, height=1000, fabric_count=14)
    dialog = HoopPlannerDialog(pattern)
    qtbot.addWidget(dialog)

    dialog.spin_w.setValue(100)
    dialog.spin_h.setValue(100)
    dialog.spin_overlap.setValue(0)

    assert dialog.table.rowCount() == 100
    assert "⚠" not in dialog.summary_label.text()


def test_dialog_recovers_after_shrinking_back_to_reasonable_hoop_size(qtbot):
    """Nachdem der Guard gegriffen hat, muss eine anschliessende
    vernuenftige Rahmen-Groesse wieder eine normale Vorschau/Tabelle
    liefern (keine dauerhaft haengenbleibende Fehler-Anzeige)."""
    from pysticky.ui.dialogs.hoop_planner_dialog import HoopPlannerDialog

    pattern = Pattern(width=500, height=500, fabric_count=14)
    dialog = HoopPlannerDialog(pattern)
    qtbot.addWidget(dialog)

    dialog.spin_w.setValue(10)
    dialog.spin_h.setValue(10)
    dialog.spin_overlap.setValue(50)  # klemmt auf 9 -> Guard greift
    assert dialog.table.rowCount() == 0

    dialog.spin_overlap.setValue(2)
    dialog.spin_w.setValue(150)
    dialog.spin_h.setValue(150)

    assert dialog.table.rowCount() > 0
    assert "⚠" not in dialog.summary_label.text()
