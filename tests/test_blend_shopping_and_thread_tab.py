# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 58 Nachtrag): Fuer eine Tweed-Blend-Farbe
(`entry.thread.is_blend`) zeigten der Garnverbrauch-Tab
(`ThreadTab._recalculate_thread`) und der CSV-Export
(`PatternStatisticsDialog._on_export_csv`) jeweils nur EINE Zeile fuer den
synthetischen Blend-Thread selbst (z.B. Name "DMC 310 / DMC 745 (1+1)"),
statt die beiden ECHTEN Komponenten-Garne (DMC 310, DMC 745) separat mit
der vollen Stichzahl aufzufuehren -- analog zum bereits gefixten
`core/inventory.py::compute_shopping_list()` (siehe
`_shoppable_threads()`/`Thread.real_components()`). Die "Gesamt"-Summary
im Tab zaehlte dadurch fuer jede Blend-Farbe nur einmal statt fuer BEIDE
tatsaechlich verbrauchten Garne.
"""

import csv

import pytest

from pysticky.core import Pattern, Thread
from pysticky.ui.dialogs.statistics_dialog import PatternStatisticsDialog
from pysticky.ui.dialogs.statistics_tabs.thread_tab import ThreadTab

pytestmark = pytest.mark.usefixtures("qtbot")


def _blend_pattern() -> Pattern:
    pattern = Pattern(width=5, height=5)
    pattern.color_entries.clear()
    a = Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310")
    b = Thread.from_hex("Yellow", "#FFE6A8", manufacturer="DMC", catalog_number="745")
    blend = Thread.blend([a, b], [1, 1])
    pattern.add_color(blend)
    pattern.set_stitch(0, 0, 0)
    pattern.set_stitch(1, 0, 0)
    return pattern


def test_thread_tab_expands_blend_into_both_components(qtbot):
    pattern = _blend_pattern()
    stitch_count = pattern.color_entries[0].stitch_count
    assert stitch_count == 2

    tab = ThreadTab()
    qtbot.addWidget(tab)
    tab.update_stats(pattern, {})

    assert tab._thread_table.rowCount() == 2
    names = {tab._thread_table.item(row, 1).text() for row in range(2)}
    assert names == {"Black", "Yellow"}

    # Beide Komponenten muessen mit der VOLLEN (nicht halbierten) Stichzahl
    # gefuehrt werden -- jeder Stich braucht einen vollen Strang JEDER
    # Komponente.
    stitches = {int(tab._thread_table.item(row, 2).text()) for row in range(2)}
    assert stitches == {stitch_count}


def test_csv_export_expands_blend_into_both_components(qtbot, tmp_path, monkeypatch):
    pattern = _blend_pattern()

    dialog = PatternStatisticsDialog(pattern)
    qtbot.addWidget(dialog)

    out_path = tmp_path / "blend_stats.csv"

    import pysticky.ui.dialogs.statistics_dialog as module

    monkeypatch.setattr(
        module.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out_path), ""))
    )
    monkeypatch.setattr(module.QMessageBox, "information", staticmethod(lambda *a, **k: None))

    dialog._on_export_csv()

    with open(out_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    header, data_rows = rows[0], rows[1:]
    assert len(data_rows) == 2

    name_idx = header.index("Name")
    catalog_idx = header.index("Katalognummer")
    stitches_idx = header.index("Stiche")

    names = {row[name_idx] for row in data_rows}
    catalogs = {row[catalog_idx] for row in data_rows}
    assert names == {"Black", "Yellow"}
    assert catalogs == {"310", "745"}

    stitch_count = pattern.color_entries[0].stitch_count
    for row in data_rows:
        assert int(row[stitches_idx]) == stitch_count
