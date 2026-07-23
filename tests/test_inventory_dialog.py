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
