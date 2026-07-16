# -*- coding: utf-8 -*-
"""Tests für die gemeinsamen Helfer (color_utils, clamp, css_rgb)."""


def test_clamp():
    from pysticky.utils import clamp, clamp_int

    assert clamp(5, 0, 3) == 3
    assert clamp(-1, 0, 3) == 0
    assert clamp(2, 0, 3) == 2
    assert clamp(2.5, 0.0, 10.0) == 2.5
    assert clamp_int(300, 0, 255) == 255
    assert isinstance(clamp_int(300, 0, 255), int)


def test_css_rgb():
    from pysticky.io.export_common import css_rgb

    assert css_rgb((255, 128, 0)) == "rgb(255,128,0)"
    assert css_rgb((0, 0, 0)) == "rgb(0,0,0)"


def test_to_qcolor_roundtrip(qapp):
    from pysticky.core.thread import ThreadColor
    from pysticky.ui.color_utils import from_qcolor, to_qcolor

    color = ThreadColor(12, 200, 99)
    qcolor = to_qcolor(color)
    assert (qcolor.red(), qcolor.green(), qcolor.blue(), qcolor.alpha()) == (12, 200, 99, 255)

    translucent = to_qcolor(color, alpha=128)
    assert translucent.alpha() == 128

    assert from_qcolor(qcolor) == color


def test_color_swatch_icon_variants(qapp):
    from pysticky.core.thread import ThreadColor
    from pysticky.ui.color_utils import color_swatch_icon

    color = ThreadColor(200, 30, 30)
    for kwargs in ({}, {"rounded": True}, {"border": False}):
        icon = color_swatch_icon(color, 18, **kwargs)
        assert not icon.isNull()
        assert icon.pixmap(18, 18).size().width() == 18

    # QColor wird ebenfalls akzeptiert
    from PySide6.QtGui import QColor

    assert not color_swatch_icon(QColor(1, 2, 3), 16).isNull()
