# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 14): ColorButton._pick_color() rief
QColorDialog.getColor() mit einem rohen "Farbe wählen"-Literal statt
t("Farbe wählen") auf -- die strukturell gleiche Klasse in
grid_options_dialog.py macht das schon immer korrekt, und en.json hat
laengst eine Uebersetzung fuer genau diesen String. Im Englisch-Modus
blieb der Farbwaehler-Dialogtitel dadurch deutsch, waehrend jeder andere
Farbwaehler im Programm korrekt uebersetzte.
"""

import pytest
from PySide6.QtWidgets import QColorDialog

from pysticky.core.i18n import set_language

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture
def english_language():
    set_language("en")
    try:
        yield
    finally:
        set_language("de")


def test_pick_color_uses_translated_title(qtbot, english_language, monkeypatch):
    from pysticky.ui.dialogs.settings_tabs.color_button import ColorButton

    captured = {}

    def fake_get_color(initial, parent, title):
        captured["title"] = title
        from PySide6.QtGui import QColor

        return QColor()  # invalid -> _pick_color no-ops after this

    monkeypatch.setattr(QColorDialog, "getColor", staticmethod(fake_get_color))

    btn = ColorButton("#ff0000")
    qtbot.addWidget(btn)
    btn._pick_color()

    assert captured["title"] == "Choose color"
