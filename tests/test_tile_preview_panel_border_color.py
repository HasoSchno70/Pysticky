# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 29): TilePreviewWidget.paintEvent() baute die Farbe
der gestrichelten Kachel-Umrandung per String-Konkatenation
`QColor(THEME.accent_primary + "99")`.

QColor interpretiert einen 8-stelligen Hex-String als #AARRGGBB (Alpha an
erster Stelle), nicht als #RRGGBBAA. Ein ans Ende angehaengtes
Alpha-Suffix verschiebt dadurch alle Farbkanaele um ein Byte -- statt
eines durchscheinenden accent_primary kam eine voellig andere,
undurchsichtige Farbe heraus. Beispiel mit accent_primary = "#3d8bfd":
QColor("#3d8bfd99").getRgb() == (139, 253, 153, 61) statt der
gewuenschten (61, 139, 253, 153).
"""

import pytest

from pysticky.ui.styles import THEME

pytestmark = pytest.mark.usefixtures("qtbot")


def test_tile_border_color_preserves_accent_rgb_with_correct_alpha(qtbot):
    from PySide6.QtGui import QColor

    from pysticky.ui.panels.tile_preview_panel import TilePreviewWidget

    widget = TilePreviewWidget()
    qtbot.addWidget(widget)

    border_color = widget._tile_border_color()
    expected_rgb = QColor(THEME.accent_primary).getRgb()[:3]

    assert border_color.getRgb()[:3] == expected_rgb, (
        "Die RGB-Kanaele der Umrandungsfarbe muessen mit accent_primary "
        "uebereinstimmen -- die alte String-Konkatenation vertauschte sie "
        "mit dem Alpha-Byte."
    )
    assert border_color.alpha() == 0x99
