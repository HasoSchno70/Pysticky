# -*- coding: utf-8 -*-
"""
Tests fuer Hover-Auto-Scroll der Farbleiste (ColorBar).

Analog zur oberen IconToolBar (widgets/icon_toolbar.py): statt nur des
klassischen Scrollbalkens soll die Maus am linken/rechten Rand der
Farbleiste automatisch scrollen, wenn mehr Farben vorhanden sind als auf
den Bildschirm passen.
"""

from PySide6.QtGui import QCursor

from pysticky.core import Pattern, Thread
from pysticky.ui.widgets.color_bar import ColorBar


def _pattern_with_many_colors(n: int) -> Pattern:
    """Erzeugt ein Pattern mit `n` Farben -- genug, um die Farbleiste bei
    normaler Fensterbreite garantiert zum Ueberlaufen zu bringen."""
    pattern = Pattern(name="Viele Farben", width=10, height=10)
    pattern.color_entries.clear()
    for i in range(n):
        pattern.add_color(Thread.from_hex(f"Farbe{i}", f"#{i:06x}"))
    return pattern


def _make_overflowing_bar(qtbot):
    bar = ColorBar()
    qtbot.addWidget(bar)
    bar.resize(300, 96)  # schmal genug, dass 60 Farben nicht hineinpassen
    bar.set_pattern(_pattern_with_many_colors(60))
    bar.show()
    return bar


def test_scroll_hints_hidden_when_content_fits(qtbot):
    """Wenige Farben, keine Ueberlauf -- keine Scroll-Hinweise noetig."""
    bar = ColorBar()
    qtbot.addWidget(bar)
    bar.resize(800, 96)
    bar.set_pattern(_pattern_with_many_colors(3))
    bar.show()

    bar._update_scroll_hints()
    assert bar._scroll_hint_left.isVisible() is False
    assert bar._scroll_hint_right.isVisible() is False


def test_scroll_hint_right_visible_when_scrolled_to_start(qtbot):
    """Am linken Rand (Start) muss nur der rechte Hinweis sichtbar sein --
    es gibt noch mehr Farben rechts, aber keine links."""
    bar = _make_overflowing_bar(qtbot)
    bar_scrollbar = bar._scroll.horizontalScrollBar()
    assert bar_scrollbar.maximum() > bar_scrollbar.minimum(), "Test-Setup muss ueberlaufen"

    bar._update_scroll_hints()
    assert bar._scroll_hint_left.isVisible() is False
    assert bar._scroll_hint_right.isVisible() is True


def test_scroll_hint_left_visible_when_scrolled_to_end(qtbot):
    """Am rechten Rand (Ende) muss nur der linke Hinweis sichtbar sein."""
    bar = _make_overflowing_bar(qtbot)
    scrollbar = bar._scroll.horizontalScrollBar()
    scrollbar.setValue(scrollbar.maximum())

    bar._update_scroll_hints()
    assert bar._scroll_hint_left.isVisible() is True
    assert bar._scroll_hint_right.isVisible() is False


def test_hover_left_edge_scrolls_left(qtbot, monkeypatch):
    """Maus in die linke Hover-Zone -> Scrollbalken bewegt sich nach links."""
    bar = _make_overflowing_bar(qtbot)
    scrollbar = bar._scroll.horizontalScrollBar()
    scrollbar.setValue(scrollbar.maximum())  # erst ans Ende, damit links Platz zum Scrollen ist
    start_value = scrollbar.value()

    viewport = bar._scroll.viewport()
    hover_pos = viewport.mapToGlobal(viewport.rect().topLeft())
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: hover_pos))

    bar._poll_auto_scroll()

    assert scrollbar.value() < start_value


def test_hover_right_edge_scrolls_right(qtbot, monkeypatch):
    """Maus in die rechte Hover-Zone -> Scrollbalken bewegt sich nach rechts."""
    bar = _make_overflowing_bar(qtbot)
    scrollbar = bar._scroll.horizontalScrollBar()
    assert scrollbar.value() == scrollbar.minimum()  # Start: ganz links

    viewport = bar._scroll.viewport()
    hover_pos = viewport.mapToGlobal(viewport.rect().topRight())
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: hover_pos))

    bar._poll_auto_scroll()

    assert scrollbar.value() > scrollbar.minimum()


def test_hover_center_does_not_scroll(qtbot, monkeypatch):
    """Maus in der Mitte der Leiste (nicht am Rand) -> kein Auto-Scroll."""
    bar = _make_overflowing_bar(qtbot)
    scrollbar = bar._scroll.horizontalScrollBar()
    start_value = scrollbar.value()

    viewport = bar._scroll.viewport()
    hover_pos = viewport.mapToGlobal(viewport.rect().center())
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: hover_pos))

    bar._poll_auto_scroll()

    assert scrollbar.value() == start_value


def test_auto_scroll_noop_when_content_fits(qtbot, monkeypatch):
    """Ohne Ueberlauf darf _poll_auto_scroll() nichts tun, selbst wenn die
    (dann irrelevante) Cursor-Position zufaellig am Rand liegt."""
    bar = ColorBar()
    qtbot.addWidget(bar)
    bar.resize(800, 96)
    bar.set_pattern(_pattern_with_many_colors(3))
    bar.show()

    scrollbar = bar._scroll.horizontalScrollBar()
    assert scrollbar.maximum() == scrollbar.minimum()

    viewport = bar._scroll.viewport()
    hover_pos = viewport.mapToGlobal(viewport.rect().topLeft())
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: hover_pos))

    bar._poll_auto_scroll()  # darf nicht crashen, Wert bleibt bei 0

    assert scrollbar.value() == 0
