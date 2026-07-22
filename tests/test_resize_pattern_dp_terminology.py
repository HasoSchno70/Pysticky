# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 23): edit_handlers.py::_on_resize_pattern() zeigte
hart-codiert "Stiche" als Spinbox-Suffix und im Verkleinerungs-Warnhinweis,
auch fuer Diamond-Painting-Muster -- anders als file_handlers.py::_on_new(),
das bereits modus-abhaengig zwischen "Drills"/"Stiche" unterscheidet.
"""

from PySide6.QtWidgets import QDialog, QSpinBox

from pysticky.core import Pattern


def _capture_spinbox_suffixes(main_window, monkeypatch):
    captured = {}

    def fake_exec(self):
        spins = self.findChildren(QSpinBox)
        captured["suffixes"] = [s.suffix() for s in spins]
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", fake_exec)
    main_window._on_resize_pattern()
    return captured


def test_resize_dialog_shows_drills_suffix_for_diamond_pattern(qtbot, monkeypatch):
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    dp_pattern = Pattern(width=10, height=10, mode="diamond", fabric_count=10)
    w.set_pattern(dp_pattern)

    captured = _capture_spinbox_suffixes(w, monkeypatch)

    assert captured["suffixes"], "Keine Spinboxen im Dialog gefunden"
    for suffix in captured["suffixes"]:
        assert "Drills" in suffix
        assert "Stiche" not in suffix


def test_resize_dialog_shows_stiche_suffix_for_cross_stitch_pattern(qtbot, monkeypatch):
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    pattern = Pattern(width=10, height=10)
    w.set_pattern(pattern)

    captured = _capture_spinbox_suffixes(w, monkeypatch)

    assert captured["suffixes"], "Keine Spinboxen im Dialog gefunden"
    for suffix in captured["suffixes"]:
        assert "Stiche" in suffix
