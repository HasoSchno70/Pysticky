# -*- coding: utf-8 -*-
"""Regressionstest (Runde 27): _perform_start_action()'s Zweig fuer
start_action==0 ("Leeres Muster erstellen" in general_tab.py's Combo) tat
in Wahrheit exakt dasselbe wie start_action==3 ("Nichts tun") -- zeigte nur
den Welcome-Screen, ohne jemals ein Pattern zu erzeugen. Der Nutzer waehlt
explizit "Leeres Muster erstellen" und bekommt trotzdem den Willkommen-
Bildschirm zu sehen, identisch zur "Nichts tun"-Option. Jetzt erstellt
start_action==0 direkt ein leeres Standard-Pattern (ohne Dialog, im
Gegensatz zu start_action==1, das den Neues-Projekt-Dialog oeffnet)."""

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


def test_start_action_zero_creates_empty_pattern_not_welcome_screen(main_window):
    w = main_window
    original_value = w._settings.value("start_action", 0, type=int)
    w._settings.setValue("start_action", 0)
    w._pattern_explicitly_set = False
    w.current_file = None
    w._unsaved_changes = False

    try:
        w._perform_start_action()

        assert w._pattern_explicitly_set, (
            "Regression: start_action==0 zeigte weiterhin nur den Welcome-Screen "
            "statt ein Pattern zu erstellen"
        )
        assert w.canvas_container._stack.currentIndex() == 0, (
            "Regression: Welcome-Screen (Stack-Index 1) blieb sichtbar statt auf "
            "das neu erstellte Pattern (Stack-Index 0) umzuschalten"
        )
    finally:
        w._settings.setValue("start_action", original_value)
