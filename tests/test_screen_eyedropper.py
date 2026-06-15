# -*- coding: utf-8 -*-
"""Tests fuer den Screen-EyeDropper (pick_color_at + find_nearest_thread)."""

import pytest


@pytest.fixture
def qapp():
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWidgets import QApplication

    existing = QCoreApplication.instance()
    if existing is None:
        app = QApplication([])
    else:
        app = existing
    yield app


def _make_pixmap(qapp, color: tuple[int, int, int], size: int = 4):
    """Erzeugt ein einfarbiges QPixmap."""
    from PySide6.QtGui import QColor, QPixmap

    pm = QPixmap(size, size)
    pm.fill(QColor(*color))
    return pm


def test_pick_color_at_returns_correct_color(qapp):
    """pick_color_at liefert die Pixel-Farbe an (x, y)."""
    from pysticky.ui.dialogs import pick_color_at

    pm = _make_pixmap(qapp, (255, 0, 0))
    color = pick_color_at(pm, 1, 1)
    assert color is not None
    assert color.red() == 255
    assert color.green() == 0
    assert color.blue() == 0


def test_pick_color_at_returns_none_for_oob(qapp):
    """Out-of-bounds liefert None."""
    from pysticky.ui.dialogs import pick_color_at

    pm = _make_pixmap(qapp, (255, 0, 0), size=4)
    assert pick_color_at(pm, 10, 10) is None
    assert pick_color_at(pm, -1, 0) is None


def test_pick_color_at_handles_null_pixmap():
    """Null-Pixmap liefert None ohne Crash."""
    from PySide6.QtGui import QPixmap

    from pysticky.ui.dialogs import pick_color_at

    pm = QPixmap()  # null
    assert pick_color_at(pm, 0, 0) is None


def test_find_nearest_thread_returns_dmc_black_for_pure_black(qapp):
    """Pure schwarz mappt auf einen sehr dunklen DMC-Thread."""
    from PySide6.QtGui import QColor

    from pysticky.ui.dialogs import find_nearest_thread

    result = find_nearest_thread(QColor(0, 0, 0))
    assert result is not None
    assert result.color.luminance < 0.15


def test_find_nearest_thread_returns_white_for_pure_white(qapp):
    """Pure weiss mappt auf einen sehr hellen Thread."""
    from PySide6.QtGui import QColor

    from pysticky.ui.dialogs import find_nearest_thread

    result = find_nearest_thread(QColor(255, 255, 255))
    assert result is not None
    assert result.color.luminance > 0.9


def test_find_nearest_thread_returns_red_for_red(qapp):
    """Pure rot mappt auf einen Thread mit R > G und R > B."""
    from PySide6.QtGui import QColor

    from pysticky.ui.dialogs import find_nearest_thread

    result = find_nearest_thread(QColor(255, 0, 0))
    assert result is not None
    assert result.color.r > result.color.g
    assert result.color.r > result.color.b


def test_find_nearest_thread_excludes_beads(qapp):
    """Default-Liste schliesst Mill Hill Beads aus."""
    from PySide6.QtGui import QColor

    from pysticky.ui.dialogs import find_nearest_thread

    # Pearl-aehnliche Farbe (entspricht 02001 Mill Hill Pearl)
    result = find_nearest_thread(QColor(235, 235, 230))
    assert result is not None
    # Sollte aus einer Garn-Palette kommen, nicht aus Mill Hill Beads
    assert (result.manufacturer or "").lower() != "mill hill beads"


def test_find_nearest_thread_respects_explicit_palette_list(qapp):
    """Mit explizitem palette_names werden nur diese durchsucht."""
    from PySide6.QtGui import QColor

    from pysticky.ui.dialogs import find_nearest_thread

    result = find_nearest_thread(QColor(120, 120, 120), palette_names=["Anchor"])
    assert result is not None
    assert result.manufacturer == "Anchor"


def test_find_nearest_thread_empty_palette_list_returns_none(qapp):
    """Leere palette_names-Liste liefert None."""
    from PySide6.QtGui import QColor

    from pysticky.ui.dialogs import find_nearest_thread

    assert find_nearest_thread(QColor(0, 0, 0), palette_names=[]) is None


def test_find_nearest_thread_unknown_palette_skipped(qapp):
    """Unbekannte Palette-Namen werden ignoriert (kein Crash)."""
    from PySide6.QtGui import QColor

    from pysticky.ui.dialogs import find_nearest_thread

    result = find_nearest_thread(
        QColor(255, 0, 0),
        palette_names=["DoesNotExist"],
    )
    assert result is None
