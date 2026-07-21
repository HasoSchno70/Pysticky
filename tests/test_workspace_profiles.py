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
