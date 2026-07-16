# -*- coding: utf-8 -*-
"""
Regressionstests: Speichern-Fehler dürfen die App nicht crashen.

json.dump wirft bei nicht-serialisierbarem Zustand TypeError/ValueError
(nicht OSError) — die Save-Handler müssen das abfangen und einen
Fehlerdialog zeigen statt abzustürzen.
"""

import pytest


@pytest.fixture
def main_window(qtbot):
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    # pytest-qt schliesst das Fenster im Teardown VOR den Fixture-Finalizern —
    # closeEvent wuerde dann den modalen "Aenderungen speichern?"-Dialog oeffnen
    # und die Suite haengen lassen. Daher die Nachfrage auf der Instanz stilllegen.
    w._check_save_changes = lambda: True
    # Autosave-Timer stoppen: feuert er waehrend eines laufenden Event-Loops
    # (z.B. QMessageBox in einem anderen Test), schreibt er eine echte
    # %TEMP%-Autosave-Datei und legt damit die Recovery-Dialog-Falle.
    w._autosave_timer.stop()
    return w


def _patch_save_to_raise(monkeypatch, exc):
    """Lässt core.save_pattern die gegebene Exception werfen."""
    import pysticky.core as core

    def boom(pattern, path):
        raise exc

    monkeypatch.setattr(core, "save_pattern", boom)


@pytest.mark.parametrize("exc", [TypeError("not serializable"), ValueError("circular")])
def test_on_save_survives_serialization_error(main_window, monkeypatch, tmp_path, exc):
    """_on_save darf bei TypeError/ValueError aus json.dump nicht crashen."""
    from PySide6.QtWidgets import QMessageBox

    shown = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: shown.append(args))
    _patch_save_to_raise(monkeypatch, exc)

    main_window.current_file = tmp_path / "test.pxs"
    main_window._on_save()  # darf keine Exception werfen

    assert shown, "Fehlerdialog wurde nicht angezeigt"


def test_on_autosave_survives_serialization_error(main_window, monkeypatch, tmp_path):
    """_on_autosave darf bei TypeError aus json.dump nicht crashen."""
    _patch_save_to_raise(monkeypatch, TypeError("not serializable"))

    main_window.current_file = tmp_path / "test.pxs"
    main_window._unsaved_changes = True
    main_window._on_autosave()  # darf keine Exception werfen

    # Es darf keine kaputte Tempdatei liegen bleiben
    assert not list(tmp_path.glob("*.tmp"))


def test_maybe_create_snapshot_logs_instead_of_silent(main_window, monkeypatch, caplog):
    """Snapshot-Fehler werden geloggt statt still verschluckt."""
    import pysticky.core.snapshots as snapshots

    monkeypatch.setattr(snapshots, "should_snapshot", lambda key: True)

    def boom(pattern, key):
        raise OSError("disk full")

    monkeypatch.setattr(snapshots, "create_snapshot", boom)

    with caplog.at_level("ERROR", logger="pysticky"):
        main_window._maybe_create_snapshot()  # darf keine Exception werfen

    assert any("Snapshot" in rec.message for rec in caplog.records)
