# -*- coding: utf-8 -*-
"""Regressionstest (Runde 26): ColorSwatch._create_tooltip() (color_bar.py)
importiert und nutzt t() korrekt fuer die meisten Labels, aber der
"Wird nicht gestickt"-Skip-Marker und das "Stiche"-Suffix der Stichanzahl
waren rohe deutsche Literale -- eine schmale, aber echte i18n-Luecke
innerhalb einer sonst korrekt uebersetzten Datei."""

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


def _swatch(qtbot, skip_stitching: bool):
    from pysticky.ui.widgets.color_bar import ColorSwatch

    pattern = Pattern(name="Test", width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    entry = pattern.color_entries[0]
    entry.stitch_count = 7
    entry.skip_stitching = skip_stitching

    swatch = ColorSwatch(0, entry)
    qtbot.addWidget(swatch)
    return swatch


def test_tooltip_stitch_count_is_translated(qtbot, english_language):
    swatch = _swatch(qtbot, skip_stitching=False)
    tooltip = swatch._create_tooltip()

    assert "7 stitches" in tooltip
    assert "Stiche" not in tooltip


def test_tooltip_skip_marker_is_translated(qtbot, english_language):
    swatch = _swatch(qtbot, skip_stitching=True)
    tooltip = swatch._create_tooltip()

    assert "Not stitched" in tooltip
    assert "Wird nicht gestickt" not in tooltip
