# -*- coding: utf-8 -*-
"""
Runde 73 (Clean-Code-Audit): Select/Lasso-Zwischenablage bleibt innerhalb
DESSELBEN Patterns stehen, wenn die Farbpalette bearbeitet wird.

Bereits vorher gefixt (siehe canvas.py::set_pattern() und
view_handlers.py::_apply_pattern_mode()): ein kompletter Pattern-Wechsel
(Datei -> Neu/Oeffnen) und der Sticken/Diamond-Painting-Modenwechsel leeren
SelectTool._clipboard bereits, weil der Zwischenspeicher nur einen rohen
Farb-INDEX haelt, keinen Bezug zur Quellfarbe.

NEU in Runde 73: Die Farbpaletten-Dialoge (Farben verwalten -> Loeschen/
Ungenutzte entfernen/Zusammenfuehren, sowie "Aehnliche Farben
zusammenfuehren") aendern Farbindizes GENAU SO -- innerhalb DESSELBEN
Patterns, ohne dass set_pattern()/convert_to_mode() je aufgerufen wird.
Diese Dialoge leerten bereits den Undo-Verlauf aus exakt diesem Grund
(siehe Kommentare in canvas.py/view_handlers.py, die diese Dialoge sogar
namentlich als "bereits geleert" referenzieren) -- den Clipboard-Reset
hatten sie aber nie nachgezogen. Ohne Fix faerbt ein Paste NACH so einem
Dialog die eingefuegte Auswahl lautlos mit der FALSCHEN Farbe ein (kein
Crash, keine Warnung) -- siehe test_stale_clipboard_survives_color_shift_*
fuer den rohen Repro auf Tool-Ebene, und die beiden
Test-Klassen unten fuer den Fix ueber die tatsaechlichen
MainWindow-Handler _on_manage_colors()/_on_merge_similar_colors().
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication

from pysticky.core import NO_STITCH, Pattern, Thread
from pysticky.ui.tools.base_tool import ToolContext
from pysticky.ui.tools.select_tool import SelectTool

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture(autouse=True)
def _reset_clipboard():
    """SelectTool._clipboard ist eine KLASSENvariable -- ohne Reset
    verseucht ein Test die anderen in der vollen Suite."""
    SelectTool._clipboard = None
    SelectTool._clipboard_size = (0, 0)
    yield
    SelectTool._clipboard = None
    SelectTool._clipboard_size = (0, 0)


def _make_ctx(pattern: Pattern, gx: int, gy: int) -> ToolContext:
    from unittest.mock import MagicMock

    canvas = MagicMock()
    canvas.snap_position.side_effect = lambda x, y: (x, y)
    canvas.snap_to_grid = False
    canvas.snap_interval = 1
    return ToolContext(
        canvas=canvas,
        pattern=pattern,
        current_color_index=0,
        grid_x=gx,
        grid_y=gy,
        screen_x=gx * 20,
        screen_y=gy * 20,
        cell_size=20,
        offset_x=0,
        offset_y=0,
    )


def _make_five_color_pattern() -> Pattern:
    pattern = Pattern(name="A", width=20, height=20)
    pattern.color_entries.clear()
    for name, hexv in [
        ("Schwarz", "#000000"),
        ("Weiss", "#FFFFFF"),
        ("Rot", "#FF0000"),
        ("Gruen", "#00FF00"),
        ("Blau", "#0000FF"),
    ]:
        pattern.add_color(Thread.from_hex(name, hexv, manufacturer="DMC"))
    return pattern


# === Reiner Tool-Level-Repro (ohne MainWindow) ===


def test_stale_clipboard_survives_color_shift_within_same_pattern():
    """Rohe Reproduktion: SelectTool._clipboard alleine kennt kein
    Pattern-Objekt und kann eine Farbverschiebung im selben Pattern nicht
    erkennen. Dieser Test dokumentiert das Tool-Verhalten OHNE den Fix in
    main_window.py -- der eigentliche Fix (Clipboard-Reset in den
    Handlern) wird von den MainWindow-Tests unten geprueft."""
    pattern = _make_five_color_pattern()

    # Stich mit Farbindex 3 == Gruen
    pattern.set_stitch(5, 5, 3)

    tool = SelectTool()
    tool._selection = QRect(5, 5, 1, 1)
    ctx = _make_ctx(pattern, 5, 5)
    assert tool.copy_selection(ctx) is True
    assert SelectTool._clipboard == [(0, 0, 3, 0)]

    # Farbe 0 (Schwarz) wird entfernt -- alle Indizes >= 1 ruecken um 1 nach
    # unten, exakt wie ColorManagementDialog._remove_color_at_index()/
    # Pattern.remove_color().
    pattern.remove_color(0)
    assert [e.thread.name for e in pattern.color_entries] == [
        "Weiss",
        "Rot",
        "Gruen",
        "Blau",
    ]
    # Die tatsaechliche Zelle im Grid wurde korrekt nachgezogen (Index 2 == Gruen).
    assert pattern.get_stitch(5, 5) == 2

    # Der eingefrorene Zwischenablage-Snapshot zeigt weiterhin auf Index 3
    # -- das ist nach der Verschiebung "Blau", nicht mehr "Gruen".
    ctx2 = _make_ctx(pattern, 10, 10)
    assert tool.start_paste(ctx2) is True
    tool._paste_position = (10, 10)
    changes = tool._confirm_paste(ctx2)
    assert changes == [(10, 10, 3, 0)]
    pattern.set_stitch(10, 10, 3, 0)
    assert pattern.color_entries[3].thread.name == "Blau", (
        "Erwartetes (unkorrigiertes) Tool-Verhalten: der Rohindex 3 im "
        "Clipboard zeigt nach der Farbverschiebung auf eine andere Farbe."
    )


# === MainWindow-Handler-Tests (echter Fix) ===


@pytest.fixture
def main_window(qtbot):
    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    return w


def _prepare_pattern_and_clipboard(main_window) -> None:
    """Ersetzt das Pattern des main_window-Fixtures durch ein 5-Farben-
    Pattern mit einem Stich in Gruen (Index 3), kopiert diesen Stich in die
    Zwischenablage."""
    pattern = _make_five_color_pattern()
    pattern.set_stitch(5, 5, 3)
    # set_pattern() leert die Zwischenablage bereits (bestehender Fix) --
    # unschaedlich, wir kopieren erst DANACH neu hinein.
    main_window.set_pattern(pattern)

    tool = SelectTool()
    tool._selection = QRect(5, 5, 1, 1)
    ctx = _make_ctx(pattern, 5, 5)
    assert tool.copy_selection(ctx) is True
    assert SelectTool._clipboard == [(0, 0, 3, 0)]


class TestManageColorsDialogClearsClipboard:
    """Regressionstest fuer den Runde-73-Fix in
    edit_handlers.py::_on_manage_colors(): das Loeschen/Zusammenfuehren von
    Farben im ColorManagementDialog verschiebt Farbindizes im AKTIVEN
    Pattern -- ein Copy davor darf nach dem Dialog nicht mehr in der
    Zwischenablage liegen."""

    def test_deleting_a_color_clears_stale_clipboard(self, main_window, monkeypatch):
        _prepare_pattern_and_clipboard(main_window)
        pattern = main_window.current_pattern

        class _FakeManageDialog:
            """Ersetzt den echten (modalen) ColorManagementDialog: fuehrt
            exakt dieselbe Indexverschiebung wie
            ColorManagementDialog._remove_color_at_index(0) real am Pattern
            aus, ohne eine Qt-Eventloop/QMessageBox zu benoetigen."""

            def __init__(self, pat, parent):
                self._pattern = pat

            def exec(self):
                index = 0
                for layer in self._pattern.layer_stack:
                    layer.replace_color(index, NO_STITCH)
                    layer.shift_color_indices(index + 1, -1)
                self._pattern.backstitch_manager.update_color_indices(index)
                del self._pattern.color_entries[index]
                self._pattern.recalculate_stitch_counts()
                return 1

            def has_changes(self):
                return True

        monkeypatch.setattr("pysticky.ui.dialogs.ColorManagementDialog", _FakeManageDialog)

        assert SelectTool._clipboard is not None
        main_window._on_manage_colors()

        assert pattern.color_entries[0].thread.name == "Weiss"
        assert SelectTool._clipboard is None, (
            "Regression: ColorManagementDialog (Loeschen/Zusammenfuehren) "
            "verschiebt Farbindizes im gleichen Pattern, liess die "
            "Select/Lasso-Zwischenablage aber unangetastet -- ein Paste "
            "danach faerbte lautlos mit der falschen Farbe."
        )


class TestMergeSimilarColorsDialogClearsClipboard:
    """Analoger Regressionstest fuer
    edit_handlers.py::_on_merge_similar_colors()."""

    def test_merging_colors_clears_stale_clipboard(self, main_window, monkeypatch):
        _prepare_pattern_and_clipboard(main_window)
        pattern = main_window.current_pattern

        class _FakeMergeDialog:
            def __init__(self, pat, parent):
                self._pattern = pat

            def exec(self):
                # Schwarz (0) in Weiss (1) zusammenfuehren -- identischer
                # Effekt auf color_entries wie SimilarColorsDialog._on_merge().
                self._pattern.merge_colors_stitches(0, 1)
                self._pattern.remove_color(0)
                return 1

        monkeypatch.setattr("pysticky.ui.dialogs.SimilarColorsDialog", _FakeMergeDialog)

        assert SelectTool._clipboard is not None
        main_window._on_merge_similar_colors()

        assert pattern.color_entries[0].thread.name == "Weiss"
        assert SelectTool._clipboard is None, (
            "Regression: SimilarColorsDialog-Merge verschiebt Farbindizes im "
            "gleichen Pattern, liess die Select/Lasso-Zwischenablage aber "
            "unangetastet."
        )
