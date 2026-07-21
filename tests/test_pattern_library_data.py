# -*- coding: utf-8 -*-
"""Tests fuer die Muster-Bibliotheks-Datenklassen (ui/dialogs/pattern_library_data.py)."""

from pysticky.ui.dialogs.pattern_library_data import LibraryData, LibraryEntry


def _valid_entry_dict(name="Test"):
    return {
        "filepath": "/tmp/test.pxs",
        "name": name,
        "width": 50,
        "height": 50,
        "color_count": 5,
        "stitch_count": 100,
    }


def test_from_dict_loads_valid_entries():
    data = {"version": "1.0", "entries": [_valid_entry_dict("A"), _valid_entry_dict("B")]}
    lib = LibraryData.from_dict(data)
    assert len(lib.entries) == 2
    assert lib.entries[0].name == "A"
    assert lib.entries[1].name == "B"


def test_from_dict_skips_malformed_entry_keeps_valid_ones():
    """Regression: ein einzelner fehlerhafter Eintrag (fehlendes/falsches
    Feld) liess frueher LibraryEntry(**e) mit TypeError crashen -- das
    riss den gesamten from_dict()-Aufruf mit, auch fuer alle davor/danach
    stehenden gueltigen Eintraege. _load_library() in
    pattern_library_dialog.py faengt nur (OSError, JSONDecodeError,
    ValueError), also propagierte der TypeError bis dahin ungefangen und
    liess den ganzen Dialog abstuerzen."""
    malformed = {"unexpected_field": "boom"}  # fehlende required Felder
    data = {
        "version": "1.0",
        "entries": [_valid_entry_dict("A"), malformed, _valid_entry_dict("B")],
    }
    lib = LibraryData.from_dict(data)
    assert len(lib.entries) == 2
    assert [e.name for e in lib.entries] == ["A", "B"]


def test_from_dict_empty_entries():
    lib = LibraryData.from_dict({"version": "1.0", "entries": []})
    assert lib.entries == []


def test_to_dict_roundtrip():
    lib = LibraryData()
    lib.entries.append(LibraryEntry(**_valid_entry_dict("Roundtrip")))
    data = lib.to_dict()
    lib2 = LibraryData.from_dict(data)
    assert len(lib2.entries) == 1
    assert lib2.entries[0].name == "Roundtrip"


def test_entry_without_fabric_count_defaults_to_14():
    """Alte library.json-Eintraege ohne fabric_count-Feld muessen weiter
    ladbar bleiben (Default 14 = DEFAULT_FABRIC_COUNT)."""
    lib = LibraryData.from_dict({"version": "1.0", "entries": [_valid_entry_dict("Old")]})
    assert lib.entries[0].fabric_count == 14


def test_entry_stores_explicit_fabric_count():
    d = _valid_entry_dict("Custom")
    d["fabric_count"] = 18
    entry = LibraryEntry(**d)
    assert entry.fabric_count == 18
