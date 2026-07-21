# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 15): keines der acht Dock-Widgets bekam jemals
setObjectName() -- QMainWindow.saveState()/restoreState() identifiziert
Docks intern ausschliesslich ueber objectName(). Ohne eindeutige Namen
schlaegt restoreState() NICHT fehl (kein Fehler, kein Exception), sondern
stellt lautlos GAR NICHTS wieder her. Das betraf sowohl den "Dock-Layout
beim Start wiederherstellen"-Pfad (main_window.py) als auch
WorkspaceProfileManager (Runde 12) -- dessen ganze Existenzberechtigung
(Dock-Layouts speichern/laden) war dadurch faktisch nie wirksam.
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture
def main_window(qtbot):
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    return w


def test_every_dock_has_a_unique_nonempty_object_name(main_window):
    from PySide6.QtWidgets import QDockWidget

    docks = main_window.findChildren(QDockWidget)
    assert len(docks) >= 8

    names = [d.objectName() for d in docks]
    assert all(name for name in names), f"Dock ohne objectName gefunden: {names}"
    assert len(names) == len(set(names)), f"Doppelte Dock-Namen: {names}"


def test_dock_visibility_roundtrips_through_save_restore_state(main_window, qtbot):
    """Direkter Nachweis, dass saveState()/restoreState() jetzt tatsaechlich
    etwas bewirkt: ein Dock verstecken, State sichern, wieder einblenden,
    State restaurieren -- muss wieder versteckt sein."""
    w = main_window
    w.show()
    qtbot.waitExposed(w)
    from PySide6.QtWidgets import QDockWidget

    layer_dock = next(d for d in w.findChildren(QDockWidget) if d.widget() is w.layer_panel)

    layer_dock.setVisible(False)
    state = w.saveState()

    layer_dock.setVisible(True)
    assert layer_dock.isVisible() is True

    restored_ok = w.restoreState(state)
    assert restored_ok is True
    assert layer_dock.isVisible() is False
