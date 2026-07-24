# -*- coding: utf-8 -*-
"""
Regressionstests: MainWindow.add_color_to_pattern() kollabierte frei
angelegte/eigene Farben ohne Hersteller+Katalognummer faelschlich auf einen
einzigen Eintrag (Clean-Code-Audit Runde 70).

PySticky hat kein Feature, um dauerhaft benannte, wiederverwendbare
"eigene Paletten" (analog zu den mitgelieferten DMC/Anchor/... Paletten aus
resources/palettes/) anzulegen -- die Palette-Auswahl in der UI listet
ausschliesslich die mitgelieferten Paletten (core/palette.py::PaletteManager
laedt nur aus resources/palettes/, es gibt keinen "add_palette"/"create
custom palette"-Pfad). Das naechstliegende Aequivalent ist "Palette
exportieren/importieren" (ui/handlers/edit_handlers.py::_on_export_palette /
_on_import_palette): die aktuellen Musterfarben werden als JSON
("pysticky_palette"-Format) exportiert bzw. aus so einer Datei wieder in
das Muster importiert -- das ist die vom Nutzer tatsaechlich nutzbare Form
einer "eigenen Palette".

Beim Import ruft _on_import_palette() fuer jede Farbe
MainWindow.add_color_to_pattern() auf, um Duplikate zu vermeiden. Dessen
Dedup-Check verglich NUR (manufacturer, catalog_number) -- fehlen beide (wie
bei frei/eigen angelegten Farben ohne Hersteller/Katalognummer, dem
Normalfall fuer eine "eigene Palette"), sind beide Werte fuer JEDE
katalog-lose Farbe `None`, wodurch `None == None` faelschlich als Duplikat
erkannt wurde -- unabhaengig vom tatsaechlichen RGB-Wert. Ergebnis: die
zweite, dritte, ... eigene Farbe landete nie als neuer color_entries-Eintrag,
sondern wurde stumm auf den Index der ERSTEN bereits vorhandenen
katalog-losen Farbe umgeleitet (dieselbe Kollaps-Fehlerklasse wie der
Katalognummer-Feld-Bug bei mitgelieferten Paletten, hier aber auf
Pattern-Ebene statt beim Palette-Laden).

Fix: der Dedup-Check in add_color_to_pattern() vergleicht bei fehlender
Katalog-Identitaet (beide catalog_number None) zusaetzlich die tatsaechliche
Farbe -- nur bei echter RGB-Uebereinstimmung gilt es als Duplikat.
"""

import json

import pytest

pytest.importorskip("PySide6")


def _make_window(qtbot, empty_pattern):
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    w.current_pattern = empty_pattern
    return w


def test_add_color_to_pattern_does_not_collapse_distinct_catalog_less_colors(qtbot, empty_pattern):
    """Zwei frei angelegte Farben ohne Hersteller/Katalognummer, aber mit
    unterschiedlichem RGB-Wert, muessen als ZWEI getrennte Eintraege landen."""
    from pysticky.core import Thread
    from pysticky.core.thread import ThreadColor

    w = _make_window(qtbot, empty_pattern)

    red = Thread(name="Mein Rot", color=ThreadColor(255, 0, 0))
    blue = Thread(name="Mein Blau", color=ThreadColor(0, 0, 255))

    idx_red = w.add_color_to_pattern(red)
    idx_blue = w.add_color_to_pattern(blue)

    assert idx_red != idx_blue
    assert empty_pattern.color_entries[idx_red].thread.color == ThreadColor(255, 0, 0)
    assert empty_pattern.color_entries[idx_blue].thread.color == ThreadColor(0, 0, 255)


def test_add_color_to_pattern_still_dedupes_identical_catalog_less_color(qtbot, empty_pattern):
    """Wird dieselbe katalog-lose Farbe (identisches RGB) zweimal hinzugefuegt,
    soll weiterhin auf denselben Eintrag dedupliziert werden -- der Fix darf
    die eigentliche Dedup-Funktion nicht abschalten, nur den falschen
    Vergleichsschluessel korrigieren."""
    from pysticky.core import Thread
    from pysticky.core.thread import ThreadColor

    w = _make_window(qtbot, empty_pattern)

    red1 = Thread(name="Mein Rot", color=ThreadColor(255, 0, 0))
    red2 = Thread(name="Mein Rot (Kopie)", color=ThreadColor(255, 0, 0))

    idx1 = w.add_color_to_pattern(red1)
    idx2 = w.add_color_to_pattern(red2)

    assert idx1 == idx2


def test_add_color_to_pattern_still_dedupes_real_catalog_thread(qtbot, empty_pattern):
    """Regressionsschutz: der eigentliche, urspruengliche Zweck des Dedup-Checks
    (echte Katalog-Threads mit gleichem Hersteller+Katalognummer) darf durch
    den Fix nicht kaputtgehen."""
    from pysticky.core import Thread
    from pysticky.core.thread import ThreadColor

    w = _make_window(qtbot, empty_pattern)

    dmc_310_a = Thread(
        name="Black", color=ThreadColor(0, 0, 0), manufacturer="DMC", catalog_number="310"
    )
    dmc_310_b = Thread(
        name="Schwarz", color=ThreadColor(0, 0, 0), manufacturer="DMC", catalog_number="310"
    )

    idx1 = w.add_color_to_pattern(dmc_310_a)
    idx2 = w.add_color_to_pattern(dmc_310_b)

    assert idx1 == idx2


def test_import_own_palette_json_with_two_catalog_less_colors_does_not_collapse(
    qtbot, empty_pattern, tmp_path, monkeypatch
):
    """End-to-End ueber den tatsaechlichen Nutzer-Workflow: eine exportierte
    "eigene Palette" (JSON im pysticky_palette-Format) mit zwei frei
    angelegten Farben ohne Hersteller/Katalognummer muss beim Import zwei
    neue, unterschiedliche Farbeintraege ergeben -- nicht einen."""
    from PySide6.QtWidgets import QFileDialog

    w = _make_window(qtbot, empty_pattern)
    entries_before = len(empty_pattern.color_entries)

    palette_file = tmp_path / "meine_palette.json"
    palette_file.write_text(
        json.dumps(
            {
                "format": "pysticky_palette",
                "version": "1.0",
                "name": "Meine Palette",
                "colors": [
                    {
                        "name": "Mein Rot",
                        "color": {"r": 255, "g": 0, "b": 0},
                        "manufacturer": "",
                        "catalog_number": "",
                        "symbol": "1",
                    },
                    {
                        "name": "Mein Blau",
                        "color": {"r": 0, "g": 0, "b": 255},
                        "manufacturer": "",
                        "catalog_number": "",
                        "symbol": "2",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(palette_file), ""))
    )

    w._on_import_palette()

    new_colors = empty_pattern.color_entries[entries_before:]
    assert len(new_colors) == 2
    rgb_values = {c.thread.color.to_tuple() for c in new_colors}
    assert rgb_values == {(255, 0, 0), (0, 0, 255)}
