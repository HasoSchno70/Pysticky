# -*- coding: utf-8 -*-
"""Regressionstests fuer die "Zuletzt geoeffnet"-Liste (Runde 49, 2026-07-23).

Kontext: MainWindow._recent_files und der WelcomeWidget-Snapshot koennen
auseinanderlaufen (WelcomeWidget.set_recent_files() bekommt eine reine
Werte-Kopie via list(files), keine Live-Referenz -- siehe
ui/widgets/welcome_widget.py). Wird spaeter self._recent_files getrimmt
(max_recent_files-Obergrenze) oder ein Eintrag entfernt, kann ein
Klick auf einen im WelcomeWidget noch sichtbaren, aber aus
MainWindow._recent_files bereits verschwundenen Eintrag zusaetzlich auf
eine mittlerweile geloeschte Datei zeigen. _open_recent_file() rief in
diesem Fall self._recent_files.remove(path) ungeschuetzt auf und crashte
mit einem unbehandelten ValueError, statt den Fehlerdialog anzuzeigen und
sauber zurueckzukehren.
"""

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox


def _qsettings_with_scope():
    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    return QSettings()


def test_open_recent_missing_file_not_in_list_does_not_crash(qtbot, tmp_path, monkeypatch):
    """Regression: ein Klick auf eine fehlende Datei, deren Pfad NICHT
    (mehr) in self._recent_files steht (z.B. weil ein stale WelcomeWidget-
    Snapshot einen inzwischen per max_recent_files verdraengten Eintrag noch
    anzeigt), darf keinen unbehandelten ValueError werfen."""
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old_recent = s.value("recent_files")
    try:
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()

        target = tmp_path / "ghost.pxs"
        target.write_text("{}", encoding="utf-8")
        stale_path = str(target)

        # Datei existiert nicht mehr UND der Pfad ist nicht (mehr) Teil der
        # aktuellen Liste -- genau die Kombination, die vorher crashte.
        target.unlink()
        w._recent_files = ["C:/some/other/file.pxs"]
        assert stale_path not in w._recent_files

        warnings = []
        monkeypatch.setattr(
            QMessageBox,
            "warning",
            lambda *a, **k: warnings.append(a) or QMessageBox.StandardButton.Ok,
        )

        # Darf nicht raisen.
        w._open_recent_file(stale_path)

        assert len(warnings) == 1
        # Die (unveraenderte) Liste bleibt wie sie war -- der Fremdeintrag
        # wurde nicht faelschlich entfernt.
        assert w._recent_files == ["C:/some/other/file.pxs"]
    finally:
        if old_recent is None:
            s.remove("recent_files")
        else:
            s.setValue("recent_files", old_recent)


def test_open_recent_missing_file_in_list_is_pruned(qtbot, tmp_path, monkeypatch):
    """Normalfall (unveraendert): eine fehlende Datei, deren Pfad noch in
    self._recent_files steht, wird nach dem Warnhinweis aus der Liste
    entfernt."""
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old_recent = s.value("recent_files")
    try:
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()

        target = tmp_path / "ghost2.pxs"
        target.write_text("{}", encoding="utf-8")
        w._add_recent_file(str(target))
        stored_path = w._recent_files[0]

        target.unlink()

        warnings = []
        monkeypatch.setattr(
            QMessageBox,
            "warning",
            lambda *a, **k: warnings.append(a) or QMessageBox.StandardButton.Ok,
        )

        w._open_recent_file(stored_path)

        assert len(warnings) == 1
        assert stored_path not in w._recent_files
    finally:
        if old_recent is None:
            s.remove("recent_files")
        else:
            s.setValue("recent_files", old_recent)


def test_add_recent_file_moves_duplicate_to_front(qtbot, tmp_path):
    """Dieselbe Datei erneut oeffnen darf keinen zweiten Eintrag erzeugen,
    sondern muss den bestehenden Eintrag an die Spitze verschieben."""
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old_recent = s.value("recent_files")
    try:
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()
        w._recent_files = []

        f_a = tmp_path / "a.pxs"
        f_b = tmp_path / "b.pxs"
        f_a.write_text("{}", encoding="utf-8")
        f_b.write_text("{}", encoding="utf-8")

        w._add_recent_file(str(f_a))
        w._add_recent_file(str(f_b))
        w._add_recent_file(str(f_a))  # a erneut oeffnen

        assert len(w._recent_files) == 2
        assert Path(w._recent_files[0]).name == "a.pxs"
        assert Path(w._recent_files[1]).name == "b.pxs"
    finally:
        if old_recent is None:
            s.remove("recent_files")
        else:
            s.setValue("recent_files", old_recent)


def test_add_recent_file_roundtrips_unicode_path(qtbot, tmp_path):
    """Umlaute/Sonderzeichen im Dateinamen ueberleben einen
    QSettings-Save/Load-Zyklus unveraendert."""
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old_recent = s.value("recent_files")
    try:
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()
        w._recent_files = []

        target = tmp_path / "Muster_äöü_日本語.pxs"
        target.write_text("{}", encoding="utf-8")
        w._add_recent_file(str(target))

        reloaded = w._load_recent_files()
        assert any(Path(p).name == target.name for p in reloaded)
    finally:
        if old_recent is None:
            s.remove("recent_files")
        else:
            s.setValue("recent_files", old_recent)
