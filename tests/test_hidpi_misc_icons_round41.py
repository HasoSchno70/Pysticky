# -*- coding: utf-8 -*-
"""Regressionstests (HiDPI-Audit Runde 41, Nachtrag zu Runde 40):

Runde 40 hatte den IconProvider (`ui/icons/icon_provider.py`) auf physische
Pixel umgestellt, dabei aber festgestellt, dass fünf weitere Stellen ihr
eigenes, unabhängiges `QPixmap` rendern (Dot-Marker für Dock-Tabs,
Toolbar-Emoji-Icons, Layer-Panel Augen-/Schloss-Icons, Palette-Panel
Farb-Swatches, `color_swatch_icon`) und denselben Grundfehler zeigen -- immer
mit 1 physischem Pixel pro logischem Pixel angelegt, unabhängig vom
tatsächlichen Bildschirm-`devicePixelRatio()`. Diese Runde fixt alle fünf
einzeln (keine gemeinsame Abstraktion -- fünf unabhängige Handschriften,
siehe Runde 40 Begründung) nach demselben Muster wie
`IconProvider._render_emoji_icon`: Pixmap in physischen Pixeln
(`round(size * dpr)`) anlegen, `setDevicePixelRatio(dpr)` setzen, alle
Zeichenoperationen unverändert in logischen Koordinaten belassen. Keine der
fünf Funktionen cached ihr Ergebnis (alle rendern bei jedem Aufruf neu), daher
ist in keinem Fall eine Cache-Key-Änderung nötig."""

import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

pytestmark = pytest.mark.usefixtures("qtbot")


def _primary_screen():
    screen = QApplication.primaryScreen()
    assert screen is not None, "Test benötigt eine echte QApplication mit Bildschirm"
    return screen


def test_make_dot_icon_is_crisp_at_hidpi_scale_factor(monkeypatch):
    """`mw_docks_mixin._make_dot_icon` muss bei devicePixelRatio=1.5 eine
    Pixmap mit 1.5 physischen Pixeln pro logischem Pixel liefern."""
    from PySide6.QtCore import QSize

    from pysticky.ui.builders.mw_docks_mixin import _make_dot_icon

    screen = _primary_screen()
    monkeypatch.setattr(type(screen), "devicePixelRatio", lambda self: 1.5)

    size = 14
    icon = _make_dot_icon("#ff0000", size=size)

    assert QSize(round(size * 1.5), round(size * 1.5)) in icon.availableSizes(), (
        "Regression: _make_dot_icon ignoriert das Bildschirm-devicePixelRatio -- "
        "die hinterlegte Pixmap liegt nicht in physischen Pixeln vor"
    )


def test_create_emoji_icon_is_crisp_at_hidpi_scale_factor(monkeypatch, qtbot):
    """`mw_toolbar_mixin.ToolbarBuilderMixin._create_emoji_icon` muss bei
    devicePixelRatio=1.5 eine Pixmap mit 1.5 physischen Pixeln pro logischem
    Pixel liefern."""
    from pysticky.ui.builders.mw_toolbar_mixin import ToolbarBuilderMixin

    screen = _primary_screen()
    monkeypatch.setattr(type(screen), "devicePixelRatio", lambda self: 1.5)

    class _Host(ToolbarBuilderMixin):
        pass

    host = _Host()
    size = 24
    pixmap = host._create_emoji_icon("✏", size)

    assert pixmap.devicePixelRatio() == 1.5, (
        "Regression: _create_emoji_icon wurde ohne devicePixelRatio angelegt -- "
        "auf einem HiDPI-Bildschirm rendert Qt sie dadurch unscharf hochskaliert"
    )
    assert pixmap.width() == round(size * 1.5)
    assert pixmap.height() == round(size * 1.5)
    assert pixmap.size().width() / pixmap.devicePixelRatio() == size
    assert pixmap.size().height() / pixmap.devicePixelRatio() == size


