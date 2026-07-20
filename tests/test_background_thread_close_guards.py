# -*- coding: utf-8 -*-
"""
Regressionstests: Fenster/Dialoge duerfen nicht schliessen, waehrend ein
Hintergrund-Thread noch laeuft -- sonst kann dessen spaeter feuerndes
finished/error-Signal auf ein bereits zerstoertes Objekt zugreifen (Qt
"QThread: Destroyed while thread is still running").

Der etablierte, bereits korrekte Fall ist `ImageImportDialog` (siehe
`ui/dialogs/image_import/dialog.py::reject`/`closeEvent`). Dieselbe Luecke
wurde bei einem Clean-Code-Nachaudit (2026-07-19) in `PatternImportDialog`
und `MainWindow` (laufender Export) gefunden und dort nachgezogen.
"""

import time

import pytest
from PySide6.QtCore import QThread


class _SleepingThread(QThread):
    """Simuliert einen laufenden Hintergrund-Job fuer die Guard-Tests."""

    def run(self) -> None:
        time.sleep(0.3)


@pytest.fixture
def main_window(qtbot):
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    # Siehe test_save_error_handling.py::main_window fuer die Begruendung.
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    return w


def test_main_window_close_blocked_while_export_running(qtbot, main_window):
    """closeEvent muss das Schliessen verhindern, solange _export_thread laeuft."""
    thread = _SleepingThread()
    main_window._export_thread = thread
    thread.start()
    qtbot.waitUntil(thread.isRunning, timeout=1000)

    try:
        # QWidget.close() liefert False zurueck, wenn closeEvent() das
        # Event mit ignore() abgelehnt hat -- das ist der eigentliche Beleg.
        assert main_window.close() is False
    finally:
        thread.wait(2000)


def test_main_window_close_allowed_after_export_finishes(qtbot, main_window):
    """Sobald der Export-Thread durch ist, darf das Fenster normal schliessen."""
    thread = _SleepingThread()
    main_window._export_thread = thread
    thread.start()
    qtbot.waitUntil(lambda: not thread.isRunning(), timeout=2000)

    assert main_window.close() is True


def test_pattern_import_dialog_reject_blocked_while_loading(qtbot):
    """reject() darf den Dialog nicht schliessen, waehrend _load_thread laeuft
    (Pendant zum bereits korrekten `ImageImportDialog._import_running()`-Guard)."""
    from pysticky.ui.dialogs.pattern_import_dialog import PatternImportDialog

    dialog = PatternImportDialog()
    qtbot.addWidget(dialog)
    dialog.show()

    thread = _SleepingThread()
    dialog._load_thread = thread
    thread.start()
    qtbot.waitUntil(thread.isRunning, timeout=1000)

    try:
        assert dialog._load_running() is True
        dialog.reject()
        # QDialog.result() ist per Default schon 0 == Rejected, auch OHNE
        # jeden reject()-Aufruf -- daher hier ueber Sichtbarkeit pruefen,
        # nicht ueber result(): ein durchgelassenes reject() wuerde den
        # Dialog schliessen/verstecken.
        assert dialog.isVisible() is True
    finally:
        thread.wait(2000)


def test_pattern_import_dialog_reject_allowed_after_loading_finishes(qtbot):
    """Nach Thread-Ende funktioniert reject() wieder normal."""
    from pysticky.ui.dialogs.pattern_import_dialog import PatternImportDialog

    dialog = PatternImportDialog()
    qtbot.addWidget(dialog)
    dialog.show()

    thread = _SleepingThread()
    dialog._load_thread = thread
    thread.start()
    qtbot.waitUntil(lambda: not thread.isRunning(), timeout=2000)

    assert dialog._load_running() is False
    dialog.reject()
    assert dialog.isVisible() is False
