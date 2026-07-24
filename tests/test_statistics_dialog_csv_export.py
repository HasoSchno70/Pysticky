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


def test_csv_export_omits_meaningless_skein_columns_in_diamond_mode(qtbot, tmp_path, monkeypatch):
    """Regression (Runde 17): der CSV-Export las Strang-/Kosten-Werte immer
    vom (im DP-Modus versteckten) Garnverbrauch-Tab, das nie mit
    pattern.fabric_count synchronisiert wird -- Diamond-Painting-Exporte
    enthielten dadurch bedeutungslose "Stränge"/"Kosten"-Spalten, obwohl DP
    keine Skein-Einheit kennt (siehe dp-stitch-parity-2026-07-18.md)."""
    pattern = Pattern(width=5, height=5)
    pattern.mode = "diamond"
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.set_stitch(0, 0, 0)

    dialog = PatternStatisticsDialog(pattern)
    qtbot.addWidget(dialog)

    out_path = tmp_path / "stats_dp.csv"

    import pysticky.ui.dialogs.statistics_dialog as module

    monkeypatch.setattr(
        module.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out_path), ""))
    )
    monkeypatch.setattr(module.QMessageBox, "information", staticmethod(lambda *a, **k: None))

    dialog._on_export_csv()

    with open(out_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    header = rows[0]
    assert "Stränge" not in header
    assert "Kosten" not in header
    assert "Nicht sticken" in header  # andere Spalten bleiben unveraendert


def test_csv_export_has_utf8_bom_for_excel(qtbot, tmp_path, monkeypatch):
    """Regression (Runde 62): der Statistik-CSV-Export schrieb reines
    "utf-8" ohne BOM. Per Doppelklick in Excel geoeffnet (der naheliegendste
    Weg, eine Statistik-/Garnliste-CSV anzusehen), interpretiert Excel eine
    BOM-lose Datei ueber die System-Codepage (auf deutschem Windows meist
    cp1252) statt UTF-8 -- ein Farbname mit Umlaut wie "Türkisblau" wurde
    dadurch als Mojibake dargestellt, obwohl die Datei selbst korrekt
    UTF-8-kodiert war. "utf-8-sig" schreibt die fuehrende BOM, die Excel als
    UTF-8-Signal erkennt; csv.reader liest die Datei unveraendert korrekt."""
    pattern = Pattern(width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(
        Thread.from_hex("Türkisblau", "#00CED1", manufacturer="DMC", catalog_number="807")
    )
    pattern.set_stitch(0, 0, 0)

    dialog = PatternStatisticsDialog(pattern)
    qtbot.addWidget(dialog)

    out_path = tmp_path / "stats_umlaut.csv"

    import pysticky.ui.dialogs.statistics_dialog as module

    monkeypatch.setattr(
        module.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out_path), ""))
    )
    monkeypatch.setattr(module.QMessageBox, "information", staticmethod(lambda *a, **k: None))

    dialog._on_export_csv()

    raw = out_path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "Statistik-CSV sollte ein UTF-8-BOM tragen"

    # Mit utf-8-sig geoeffnet (das BOM wird automatisch entfernt) bleibt der
    # Inhalt inklusive Umlaut korrekt und CSV-konform lesbar.
    with open(out_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    assert rows[1][1] == "Türkisblau"
