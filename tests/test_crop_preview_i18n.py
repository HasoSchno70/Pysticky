# -*- coding: utf-8 -*-
"""Regressionstest (Runde 26): CropPreviewWidget.paintEvent()'s "Kein Bild
geladen"-Platzhaltertext war eine rohe deutsche Konstante, die Datei
importierte `t()` gar nicht -- im Englisch-Modus blieb der Platzhalter
dauerhaft deutsch."""

from unittest.mock import patch

import pytest
from PySide6.QtGui import QPainter, QPixmap

from pysticky.core.i18n import set_language

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture
def english_language():
    set_language("en")
    try:
        yield
    finally:
        set_language("de")


def test_no_image_placeholder_is_translated(qtbot, english_language):
    from pysticky.ui.widgets.crop_preview import CropPreviewWidget

    widget = CropPreviewWidget()
    qtbot.addWidget(widget)
    widget.resize(200, 200)

    drawn_texts = []
    orig_draw_text = QPainter.drawText

    def _spy_draw_text(self, *args, **kwargs):
        for arg in args:
            if isinstance(arg, str):
                drawn_texts.append(arg)
        return orig_draw_text(self, *args, **kwargs)

    pixmap = QPixmap(widget.size())
    with patch.object(QPainter, "drawText", _spy_draw_text):
        widget.render(pixmap)

    assert any("No image loaded" in t for t in drawn_texts)
    assert not any("Kein Bild" in t for t in drawn_texts)
