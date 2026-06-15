# -*- coding: utf-8 -*-
"""
Smoke-Test fuer den Englisch-Modus der i18n.

Die uebrigen Tests laufen mit Default-Sprache 'de', wo t(key) den Key selbst
liefert — sie wuerden also einen kaputten t()-Aufruf (z.B. eine lokale
Variable 't', die die importierte Funktion ueberschattet) NICHT bemerken.

Dieser Test setzt die Sprache auf 'en' und baut das komplette Hauptfenster
(Menues, Toolbar, Docks, Panels) auf — dabei werden hunderte t()-Aufrufe
in Buildern/Handlern/Panels ausgefuehrt. Ein Absturz hier deutet auf ein
i18n-Problem hin. Anschliessend wird die Sprache wieder auf 'de' gesetzt,
damit nachfolgende Tests (die deutschen Text erwarten) nicht brechen.
"""

import pytest

from pysticky.core.i18n import set_language


@pytest.fixture
def english_language():
    """Aktiviert Englisch fuer die Dauer des Tests, danach zurueck auf Deutsch."""
    set_language("en")
    try:
        yield
    finally:
        set_language("de")


def test_mainwindow_builds_in_english(qtbot, english_language):
    """Hauptfenster-Konstruktion in 'en' darf nicht abstuerzen.

    Deckt die t()-Aufrufe in Buildern (Menue/Toolbar/Docks/Actions),
    Signal-Verdrahtung und allen angedockten Panels ab.
    """
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)

    # Konstruktion erfolgreich + zentrale UI-Elemente vorhanden.
    assert w.menuBar() is not None
    assert w.current_pattern is not None


def test_statistics_dialog_builds_in_english(qtbot, english_language, pattern_with_stitches):
    """Der am staerksten internationalisierte Dialog (Statistik) darf in 'en'
    nicht abstuerzen — exerziert ~50 t()-Aufrufe in _setup_ui."""
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.dialogs.statistics_dialog import PatternStatisticsDialog

    dlg = PatternStatisticsDialog(pattern_with_stitches)
    qtbot.addWidget(dlg)
    assert dlg.windowTitle()  # nicht leer


def test_en_translation_lookup_returns_english():
    """In 'en' liefert t() fuer einen vorhandenen Key die Uebersetzung,
    fuer einen unbekannten Key den Key selbst (Identity-Fallback)."""
    from pysticky.core.i18n import t

    set_language("en")
    try:
        assert t("&Datei") == "&File"  # vorhandener Key
        assert t("__kein_solcher_key__") == "__kein_solcher_key__"  # Fallback
    finally:
        set_language("de")
