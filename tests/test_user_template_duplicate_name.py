# -*- coding: utf-8 -*-
"""Regressionstest (Clean-Code-Audit Runde 66): weder SaveTemplateDialog noch
ManageTemplatesDialog._on_rename() pruefen, ob bereits eine Vorlage mit dem
(getrimmten) eingegebenen Namen existiert. Vor diesem Fix konnten beliebig
viele Vorlagen mit identischem Namen entstehen (Speichern-Dialog haengt
einfach an, Umbenennen ueberschreibt den Namen ohne jede Pruefung) --
in "Templates verwalten" und im "Eigene Templates"-Tab von "Neues Projekt"
sind solche Eintraege fuer den Nutzer nicht mehr unterscheidbar, welche
Vorlage tatsaechlich gemeint ist (z.B. beim spaeteren Loeschen/Umbenennen).

Zusaetzlich: der Vorlagen-Name wird konsistent VOR dem Vergleich getrimmt,
damit "Mein Template" und "Mein Template " (Leerzeichen am Ende) als Duplikat
erkannt werden.
"""

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


def test_save_template_dialog_rejects_duplicate_name(qtbot, tmp_path, monkeypatch):
    from pysticky.ui.dialogs import user_template_dialog

    monkeypatch.setattr(user_template_dialog, "get_templates_path", lambda: tmp_path)
    user_template_dialog.save_user_templates(
        [user_template_dialog.UserTemplate(name="Mein Template", width=10, height=10)]
    )

    dlg = user_template_dialog.SaveTemplateDialog(width=20, height=20, fabric_count=14)
    qtbot.addWidget(dlg)
    # Fuehrende/nachfolgende Leerzeichen duerfen die Duplikat-Erkennung nicht
    # umgehen -- der Name muss vor dem Vergleich getrimmt werden.
    dlg._name_input.setText("  Mein Template  ")

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **kw: warnings.append((a, kw)))

    dlg._on_save()

    assert warnings, (
        "Ein Name, der (nach Trimmen) bereits als Vorlage existiert, muss "
        "abgelehnt werden statt eine zweite gleichnamige Vorlage entstehen "
        "zu lassen."
    )
    assert dlg.template is None
    assert dlg.result() != dlg.DialogCode.Accepted


def test_save_template_dialog_allows_unique_name(qtbot, tmp_path, monkeypatch):
    """Gegenprobe: ein neuer, noch nicht vergebener Name muss weiterhin klappen."""
    from pysticky.ui.dialogs import user_template_dialog

    monkeypatch.setattr(user_template_dialog, "get_templates_path", lambda: tmp_path)
    user_template_dialog.save_user_templates(
        [user_template_dialog.UserTemplate(name="Bestehend", width=10, height=10)]
    )

    dlg = user_template_dialog.SaveTemplateDialog(width=20, height=20, fabric_count=14)
    qtbot.addWidget(dlg)
    dlg._name_input.setText("Ganz neu")

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **kw: warnings.append((a, kw)))

    dlg._on_save()

    assert not warnings
    assert dlg.template is not None
    assert dlg.template.name == "Ganz neu"


def test_rename_rejects_duplicate_name(qtbot, tmp_path, monkeypatch):
    from pysticky.ui.dialogs import user_template_dialog

    template_a = user_template_dialog.UserTemplate(name="A", width=10, height=10)
    template_b = user_template_dialog.UserTemplate(name="B", width=10, height=10)
    dlg = _make_manage_dialog(qtbot, tmp_path, monkeypatch, [template_a, template_b])

    # "B" in "  A  " umbenennen (mit Leerzeichen) -- kollidiert nach dem
    # Trimmen mit dem bereits existierenden Namen "A".
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **kw: ("  A  ", True))

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **kw: warnings.append((a, kw)))
    save_calls = []
    monkeypatch.setattr(
        user_template_dialog,
        "save_user_templates",
        lambda templates: save_calls.append(list(templates)) or True,
    )

    dlg._list.setCurrentRow(1)  # "B"
    dlg._on_rename()

    assert warnings, (
        "Umbenennen in einen bereits vergebenen Namen muss abgelehnt werden "
        "statt zwei Vorlagen mit identischem Namen entstehen zu lassen."
    )
    assert template_b.name == "B", "Name darf bei abgelehntem Duplikat nicht veraendert werden."
    assert not save_calls, "Bei abgelehntem Duplikat darf gar nicht erst gespeichert werden."


def test_rename_allows_unique_name(qtbot, tmp_path, monkeypatch):
    """Gegenprobe: Umbenennen in einen freien Namen muss weiterhin klappen."""
    from pysticky.ui.dialogs import user_template_dialog

    template_a = user_template_dialog.UserTemplate(name="A", width=10, height=10)
    template_b = user_template_dialog.UserTemplate(name="B", width=10, height=10)
    dlg = _make_manage_dialog(qtbot, tmp_path, monkeypatch, [template_a, template_b])

    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **kw: ("C", True))

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **kw: warnings.append((a, kw)))
    monkeypatch.setattr(user_template_dialog, "save_user_templates", lambda templates: True)

    dlg._list.setCurrentRow(1)  # "B"
    dlg._on_rename()

    assert not warnings
    assert template_b.name == "C"


def test_rename_to_own_current_name_is_not_a_duplicate(qtbot, tmp_path, monkeypatch):
    """Gegenprobe: Umbenennen auf den eigenen (unveraenderten) Namen ist kein
    Duplikat -- self-Vergleich darf nicht faelschlich ablehnen."""
    from pysticky.ui.dialogs import user_template_dialog

    template_a = user_template_dialog.UserTemplate(name="A", width=10, height=10)
    dlg = _make_manage_dialog(qtbot, tmp_path, monkeypatch, [template_a])

    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **kw: ("A", True))

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **kw: warnings.append((a, kw)))
    monkeypatch.setattr(user_template_dialog, "save_user_templates", lambda templates: True)

    dlg._list.setCurrentRow(0)
    dlg._on_rename()

    assert not warnings
    assert template_a.name == "A"
