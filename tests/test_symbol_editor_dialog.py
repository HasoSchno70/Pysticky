# -*- coding: utf-8 -*-
"""Regressionstests fuer SymbolEditorDialog.

Findet: der Editor liess zwei Farben dasselbe Symbol tragen (kein
Duplikat-Check), obwohl Pattern.add_color() diese Invariante beim
automatischen Zuweisen laengst durchsetzt. Zusaetzlich akzeptierte ein
reines Leerzeichen als "gueltiges" Custom-Symbol.
"""

from PySide6.QtWidgets import QMessageBox

from pysticky.core import Pattern, Thread
from pysticky.ui.dialogs.symbol_editor_dialog import SymbolEditorDialog


def _make_pattern_with_two_colors():
    pattern = Pattern(width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("A", "#111111"))
    pattern.add_color(Thread.from_hex("B", "#222222"))
    return pattern


def test_accept_rejects_symbol_already_used_by_another_color(qtbot, monkeypatch):
    pattern = _make_pattern_with_two_colors()
    other_symbol = pattern.color_entries[1].symbol
    original_symbol = pattern.color_entries[0].symbol
    assert other_symbol != original_symbol  # add_color() garantiert das

    dialog = SymbolEditorDialog(pattern, color_index=0)
    qtbot.addWidget(dialog)
    dialog._selected_symbol = other_symbol  # Duplikat mit Farbe 1

    warned = {}
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warned.setdefault("called", True))

    dialog._on_accept()

    assert warned.get("called") is True
    assert pattern.color_entries[0].symbol == original_symbol  # unveraendert


def test_accept_allows_symbol_not_used_elsewhere(qtbot):
    pattern = _make_pattern_with_two_colors()
    dialog = SymbolEditorDialog(pattern, color_index=0)
    qtbot.addWidget(dialog)
    dialog._selected_symbol = "Q"  # von keiner anderen Farbe belegt

    dialog._on_accept()

    assert pattern.color_entries[0].symbol == "Q"


def test_custom_symbol_rejects_whitespace_only_input(qtbot):
    pattern = _make_pattern_with_two_colors()
    dialog = SymbolEditorDialog(pattern, color_index=0)
    qtbot.addWidget(dialog)
    original = dialog._selected_symbol

    dialog._on_custom_symbol(" ")

    assert dialog._selected_symbol == original  # unveraendert, kein Leerzeichen uebernommen


def test_custom_symbol_accepts_normal_character(qtbot):
    pattern = _make_pattern_with_two_colors()
    dialog = SymbolEditorDialog(pattern, color_index=0)
    qtbot.addWidget(dialog)

    dialog._on_custom_symbol("Z")

    assert dialog._selected_symbol == "Z"
