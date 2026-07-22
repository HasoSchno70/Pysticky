# -*- coding: utf-8 -*-
"""
Regressionstests (Runde 23) fuer zwei Bugs in view_handlers.py:

1. _on_toggle_stitch_mode() verglich dock.windowTitle() gegen den rohen
   deutschen Literal "Fortschritt" statt t("Fortschritt") -- in jeder
   Nicht-Deutsch-Sprache (z.B. Englisch: "Progress") versteckte sich dadurch
   auch das Fortschritts-Dock selbst beim Aktivieren des Sticken-Modus,
   genau das Gegenteil des beabsichtigten Verhaltens.
2. _on_snap_grid_changed() setzte canvas.snap_interval unbedingt auf
   canvas.minor_grid_interval -- zwei unabhaengige Einstellungen, das hat
   das vom Nutzer konfigurierte Snap-Intervall bei jedem Umschalten der
   Checkbox stillschweigend ueberschrieben.
"""

import pytest

from pysticky.core.i18n import set_language


@pytest.fixture
def english_language():
    set_language("en")
    try:
        yield
    finally:
        set_language("de")


def test_stitch_mode_keeps_progress_dock_visible_in_english_locale(qtbot, english_language):
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    w.show()
    qtbot.waitExposed(w)

    w.action_stitch_mode.trigger()

    assert w.progress_dock.isVisible() is True


def test_stitch_mode_hides_other_docks_in_english_locale(qtbot, english_language):
    from PySide6.QtWidgets import QDockWidget

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    w.show()
    qtbot.waitExposed(w)

    w.action_stitch_mode.trigger()

    for dock in w.findChildren(QDockWidget):
        if dock is not w.progress_dock:
            assert dock.isVisible() is False, f"{dock.windowTitle()} sollte versteckt sein"


def test_snap_grid_toggle_preserves_configured_snap_interval(qtbot):
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    w.canvas.minor_grid_interval = 5
    w.canvas.snap_interval = 10

    w._on_snap_grid_changed(True)
    assert w.canvas.snap_interval == 10

    w._on_snap_grid_changed(False)
    assert w.canvas.snap_interval == 10


def test_leaving_stitch_mode_restores_completion_checkbox(qtbot):
    """Runde 30: _on_toggle_stitch_mode() setzte beim Aktivieren
    action_show_completion unbedingt auf True (Completion-Overlay soll im
    Sticken-Modus sichtbar sein), stellte den gespeicherten Wert beim
    Verlassen aber nur auf canvas._show_completion zurueck -- die Checkbox
    selbst blieb dauerhaft angehakt, obwohl "Fortschritt anzeigen" vorher
    aus war. Checkbox-Anzeige und tatsaechlicher Overlay-Zustand liefen
    dadurch auseinander."""
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    # Vorbedingung: "Fortschritt anzeigen" ist AUS.
    w.canvas._show_completion = False
    w.action_show_completion.setChecked(False)

    w._on_toggle_stitch_mode(True)
    assert w.action_show_completion.isChecked() is True

    w._on_toggle_stitch_mode(False)
    assert w.canvas._show_completion is False
    assert w.action_show_completion.isChecked() is False
