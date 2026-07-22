# -*- coding: utf-8 -*-
"""Regressionstest (Runde 31): action_diamond_view (mw_actions_mixin.py)
behauptete im Tooltip "...und zeigt DMC-Nummern statt Symbolen (Ctrl+D)".

Das war korrekt bis zum Diamond-Symbol-Konsistenz-Fix vom 2026-07-18 (siehe
MEMORY.md), seitdem zeichnet rendering_mixin.py::_draw_layer_cells in BEIDEN
Modi dasselbe Farb-Symbol (entry.symbol) -- diamond_view aendert nur die
Zell-FORM (facettierter Drill statt Quadrat fuer volle Stiche), niemals das
Symbol. Der Tooltip beschrieb seit vier Tagen ein Verhalten, das es nicht
mehr gab: Nutzer, die per Hover/Ctrl+D nachschauen, wurden falsch informiert.
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


def test_diamond_view_tooltip_does_not_claim_dmc_numbers_replace_symbols(main_window):
    tooltip = main_window.action_diamond_view.toolTip()
    assert "DMC-Nummern statt Symbolen" not in tooltip
    assert "DMC numbers instead of symbols" not in tooltip


def test_diamond_view_tooltip_mentions_shape_change(main_window):
    tooltip = main_window.action_diamond_view.toolTip()
    assert "Drill" in tooltip
    assert "Ctrl+D" in tooltip
