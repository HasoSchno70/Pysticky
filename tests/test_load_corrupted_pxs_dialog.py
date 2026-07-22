# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 23): file_handlers.py::_load_pattern_file() hatte
ein `except json.JSONDecodeError` fuer die "Ungültige Datei"-Meldung --
totes Code, da core/file_io.py::load_pattern() JSONDecodeError intern
faengt und als ValueError weiterwirft. Eine beschaedigte .pxs-Datei fiel
dadurch immer in den generischen `except Exception`-Handler ("Fehler"
statt der spezifischeren "Ungültige Datei"-Meldung).
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


def test_corrupted_pxs_file_shows_invalid_file_dialog(main_window, tmp_path):
    bad_file = tmp_path / "kaputt.pxs"
    bad_file.write_text("das ist kein gueltiges JSON {{{", encoding="utf-8")

    with patch("pysticky.ui.handlers.file_handlers.QMessageBox.critical") as mock_critical:
        result = main_window._load_pattern_file(bad_file)

        assert result is False
        assert mock_critical.called
        title = mock_critical.call_args[0][1]
        assert title == "Ungültige Datei"
