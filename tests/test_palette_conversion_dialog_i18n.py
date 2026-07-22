# -*- coding: utf-8 -*-
"""Regressionstest (Runde 25): PaletteConversionDialog._on_apply() baute die
"Fehlende Zuordnungen"- und "Schlechte Zuordnungen"-Meldungen als rohe
deutsche f-Strings statt sie durch t() zu schicken -- im Englisch-Modus
blieben beide Warnungen dauerhaft deutsch, obwohl die "Mehrfachzuordnung"-
Warnung direkt daneben schon korrekt t()-gewrappt war (Inkonsistenz
innerhalb derselben Methode)."""

from unittest.mock import patch

import pytest

from pysticky.core import Pattern, Thread
from pysticky.core.i18n import set_language

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture
def english_language():
    set_language("en")
    try:
        yield
    finally:
        set_language("de")


def _dialog(qtbot):
    from pysticky.ui.dialogs.palette_conversion_dialog import PaletteConversionDialog

    pattern = Pattern(name="Test", width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))

    dialog = PaletteConversionDialog(pattern, parent=None)
    qtbot.addWidget(dialog)
    return dialog


def test_missing_mapping_warning_is_translated(qtbot, english_language):
    dialog = _dialog(qtbot)
    dialog._mapping = [
        {"entry": dialog._pattern.color_entries[0], "target_thread": None, "distance": 0.0}
    ]

    with patch("pysticky.ui.dialogs.palette_conversion_dialog.QMessageBox.warning") as mock_warn:
        dialog._on_apply()

    assert mock_warn.called
    message = mock_warn.call_args[0][2]
    assert "have no assignment" in message
    assert "Zuordnung" not in message


def test_poor_match_warning_is_translated(qtbot, english_language):
    dialog = _dialog(qtbot)
    entry = dialog._pattern.color_entries[0]
    dialog._mapping = [{"entry": entry, "target_thread": entry.thread, "distance": 99.0}]

    with patch(
        "pysticky.ui.dialogs.palette_conversion_dialog.QMessageBox.question",
        return_value=__import__(
            "PySide6.QtWidgets", fromlist=["QMessageBox"]
        ).QMessageBox.StandardButton.No,
    ) as mock_question:
        dialog._on_apply()

    assert mock_question.called
    message = mock_question.call_args[0][2]
    assert "large color distance" in message
    assert "Farbabstand" not in message
