# -*- coding: utf-8 -*-
"""Regressionstest (Runde 81): _perform_start_action()'s Zweig fuer
start_action==1 ("Neues Projekt-Dialog öffnen") ruft _on_new() auf, was den
NewProjectDialog zeigt. Bricht der Nutzer diesen Dialog beim App-Start ab
(kein Pattern wird erzeugt), kehrt _on_new() einfach kommentarlos zurueck --
weder wird (wie bei start_action==0) ein leeres Standard-Pattern erstellt,
noch wird (wie bei start_action==2/3 im Leerlauf-Fall) der Welcome-Screen
gezeigt. Der Nutzer landet in einem leeren, unbenutzbaren Fenster ohne
jeden Hinweis -- exakt die Bug-Klasse, die Runde 71 fuer die Zweige 0/2/3
bereits gefixt hat, hier aber fuer Zweig 1 (Dialog-Abbruch) uebersehen.

HINWEIS: unittest.mock.patch() auf NewProjectDialog.exec (einer PySide6-
QDialog-Methode) fuehrte in diesem Environment zu einem nativen Absturz
(access violation) beim naechsten Konstruieren des Dialogs -- ein reines
Mock/Shiboken-Interaktionsproblem, kein App-Bug. monkeypatch.setattr() mit
einer echten Python-Funktion umgeht das."""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


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


def test_start_action_one_cancel_shows_welcome_not_blank_window(main_window, monkeypatch):
    from pysticky.ui.dialogs.new_project_dialog import NewProjectDialog

    w = main_window
    original_value = w._settings.value("start_action", 0, type=int)
    w._settings.setValue("start_action", 1)
    w._pattern_explicitly_set = False
    w.current_file = None
    w._unsaved_changes = False

    # NewProjectDialog.exec() simuliert Abbrechen (Cancel/Reject -> 0).
    monkeypatch.setattr(NewProjectDialog, "exec", lambda self: 0)

    try:
        w._perform_start_action()

        assert w.canvas_container._stack.currentIndex() == 1, (
            "Regression: Abbrechen des Neues-Projekt-Dialogs beim Start liess "
            "ein leeres, unbenutzbares Fenster ohne Welcome-Screen zurueck"
        )
    finally:
        w._settings.setValue("start_action", original_value)
