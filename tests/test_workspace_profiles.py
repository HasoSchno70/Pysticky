# -*- coding: utf-8 -*-
"""Tests fuer WorkspaceProfileManager (core/../ui/workspace_profiles.py)."""

import pytest

from pysticky.ui.workspace_profiles import WorkspaceProfileManager

pytestmark = pytest.mark.usefixtures("qtbot")


def _qsettings_with_scope():
    from PySide6.QtCore import QCoreApplication, QSettings

    app = QCoreApplication.instance()
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    return QSettings()


def test_save_and_load_profile_roundtrip(qtbot):
    from PySide6.QtWidgets import QMainWindow

    s = _qsettings_with_scope()
    mgr = WorkspaceProfileManager(s)
    try:
        w1 = QMainWindow()
        qtbot.addWidget(w1)
        mgr.save_profile("test_profile", w1)

        assert mgr.has_profile("test_profile")
        assert "test_profile" in mgr.list_profiles()

        w2 = QMainWindow()
        qtbot.addWidget(w2)
        assert mgr.load_profile("test_profile", w2) is True
    finally:
        mgr.delete_profile("test_profile")


def test_save_and_load_profile_restores_real_dock_visibility(qtbot):
    """Staerkerer Nachweis als test_save_and_load_profile_roundtrip():
    dieser Test geht durch WorkspaceProfileManager's eigene API mit einem
    ECHTEN MainWindow (8 benannte Docks), nicht mit einem nackten
    QMainWindow ohne Docks. Runde 15 fixte den fehlenden setObjectName()
    auf jedem Dock -- ohne den Fix wuerde restoreState() intern lautlos
    nichts wiederherstellen (kein Fehler, einfach No-Op), und dieser Test
    wuerde das tatsaechlich auffangen (der alte roundtrip-Test mit
    docklosen QMainWindows haette das NICHT gekonnt, siehe Runde-17-
    Test-Suite-Audit)."""
    from PySide6.QtWidgets import QApplication, QDockWidget

    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    mgr = WorkspaceProfileManager(s)
    try:
        w1 = MainWindow()
        qtbot.addWidget(w1)
        w1._check_save_changes = lambda: True
        w1._autosave_timer.stop()
        w1.show()
        qtbot.waitExposed(w1)

        layer_dock = next(d for d in w1.findChildren(QDockWidget) if d.widget() is w1.layer_panel)
        layer_dock.setVisible(False)
        mgr.save_profile("real_dock_profile", w1)

        layer_dock.setVisible(True)
        assert layer_dock.isVisible() is True

        assert mgr.load_profile("real_dock_profile", w1) is True
        assert layer_dock.isVisible() is False
    finally:
        mgr.delete_profile("real_dock_profile")


def test_load_missing_profile_returns_false(qtbot):
    from PySide6.QtWidgets import QMainWindow

    s = _qsettings_with_scope()
    mgr = WorkspaceProfileManager(s)
    w = QMainWindow()
    qtbot.addWidget(w)
    assert mgr.load_profile("does_not_exist", w) is False


def test_load_profile_falls_back_when_saved_geometry_is_off_screen(qtbot):
    """Regression: load_profile() rief main_window.restoreGeometry(geometry)
    ohne jeden Rueckgabewert- oder Sichtbarkeits-Check auf -- dieselbe
    Bug-Klasse, die main_window.py::_setup_window schon in Runde 7 fuer
    den normalen Programmstart gefixt bekam (siehe
    test_general_settings_wiring.py::test_restore_window_falls_back_when_saved_geometry_is_off_screen),
    aber auf diesem strukturell aehnlichen Pfad (Workspace-Profile laden)
    uebersehen wurde. Ein Profil, das mit einem inzwischen abgesteckten
    zweiten Monitor gespeichert wurde, liess das Fenster beim Laden
    unerreichbar off-screen haengen."""
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QMainWindow

    s = _qsettings_with_scope()
    mgr = WorkspaceProfileManager(s)
    try:
        w1 = QMainWindow()
        qtbot.addWidget(w1)
        w1.move(500_000, 500_000)
        mgr.save_profile("offscreen_profile", w1)

        w2 = QMainWindow()
        qtbot.addWidget(w2)
        assert mgr.load_profile("offscreen_profile", w2) is True

        frame = w2.frameGeometry()
        assert any(
            screen.availableGeometry().intersects(frame) for screen in QGuiApplication.screens()
        )
    finally:
        mgr.delete_profile("offscreen_profile")
