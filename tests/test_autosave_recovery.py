# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 13): _check_autosave_recovery() prüfte beim Start
IMMER NUR die generische %TEMP%/pysticky_autosave.pxs -- die datei-
spezifische Autosave (<datei>.pxs.autosave, die _on_autosave anlegt,
sobald current_file gesetzt ist) wurde von NICHTS im ganzen Programm
jemals wieder gelesen. Wer also eine benannte Datei geoeffnet, weiter
editiert hatte und dann abstuerzte, bekam beim naechsten Oeffnen dieser
Datei nie eine Recovery angeboten -- die Autosave-Datei lag zwar korrekt
neben dem Projekt, aber komplett wirkungslos.

Diese Tests umgehen bewusst die globale autouse-Fixture
`_no_autosave_side_effects` (die _check_autosave_recovery normalerweise
zu einem No-Op macht), um das ECHTE Verhalten zu pruefen -- inklusive des
modalen QMessageBox.question, das dafuer gemockt wird.
"""

import pytest
from PySide6.QtWidgets import QMessageBox

from pysticky.ui.handlers.autosave_handlers import AutosaveHandlersMixin

# Referenz auf die ECHTE Methode, eingesammelt beim Modul-Import -- also
# BEVOR die autouse-Fixture sie in irgendeinem Test durch ein No-Op ersetzt.
_REAL_CHECK_AUTOSAVE_RECOVERY = AutosaveHandlersMixin._check_autosave_recovery


@pytest.fixture
def main_window(qtbot):
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    return w


def test_load_pattern_file_offers_recovery_for_sibling_autosave(main_window, monkeypatch, tmp_path):
    """_load_pattern_file() muss nach dem Oeffnen die datei-spezifische
    <datei>.pxs.autosave pruefen und bei Bestaetigung deren Inhalt laden."""
    from pysticky.core import Pattern, save_pattern

    monkeypatch.setattr(
        AutosaveHandlersMixin, "_check_autosave_recovery", _REAL_CHECK_AUTOSAVE_RECOVERY
    )

    saved_path = tmp_path / "mein_muster.pxs"
    saved_pattern = Pattern(name="Gespeichert", width=5, height=5)
    save_pattern(saved_pattern, saved_path)

    autosave_path = saved_path.with_suffix(".pxs.autosave")
    autosave_pattern = Pattern(name="Autosave-Stand", width=5, height=5)
    save_pattern(autosave_pattern, autosave_path)

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)

    assert main_window._load_pattern_file(saved_path) is True

    assert main_window.current_pattern.name == "Autosave-Stand"
    assert main_window._unsaved_changes is True
    # Autosave-Datei wird nach der Entscheidung aufgeraeumt.
    assert not autosave_path.exists()


def test_load_pattern_file_keeps_loaded_pattern_when_recovery_declined(
    main_window, monkeypatch, tmp_path
):
    from pysticky.core import Pattern, save_pattern

    monkeypatch.setattr(
        AutosaveHandlersMixin, "_check_autosave_recovery", _REAL_CHECK_AUTOSAVE_RECOVERY
    )

    saved_path = tmp_path / "mein_muster.pxs"
    saved_pattern = Pattern(name="Gespeichert", width=5, height=5)
    save_pattern(saved_pattern, saved_path)

    autosave_path = saved_path.with_suffix(".pxs.autosave")
    autosave_pattern = Pattern(name="Autosave-Stand", width=5, height=5)
    save_pattern(autosave_pattern, autosave_path)

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)

    assert main_window._load_pattern_file(saved_path) is True

    assert main_window.current_pattern.name == "Gespeichert"
    # Trotz Ablehnung wird die Autosave-Datei aufgeraeumt (kein erneutes
    # Nachfragen bei jedem weiteren Oeffnen derselben Datei).
    assert not autosave_path.exists()


def test_load_pattern_file_without_sibling_autosave_does_not_prompt(
    main_window, monkeypatch, tmp_path
):
    """Ohne existierende <datei>.pxs.autosave darf ueberhaupt kein Dialog
    erscheinen (regressionsschutz gegen Stoerung des normalen Oeffnens)."""
    from pysticky.core import Pattern, save_pattern

    monkeypatch.setattr(
        AutosaveHandlersMixin, "_check_autosave_recovery", _REAL_CHECK_AUTOSAVE_RECOVERY
    )

    saved_path = tmp_path / "ohne_autosave.pxs"
    save_pattern(Pattern(name="Normal", width=5, height=5), saved_path)

    called = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: called.append(1))

    assert main_window._load_pattern_file(saved_path) is True
    assert called == []
    assert main_window.current_pattern.name == "Normal"
