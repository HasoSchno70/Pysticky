# -*- coding: utf-8 -*-
"""Regressionstest (Runde 26): path_preview.py hatte KEINE i18n-Abdeckung
(kein `t()`-Import) -- Hover-Tooltip, das Info-Overlay im Widget und die
Legende in render_to_image() (fuer Export) waren alle rohe deutsche
f-Strings. Im Englisch-Modus blieben Stickpfad-Tooltip und Export-Legende
dauerhaft deutsch, waehrend praktisch jeder andere UI-Text der App
uebersetzt wird."""

from unittest.mock import patch

import pytest

from pysticky.core import ColorPath, Pattern, StitchStep, Thread
from pysticky.core.i18n import set_language

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture
def english_language():
    set_language("en")
    try:
        yield
    finally:
        set_language("de")


def _widget_with_path(qtbot):
    from pysticky.ui.widgets.path_preview import PathPreviewWidget

    pattern = Pattern(name="Test", width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.set_stitch(0, 0, 0)
    pattern.set_stitch(1, 1, 0)

    color_path = ColorPath(
        color_index=0,
        steps=[
            StitchStep(x=0, y=0, color_index=0, step_number=1, distance_from_prev=0.0),
            StitchStep(
                x=1, y=1, color_index=0, step_number=2, distance_from_prev=1.4, is_jump=True
            ),
        ],
        total_distance=1.4,
        jump_count=1,
        stitch_count=2,
    )

    widget = PathPreviewWidget()
    qtbot.addWidget(widget)
    widget.set_pattern(pattern)
    widget.set_color_path(color_path)
    return widget


def test_render_to_image_legend_is_translated(qtbot, english_language):
    widget = _widget_with_path(qtbot)

    drawn_texts = []
    from PySide6.QtGui import QPainter

    orig_draw_text = QPainter.drawText

    def _spy_draw_text(self, *args, **kwargs):
        for arg in args:
            if isinstance(arg, str):
                drawn_texts.append(arg)
        return orig_draw_text(self, *args, **kwargs)

    with patch.object(QPainter, "drawText", _spy_draw_text):
        image = widget.render_to_image()

    assert image is not None
    joined = "\n".join(drawn_texts)
    assert "Color:" in joined
    assert "Stitches:" in joined
    assert "Farbe" not in joined
    assert "Stiche" not in joined


def test_hover_tooltip_is_translated(qtbot, english_language):
    from PySide6.QtCore import QPointF

    widget = _widget_with_path(qtbot)
    widget.resize(300, 300)

    captured = {}

    def _fake_show_tooltip(text, pos):
        captured["text"] = text

    with patch("pysticky.ui.widgets.path_preview.show_custom_tooltip", _fake_show_tooltip):
        with patch.object(
            widget,
            "_stitch_at_pos",
            return_value=widget._color_path.steps[1],
        ):
            widget.mouseMoveEvent(
                type(
                    "FakeEvent",
                    (),
                    {
                        "position": lambda self=None: QPointF(10, 10),
                        "globalPosition": lambda self=None: QPointF(10, 10),
                        "buttons": lambda self=None: 0,
                        "accept": lambda self=None: None,
                    },
                )()
            )

    assert "text" in captured
    assert "Step" in captured["text"]
    assert "Jump" in captured["text"]
    assert "Schritt" not in captured["text"]
    assert "Sprung" not in captured["text"]
