# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 30): MiscHandlersMixin._on_show_shortcuts() (Hilfe ->
Tastenkuerzel) baute seine Tabelle aus einer zweiten, hart-codierten Liste
statt aus der lebenden ShortcutRegistry (ui/shortcuts_registry.py) -- genau
die "Zwei-Listen-Falle", die die Registry laut ihrem eigenen Modul-Docstring
fuer den Tastenkuerzel-Settings-Tab vermeidet. Nach einer Anpassung ueber
diesen Tab zeigte der Hilfe-Dialog trotzdem weiterhin den urspruenglichen
Default-Wert (z.B. "Speichern" -> "Ctrl+S"), obwohl der tatsaechlich aktive
Shortcut ein anderer war.
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def test_shortcuts_help_dialog_reflects_live_override(qtbot, monkeypatch):
    from PySide6.QtWidgets import QDialog, QTableWidget

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    # Shortcut ueber die Registry umbiegen -- simuliert, was der
    # Tastenkuerzel-Settings-Tab beim Speichern tut.
    w._shortcut_registry.set_shortcut("action_save", "Ctrl+Shift+S")

    captured = {}

    def fake_exec(self):
        captured["dialog"] = self
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", fake_exec)

    w._on_show_shortcuts()

    dialog = captured.get("dialog")
    assert dialog is not None
    table = dialog.findChild(QTableWidget)
    assert table is not None

    rows = {table.item(r, 0).text(): table.item(r, 1).text() for r in range(table.rowCount())}
    save_label = w._shortcut_registry.label("action_save")
    actual = rows.get(save_label)
    assert actual == "Ctrl+Shift+S", f"Hilfe-Dialog zeigt veralteten Shortcut: {actual!r}"
