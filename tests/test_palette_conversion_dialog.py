# -*- coding: utf-8 -*-
"""
Regressionstest: PaletteConversionDialog._on_apply() konvertierte Farben
ohne zu pruefen, ob mehrere Quellfarben auf dieselbe Zielfarbe abgebildet
wurden -- das Muster haette danach zwei nicht mehr unterscheidbare
Farbeintraege enthalten, ohne jede Warnung (similar_colors_dialog.py's
Merge-Konflikt-Check wurde in einer frueheren Runde gefixt, dieser Dialog
nie mit nachgezogen).
"""

from PySide6.QtWidgets import QMessageBox

from pysticky.core import Pattern, Thread
from pysticky.ui.dialogs.palette_conversion_dialog import PaletteConversionDialog


def _make_pattern():
    pattern = Pattern(width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("A", "#111111", manufacturer="DMC", catalog_number="1"))
    pattern.add_color(Thread.from_hex("B", "#222222", manufacturer="DMC", catalog_number="2"))
    return pattern


def test_apply_warns_on_duplicate_target_mapping(qtbot, monkeypatch):
    pattern = _make_pattern()
    dialog = PaletteConversionDialog(pattern)
    qtbot.addWidget(dialog)

    same_target = Thread.from_hex("Ziel", "#333333", manufacturer="Anchor", catalog_number="9")
    dialog._mapping = [
        {"entry": pattern.color_entries[0], "target_thread": same_target, "distance": 1.0},
        {"entry": pattern.color_entries[1], "target_thread": same_target, "distance": 1.0},
    ]

    asked = {}

    def fake_question(*a, **k):
        asked["called"] = True
        return QMessageBox.StandardButton.No  # Nutzer bricht ab

    monkeypatch.setattr(QMessageBox, "question", fake_question)

    dialog._on_apply()

    assert asked.get("called") is True
    # Bei "No" darf NICHTS konvertiert worden sein.
    assert pattern.color_entries[0].thread.name == "A"
    assert pattern.color_entries[1].thread.name == "B"


def test_apply_proceeds_without_prompt_when_no_collision(qtbot, monkeypatch):
    pattern = _make_pattern()
    dialog = PaletteConversionDialog(pattern)
    qtbot.addWidget(dialog)

    target_a = Thread.from_hex("Ziel A", "#333333", manufacturer="Anchor", catalog_number="9")
    target_b = Thread.from_hex("Ziel B", "#444444", manufacturer="Anchor", catalog_number="10")
    dialog._mapping = [
        {"entry": pattern.color_entries[0], "target_thread": target_a, "distance": 1.0},
        {"entry": pattern.color_entries[1], "target_thread": target_b, "distance": 1.0},
    ]

    asked = {}
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: asked.setdefault("called", True))

    dialog._on_apply()

    assert "called" not in asked
    assert pattern.color_entries[0].thread.name == "Ziel A"
    assert pattern.color_entries[1].thread.name == "Ziel B"
