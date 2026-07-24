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


@pytest.fixture
def _reset_language():
    """set_language() ist global -- Test muss die App-Sprache danach zurücksetzen."""
    from pysticky.core.i18n import current_language, set_language

    original = current_language()
    yield
    set_language(original)


def test_format_number_uses_dot_separator_in_german_app_language(_reset_language):
    """Runde 71: format_number() muss der App-Sprache (t()/set_language()),
    NICHT der OS-Locale folgen -- Deutsch gruppiert mit Punkt."""
    from pysticky.core.i18n import format_number, set_language

    set_language("de")
    assert format_number(12345) == "12.345"


def test_format_number_uses_comma_separator_in_english_app_language(_reset_language):
    """Gegenprobe: Englisch gruppiert mit Komma (Python-Default)."""
    from pysticky.core.i18n import format_number, set_language

    set_language("en")
    assert format_number(12345) == "12,345"


def test_info_panel_and_statistics_overview_agree_on_stitch_count_formatting(
    qtbot, _reset_language
):
    """Regression (Runde 71): dieselbe Stich-Anzahl (>= 1000, damit ein
    Tausendertrennzeichen ueberhaupt sichtbar wird) erschien im Info-Panel-
    Dock ("12.345", hartkodierter f"{n:,}".replace(",", ".")-Hack -- IMMER
    deutsches Format) und im Statistik-Dialog-Overview-Tab ("12,345", roher
    Python-Default f"{n:,}" -- IMMER englisches Format) unterschiedlich
    formatiert, und zwar VOELLIG UNABHAENGIG von der tatsaechlich
    eingestellten App-Sprache. Mit format_number() muessen beide Stellen für
    dieselbe Sprache identisch formatieren.
    """
    from pysticky.core import Pattern, Thread
    from pysticky.core.i18n import set_language
    from pysticky.ui.dialogs.statistics_tabs.overview_tab import OverviewTab
    from pysticky.ui.panels.info_panel import InfoPanel

    # 40x40 = 1600 Stiche, eine einzige Farbe, keine übersprungenen Stiche
    # -> beide Widgets nehmen den "else"-Zweig (kein skip_stitching-Zusatz).
    pattern = Pattern(width=40, height=40)
    pattern.color_entries.clear()
    idx = pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    for y in range(40):
        for x in range(40):
            pattern.set_stitch(x, y, idx)

    for lang in ("de", "en"):
        set_language(lang)
        stats = pattern.get_statistics()

        info = InfoPanel()
        qtbot.addWidget(info)
        info.update_info(pattern)

        overview = OverviewTab()
        qtbot.addWidget(overview)
        overview.update_stats(pattern, stats)

        info_text = info.card_stitches.lbl_value.text()
        overview_text = overview._card_stitches._value_label.text()

        assert info_text == overview_text, (
            f"Sprache={lang!r}: Info-Panel zeigt {info_text!r}, "
            f"Statistik-Overview zeigt {overview_text!r}"
        )
        # Bei 1600 muss ueberhaupt ein Trennzeichen vorkommen (sonst waere
        # der Test trivial erfuellt, weil beide Seiten zufaellig "1600" ohne
        # jede Formatierung zeigen wuerden).
        assert any(sep in info_text for sep in (".", ","))


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
