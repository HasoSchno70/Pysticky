# -*- coding: utf-8 -*-
"""
Regression: RenderingMixin._draw_backstitches() baute den Rueckstich-Start-
Punkt-Marker per String-Konkatenation QColor(THEME.accent_primary + "99") --
dieselbe Alpha-Suffix-Falle wie beim Lineal-Hover (siehe
tests/test_ruler_hover_color.py) und dem Kachel-Vorschau-Rahmen (siehe
tests/test_tile_preview_panel_border_color.py): ein 8-stelliger Hex-String
wird von QColor als #AARRGGBB interpretiert (Alpha ZUERST), nicht als
#RRGGBBAA.
"""

import pytest
from PySide6.QtGui import QColor

from pysticky.ui.styles import THEME

pytestmark = pytest.mark.usefixtures("qtbot")


def test_backstitch_start_point_color_preserves_accent_rgb_with_correct_alpha():
    from pysticky.ui.canvas.mixins.rendering_mixin import RenderingMixin

    color = RenderingMixin._backstitch_start_point_color()
    expected_rgb = QColor(THEME.accent_primary)

    assert color.red() == expected_rgb.red()
    assert color.green() == expected_rgb.green()
    assert color.blue() == expected_rgb.blue()
    assert color.alpha() == 0x99
