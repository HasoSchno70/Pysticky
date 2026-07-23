# -*- coding: utf-8 -*-
"""
Regressionstests: StitchPathDialog (Stickpfad-Optimierung) durfte den
sichtbaren "Schliessen"-Button (verbunden mit accept()) und Escape
(loest reject() aus) benutzen, OHNE dass eine laufende Hintergrund-
Optimierung abgebrochen wurde -- die Abbruch/Cleanup-Logik hing
ausschliesslich in closeEvent(), das QDialog::done() (von accept()/
reject() intern genutzt) aber NIEMALS aufruft (done() ruft nur hide()
auf, nicht close()). Ein Klick auf "Schliessen" oder Escape liess die
Optimierung dadurch unbeaufsichtigt im Hintergrund weiterlaufen.

Zusaetzlich: _cleanup_worker() setzte self._worker/self._thread auch
dann auf None, wenn der Thread nach dem 1s-Timeout in wait(1000) immer
noch lief (z.B. bei grossen Mustern mit NEAREST_NEIGHBOR-Strategie,
deren innere Optimierungsschleife den Abbruch-Flag nur ZWISCHEN Farben
prueft) -- das entfernt die letzte Python-Referenz auf ein
QThread-Objekt ohne Qt-Parent WAEHREND es noch laeuft (Qt:
"QThread: Destroyed while thread is still running").
"""

from unittest.mock import MagicMock

import pytest

from pysticky.core import Pattern
from pysticky.ui.dialogs.stitch_path_dialog import StitchPathDialog


@pytest.fixture
def dialog(qtbot):
    pattern = Pattern(name="Test", width=5, height=5)
    dlg = StitchPathDialog(pattern)
    qtbot.addWidget(dlg)
    return dlg


class _FakeThread:
    """Stub fuer self._thread -- steuert isRunning()/wait() deterministisch,
    ohne einen echten QThread starten zu muessen."""

    def __init__(self, running: bool, wait_succeeds: bool) -> None:
        self._running = running
        self._wait_succeeds = wait_succeeds
        self.quit_called = False

    def isRunning(self) -> bool:
        return self._running

    def quit(self) -> None:
        self.quit_called = True

    def wait(self, _timeout_ms: int) -> bool:
        if self._wait_succeeds:
            self._running = False
        return self._wait_succeeds


def test_accept_cancels_running_worker(dialog):
    """Der 'Schliessen'-Button ruft accept() auf -- das muss den Worker
    abbrechen, statt ihn unbeaufsichtigt weiterlaufen zu lassen."""
    worker = MagicMock()
    dialog._worker = worker
    dialog._thread = _FakeThread(running=False, wait_succeeds=True)

    dialog.accept()

    worker.cancel.assert_called_once()


def test_reject_cancels_running_worker(dialog):
    """Escape ruft reject() auf -- muss denselben Abbruch ausloesen wie
    das Schliessen ueber den Fenster-X-Button (closeEvent)."""
    worker = MagicMock()
    dialog._worker = worker
    dialog._thread = _FakeThread(running=False, wait_succeeds=True)

    dialog.reject()

    worker.cancel.assert_called_once()


def test_cleanup_worker_keeps_reference_while_thread_still_running(dialog):
    """wait(1000)-Timeout (Thread laeuft noch): _worker/_thread duerfen NICHT
    auf None gesetzt werden -- sonst wird das letzte Python-Referenz auf ein
    parentloses, noch laufendes QThread-Objekt fallengelassen (Crash-Risiko)."""
    worker = MagicMock()
    thread = _FakeThread(running=True, wait_succeeds=False)
    dialog._worker = worker
    dialog._thread = thread

    dialog._cleanup_worker()

    assert thread.quit_called is True
    assert dialog._thread is thread
    assert dialog._worker is worker


def test_cleanup_worker_clears_reference_once_thread_finishes(dialog):
    """Normalfall (Thread stoppt rechtzeitig): Referenzen werden wie bisher
    auf None gesetzt."""
    worker = MagicMock()
    thread = _FakeThread(running=True, wait_succeeds=True)
    dialog._worker = worker
    dialog._thread = thread

    dialog._cleanup_worker()

    assert dialog._thread is None
    assert dialog._worker is None
