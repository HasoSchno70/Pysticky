# -*- coding: utf-8 -*-
"""Regressionstests für den Allgemein-Settings-Tab (2026-07-18): 6 von 16
Einstellungen waren totes UI (autosave_backup, max_recent_files,
restore_window, confirm_exit, confirm_overwrite, status_timeout)."""

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox


def _qsettings_with_scope():
    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    return QSettings()


def test_status_timeout_applied_at_startup_and_live(qtbot):
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old = s.value("status_timeout")
    try:
        s.setValue("status_timeout", 9)
        w = MainWindow()
        qtbot.addWidget(w)
        assert w._status_timeout_ms == 9000

        s.setValue("status_timeout", 2)
        w._apply_settings_from_dialog()
        assert w._status_timeout_ms == 2000
    finally:
        if old is None:
            s.remove("status_timeout")
        else:
            s.setValue("status_timeout", old)


def test_max_recent_files_limits_list(qtbot, tmp_path):
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old = s.value("max_recent_files")
    old_recent = s.value("recent_files")
    try:
        s.setValue("max_recent_files", 2)
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()

        files = [tmp_path / f"p{i}.pxs" for i in range(4)]
        for f in files:
            f.write_text("{}", encoding="utf-8")

        for f in files:
            w._add_recent_file(str(f))

        assert len(w._recent_files) == 2
        # Zuletzt hinzugefuegt zuerst
        assert Path(w._recent_files[0]).name == "p3.pxs"
    finally:
        if old is None:
            s.remove("max_recent_files")
        else:
            s.setValue("max_recent_files", old)
        if old_recent is None:
            s.remove("recent_files")
        else:
            s.setValue("recent_files", old_recent)


def test_restore_window_disabled_ignores_saved_geometry(qtbot):
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old_restore = s.value("restore_window")
    old_geo = s.value("window/geometry")
    try:
        # Erstes Fenster erzeugt eine echte Geometrie zum Wiederherstellen.
        w1 = MainWindow()
        qtbot.addWidget(w1)
        w1._check_save_changes = lambda: True
        w1._autosave_timer.stop()
        w1.resize(999, 555)
        s.setValue("window/geometry", w1.saveGeometry())

        s.setValue("restore_window", False)
        w2 = MainWindow()
        qtbot.addWidget(w2)
        w2._check_save_changes = lambda: True
        w2._autosave_timer.stop()
        # Ohne Wiederherstellung darf die Testgroesse (999x555) nicht uebernommen sein.
        assert w2.size().width() != 999 or w2.size().height() != 555
    finally:
        if old_restore is None:
            s.remove("restore_window")
        else:
            s.setValue("restore_window", old_restore)
        if old_geo is None:
            s.remove("window/geometry")
        else:
            s.setValue("window/geometry", old_geo)


def test_restore_window_falls_back_when_saved_geometry_is_off_screen(qtbot):
    """Regression: restoreGeometry() kann erfolgreich sein, obwohl das
    Ergebnis auf keinem aktuell angeschlossenen Bildschirm mehr sichtbar
    ist (z.B. Geometrie von einem inzwischen abgesteckten zweiten Monitor).
    MainWindow muss in dem Fall auf die zentrierte Standard-Groesse
    zurueckfallen statt das Fenster unerreichbar off-screen zu lassen."""
    from PySide6.QtCore import QByteArray

    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old_restore = s.value("restore_window")
    old_geo = s.value("window/geometry")
    try:
        w1 = MainWindow()
        qtbot.addWidget(w1)
        w1._check_save_changes = lambda: True
        w1._autosave_timer.stop()
        # Weit ausserhalb jedes realistischen Bildschirms platzieren, dann
        # die Geometrie DORT speichern (saveGeometry() serialisiert die
        # aktuelle Fenster-Position/-Groesse).
        w1.move(500_000, 500_000)
        off_screen_geometry: QByteArray = w1.saveGeometry()

        s.setValue("restore_window", True)
        s.setValue("window/geometry", off_screen_geometry)

        w2 = MainWindow()
        qtbot.addWidget(w2)
        w2._check_save_changes = lambda: True
        w2._autosave_timer.stop()

        from PySide6.QtGui import QGuiApplication

        frame = w2.frameGeometry()
        assert any(
            screen.availableGeometry().intersects(frame) for screen in QGuiApplication.screens()
        )
    finally:
        if old_restore is None:
            s.remove("restore_window")
        else:
            s.setValue("restore_window", old_restore)
        if old_geo is None:
            s.remove("window/geometry")
        else:
            s.setValue("window/geometry", old_geo)


def test_autosave_backup_creates_bak_file(qtbot, tmp_path, monkeypatch):
    from pysticky.core import Pattern
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old = s.value("autosave_backup")
    old_recent = s.value("recent_files")
    try:
        s.setValue("autosave_backup", True)
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()

        target = tmp_path / "test.pxs"
        target.write_text('{"old": "content"}', encoding="utf-8")
        w.current_file = target
        w.current_pattern = Pattern(name="Test", width=5, height=5)
        w.current_pattern.color_entries.clear()

        w._on_save()

        backup = target.with_suffix(target.suffix + ".bak")
        assert backup.exists()
        assert backup.read_text(encoding="utf-8") == '{"old": "content"}'
    finally:
        if old is None:
            s.remove("autosave_backup")
        else:
            s.setValue("autosave_backup", old)
        if old_recent is None:
            s.remove("recent_files")
        else:
            s.setValue("recent_files", old_recent)


def test_confirm_exit_blocks_close_on_no(qtbot, monkeypatch):
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old = s.value("confirm_exit")
    try:
        s.setValue("confirm_exit", True)
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()
        monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)

        from PySide6.QtGui import QCloseEvent

        event = QCloseEvent()
        w.closeEvent(event)
        assert not event.isAccepted()
    finally:
        if old is None:
            s.remove("confirm_exit")
        else:
            s.setValue("confirm_exit", old)


def test_confirm_overwrite_blocks_save_as_on_no(qtbot, tmp_path, monkeypatch):
    from pysticky.core import Pattern
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old = s.value("confirm_overwrite")
    try:
        s.setValue("confirm_overwrite", True)
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()

        existing = tmp_path / "existing.pxs"
        existing.write_text('{"marker": "untouched"}', encoding="utf-8")

        from PySide6.QtWidgets import QFileDialog

        monkeypatch.setattr(
            QFileDialog, "getSaveFileName", lambda *a, **k: (str(existing), "PySticky (*.pxs)")
        )
        monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)

        w.current_pattern = Pattern(name="Test", width=5, height=5)
        w.current_pattern.color_entries.clear()
        w._on_save_as()

        # Bei "No" darf current_file nicht auf die existierende Datei
        # umgestellt worden sein -- der Save wurde abgebrochen.
        assert w.current_file != existing
        assert existing.read_text(encoding="utf-8") == '{"marker": "untouched"}'
    finally:
        if old is None:
            s.remove("confirm_overwrite")
        else:
            s.setValue("confirm_overwrite", old)
