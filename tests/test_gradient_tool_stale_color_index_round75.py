# -*- coding: utf-8 -*-
"""
Runde 75 (Clean-Code-Audit): Farbverlauf-Panel/-Tool bleiben innerhalb
DESSELBEN Patterns stehen, wenn die Farbpalette bearbeitet wird -- dieselbe
Staleness-Klasse wie die Select/Lasso-Zwischenablage aus Runde 73
(test_clipboard_stale_color_index_round73.py), nur fuer
GradientTool._start_color_index/_end_color_index statt SelectTool._clipboard.

GradientTool.set_start_color()/set_end_color() (gradient_options_panel.py's
Start-/Endfarbe-Comboboxen) speichern rohe Farb-INDIZES, unabhaengig von
ctx.current_color_index. ColorManagementDialog (Loeschen/"Ungenutzte
entfernen"/Zusammenfuehren) und SimilarColorsDialog verschieben
nachfolgende Farbindizes im AKTIVEN Pattern um -1 nach unten
(Pattern.remove_color()) -- exakt wie beim Zwischenablage-Bug. Ohne Fix:

1. Zeigt der eingefrorene Index nach der Verschiebung auf eine ANDERE
   Farbe, faerbt ein spaeterer Verlauf lautlos mit der falschen Farbe
   (kein Crash, keine Warnung).
2. Wird der hoechste Index betroffen (out of range), wird
   _calculate_gradient() zu einem stillen No-Op: Ziehen einer Linie
   erzeugt ueberhaupt keine Aenderungen, ohne jede Fehlermeldung.

Siehe test_stale_gradient_indices_survive_color_shift_at_tool_level fuer
den rohen Repro auf Tool-Ebene (ohne Fix), und die beiden Testklassen
unten fuer den tatsaechlichen Fix ueber die MainWindow-Handler
_on_manage_colors()/_on_merge_similar_colors()
(tool_handlers.py::resync_gradient_tool_after_palette_shift()).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication

from pysticky.core import NO_STITCH, Pattern, Thread
from pysticky.ui.tools.base_tool import ToolContext
from pysticky.ui.tools.gradient_tool import GradientTool

pytestmark = pytest.mark.usefixtures("qtbot")


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
        pattern.add_color(Thread.from_hex(name, hexv))
    return pattern


def _make_ctx(pattern: Pattern, gx: int, gy: int) -> ToolContext:
    return ToolContext(
        canvas=None,
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


def _mouse_event(button: Qt.MouseButton = Qt.MouseButton.LeftButton) -> MagicMock:
    evt = MagicMock()
    evt.button.return_value = button
    evt.position.return_value = QPoint(0, 0)
    return evt


# === Reiner Tool-Level-Repro (ohne MainWindow) ===


def test_stale_gradient_indices_survive_color_shift_at_tool_level():
    """Rohe Reproduktion: GradientTool alleine kennt keinen Bezug zur
    urspruenglich ausgewaehlten Farbe, nur den rohen Index. Dokumentiert
    das Tool-Verhalten OHNE den Fix in main_window.py -- der eigentliche
    Fix (Resync in den Handlern) wird von den MainWindow-Tests unten
    geprueft."""
    pattern = _make_five_color_pattern()

    tool = GradientTool()
    # Nutzer waehlt im Panel Startfarbe=Weiss(1), Endfarbe=Rot(2).
    tool.set_start_color(1)
    tool.set_end_color(2)
    assert pattern.color_entries[tool.start_color_index].thread.name == "Weiss"
    assert pattern.color_entries[tool.end_color_index].thread.name == "Rot"

    # Farbe 0 (Schwarz) wird entfernt -- alle Indizes >= 1 ruecken um 1
    # nach unten, exakt wie ColorManagementDialog._remove_color_at_index()/
    # Pattern.remove_color().
    pattern.remove_color(0)
    assert [e.thread.name for e in pattern.color_entries] == [
        "Weiss",
        "Rot",
        "Gruen",
        "Blau",
    ]

    # Die eingefrorenen Rohindizes im Tool zeigen jetzt auf ANDERE Farben.
    assert pattern.color_entries[tool.start_color_index].thread.name == "Rot", (
        "Erwartetes (unkorrigiertes) Tool-Verhalten: Index 1 zeigt nach der "
        "Verschiebung nicht mehr auf Weiss, sondern auf Rot."
    )
    assert pattern.color_entries[tool.end_color_index].thread.name == "Gruen", (
        "Erwartetes (unkorrigiertes) Tool-Verhalten: Index 2 zeigt nach der "
        "Verschiebung nicht mehr auf Rot, sondern auf Gruen."
    )


def test_stale_gradient_end_index_out_of_range_becomes_silent_no_op():
    """Betrifft die Verschiebung den hoechsten Index, zeigt er anschliessend
    komplett ins Leere -- _calculate_gradient() faengt das zwar ab
    (get_color_entry() liefert None), das Ziehen einer Linie erzeugt dann
    aber STILLSCHWEIGEND gar keine Aenderungen."""
    pattern = _make_five_color_pattern()

    tool = GradientTool()
    tool.set_start_color(3)  # Gruen
    tool.set_end_color(4)  # Blau

    pattern.remove_color(0)  # Schwarz entfernen -- 5 Farben werden zu 4
    assert len(pattern.color_entries) == 4
    assert tool.end_color_index == 4  # aus der Range gelaufen (nur 0..3 gueltig)

    ctx1 = _make_ctx(pattern, 0, 0)
    tool.on_mouse_press(ctx1, _mouse_event())
    ctx2 = _make_ctx(pattern, 3, 0)
    tool.on_mouse_move(ctx2, _mouse_event())
    changes = tool.on_mouse_release(ctx2, _mouse_event())

    assert changes == [], (
        "Erwartetes (unkorrigiertes) Tool-Verhalten: ein Verlauf ueber 4 "
        "Zellen erzeugt gar keine Aenderungen, weil der eingefrorene "
        "Endindex nach der Farbverschiebung ausserhalb der Palette liegt."
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


def _prepare_pattern_and_gradient_selection(main_window) -> None:
    """Ersetzt das Pattern des main_window-Fixtures durch ein 5-Farben-
    Pattern und waehlt im Farbverlauf-Tool Start=Weiss(1)/Ende=Rot(2), so
    wie ueber die Panel-Comboboxen."""
    pattern = _make_five_color_pattern()
    main_window.set_pattern(pattern)

    from pysticky.ui.tools.tool_enum import Tool

    main_window.tool_bar.select_tool(Tool.GRADIENT)
    gradient_tool = main_window.canvas._tool_manager.get_gradient_tool()
    gradient_tool.set_start_color(1)
    gradient_tool.set_end_color(2)
    main_window.gradient_options_panel.set_start_color(1)
    main_window.gradient_options_panel.set_end_color(2)


class TestManageColorsDialogResyncsGradientTool:
    """Regressionstest fuer den Runde-75-Fix in
    edit_handlers.py::_on_manage_colors(): das Loeschen/Zusammenfuehren von
    Farben im ColorManagementDialog verschiebt Farbindizes im AKTIVEN
    Pattern -- eine Start-/Endfarbe-Auswahl im Farbverlauf-Panel davor darf
    danach nicht mehr auf die falsche (oder eine ungueltige) Farbe zeigen."""

    def test_deleting_a_color_resyncs_gradient_selection(self, main_window, monkeypatch):
        _prepare_pattern_and_gradient_selection(main_window)
        pattern = main_window.current_pattern
        gradient_tool = main_window.canvas._tool_manager.get_gradient_tool()

        class _FakeManageDialog:
            """Ersetzt den echten (modalen) ColorManagementDialog: fuehrt
            exakt dieselbe Indexverschiebung wie
            ColorManagementDialog._remove_color_at_index(0) real am
            Pattern aus, ohne eine Qt-Eventloop/QMessageBox zu benoetigen."""

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

        assert gradient_tool.start_color_index == 1
        assert gradient_tool.end_color_index == 2
        main_window._on_manage_colors()

        assert pattern.color_entries[0].thread.name == "Weiss"
        # Ohne Fix bleiben die rohen Indizes 1/2 stehen -- die zeigen nach
        # der Verschiebung (Schwarz entfernt) aber nicht mehr auf Weiss/Rot,
        # sondern auf Rot/Gruen. Das Tool muss stattdessen auf tatsaechlich
        # existierende, mit dem (ebenfalls resynchronisierten) Panel
        # konsistente Farben zeigen.
        assert 0 <= gradient_tool.start_color_index < len(pattern.color_entries)
        assert 0 <= gradient_tool.end_color_index < len(pattern.color_entries)
        assert pattern.color_entries[gradient_tool.start_color_index].thread.name == "Weiss", (
            "Regression: ColorManagementDialog (Loeschen/Zusammenfuehren) "
            "verschiebt Farbindizes im gleichen Pattern, liess das "
            "Farbverlauf-Tool aber mit dem eingefrorenen Rohindex stehen -- "
            "ein spaeterer Verlauf faerbte lautlos mit der falschen Farbe."
        )
        assert pattern.color_entries[gradient_tool.end_color_index].thread.name == "Rot"
        assert (
            gradient_tool.start_color_index == main_window.gradient_options_panel.start_color_index
        )
        assert gradient_tool.end_color_index == main_window.gradient_options_panel.end_color_index


class TestMergeSimilarColorsDialogResyncsGradientTool:
    """Analoger Regressionstest fuer
    edit_handlers.py::_on_merge_similar_colors()."""

    def test_merging_colors_resyncs_gradient_selection(self, main_window, monkeypatch):
        _prepare_pattern_and_gradient_selection(main_window)
        pattern = main_window.current_pattern
        gradient_tool = main_window.canvas._tool_manager.get_gradient_tool()

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

        assert gradient_tool.start_color_index == 1
        assert gradient_tool.end_color_index == 2
        main_window._on_merge_similar_colors()

        assert pattern.color_entries[0].thread.name == "Weiss"
        assert 0 <= gradient_tool.start_color_index < len(pattern.color_entries)
        assert 0 <= gradient_tool.end_color_index < len(pattern.color_entries)
        assert pattern.color_entries[gradient_tool.start_color_index].thread.name == "Weiss", (
            "Regression: SimilarColorsDialog-Merge verschiebt Farbindizes im "
            "gleichen Pattern, liess das Farbverlauf-Tool aber mit dem "
            "eingefrorenen Rohindex stehen."
        )
        assert pattern.color_entries[gradient_tool.end_color_index].thread.name == "Rot"
        assert (
            gradient_tool.start_color_index == main_window.gradient_options_panel.start_color_index
        )
        assert gradient_tool.end_color_index == main_window.gradient_options_panel.end_color_index
