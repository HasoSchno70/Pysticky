# -*- coding: utf-8 -*-
"""Regressionstests fuer SimilarColorsDialog.

Findet: eine Farbe, die in zwei ausgewaehlten Merge-Paaren gleichzeitig
als "wird ersetzt" (idx_b) vorkommt, liess die alte Dedup-Logik eines der
beiden Paare lautlos verwerfen -- ohne jede Rueckmeldung an den User.
"""

from PySide6.QtWidgets import QMessageBox

from pysticky.core import Pattern, Thread
from pysticky.ui.color_utils import to_qcolor
from pysticky.ui.dialogs.similar_colors_dialog import SimilarColorsDialog, _ColorPairRow


def _make_pattern():
    pattern = Pattern(width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("A", "#111111"))
    pattern.add_color(Thread.from_hex("B", "#222222"))
    pattern.add_color(Thread.from_hex("C", "#333333"))
    return pattern


def _checked_row(pattern, idx_a, idx_b):
    entry_a = pattern.color_entries[idx_a]
    entry_b = pattern.color_entries[idx_b]
    row = _ColorPairRow(
        idx_a,
        idx_b,
        entry_a.thread.name,
        entry_b.thread.name,
        to_qcolor(entry_a.thread.color),
        to_qcolor(entry_b.thread.color),
        distance=5.0,
    )
    row.checkbox.setChecked(True)
    return row


def test_warns_and_refuses_conflicting_merge_selection(qtbot, monkeypatch):
    """Farbe 2 waere gleichzeitig durch Farbe 0 UND Farbe 1 zu ersetzen --
    muss abgelehnt werden statt eines der beiden Paare stillschweigend zu
    verwerfen."""
    pattern = _make_pattern()
    dialog = SimilarColorsDialog(pattern)
    qtbot.addWidget(dialog)

    dialog._pair_rows = [
        _checked_row(pattern, 0, 2),
        _checked_row(pattern, 1, 2),  # Farbe 2 taucht hier ein zweites Mal als idx_b auf
    ]

    warned = {}

    def fake_warning(parent, title, text):
        warned["called"] = True
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "warning", fake_warning)

    dialog._on_merge()

    assert warned.get("called") is True
    # Beide Farben muessen unangetastet bleiben -- kein Merge darf
    # stillschweigend durchgelaufen sein.
    assert len(pattern.color_entries) == 3


def test_non_conflicting_merges_proceed_normally(qtbot, monkeypatch):
    """Zwei Paare ohne gemeinsame idx_b duerfen weiterhin normal
    zusammengefuehrt werden (keine Regression durch den neuen Check)."""
    pattern = _make_pattern()
    pattern.add_color(Thread.from_hex("D", "#444444"))
    dialog = SimilarColorsDialog(pattern)
    qtbot.addWidget(dialog)

    dialog._pair_rows = [
        _checked_row(pattern, 0, 2),
        _checked_row(pattern, 1, 3),
    ]

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    warned = {}
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warned.setdefault("called", True))

    dialog._on_merge()

    assert "called" not in warned
    assert len(pattern.color_entries) == 2  # zwei Farben wegfusioniert
