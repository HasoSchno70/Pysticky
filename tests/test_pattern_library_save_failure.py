# -*- coding: utf-8 -*-
"""
Regressionstest (Silent-Exception-Audit): PatternLibraryDialog._save_library()
fing (OSError, ValueError) beim Schreiben von library.json ab und loggte den
Fehler nur (logger.error) -- der Dialog selbst zeigte NICHTS an. _save_library()
wird von 10+ Stellen aufgerufen (Favorit umschalten, Tags/Notizen aendern,
Eintrag entfernen/hinzufuegen, ...), keine davon prueft einen Rueckgabewert.

Schlaegt das Schreiben fehl (z.B. abgestecktes Netzlaufwerk, volle Platte),
wirkt die Aktion im laufenden Dialog trotzdem uebernommen (In-Memory-Zustand
aendert sich), geht aber beim naechsten Programmstart stillschweigend
verloren -- der Nutzer hat keinerlei Hinweis darauf, dass sein Favorit-Toggle/
Tag-Edit/etc. nie auf der Platte ankam.
"""

from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtWidgets import QMessageBox


def _qsettings_with_scope():
    app = QCoreApplication.instance()
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    return QSettings()


def _make_dialog(qtbot, tmp_path):
    from pysticky.ui.dialogs.pattern_library_dialog import PatternLibraryDialog

    s = _qsettings_with_scope()
    old = s.value("library_path")
    custom_dir = tmp_path / "bibliothek"
    s.setValue("library_path", str(custom_dir))
    dlg = PatternLibraryDialog()
    qtbot.addWidget(dlg)

    def _restore():
        if old is None:
            s.remove("library_path")
        else:
            s.setValue("library_path", old)

    return dlg, _restore


def test_save_library_failure_shows_warning(qtbot, tmp_path, monkeypatch):
    dlg, restore = _make_dialog(qtbot, tmp_path)
    try:
        warnings = []
        monkeypatch.setattr(
            QMessageBox,
            "warning",
            lambda *a, **kw: warnings.append((a, kw)),
        )

        def fail_open(*args, **kwargs):
            raise OSError("simulated: Netzlaufwerk nicht erreichbar")

        monkeypatch.setattr(
            "pysticky.ui.dialogs.pattern_library_dialog.open",
            fail_open,
            raising=False,
        )

        dlg._save_library()

        assert warnings, (
            "Ein fehlgeschlagenes Schreiben der library.json muss dem Nutzer "
            "gemeldet werden, nicht nur geloggt werden."
        )
    finally:
        restore()


def test_save_library_success_shows_no_warning(qtbot, tmp_path, monkeypatch):
    """Gegenprobe: der Normalfall (Schreiben klappt) darf keinen Dialog zeigen."""
    dlg, restore = _make_dialog(qtbot, tmp_path)
    try:
        warnings = []
        monkeypatch.setattr(
            QMessageBox,
            "warning",
            lambda *a, **kw: warnings.append((a, kw)),
        )

        dlg._save_library()

        assert not warnings
    finally:
        restore()
