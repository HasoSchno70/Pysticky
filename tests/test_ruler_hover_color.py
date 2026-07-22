# -*- coding: utf-8 -*-
"""
Regression: RulerCorner baute die Hover-Fuellfarbe per String-Konkatenation
QColor(THEME.accent_primary + "40") -- ein 8-stelliger Hex-String wird von
QColor als #AARRGGBB interpretiert (Alpha ZUERST), nicht als #RRGGBBAA. Das
angehaengte Alpha-Suffix verschob dadurch alle Farbkanaele und ergab eine
komplett falsche, fast undurchsichtige Farbe statt eines durchscheinenden
accent_primary -- dieselbe Falle wie beim Kachel-Vorschau-Rahmen (siehe
tests/test_tile_preview_panel_border_color.py) und dem Rueckstich-Start-Punkt-
Marker (siehe tests/test_canvas_backstitch_start_point_color.py).
"""

import pytest
from PySide6.QtGui import QColor

from pysticky.ui.styles import THEME

pytestmark = pytest.mark.usefixtures("qtbot")


def test_ruler_corner_hover_fill_color_preserves_accent_rgb_with_correct_alpha():
    from pysticky.ui.widgets.ruler import RulerCorner

    color = RulerCorner._hover_fill_color()
    expected_rgb = QColor(THEME.accent_primary)

    assert color.red() == expected_rgb.red()
    assert color.green() == expected_rgb.green()
    assert color.blue() == expected_rgb.blue()
    assert color.alpha() == 0x40
