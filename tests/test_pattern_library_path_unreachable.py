# -*- coding: utf-8 -*-
"""Regressionstest (Runde 27): PatternLibraryDialog._get_library_path() rief
mkdir() auf dem in Einstellungen -> Dateien -> "Bibliothek" konfigurierten
Ordner OHNE try/except auf -- ein nicht mehr erreichbarer Ordner
(abgestecktes Netzlaufwerk/USB-Stick, entfernte Berechtigung) liess
"Datei -> Muster-Bibliothek" mit einem rohen OSError abstuerzen, statt auf
den Standard-Ordner zurueckzufallen.

Nutzt dasselbe QSettings-Isolationsmuster wie test_pattern_library_dialog_notes.py
(library_path auf tmp_path umbiegen), damit kein Test die echte Bibliothek des
Nutzers beruehrt."""

from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QSettings

pytestmark = pytest.mark.usefixtures("qtbot")


def _qsettings_with_scope():
    app = QCoreApplication.instance()
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    return QSettings()


def test_get_library_path_falls_back_when_configured_dir_unreachable(qtbot, tmp_path, monkeypatch):
    from pysticky.ui.dialogs.pattern_library_dialog import PatternLibraryDialog

    unreachable = tmp_path / "unreachable"

    s = _qsettings_with_scope()
    old = s.value("library_path")
    s.setValue("library_path", str(unreachable))

    orig_mkdir = Path.mkdir

    def fake_mkdir(self, *args, **kwargs):
        if self == unreachable:
            raise PermissionError("simulated: unreachable")
        return orig_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    try:
        dlg = PatternLibraryDialog()
        qtbot.addWidget(dlg)

        assert dlg._library_path.parent != unreachable
        assert dlg._library_path.parent.exists()
    finally:
        if old is None:
            s.remove("library_path")
        else:
            s.setValue("library_path", old)
