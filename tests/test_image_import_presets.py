# -*- coding: utf-8 -*-
"""Tests fuer die User-Preset-Verwaltung des Bildimport-Dialogs
(ui/dialogs/image_import_presets.py)."""

import json

from pysticky.ui.dialogs.image_import_presets import (
    load_user_presets,
    save_user_presets,
)


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    from pysticky.ui.dialogs import image_import_presets as mod

    path = tmp_path / "import_presets.json"
    monkeypatch.setattr(mod, "get_user_presets_path", lambda: path)

    presets = [{"name": "Mein Preset", "width": 50, "height": 50}]
    save_user_presets(presets)
    assert path.exists()

    loaded = load_user_presets()
    assert loaded == presets


def test_save_writes_atomically_no_leftover_tmp_file(tmp_path, monkeypatch):
    from pysticky.ui.dialogs import image_import_presets as mod

    path = tmp_path / "import_presets.json"
    monkeypatch.setattr(mod, "get_user_presets_path", lambda: path)

    save_user_presets([{"name": "A"}])

    assert path.exists()
    assert not path.with_suffix(".json.tmp").exists()


def test_load_missing_file_returns_empty_list(tmp_path, monkeypatch):
    from pysticky.ui.dialogs import image_import_presets as mod

    monkeypatch.setattr(mod, "get_user_presets_path", lambda: tmp_path / "does_not_exist.json")
    assert load_user_presets() == []


def test_load_corrupt_json_returns_empty_list_not_crash(tmp_path, monkeypatch):
    from pysticky.ui.dialogs import image_import_presets as mod

    path = tmp_path / "import_presets.json"
    path.write_text("{ not valid json", encoding="utf-8")
    monkeypatch.setattr(mod, "get_user_presets_path", lambda: path)

    assert load_user_presets() == []


def test_load_wrong_top_level_type_returns_empty_list(tmp_path, monkeypatch):
    """Regression: eine Datei, die zu einem dict statt einer Liste
    deserialisiert, crashte frueher _populate_presets() mit TypeError,
    sobald ueber die Eintraege iteriert wurde."""
    from pysticky.ui.dialogs import image_import_presets as mod

    path = tmp_path / "import_presets.json"
    path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    monkeypatch.setattr(mod, "get_user_presets_path", lambda: path)

    assert load_user_presets() == []


def test_load_skips_malformed_entries_keeps_valid_ones(tmp_path, monkeypatch):
    """Regression: ein einzelner strukturell falscher Eintrag (fehlendes
    "name"-Feld, oder gar kein dict) crashte _populate_presets() mit
    KeyError/TypeError und riss dabei alle davor/danach stehenden
    gueltigen Presets mit -- der komplette Bildimport-Dialog stuerzte
    schon beim Oeffnen ab."""
    from pysticky.ui.dialogs import image_import_presets as mod

    path = tmp_path / "import_presets.json"
    raw = [
        {"name": "Gueltig A", "width": 10},
        {"width": 20},  # fehlendes "name"
        "kaputt",  # kein dict
        {"name": "Gueltig B", "width": 30},
    ]
    path.write_text(json.dumps(raw), encoding="utf-8")
    monkeypatch.setattr(mod, "get_user_presets_path", lambda: path)

    loaded = load_user_presets()
    assert [p["name"] for p in loaded] == ["Gueltig A", "Gueltig B"]
