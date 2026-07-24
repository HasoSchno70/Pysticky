# -*- coding: utf-8 -*-
"""
Regressionstest: zwei gleichzeitig laufende PySticky-Instanzen, die BEIDE
ein nie gespeichertes Pattern haben (current_file is None -- z.B. zwei
"Datei -> Neu"-Fenster), schrieben ihre Temp-Autosave vor diesem Fix beide
auf denselben globalen Pfad %TEMP%/pysticky_autosave.pxs. Welcher Autosave-
Timer zuletzt feuerte, gewann -- die andere Instanz verlor ihren Stand
kommentarlos. Stuerzte danach eine Instanz ab, bot die naechste
_check_autosave_recovery() womoeglich den Stand der FALSCHEN Instanz an.

Fix: _on_autosave() schreibt bei current_file is None auf einen PID-
spezifischen Pfad (pysticky_autosave_<pid>.pxs). _check_autosave_recovery()
scannt ohne Argument (Programmstart) alle solchen Dateien im Temp-Ordner
(ausser der eigenen, gerade erst ermittelten PID-Datei) und bietet fuer
jede gefundene Datei einzeln Recovery an.

Diese Tests umgehen bewusst die globale autouse-Fixture
`_no_autosave_side_effects` (die _check_autosave_recovery normalerweise
zu einem No-Op macht), um das ECHTE Verhalten zu pruefen -- inklusive des
modalen QMessageBox.question, das dafuer gemockt wird. Der echte Temp-
Ordner wird durch tmp_path ersetzt (ueber pysticky.ui.handlers.
autosave_handlers.tempfile.gettempdir), damit Tests nicht in den
tatsaechlichen System-Temp-Ordner schreiben.
"""

import os

import pytest
from PySide6.QtWidgets import QMessageBox

from pysticky.ui.handlers import autosave_handlers
from pysticky.ui.handlers.autosave_handlers import AutosaveHandlersMixin

# Referenz auf die ECHTE Methode, eingesammelt beim Modul-Import -- also
# BEVOR die autouse-Fixture sie in irgendeinem Test durch ein No-Op ersetzt.
_REAL_CHECK_AUTOSAVE_RECOVERY = AutosaveHandlersMixin._check_autosave_recovery


@pytest.fixture
def isolated_temp_dir(monkeypatch, tmp_path):
    """Ersetzt tempfile.gettempdir() innerhalb des Autosave-Moduls durch
    tmp_path, damit Tests nicht den echten System-Temp-Ordner beruehren."""
    monkeypatch.setattr(autosave_handlers.tempfile, "gettempdir", lambda: str(tmp_path))
    return tmp_path


def _make_window(qtbot):
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    return w


@pytest.fixture
def main_window(qtbot):
    return _make_window(qtbot)


def test_on_autosave_never_saved_pattern_uses_pid_specific_path(
    main_window, isolated_temp_dir, monkeypatch
):
    """_on_autosave() muss bei current_file is None auf eine PID-
    spezifische Datei schreiben, nicht auf den alten globalen Namen."""
    monkeypatch.setattr(os, "getpid", lambda: 4242)

    assert main_window.current_file is None
    main_window._mark_unsaved()
    main_window._on_autosave()

    expected = isolated_temp_dir / "pysticky_autosave_4242.pxs"
    assert expected.exists()
    # Der alte, kollisionsanfaellige globale Name darf nicht mehr benutzt werden.
    assert not (isolated_temp_dir / "pysticky_autosave.pxs").exists()


def test_two_concurrent_never_saved_instances_do_not_collide(qtbot, isolated_temp_dir, monkeypatch):
    """Zwei "Instanzen" (simuliert durch zwei MainWindows mit unterschied-
    lichen os.getpid()-Werten) duerfen sich beim Autosave nicht gegenseitig
    ueberschreiben."""
    window_a = _make_window(qtbot)
    window_b = _make_window(qtbot)

    window_a.current_pattern.name = "Instanz A"
    window_b.current_pattern.name = "Instanz B"
    window_a._mark_unsaved()
    window_b._mark_unsaved()

    monkeypatch.setattr(os, "getpid", lambda: 1111)
    window_a._on_autosave()

    monkeypatch.setattr(os, "getpid", lambda: 2222)
    window_b._on_autosave()

    path_a = isolated_temp_dir / "pysticky_autosave_1111.pxs"
    path_b = isolated_temp_dir / "pysticky_autosave_2222.pxs"
    assert path_a.exists()
    assert path_b.exists()

    from pysticky.core import load_pattern

    assert load_pattern(str(path_a)).name == "Instanz A"
    assert load_pattern(str(path_b)).name == "Instanz B"