def test_make_eye_icon_is_crisp_at_hidpi_scale_factor(monkeypatch):
    """`layer_panel._make_eye_icon` muss bei devicePixelRatio=1.5 eine Pixmap
    mit 1.5 physischen Pixeln pro logischem Pixel liefern."""
    from PySide6.QtCore import QSize

    from pysticky.ui.panels.layer_panel import _make_eye_icon

    screen = _primary_screen()
    monkeypatch.setattr(type(screen), "devicePixelRatio", lambda self: 1.5)

    size = 20
    icon = _make_eye_icon(True, QColor("white"), size=size)

    assert QSize(round(size * 1.5), round(size * 1.5)) in icon.availableSizes(), (
        "Regression: _make_eye_icon ignoriert das Bildschirm-devicePixelRatio -- "
        "die hinterlegte Pixmap liegt nicht in physischen Pixeln vor"
    )


def test_make_lock_icon_is_crisp_at_hidpi_scale_factor(monkeypatch):
    """`layer_panel._make_lock_icon` muss bei devicePixelRatio=1.5 eine Pixmap
    mit 1.5 physischen Pixeln pro logischem Pixel liefern."""
    from PySide6.QtCore import QSize

    from pysticky.ui.panels.layer_panel import _make_lock_icon

    screen = _primary_screen()
    monkeypatch.setattr(type(screen), "devicePixelRatio", lambda self: 1.5)

    size = 20
    icon = _make_lock_icon(False, QColor("white"), size=size)

    assert QSize(round(size * 1.5), round(size * 1.5)) in icon.availableSizes(), (
        "Regression: _make_lock_icon ignoriert das Bildschirm-devicePixelRatio -- "
        "die hinterlegte Pixmap liegt nicht in physischen Pixeln vor"
    )


def test_create_color_icon_is_crisp_at_hidpi_scale_factor(monkeypatch, qtbot):
    """`palette_panel.PalettePanel._create_color_icon` muss bei
    devicePixelRatio=1.5 eine Pixmap mit 1.5 physischen Pixeln pro logischem
    Pixel liefern."""
    from pysticky.core import Thread
    from pysticky.ui.panels.palette_panel import PalettePanel

    screen = _primary_screen()
    monkeypatch.setattr(type(screen), "devicePixelRatio", lambda self: 1.5)

    panel = PalettePanel()
    qtbot.addWidget(panel)
    thread = Thread.from_hex("Rot", "#FF0000")

    pixmap = panel._create_color_icon(thread, False)

    size = panel.ICON_SIZE
    assert pixmap.devicePixelRatio() == 1.5, (
        "Regression: _create_color_icon wurde ohne devicePixelRatio angelegt -- "
        "auf einem HiDPI-Bildschirm rendert Qt sie dadurch unscharf hochskaliert"
    )
    assert pixmap.width() == round(size * 1.5)
    assert pixmap.height() == round(size * 1.5)
    assert pixmap.size().width() / pixmap.devicePixelRatio() == size
    assert pixmap.size().height() / pixmap.devicePixelRatio() == size


def test_color_swatch_icon_is_crisp_at_hidpi_scale_factor(monkeypatch):
    """`color_utils.color_swatch_icon` muss bei devicePixelRatio=1.5 eine
    Pixmap mit 1.5 physischen Pixeln pro logischem Pixel liefern (für alle
    drei Zeichenpfade: rounded, border, plain fill)."""
    from PySide6.QtCore import QSize

    from pysticky.ui.color_utils import color_swatch_icon

    screen = _primary_screen()
    monkeypatch.setattr(type(screen), "devicePixelRatio", lambda self: 1.5)

    size = 16
    expected = QSize(round(size * 1.5), round(size * 1.5))

    for kwargs in ({"rounded": True}, {"border": True}, {"border": False}):
        icon = color_swatch_icon(QColor("#00ff00"), size=size, **kwargs)
        assert expected in icon.availableSizes(), (
            f"Regression: color_swatch_icon({kwargs}) ignoriert das "
            "Bildschirm-devicePixelRatio -- die hinterlegte Pixmap liegt "
            "nicht in physischen Pixeln vor"
        )
