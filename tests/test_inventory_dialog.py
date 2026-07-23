# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 22/25-Nachfolge): InventoryDialog zeigte in Tab 1
("Im Muster") und Tab 3 ("Mehrere Projekte") immer "Stränge"-Vokabular an,
auch fuer Diamond-Painting-Muster, wo eine Farbe stueckweise als Drill statt
als Garn-Strang verbraucht wird. Jetzt richtet sich Spaltenkopf/Spinbox-
Suffix nach `pattern.mode`.

WICHTIG: InventoryDialog() erzeugt intern `Inventory()`/`ProjectList()` ohne
expliziten Pfad -- das laedt/speichert normalerweise die ECHTEN globalen
App-Daten-Dateien des Users. Jeder Test hier patcht `get_inventory_path()`/
`get_project_list_path()` auf ein tmp_path-Ziel, damit kein Testlauf die
echte Vorratsliste/Projektliste des Users liest oder ueberschreibt.
"""

from pysticky.core import Pattern, Thread
from pysticky.ui.dialogs.inventory_dialog import InventoryDialog


def _isolate_app_data(monkeypatch, tmp_path):
    """Leitet Inventory()/ProjectList() auf tmp_path statt die echten
    App-Daten-Dateien des Users um (siehe Modul-Docstring)."""
    monkeypatch.setattr(
        "pysticky.core.inventory.get_inventory_path", lambda: tmp_path / "inventory.json"
    )
    monkeypatch.setattr(
        "pysticky.core.project_list.get_project_list_path", lambda: tmp_path / "projects.json"
    )


def test_pattern_tab_shows_strand_vocabulary_for_stitch_pattern(qtbot, tmp_path, monkeypatch):
    _isolate_app_data(monkeypatch, tmp_path)
    pattern = Pattern(width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000", catalog_number="321"))
    pattern.set_stitch(0, 0, 0)

    dialog = InventoryDialog(pattern)
    qtbot.addWidget(dialog)

    header_item = dialog._pattern_table.horizontalHeaderItem(5)
    assert "Stränge" in header_item.text()

    spin = dialog._pattern_table.cellWidget(0, 5)
    assert spin.suffix().strip() == "Strang"


def test_pattern_tab_shows_drill_vocabulary_for_diamond_pattern(qtbot, tmp_path, monkeypatch):
    _isolate_app_data(monkeypatch, tmp_path)
    pattern = Pattern(width=5, height=5, mode="diamond")
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Blau", "#0000FF", catalog_number="DB1"), is_diamond=True)
    pattern.set_stitch(0, 0, 0)

    dialog = InventoryDialog(pattern)
    qtbot.addWidget(dialog)

    header_item = dialog._pattern_table.horizontalHeaderItem(5)
    assert "Drills" in header_item.text()
    assert "Stränge" not in header_item.text()

    spin = dialog._pattern_table.cellWidget(0, 5)
    assert spin.suffix().strip() == "Drill"


def test_all_tab_has_name_column(qtbot, tmp_path, monkeypatch):
    """Regression (zurueckgestellter Fund aus Runde 22, hier nachgeholt):
    "Alle Eintraege"-Tab braucht eine Namens-Spalte, sonst sind zwei
    "unbekannte" Farben (leerer Hersteller + leere Katalognummer) in der
    Tabelle nicht voneinander zu unterscheiden."""
    _isolate_app_data(monkeypatch, tmp_path)
    pattern = Pattern(width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000", catalog_number="321"))
    pattern.set_stitch(0, 0, 0)

    dialog = InventoryDialog(pattern)
    qtbot.addWidget(dialog)

    assert dialog._all_table.columnCount() == 5
    header_texts = [dialog._all_table.horizontalHeaderItem(i).text() for i in range(5)]
    assert header_texts[1] == "Farbe"


def test_pattern_tab_tracks_unknown_colors_separately_by_name(qtbot, tmp_path, monkeypatch):
    """Der eigentliche Bugfix: zwei Farben ohne Hersteller/Katalognummer im
    selben Muster (z.B. aus einem Bildimport ohne Palette-Metadaten) duerfen
    sich NICHT mehr denselben Lagerbestand teilen, nur weil core.inventory
    beide vorher auf denselben "unknown::unknown"-Schluessel gemappt hat."""
    _isolate_app_data(monkeypatch, tmp_path)
    pattern = Pattern(width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Custom Rot", "#FF0000"))
    pattern.add_color(Thread.from_hex("Custom Blau", "#0000FF"))
    pattern.set_stitch(0, 0, 0)
    pattern.set_stitch(1, 0, 1)

    dialog = InventoryDialog(pattern)
    qtbot.addWidget(dialog)

    assert dialog._pattern_table.rowCount() == 2
    # Beide Farben haben leeren Hersteller/Katalognummer -- Zeilen ueber die
    # Namens-Spalte (1) auseinanderhalten statt uns auf die Reihenfolge zu
    # verlassen.
    row_by_name = {
        dialog._pattern_table.item(row, 1).text(): row
        for row in range(dialog._pattern_table.rowCount())
    }
    red_row = row_by_name["Custom Rot"]
    blue_row = row_by_name["Custom Blau"]

    red_spin = dialog._pattern_table.cellWidget(red_row, 5)
    blue_spin = dialog._pattern_table.cellWidget(blue_row, 5)
    assert red_spin.value() == 0
    assert blue_spin.value() == 0

    red_spin.setValue(4)
    # Vorher haette dies faelschlich auch den Bestand von "Custom Blau"
    # beeinflusst (gleicher Inventory-Schluessel) -- muss jetzt unabhaengig
    # bleiben.
    assert blue_spin.value() == 0
    assert dialog._inventory.get(None, None, "Custom Rot") == 4
    assert dialog._inventory.get(None, None, "Custom Blau") == 0


def test_all_tab_shows_distinguishable_unknown_colors_after_stock_entry(
    qtbot, tmp_path, monkeypatch
):
    """Nach Eintragen von Bestand fuer zwei "unbekannte" Farben im
    "Im Muster"-Tab muss der "Alle Eintraege"-Tab sie ueber die Namens-
    Spalte auseinanderhalten koennen (nicht nur im Datenmodell korrekt,
    sondern auch fuer den Nutzer sichtbar)."""
    _isolate_app_data(monkeypatch, tmp_path)
    pattern = Pattern(width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Custom Rot", "#FF0000"))
    pattern.add_color(Thread.from_hex("Custom Blau", "#0000FF"))
    pattern.set_stitch(0, 0, 0)
    pattern.set_stitch(1, 0, 1)

    dialog = InventoryDialog(pattern)
    qtbot.addWidget(dialog)

    row_by_name = {
        dialog._pattern_table.item(row, 1).text(): row
        for row in range(dialog._pattern_table.rowCount())
    }
    dialog._pattern_table.cellWidget(row_by_name["Custom Rot"], 5).setValue(3)
    dialog._pattern_table.cellWidget(row_by_name["Custom Blau"], 5).setValue(9)

    all_names_and_stock = {}
    for row in range(dialog._all_table.rowCount()):
        name = dialog._all_table.item(row, 1).text()
        stock = dialog._all_table.cellWidget(row, 4).value()
        all_names_and_stock[name] = stock

    assert all_names_and_stock.get("Custom Rot") == 3
    assert all_names_and_stock.get("Custom Blau") == 9


def test_multi_summary_uses_drill_label_when_all_projects_are_diamond(qtbot, tmp_path, monkeypatch):
    """Registrierte Projekte, die alle im DP-Modus sind: das Summen-Label
    muss "Drills insgesamt zu kaufen" sagen, nicht "Stränge"."""
    _isolate_app_data(monkeypatch, tmp_path)
    from pysticky.core.file_io import save_pattern

    dp_pattern = Pattern(width=5, height=5, mode="diamond")
    dp_pattern.color_entries.clear()
    dp_pattern.add_color(Thread.from_hex("Blau", "#0000FF", catalog_number="DB1"), is_diamond=True)
    dp_pattern.set_stitch(0, 0, 0)
    dp_pattern.color_entries[0].stitch_count = 300

    project_file = tmp_path / "dp_project.pxs"
    save_pattern(dp_pattern, str(project_file))

    dialog = InventoryDialog(dp_pattern, current_file=project_file)
    qtbot.addWidget(dialog)
    dialog._project_list.add(project_file)
    dialog._populate_projects_tab()

    assert "Drills" in dialog._multi_summary.text()
    assert "Stränge" not in dialog._multi_summary.text()