def test_check_autosave_recovery_finds_stale_file_from_crashed_instance(
    main_window, isolated_temp_dir, monkeypatch
):
    """Eine liegen gebliebene PID-Autosave einer abgestuerzten (fremden)
    Instanz muss beim Start gefunden und zur Wiederherstellung angeboten
    werden."""
    from pysticky.core import Pattern, save_pattern

    monkeypatch.setattr(
        AutosaveHandlersMixin, "_check_autosave_recovery", _REAL_CHECK_AUTOSAVE_RECOVERY
    )
    monkeypatch.setattr(os, "getpid", lambda: 9999)  # eigene, "frische" PID

    stale_path = isolated_temp_dir / "pysticky_autosave_1234.pxs"
    save_pattern(Pattern(name="Abgestuerzt", width=5, height=5), stale_path)

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)

    main_window._check_autosave_recovery()

    assert main_window.current_pattern.name == "Abgestuerzt"
    assert main_window._unsaved_changes is True
    # Nach der Entscheidung wird aufgeraeumt.
    assert not stale_path.exists()


def test_check_autosave_recovery_ignores_own_fresh_pid_file(
    main_window, isolated_temp_dir, monkeypatch
):
    """Eine Datei, die zufaellig genau auf dem eigenen (gerade erst
    ermittelten) PID-Pfad liegt, wird von der Recovery-Suche ausgenommen --
    ein frischer Prozess kann sie unmoeglich selbst geschrieben haben (das
    kann nur eine extrem seltene PID-Wiederverwendung sein). Sie wird also
    weder angeboten noch geloescht; eine echte fremde Datei mit dieser PID
    wird beim naechsten Start (mit garantiert anderer PID) gefunden."""
    from pysticky.core import Pattern, save_pattern

    monkeypatch.setattr(
        AutosaveHandlersMixin, "_check_autosave_recovery", _REAL_CHECK_AUTOSAVE_RECOVERY
    )
    monkeypatch.setattr(os, "getpid", lambda: 5555)

    own_path = isolated_temp_dir / "pysticky_autosave_5555.pxs"
    save_pattern(Pattern(name="EigenePidWiederverwendet", width=5, height=5), own_path)

    calls = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: calls.append(1))

    main_window._check_autosave_recovery()

    assert calls == []
    assert main_window.current_pattern.name != "EigenePidWiederverwendet"
    # Die ausgeschlossene Datei wird nicht anfasst (kein versehentliches Loeschen).
    assert own_path.exists()


def test_check_autosave_recovery_offers_each_stale_file_newest_wins(
    main_window, isolated_temp_dir, monkeypatch
):
    """Existieren mehrere Stale-Autosaves (mehrere abgestuerzte Instanzen),
    muss fuer JEDE einzeln Recovery angeboten werden. Werden mehrere mit
    "Ja" bestaetigt, soll am Ende der NEUESTE Stand geladen sein (nicht ein
    aelterer, der einen bereits geladenen neueren stillschweigend
    ueberschreibt)."""
    from pysticky.core import Pattern, save_pattern

    monkeypatch.setattr(
        AutosaveHandlersMixin, "_check_autosave_recovery", _REAL_CHECK_AUTOSAVE_RECOVERY
    )
    monkeypatch.setattr(os, "getpid", lambda: 7777)

    older_path = isolated_temp_dir / "pysticky_autosave_1001.pxs"
    newer_path = isolated_temp_dir / "pysticky_autosave_1002.pxs"
    save_pattern(Pattern(name="Aelter", width=5, height=5), older_path)
    save_pattern(Pattern(name="Neuer", width=5, height=5), newer_path)

    now = os.path.getmtime(older_path)
    os.utime(older_path, (now, now))
    os.utime(newer_path, (now + 10, now + 10))

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)

    main_window._check_autosave_recovery()

    assert main_window.current_pattern.name == "Neuer"
    assert not older_path.exists()
    assert not newer_path.exists()


def test_check_autosave_recovery_without_any_stale_file_does_not_prompt(
    main_window, isolated_temp_dir, monkeypatch
):
    """Ohne irgendeine pysticky_autosave_*.pxs-Datei darf kein Dialog
    erscheinen (Regressionsschutz gegen Stoerung des normalen Starts)."""
    monkeypatch.setattr(
        AutosaveHandlersMixin, "_check_autosave_recovery", _REAL_CHECK_AUTOSAVE_RECOVERY
    )
    monkeypatch.setattr(os, "getpid", lambda: 8888)

    calls = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: calls.append(1))

    main_window._check_autosave_recovery()

    assert calls == []
