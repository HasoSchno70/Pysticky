# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 23): file_handlers.py::_on_pattern_library()'s
open_from_library() zeigte bei einem KOMPLETT fehlgeschlagenen Import
(pattern is None) nur den falsch beschrifteten "Import-Warnungen"-Dialog
(oder gar keinen, falls errors leer war) und tat danach still gar nichts
mehr -- anders als der strukturell identische Geschwister-Pfad
_load_external_pattern_file() weiter oben in derselben Datei, der korrekt
zwischen "Import fehlgeschlagen" (critical) und "Import-Warnungen"
(warning, nur bei Teilerfolg) unterscheidet.
"""

from unittest.mock import patch

import pytest


@pytest.fixture
def main_window(qtbot):
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    return w


def _trigger_library_open(main_window, monkeypatch, filepath: str):
    """Simuliert die Dialog-Auswahl ohne den modalen exec() zu blockieren."""
    from pysticky.ui.dialogs import PatternLibraryDialog

    def fake_exec(self):
        self.pattern_selected.emit(filepath)
        return 0

    monkeypatch.setattr(PatternLibraryDialog, "exec", fake_exec)
    main_window._on_pattern_library()


def test_total_import_failure_shows_critical_dialog(main_window, monkeypatch, tmp_path):
    bad_file = tmp_path / "kaputt.xsd"
    bad_file.write_bytes(b"das ist keine gueltige XSD-Datei")

    with (
        patch("pysticky.ui.handlers.file_handlers.QMessageBox.critical") as mock_critical,
        patch("pysticky.ui.handlers.file_handlers.QMessageBox.warning") as mock_warning,
    ):
        _trigger_library_open(main_window, monkeypatch, str(bad_file))

        assert mock_critical.called, (
            "Ein komplett fehlgeschlagener Import muss als 'Import fehlgeschlagen' "
            "(critical) gemeldet werden, nicht nur als Warnung oder gar nicht."
        )
        title = mock_critical.call_args[0][1]
        assert title == "Import fehlgeschlagen"
        # Bei totalem Fehlschlag darf KEIN Pattern geladen worden sein.
        assert not mock_warning.called or "warnings" not in str(mock_warning.call_args)


def test_total_import_failure_does_not_replace_current_pattern(main_window, monkeypatch, tmp_path):
    bad_file = tmp_path / "kaputt.xsd"
    bad_file.write_bytes(b"das ist keine gueltige XSD-Datei")
    original_pattern = main_window.current_pattern

    with patch("pysticky.ui.handlers.file_handlers.QMessageBox.critical"):
        _trigger_library_open(main_window, monkeypatch, str(bad_file))

    assert main_window.current_pattern is original_pattern
