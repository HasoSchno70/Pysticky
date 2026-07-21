# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 12): PatternDiffDialog._render_diff() prüfte den
falschen Wert -- `i < new.width` (i = Farbindex!) statt eines echten
Bounds-Checks gegen die Canvas-Groesse. Bei Mustern mit mehr Farben als
Breite (i >= new.width) wurde die Maske faelschlich uebersprungen, die
betroffenen Zellen blieben im Diff-Overlay grau statt mit ihrer Garnfarbe
getoent (der eigentliche Bounds-Check `new.height <= h and new.width <= w`
existierte bereits korrekt einige Zeilen weiter unten)."""

import pytest

from pysticky.core.pattern import Pattern
from pysticky.core.pattern_diff import compute_diff
from pysticky.core.thread import Thread

pytestmark = pytest.mark.usefixtures("qtbot")


def _narrow_pattern_with_many_colors() -> Pattern:
    """3 Zellen breit, aber 5 Farben -- Farbindex 4 >= width(3)."""
    p = Pattern(name="Narrow", width=3, height=3)
    p.color_entries.clear()
    for i in range(5):
        p.add_color(Thread.from_hex(f"Farbe {i}", f"#{i:02x}0000"))
    # Stich mit dem hoechsten Farbindex (4) setzen -- genau der Fall, den
    # der Bug uebersprungen hat.
    p.set_stitch(0, 0, 4)
    return p


def test_render_diff_tints_cell_with_color_index_beyond_width(qtbot):
    from pysticky.ui.dialogs.pattern_diff_dialog import PatternDiffDialog

    pattern = _narrow_pattern_with_many_colors()
    # Identisches altes/neues Pattern -> kein ADDED/REMOVED/CHANGED-Overlay
    # an Zelle (0,0), damit der Basis-Farbton (aus dem betroffenen Codepfad)
    # unverdeckt sichtbar bleibt.
    diff = compute_diff(pattern, pattern)

    dialog = PatternDiffDialog(pattern, pattern, diff)
    qtbot.addWidget(dialog)

    pixmap = dialog._render_diff()
    img = pixmap.toImage()

    # Zelle (0,0) skaliert auf CELL_SIZE=6 -> Pixel (2,2) liegt sicher
    # innerhalb des ersten Zell-Blocks.
    pixel = img.pixelColor(2, 2)

    # Vorher (Bug): Zelle blieb beim reinen Ausgrau-Hintergrund (235,235,235).
    # Nachher (Fix): mit dem Garnfarbton gemischt, also NICHT mehr reines Grau.
    assert (pixel.red(), pixel.green(), pixel.blue()) != (235, 235, 235)
