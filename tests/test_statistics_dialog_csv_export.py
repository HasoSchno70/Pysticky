# -*- coding: utf-8 -*-
"""
Regressionstest: PatternStatisticsDialog._on_export_csv() baute CSV-Zeilen
per roher f-String-Verkettung ohne Quoting/Escaping -- ein Komma oder
Anfuehrungszeichen im Garn-/Herstellernamen verschob stillschweigend alle
folgenden Spalten. Jetzt ueber csv.writer, das automatisch quotet.
"""

import csv

from pysticky.core import Pattern, Thread
from pysticky.ui.dialogs.statistics_dialog import PatternStatisticsDialog


def test_csv_export_quotes_comma_in_thread_name(qtbot, tmp_path, monkeypatch):
    pattern = Pattern(width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(
        Thread.from_hex(
            "Rot, dunkel",  # Komma im Namen -- der eigentliche Regressionsfall
            "#FF0000",
            manufacturer="DMC",
            catalog_number="321",
        )
    )
    pattern.set_stitch(0, 0, 0)

    dialog = PatternStatisticsDialog(pattern)
    qtbot.addWidget(dialog)

    out_path = tmp_path / "stats.csv"

    import pysticky.ui.dialogs.statistics_dialog as module

    monkeypatch.setattr(
        module.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out_path), ""))
    )
    monkeypatch.setattr(module.QMessageBox, "information", staticmethod(lambda *a, **k: None))

    dialog._on_export_csv()

    assert out_path.exists()
    with open(out_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    header, data_row = rows[0], rows[1]
    assert header[1] == "Name"
    # csv.reader parst die korrekt gequotete Zelle als EIN Feld zurueck --
    # bei der alten rohen Verkettung waere "Rot" und " dunkel" in zwei
    # Spalten auseinandergerissen worden.
    assert data_row[1] == "Rot, dunkel"
    assert data_row[2] == "DMC"
    assert data_row[3] == "321"
