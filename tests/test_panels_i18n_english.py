# -*- coding: utf-8 -*-
"""
Regressionstests (Runde 21): mehrere direkte deutsche String-Literale in
ui/panels/ waren nie durch t() geschickt worden (bzw. wurden bei jedem
Aufruf neu aus einem rohen f-String gebaut statt aus einer uebersetzten
Vorlage) -- im Englisch-Modus zeigten sie dauerhaft deutschen Text:

- progress_panel.py::update_progress() baute die Stich-Zaehler-Zeile aus
  einem rohen f-String mit hart-codiertem "Stiche" statt t("Stiche").
- info_panel.py::clear_info() setzte die Zeit-Karte auf das hart-codierte
  "0 Min" statt "0 " + t("Min").
- palette_panel.py::_on_apply_palette_clicked() und layer_panel.py's
  Merge-/Loeschen-/Leeren-Bestaetigungsdialoge hatten Titel/Body komplett
  ohne jeden t()-Aufruf -- vom AST-basierten Completeness-Test strukturell
  nicht erfassbar, da dieser nur bereits-t()-gewickelte Literale prueft.

Nutzt dasselbe english_language-Fixture-Muster wie test_i18n_en_smoke.py.
"""

from unittest.mock import patch

import pytest

from pysticky.core.i18n import set_language


@pytest.fixture
def english_language():
    set_language("en")
    try:
        yield
    finally:
        set_language("de")


def test_progress_panel_counts_label_is_translated(qtbot, english_language, pattern_with_stitches):
    from pysticky.ui.panels.progress_panel import ProgressPanel

    panel = ProgressPanel()
    qtbot.addWidget(panel)
    panel.update_progress(pattern_with_stitches)

    assert "Stitches" in panel.lbl_counts.text()
    assert "Stiche" not in panel.lbl_counts.text()


def test_info_panel_clear_info_time_card_is_translated(qtbot, english_language):
    from pysticky.ui.panels.info_panel import InfoPanel

    panel = InfoPanel()
    qtbot.addWidget(panel)
    panel.clear_info()

    assert panel.card_time._value == "0 min"


def test_palette_panel_apply_confirmation_is_translated(
    qtbot, english_language, pattern_with_colors
):
    from pysticky.ui.panels.palette_panel import PalettePanel

    panel = PalettePanel()
    qtbot.addWidget(panel)
    panel._current_pattern = pattern_with_colors
    panel._current_palette_name = "DMC"

    with patch("pysticky.ui.panels.palette_panel.QMessageBox.question") as mock_question:
        mock_question.return_value = None
        panel._on_apply_palette_clicked()

        args, _ = mock_question.call_args
        title, body = args[1], args[2]
        assert title == "Change palette"
        assert "recreated" in body
        assert "Muster" not in body


def test_layer_panel_remove_confirmation_is_translated(
    qtbot, english_language, pattern_with_stitches
):
    from pysticky.ui.panels.layer_panel import LayerPanel

    panel = LayerPanel()
    qtbot.addWidget(panel)
    panel.set_layer_stack(pattern_with_stitches.layer_stack)
    pattern_with_stitches.layer_stack.add_layer("Zweite Ebene")
    panel.list_widget.setCurrentRow(0)

    with patch("pysticky.ui.panels.layer_panel.QMessageBox.question") as mock_question:
        mock_question.return_value = None
        panel._on_remove_layer()

        args, _ = mock_question.call_args
        title, body = args[1], args[2]
        assert title == "Delete layer"
        assert "löschen" not in body


def test_layer_panel_clear_confirmation_is_translated(
    qtbot, english_language, pattern_with_stitches
):
    from pysticky.ui.panels.layer_panel import LayerPanel

    panel = LayerPanel()
    qtbot.addWidget(panel)
    panel.set_layer_stack(pattern_with_stitches.layer_stack)
    panel.list_widget.setCurrentRow(0)

    with patch("pysticky.ui.panels.layer_panel.QMessageBox.question") as mock_question:
        mock_question.return_value = None
        panel._on_clear_layer()

        args, _ = mock_question.call_args
        body = args[2]
        assert "entfernen" not in body
        assert "Remove all stitches" in body
