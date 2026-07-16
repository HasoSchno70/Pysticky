# -*- coding: utf-8 -*-
"""Tests für den ausgebauten Farbe-ersetzen-Dialog."""

import pytest

from pysticky.core import Pattern, Thread


@pytest.fixture
def dialog_pattern():
    """Wie in test_color_reduce: Rot(50), Dunkelrot(2), Blau(40), Hellblau(1), Grün(0)."""
    pattern = Pattern(name="DialogTest", width=20, height=20)
    pattern.color_entries.clear()
    for name, hex_color in [
        ("Rot", "#FF0000"),
        ("Dunkelrot", "#CC0000"),
        ("Blau", "#0000FF"),
        ("Hellblau", "#2020FF"),
        ("Grün", "#00FF00"),
    ]:
        pattern.add_color(Thread.from_hex(name, hex_color))

    counts = {0: 50, 1: 2, 2: 40, 3: 1}
    x = y = 0
    for idx, n in counts.items():
        for _ in range(n):
            pattern.set_stitch(x, y, idx)
            x += 1
            if x >= 20:
                x = 0
                y += 1
    return pattern


@pytest.fixture
def dialog(qtbot, dialog_pattern):
    from pysticky.ui.dialogs.replace_color_dialog import ReplaceColorDialog

    dlg = ReplaceColorDialog(dialog_pattern, current_color_index=0)
    qtbot.addWidget(dlg)
    return dlg


def test_suggestions_sorted_and_exclude_source(dialog):
    buttons = dialog._suggestion_buttons.buttons()
    assert buttons, "Vorschlags-Kacheln müssen existieren"

    ids = [dialog._suggestion_buttons.id(b) for b in buttons]
    assert 0 not in ids, "Quellfarbe darf nicht vorgeschlagen werden"
    assert ids[0] == 1, "Ähnlichste Farbe (Dunkelrot) muss zuerst stehen"


def test_suggestion_click_sets_target(dialog):
    btn = dialog._suggestion_buttons.buttons()[0]
    idx = dialog._suggestion_buttons.id(btn)
    btn.click()
    assert dialog.target_combo.currentIndex() == idx
    assert btn.isChecked()


def test_source_change_rebuilds_suggestions(dialog):
    dialog.source_combo.setCurrentIndex(2)  # Blau
    ids = [dialog._suggestion_buttons.id(b) for b in dialog._suggestion_buttons.buttons()]
    assert 2 not in ids
    assert ids[0] == 3, "Für Blau muss Hellblau der erste Vorschlag sein"


def test_manual_accept_returns_single_replacement(dialog):
    dialog.target_combo.setCurrentIndex(2)
    dialog._on_accept()
    assert dialog.get_replacements() == [(0, 2)]


def test_accept_rejects_identical_source_target(dialog, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a))
    dialog.target_combo.setCurrentIndex(0)  # gleich wie Quelle
    dialog._on_accept()
    assert warnings, "Warnung bei identischer Quell-/Zielfarbe erwartet"
    assert dialog.get_replacements() == []


def test_auto_reduce_returns_multi_replacements(dialog, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    dialog.reduce_spin.setValue(5)
    dialog._on_auto_reduce()
    assert dict(dialog.get_replacements()) == {1: 0, 3: 2}


def test_reduce_preview_disables_button_without_candidates(dialog):
    dialog.reduce_spin.setValue(1)  # nur Hellblau (1 Stich) ist selten
    assert dialog.reduce_btn.isEnabled()
    # Muster ohne seltene Farben: Schwelle 0 geht nicht (min 1) —
    # stattdessen: alle Stiche einer Farbe zuweisen und neu prüfen
    dialog.reduce_spin.setValue(999)  # alles selten -> keine häufigen Ziele
    assert not dialog.reduce_btn.isEnabled()
