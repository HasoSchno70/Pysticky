"""Regressionstests fuer ui/widgets/custom_tooltip.py (Runde 65 Clean-Code-Audit).

Deckt Grenzfaelle ab: echter globalPos()-Laufzeit-Aufruf ueber einen simulierten
QHelpEvent, Bildschirmrand-Positionierung, ungewoehnlich langer Tooltip-Text,
schnelles Hover-Wechseln zwischen Widgets und ein waehrend der Anzeige
zerstoertes Anker-Widget.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QPoint
from PySide6.QtGui import QHelpEvent
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from pysticky.ui.widgets.custom_tooltip import (
    _get_instance,
    _TooltipEventFilter,
    hide_custom_tooltip,
    reapply_custom_tooltip_theme,
    show_custom_tooltip,
)

pytestmark = pytest.mark.usefixtures("qtbot")


def test_tooltip_event_calls_globalpos_without_attributeerror(qtbot):
    """QEvent.ToolTip-Events sind zur Laufzeit QHelpEvent-Instanzen, die
    globalPos() weiterhin unterstuetzen (nur der mypy-Stub fuer die
    Basisklasse QEvent kennt die Methode nicht mehr) -- kein echter
    AttributeError beim tatsaechlichen Hover ueber ein Widget."""
    widget = QWidget()
    widget.setToolTip("Hover-Text")
    qtbot.addWidget(widget)

    event = QHelpEvent(QEvent.Type.ToolTip, QPoint(5, 5), QPoint(50, 60))
    event_filter = _TooltipEventFilter()

    # Darf keinen AttributeError werfen -- das war der konkrete Verdacht.
    handled = event_filter.eventFilter(widget, event)

    assert handled is True
    assert _get_instance().isVisible()
    hide_custom_tooltip()


def test_tooltip_stays_within_screen_near_bottom_right_corner(qtbot):
    """Nahe der rechten/unteren Bildschirmkante darf der Tooltip nicht ausserhalb
    des sichtbaren Bereichs landen."""
    screen = QApplication.primaryScreen()
    geo = screen.availableGeometry()

    pos = QPoint(geo.right() - 5, geo.bottom() - 5)
    show_custom_tooltip("Ein kurzer Tooltip-Text", pos)

    inst = _get_instance()
    assert geo.contains(inst.geometry()), (
        f"Tooltip-Geometrie {inst.geometry()} liegt ausserhalb des Bildschirms {geo}"
    )
    hide_custom_tooltip()


def test_very_long_tooltip_text_does_not_crash_and_stays_reachable(qtbot):
    """Regressionstest: Ein Tooltip, dessen Inhalt (ohne Wortumbruch) breiter als
    der Bildschirm ist, wurde vor dem Fix durch die reine Rechts-Randkorrektur
    weit ins Negative geschoben und war dadurch komplett unsichtbar/ausserhalb
    des Monitors -- selbst wenn die Anzeigeposition mittig auf dem Bildschirm
    lag. Nach dem Fix bleibt zumindest die linke obere Ecke auf dem Bildschirm."""
    screen = QApplication.primaryScreen()
    geo = screen.availableGeometry()

    long_text = "X" * 500
    pos = geo.center()

    # Darf nicht crashen:
    show_custom_tooltip(long_text, pos)

    inst = _get_instance()
    assert inst.x() >= geo.left(), (
        f"Tooltip x={inst.x()} liegt links ausserhalb des Bildschirms (left={geo.left()})"
    )
    assert inst.y() >= geo.top(), (
        f"Tooltip y={inst.y()} liegt oberhalb des Bildschirms (top={geo.top()})"
    )
    hide_custom_tooltip()


def test_rapid_hover_switch_shows_only_one_tooltip_with_latest_text(qtbot):
    """Schnelles Hover-Wechseln zwischen zwei Widgets (B wird angezeigt, bevor A
    explizit versteckt wurde) darf keine doppelten Tooltip-Fenster erzeugen --
    das Singleton-Popup wird wiederverwendet und zeigt nur den zuletzt gesetzten
    Text."""
    widget_a = QWidget()
    widget_b = QWidget()
    qtbot.addWidget(widget_a)
    qtbot.addWidget(widget_b)

    show_custom_tooltip("Text A", QPoint(10, 10), widget_a)
    inst_after_a = _get_instance()

    # B wird gezeigt, OHNE dass A vorher explizit versteckt wurde (simuliert
    # schnelles Hover-Wechseln).
    show_custom_tooltip("Text B", QPoint(20, 20), widget_b)
    inst_after_b = _get_instance()

    assert inst_after_a is inst_after_b, "Es darf nur ein Singleton-Tooltip-Fenster geben"
    label = inst_after_b.findChild(QLabel)
    assert label is not None
    assert label.text() == "Text B"
    hide_custom_tooltip()


def test_hide_after_anchor_widget_destroyed_does_not_raise(qtbot):
    """Wird das Anker-Widget waehrend der Tooltip sichtbar ist zerstoert, darf
    weder ein erneutes Verstecken noch ein Theme-Wechsel einen RuntimeError auf
    einem zerstoerten Qt-Objekt auesloesen (aehnliche Fehlerklasse wie der in
    Runde 63 gefixte Minimap-Timer-Crash)."""
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.resize(40, 20)

    show_custom_tooltip("Verankerter Text", QPoint(15, 15), widget)
    assert _get_instance().isVisible()

    widget.deleteLater()
    qtbot.wait(10)

    # Darf keinen RuntimeError werfen, obwohl das urspruengliche Anker-Widget
    # inzwischen zerstoert ist -- show_at() haelt keine Referenz darauf.
    hide_custom_tooltip()
    reapply_custom_tooltip_theme()
