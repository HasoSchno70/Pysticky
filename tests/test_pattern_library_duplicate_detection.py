# -*- coding: utf-8 -*-
"""Regressionstest (Runde 80): PatternLibraryDialog._add_pattern_file() prüfte
auf bereits vorhandene Einträge per rohem String-Vergleich (`entry.filepath ==
str(filepath)`), OHNE den Pfad zu normalisieren -- anders als das etablierte
Muster in project_list.py::add() und misc_handlers.py::_add_recent_file(),
die beide bewusst per Path(...).resolve() normalisieren, "damit derselbe Pfad
relativ vs. absolut, oder mit '../'-Segmenten, nicht als zwei unterschiedliche
Einträge geführt wird" (Zitat project_list.py).

Ohne Normalisierung landet dieselbe Muster-Datei zweimal in der Bibliothek,
sobald sie über zwei syntaktisch verschiedene, aber auf dieselbe Datei
zeigende Pfade hinzugefügt wird -- z.B. weil ein Verzeichnis-Scan über eine
andere Route (Junction, "../"-Segment, %TEMP%-Kurzname vs. Langname) läuft
als der ursprüngliche Direkt-Import.
"""

from PySide6.QtCore import QCoreApplication, QSettings


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


def test_add_pattern_file_detects_duplicate_via_dotdot_path(qtbot, tmp_path):
    """Dieselbe Datei über zwei syntaktisch verschiedene Pfade (direkt vs.
    über ein '../'-Segment umgeleitet) hinzufügen darf nur EINEN Eintrag
    erzeugen."""
    from pysticky.core import Pattern
    from pysticky.core.file_io import save_pattern

    dlg, restore = _make_dialog(qtbot, tmp_path)
    try:
        muster_dir = tmp_path / "muster"
        muster_dir.mkdir()
        pattern_file = muster_dir / "rose.pxs"
        save_pattern(Pattern(name="Rose", width=5, height=5), pattern_file)

        # Zweiter Pfad zeigt via "../"-Segment auf DIESELBE Datei, ist aber
        # als String unterschiedlich.
        other_route = tmp_path / "andere_route" / ".." / "muster" / "rose.pxs"
        assert str(pattern_file) != str(other_route)
        assert pattern_file.resolve() == other_route.resolve()

        added_first = dlg._add_pattern_file(pattern_file)
        added_second = dlg._add_pattern_file(other_route)

        assert added_first is True
        assert added_second is False, (
            "Zweiter Pfad zeigt auf dieselbe Datei -- darf nicht als neuer, "
            "doppelter Eintrag erkannt werden."
        )
        assert len(dlg._library.entries) == 1
    finally:
        restore()


def test_add_pattern_file_still_detects_exact_duplicate(qtbot, tmp_path):
    """Basisfall (identischer Pfad-String zweimal) muss weiterhin erkannt
    werden -- keine Regression durch die Normalisierung."""
    from pysticky.core import Pattern
    from pysticky.core.file_io import save_pattern

    dlg, restore = _make_dialog(qtbot, tmp_path)
    try:
        muster_dir = tmp_path / "muster"
        muster_dir.mkdir()
        pattern_file = muster_dir / "tulpe.pxs"
        save_pattern(Pattern(name="Tulpe", width=5, height=5), pattern_file)

        added_first = dlg._add_pattern_file(pattern_file)
        added_second = dlg._add_pattern_file(pattern_file)

        assert added_first is True
        assert added_second is False
        assert len(dlg._library.entries) == 1
    finally:
        restore()
