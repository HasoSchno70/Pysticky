# -*- coding: utf-8 -*-
"""Tests fuer den globalen WheelGuard (verhindert ungewolltes Aendern
von SpinBoxes/ComboBoxes beim Scrollen)."""

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


@pytest.fixture
def guard(qapp):
    """Frischer WheelGuard pro Test."""
    from pysticky.ui.wheel_guard import WheelGuard, uninstall_wheel_guard

    # Pre-cleanup falls ein vorheriger Test stehen blieb
    uninstall_wheel_guard(qapp)
    g = WheelGuard()
    qapp.installEventFilter(g)
    yield g
    qapp.removeEventFilter(g)


def _make_wheel_event(widget):
    """Erzeugt ein synthetisches QWheelEvent."""
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent

    return QWheelEvent(
        QPointF(0, 0),
        QPointF(0, 0),
        QPoint(0, -120),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )


def test_spinbox_value_unchanged_without_focus(qapp, guard):
    """SpinBox ohne Fokus: Wheel-Event aendert den Wert NICHT."""
    from PySide6.QtWidgets import QSpinBox

    sb = QSpinBox()
    sb.setRange(0, 100)
    sb.setValue(42)
    initial = sb.value()

    qapp.sendEvent(sb, _make_wheel_event(sb))
    assert sb.value() == initial


def test_spinbox_value_changes_with_focus(qapp, guard):
    """SpinBox MIT Fokus: Wheel-Event funktioniert weiter normal."""
    from PySide6.QtWidgets import QSpinBox

    sb = QSpinBox()
    sb.setRange(0, 100)
    sb.setValue(42)
    sb.show()
    sb.setFocus()
    qapp.processEvents()
    # Sicherstellen dass Fokus tatsaechlich gesetzt ist (Headless-Mode
    # kann das anders handhaben, daher direkt pruefen)
    if not sb.hasFocus():
        # Test braucht echten Window-Manager-Fokus, der headless nicht
        # zuverlaessig laeuft. In dem Fall ueberspringen wir.
        sb.hide()
        pytest.skip("Focus konnte nicht gesetzt werden (headless)")

    initial = sb.value()
    qapp.sendEvent(sb, _make_wheel_event(sb))
    # Mit Fokus sollte das Wheel den Wert aendern
    assert sb.value() != initial
    sb.hide()


def test_combobox_index_unchanged_without_focus(qapp, guard):
    """ComboBox ohne Fokus: Wheel-Event aendert den Index NICHT."""
    from PySide6.QtWidgets import QComboBox

    cb = QComboBox()
    cb.addItems(["A", "B", "C"])
    cb.setCurrentIndex(1)
    initial = cb.currentIndex()

    qapp.sendEvent(cb, _make_wheel_event(cb))
    assert cb.currentIndex() == initial


def test_slider_value_unchanged_without_focus(qapp, guard):
    """Slider ohne Fokus: Wheel-Event aendert den Wert NICHT."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QSlider

    s = QSlider(Qt.Orientation.Horizontal)
    s.setRange(0, 100)
    s.setValue(50)
    initial = s.value()

    qapp.sendEvent(s, _make_wheel_event(s))
    assert s.value() == initial


def test_other_widgets_unaffected(qapp, guard):
    """QPushButton bekommt Wheel-Events ganz normal — kein Eingriff.

    Regression (Test-Qualitaets-Audit): die vorherige Version hatte gar
    keine Assertion ("kein Pruef-Effekt") -- ein Guard, der versehentlich
    ALLE Widget-Typen abfaengt (z.B. GUARDED_TYPES-Check entfernt/kaputt),
    waere nie aufgefallen, solange nichts crasht. eventFilter() wird jetzt
    direkt aufgerufen und muss fuer einen QPushButton False liefern
    ("nicht behandelt", Event geht normal an den Button durch).
    """
    from PySide6.QtWidgets import QPushButton

    btn = QPushButton("X")
    handled = guard.eventFilter(btn, _make_wheel_event(btn))
    assert handled is False, (
        "Regression: WheelGuard greift bei einem nicht-gesperrten Widget-Typ ein"
    )


def test_install_wheel_guard_is_idempotent(qapp):
    """install_wheel_guard kann mehrfach aufgerufen werden ohne Probleme."""
    from pysticky.ui.wheel_guard import install_wheel_guard, uninstall_wheel_guard

    uninstall_wheel_guard(qapp)
    g1 = install_wheel_guard(qapp)
    g2 = install_wheel_guard(qapp)
    assert g1 is g2  # Singleton
    uninstall_wheel_guard(qapp)
