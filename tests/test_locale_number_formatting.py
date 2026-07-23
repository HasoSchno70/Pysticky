# -*- coding: utf-8 -*-
"""
Locale/Zahlenformat-Audit (Runde 36): QDoubleSpinBox folgt ohne explizites
setLocale() der Default-QLocale (== OS-Regionaleinstellung). Unter einer
deutschen Windows-Regionaleinstellung zeigt QDoubleSpinBox.text()/.cleanText()
dann "1,50" statt "1.50" -- inkonsistent zu praktisch jeder anderen
Zahlenausgabe der App (CSV-Export, HTML-/PDF-Export, statistics_dialog.py's
CSV-Export-Formatierung), die durchgaengig f"{value:.2f}"-Python-Strings
verwendet und damit IMMER Punkt-dezimal ist, unabhaengig von der Sprache/OS.

Betroffen waren die beiden einzigen QDoubleSpinBox-Instanzen im gesamten
Code (`grep -r "QDoubleSpinBox(" src/` liefert genau diese zwei Treffer):
ThreadTab._price_spin (Garnverbrauch-Rechner, Preis pro Strang) und
TimeTab._hours_spin (Zeitschaetzung, Stunden pro Tag). Beide lesen zwar
korrekt ueber .value() (nie ueber .text()/float()-Parsing), das Problem ist
rein die sichtbare Anzeige -- ein Nutzer mit deutscher Windows-Regionaleinstellung
sieht "1,50 €" im Spinbox-Feld, aber "1.50" in der exportierten CSV-Datei
fuer denselben Wert.

Fix: explizites `.setLocale(QLocale.c())` auf beiden Spinboxen erzwingt
Punkt-Dezimaltrennzeichen unabhaengig von der Default-QLocale.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QLocale

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture
def german_default_locale():
    """Simuliert eine deutsche OS-Regionaleinstellung als QLocale-Default.

    QLocale.setDefault() ist global/prozessweit -- muss nach dem Test
    zurueckgesetzt werden, sonst faerbt es auf nachfolgende Tests ab.
    """
    original = QLocale()
    QLocale.setDefault(QLocale(QLocale.Language.German, QLocale.Country.Germany))
    yield
    QLocale.setDefault(original)


def test_thread_tab_price_spin_uses_dot_decimal_under_german_locale(qtbot, german_default_locale):
    from pysticky.ui.dialogs.statistics_tabs.thread_tab import ThreadTab

    tab = ThreadTab()
    qtbot.addWidget(tab)
    tab._price_spin.setValue(1.5)

    # Ohne den Fix waere das hier "1,50 €" (deutsche QLocale-Konvention),
    # inkonsistent zum Punkt-dezimalen CSV-/HTML-/PDF-Export.
    assert "," not in tab._price_spin.text()
    assert "1.50" in tab._price_spin.text()


def test_time_tab_hours_spin_uses_dot_decimal_under_german_locale(qtbot, german_default_locale):
    from pysticky.ui.dialogs.statistics_tabs.time_tab import TimeTab

    tab = TimeTab()
    qtbot.addWidget(tab)
    tab._hours_spin.setValue(2.5)

    assert "," not in tab._hours_spin.text()
    assert "2.5" in tab._hours_spin.text()


def test_snapshot_history_tooltip_uses_german_weekday_name_in_default_language():
    """Regression: SnapshotHistoryDialog nutzte strftime('%A'), das ohne
    explizites locale.setlocale(LC_TIME, ...) (was PySticky bewusst nirgends
    tut) IMMER den englischen Wochentagsnamen liefert -- unabhaengig von
    OS-Locale UND von der App-Sprache. In der deutschen Default-Sprache der
    App stand im sonst komplett deutschen Tooltip also z.B. "Thursday,
    23.07.2026 ..." statt "Donnerstag, ...".
    """
    from datetime import datetime

    from pysticky.core.i18n import get_translation_manager
    from pysticky.ui.dialogs.snapshot_history_dialog import _weekday_name

    manager = get_translation_manager()
    original_lang = manager.current_language
    manager.set_language("de")
    try:
        # 2026-07-23 ist ein Donnerstag.
        ts = datetime(2026, 7, 23, 14, 30, 0)
        assert _weekday_name(ts) == "Donnerstag"
    finally:
        manager.set_language(original_lang)


def test_snapshot_history_tooltip_uses_english_weekday_name_in_english_mode():
    """Gegenprobe: im Englisch-Modus soll weiterhin der englische
    Wochentagsname erscheinen (kein hart-codiertes Deutsch mehr fuer alle
    Sprachen)."""
    from datetime import datetime

    from pysticky.core.i18n import get_translation_manager
    from pysticky.ui.dialogs.snapshot_history_dialog import _weekday_name

    manager = get_translation_manager()
    original_lang = manager.current_language
    manager.set_language("en")
    try:
        ts = datetime(2026, 7, 23, 14, 30, 0)
        assert _weekday_name(ts) == "Thursday"
    finally:
        manager.set_language(original_lang)
