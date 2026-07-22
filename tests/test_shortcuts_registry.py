# -*- coding: utf-8 -*-
"""
Tests für die Tastenkürzel-Registry (ui/shortcuts_registry.py) und deren
Verdrahtung in MainWindow/ShortcutsTab.

Vorher tat der Tastenkürzel-Settings-Tab buchstäblich nichts -- er
speicherte eine eigene, nirgends gelesene DEFAULT_SHORTCUTS-Liste.
Diese Tests stellen sicher, dass Bearbeitungen jetzt wirklich auf die
lebenden QAction/ToolButton-Objekte durchschlagen.
"""

import pytest
from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtGui import QAction

from pysticky.ui.shortcuts_registry import ShortcutRegistry, apply_saved_overrides

pytestmark = pytest.mark.usefixtures("qtbot")


def _qsettings_with_scope() -> QSettings:
    """QSettings() braucht Org/App-Name auf der QCoreApplication, sonst
    landen setValue()-Aufrufe im Leeren (siehe test_tablet_pressure.py)."""
    app = QCoreApplication.instance()
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    return QSettings()


@pytest.fixture
def registry():
    reg = ShortcutRegistry()
    a = QAction("Neu")
    a.setShortcut("Ctrl+N")
    b = QAction("Öffnen")
    b.setShortcut("Ctrl+O")
    reg.register("action_new", a, "Neu")
    reg.register("action_open", b, "Öffnen")
    return reg


def test_register_captures_current_shortcut_as_default(registry):
    assert registry.default("action_new") == "Ctrl+N"
    assert registry.current("action_new") == "Ctrl+N"


def test_set_shortcut_updates_live_target(registry):
    registry.set_shortcut("action_new", "Ctrl+Shift+N")
    assert registry.current("action_new") == "Ctrl+Shift+N"
    # Der Default bleibt der urspruengliche Wert (fuer Reset).
    assert registry.default("action_new") == "Ctrl+N"


def test_reset_all_restores_captured_defaults(registry):
    registry.set_shortcut("action_new", "Ctrl+Shift+N")
    registry.set_shortcut("action_open", "Ctrl+Shift+O")
    registry.reset_all()
    assert registry.current("action_new") == "Ctrl+N"
    assert registry.current("action_open") == "Ctrl+O"


def test_find_conflict_detects_duplicate_shortcut(registry):
    # Ctrl+O ist schon von action_open belegt.
    assert registry.find_conflict("Ctrl+O") == "action_open"
    # Aber nicht, wenn action_open selbst ausgeschlossen wird.
    assert registry.find_conflict("Ctrl+O", exclude_id="action_open") is None
    # Ein freier Shortcut hat keinen Konflikt.
    assert registry.find_conflict("Ctrl+Alt+Z") is None


def test_all_current_returns_full_snapshot(registry):
    assert registry.all_current() == {"action_new": "Ctrl+N", "action_open": "Ctrl+O"}


def test_apply_saved_overrides_updates_targets(registry):
    settings = _qsettings_with_scope()
    settings.setValue("shortcuts", {"action_new": "Ctrl+Alt+N"})
    apply_saved_overrides(registry, settings)
    assert registry.current("action_new") == "Ctrl+Alt+N"
    # Keine Override fuer action_open -> unveraendert.
    assert registry.current("action_open") == "Ctrl+O"


def test_apply_saved_overrides_ignores_non_dict_value(registry):
    """Robust gegen kaputte/manuell editierte QSettings-Werte."""
    settings = _qsettings_with_scope()
    settings.setValue("shortcuts", "not a dict")
    apply_saved_overrides(registry, settings)  # darf nicht crashen
    assert registry.current("action_new") == "Ctrl+N"


def test_mainwindow_registers_shortcut_targets_without_duplicates(qtbot):
    """End-to-End: MainWindow baut eine Registry ohne doppelt vergebene
    Tastenkuerzel -- genau die Bug-Klasse, die schon zweimal manuell
    gefunden wurde (Ctrl+Shift+I, Ctrl+H), soll hier automatisch auffallen."""
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)

    reg = w._shortcut_registry
    assert len(reg.ids()) > 40  # ~39 Actions + 14 Tools, grosszuegige Untergrenze

    seen: dict[str, str] = {}
    duplicates = []
    for shortcut_id in reg.ids():
        shortcut = reg.current(shortcut_id)
        if not shortcut:
            continue
        if shortcut in seen:
            duplicates.append((shortcut, seen[shortcut], shortcut_id))
        else:
            seen[shortcut] = shortcut_id
    assert duplicates == [], f"Doppelt vergebene Tastenkuerzel gefunden: {duplicates}"

    # Stichprobe: ein bekannter Shortcut ist wie erwartet registriert.
    assert reg.current("action_replace_color") == "Ctrl+R"
    assert reg.current("tool_fill") == "F"


def test_action_exit_shortcut_is_actually_ctrl_q(qtbot):
    """Regression (Runde 23): action_exit nutzte QKeySequence.StandardKey.Quit,
    das sich auf diesem Windows/Qt-Build zur seltenen Multimedia-Taste "Exit"
    aufloest (verifiziert per QKeySequence(...).toString()), NICHT zu Ctrl+Q --
    obwohl die eigene Tooltip seit jeher "Beenden (Ctrl+Q)" verspricht. Ctrl+Q
    tat dadurch schlicht nichts. Jetzt explizit gesetzt."""
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)

    assert w.action_exit.shortcut().toString() == "Ctrl+Q"


def test_mainwindow_shortcut_edit_applies_live(qtbot):
    """Simuliert, was ShortcutsTab.save_settings() tut: Pending-Edit auf
    die Registry anwenden -- muss die echte QAction live umbiegen."""
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)

    reg = w._shortcut_registry
    reg.set_shortcut("action_replace_color", "Ctrl+Shift+R")
    assert w.action_replace_color.shortcut().toString() == "Ctrl+Shift+R"
