# -*- coding: utf-8 -*-
"""Regressionstest (Runde 25): load_user_templates() fing nur
(OSError, json.JSONDecodeError, ValueError) um die
`[UserTemplate(**t) for t in data]`-Zeile ab. UserTemplate ist ein Dataclass
mit Pflichtfeldern (name/width/height, keine Defaults) -- ein Eintrag mit
fehlendem Pflichtfeld (z.B. eine handbearbeitete oder von einer aelteren
App-Version geschriebene user_templates.json) wirft TypeError, was NICHT
gefangen wurde. "⭐ Eigene Templates" (NewProjectDialog) und "Templates
verwalten" (ManageTemplatesDialog) riefen load_user_templates() ohne eigenes
try/except auf -- ein einziger kaputter Eintrag liess den kompletten Dialog
abstuerzen, statt nur den einen Eintrag zu ueberspringen (gleiche Fehlerklasse
wie bereits in pattern_library_data.py::LibraryData.from_dict() gefixt)."""

import json

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def test_load_user_templates_skips_entry_missing_required_field(tmp_path, monkeypatch):
    from pysticky.ui.dialogs import user_template_dialog

    monkeypatch.setattr(user_template_dialog, "get_templates_path", lambda: tmp_path)

    templates_file = tmp_path / "user_templates.json"
    templates_file.write_text(
        json.dumps(
            [
                {"name": "Gut", "width": 40, "height": 40},
                {"name": "Kaputt", "width": 40},  # height fehlt -> TypeError
            ]
        ),
        encoding="utf-8",
    )

    templates = user_template_dialog.load_user_templates()

    assert [t.name for t in templates] == ["Gut"]


def test_load_user_templates_all_valid_still_works(tmp_path, monkeypatch):
    from pysticky.ui.dialogs import user_template_dialog

    monkeypatch.setattr(user_template_dialog, "get_templates_path", lambda: tmp_path)

    templates_file = tmp_path / "user_templates.json"
    templates_file.write_text(
        json.dumps([{"name": "A", "width": 10, "height": 10}]),
        encoding="utf-8",
    )

    templates = user_template_dialog.load_user_templates()

    assert len(templates) == 1
    assert templates[0].name == "A"


def test_get_templates_path_falls_back_when_configured_dir_unreachable(tmp_path, monkeypatch):
    """Regression (Runde 27): get_templates_path() rief mkdir() auf dem in
    Einstellungen -> Dateien -> "Templates" konfigurierten Ordner OHNE
    try/except auf -- ein nicht mehr erreichbarer Ordner (abgestecktes
    Netzlaufwerk/USB-Stick, entfernte Berechtigung) liess "Neues Projekt"
    und "Templates verwalten" mit einem rohen OSError abstuerzen, statt auf
    den Standard-Ordner zurueckzufallen."""
    from pathlib import Path

    from PySide6.QtCore import QSettings

    from pysticky.ui.dialogs import user_template_dialog

    unreachable = tmp_path / "unreachable"
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    monkeypatch.setattr(Path, "home", lambda: home_dir)

    def fake_value(self, key, default="", type=None):  # noqa: A002
        if key == "templates_path":
            return str(unreachable)
        return default

    monkeypatch.setattr(QSettings, "value", fake_value)

    orig_mkdir = Path.mkdir

    def fake_mkdir(self, *args, **kwargs):
        if self == unreachable:
            raise PermissionError("simulated: unreachable")
        return orig_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    result = user_template_dialog.get_templates_path()

    assert result == home_dir / ".pysticky" / "templates"
    assert result.exists()
