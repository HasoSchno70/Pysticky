# -*- coding: utf-8 -*-
"""
Regressionstest (Silent-Exception-Audit): ManageTemplatesDialog._on_delete()
und _on_rename() riefen save_user_templates() auf und ignorierten komplett den
Rueckgabewert (bool) -- schlug das Schreiben von user_templates.json fehl
(z.B. abgestecktes Netzlaufwerk, volle Platte), wirkte das Loeschen/Umbenennen
im laufenden Dialog trotzdem erfolgreich (Liste aktualisiert sich, Signal
feuert), die Aenderung ging aber beim naechsten Programmstart stillschweigend
verloren -- keinerlei Hinweis an den Nutzer.

Der Geschwister-Pfad misc_handlers.py::_on_save_as_template() prueft den
Rueckgabewert bereits korrekt und zeigt bei False eine QMessageBox.warning --
_on_delete()/_on_rename() hier waren davon abweichend inkonsistent.

Zusaetzlich prueft save_user_templates() selbst: vorher gab es bei einem
Schreibfehler NICHT EINMAL ein Log -- reines stilles `return False`.
"""

import logging

import pytest
from PySide6.QtWidgets import QInputDialog, QMessageBox

pytestmark = pytest.mark.usefixtures("qtbot")


def _make_manage_dialog(qtbot, tmp_path, monkeypatch, templates):
    from pysticky.ui.dialogs import user_template_dialog

    monkeypatch.setattr(user_template_dialog, "get_templates_path", lambda: tmp_path)

    dlg = user_template_dialog.ManageTemplatesDialog()
    qtbot.addWidget(dlg)
    dlg._templates = templates
    dlg._refresh_list()
    return dlg


def test_save_user_templates_logs_on_write_failure(tmp_path, monkeypatch, caplog):
    from pysticky.ui.dialogs import user_template_dialog

    monkeypatch.setattr(user_template_dialog, "get_templates_path", lambda: tmp_path)

    def fail_open(*args, **kwargs):
        raise OSError("simulated: Platte voll")

    monkeypatch.setattr(user_template_dialog, "open", fail_open, raising=False)

    with caplog.at_level(logging.WARNING):
        result = user_template_dialog.save_user_templates(
            [user_template_dialog.UserTemplate(name="A", width=10, height=10)]
        )

    assert result is False
    assert any("gespeichert" in rec.message for rec in caplog.records), (
        "Ein Schreibfehler beim Speichern der Templates muss mindestens geloggt "
        "werden, statt komplett stumm False zurueckzugeben."
    )


def test_delete_template_shows_warning_when_save_fails(qtbot, tmp_path, monkeypatch):
    from pysticky.ui.dialogs import user_template_dialog

    template = user_template_dialog.UserTemplate(name="Zu loeschen", width=10, height=10)
    dlg = _make_manage_dialog(qtbot, tmp_path, monkeypatch, [template])

    monkeypatch.setattr(user_template_dialog, "save_user_templates", lambda templates: False)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Yes)

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **kw: warnings.append((a, kw)))

    dlg._list.setCurrentRow(0)
    dlg._on_delete()

    assert warnings, (
        "Schlaegt save_user_templates() beim Loeschen fehl, muss der Nutzer "
        "gewarnt werden, statt dass das Loeschen scheinbar klaglos durchlaeuft."
    )


def test_rename_template_shows_warning_when_save_fails(qtbot, tmp_path, monkeypatch):
    from pysticky.ui.dialogs import user_template_dialog

    template = user_template_dialog.UserTemplate(name="Alter Name", width=10, height=10)
    dlg = _make_manage_dialog(qtbot, tmp_path, monkeypatch, [template])

    monkeypatch.setattr(user_template_dialog, "save_user_templates", lambda templates: False)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **kw: ("Neuer Name", True))

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **kw: warnings.append((a, kw)))

    dlg._list.setCurrentRow(0)
    dlg._on_rename()

    assert warnings, (
        "Schlaegt save_user_templates() beim Umbenennen fehl, muss der Nutzer "
        "gewarnt werden, statt dass das Umbenennen scheinbar klaglos durchlaeuft."
    )


def test_delete_template_no_warning_when_save_succeeds(qtbot, tmp_path, monkeypatch):
    """Gegenprobe: der Normalfall (Speichern klappt) darf keinen Dialog zeigen."""
    from pysticky.ui.dialogs import user_template_dialog

    template = user_template_dialog.UserTemplate(name="Zu loeschen", width=10, height=10)
    dlg = _make_manage_dialog(qtbot, tmp_path, monkeypatch, [template])

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Yes)

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **kw: warnings.append((a, kw)))

    dlg._list.setCurrentRow(0)
    dlg._on_delete()

    assert not warnings
