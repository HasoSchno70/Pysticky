# -*- coding: utf-8 -*-
"""Regressionstest (2026-07-18): "Neu" legte ein Muster ganz ohne Farbe an
(color_entries.clear()). Zeichenwerkzeuge sind sofort aktiv und verwenden
Farbindex 0 -- seit dem Farbindex-Validierungs-Fix (siehe
test_stitch_placed_invalid_color_guard.py) wird ohne echte Farbe an Index 0
aber gar nichts mehr gezeichnet. Fix: _on_new() legt jetzt automatisch die
erste Farbe der konfigurierten Standard-Palette (bzw. bei DP-Mustern die
erste Diamond-Palette) ins neue Muster."""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def test_seed_first_color_uses_configured_default_palette(qtbot):
    from pysticky.core import Pattern
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    w._settings.setValue("default_palette", "DMC")

    pattern = Pattern(name="Test", width=10, height=10)
    pattern.color_entries.clear()
    w._seed_first_color(pattern, is_dp=False)

    assert len(pattern.color_entries) == 1
    assert pattern.color_entries[0].thread.manufacturer == "DMC"


def test_seed_first_color_dp_uses_diamond_palette(qtbot):
    from pysticky.core import Pattern
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    pattern = Pattern(name="Test", width=10, height=10)
    pattern.mode = "diamond"
    pattern.color_entries.clear()
    w._seed_first_color(pattern, is_dp=True)

    assert len(pattern.color_entries) == 1


def test_on_new_creates_pattern_with_drawable_color(qtbot, monkeypatch):
    """End-to-End: Nach 'Neu' muss sofort mit Werkzeugen gezeichnet werden
    können -- Farbindex 0 muss real existieren."""
    from pysticky.ui.dialogs.new_project_dialog import NewProjectDialog
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    monkeypatch.setattr(NewProjectDialog, "exec", lambda self: True)
    monkeypatch.setattr(
        NewProjectDialog,
        "get_settings",
        lambda self: {
            "width": 20,
            "height": 20,
            "fabric_count": 14,
            "dp_mode": False,
            "template_name": "",
        },
    )

    w._on_new()

    assert len(w.current_pattern.color_entries) == 1

    # Zeichnen mit dem Default-Farbindex (0) muss jetzt tatsaechlich einen
    # Stich setzen -- vorher (leeres Muster) wurde der Aufruf abgelehnt.
    w._on_stitch_placed(2, 2, 0)
    assert w.current_pattern.active_layer.get_stitch(2, 2) == 0
