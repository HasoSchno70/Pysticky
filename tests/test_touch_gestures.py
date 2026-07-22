# -*- coding: utf-8 -*-
"""Tests fuer Touch-Gesten (Pinch-Zoom) im Canvas.

Echtes Pinch-Gesture-Testing braucht Touch-Hardware oder einen Touch-
Simulator — was wir hier nicht haben. Wir testen die Mechanik:
- Setting steuert das Aktivieren
- Apply-Method liest das Setting und ruft grabGesture
- `_handle_gesture` liefert false bei nicht-Pinch-Events
"""

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
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    yield app


def _make_canvas(qapp):
    """Erzeugt eine minimale Canvas-Instanz fuer Headless-Tests."""
    from pysticky.core import Pattern
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    pattern = Pattern(name="Test", width=20, height=20)
    canvas.set_pattern(pattern)
    return canvas


def test_touch_default_setting_is_disabled(qapp):
    """Default: touch/gestures_enabled = False."""
    from PySide6.QtCore import QSettings, Qt

    s = QSettings()
    s.remove("touch/gestures_enabled")  # zuerst zuruecksetzen

    canvas = _make_canvas(qapp)
    canvas._apply_touch_setting()
    assert canvas.testAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents) is False


def test_touch_setting_enabled_grabs_gesture(qapp):
    """Wenn Setting auf True: WA_AcceptTouchEvents wird gesetzt und Gesture gegrabbed."""
    from PySide6.QtCore import QSettings, Qt

    s = QSettings()
    s.setValue("touch/gestures_enabled", True)
    s.sync()

    try:
        canvas = _make_canvas(qapp)
        canvas._apply_touch_setting()
        assert canvas.testAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents) is True
    finally:
        s.setValue("touch/gestures_enabled", False)
        s.sync()


def test_touch_setting_disabled_releases_gesture(qapp):
    """Wenn Setting auf False: Touch wird wieder deaktiviert."""
    from PySide6.QtCore import QSettings, Qt

    canvas = _make_canvas(qapp)

    s = QSettings()
    s.setValue("touch/gestures_enabled", True)
    s.sync()
    canvas._apply_touch_setting()
    assert canvas.testAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents) is True

    s.setValue("touch/gestures_enabled", False)
    s.sync()
    canvas._apply_touch_setting()
    assert canvas.testAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents) is False


def test_event_passes_non_gesture_to_super(qapp):
    """Nicht-Gesture-Events werden an super().event() weitergereicht und
    landen dadurch bei den regulaeren Qt-Handlern (z.B. keyPressEvent).

    Runde 28: die vorherige Version pruefte nur `isinstance(result, bool)`
    -- das waere selbst dann True gewesen, wenn TabletGestureMixin.event()
    JEDES Event verschluckt haette (jeder Rueckgabewert ist ein bool). Jetzt
    wird per Spy auf keyPressEvent tatsaechlich verifiziert, dass ein
    Tastatur-Event wirklich durchgereicht und vom Widget behandelt wird.
    """
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent

    canvas = _make_canvas(qapp)

    called = []
    canvas.keyPressEvent = lambda event: called.append(event)

    key_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)
    canvas.event(key_event)

    assert len(called) == 1, "Regression: Tastatur-Event wurde nicht an keyPressEvent durchgereicht"


def test_pinch_state_resets_scale_on_start(qapp):
    """Beim Start einer Pinch-Geste wird _gesture_last_scale auf 1.0
    zurueckgesetzt (Runde 28: die vorherige Version dieses Tests pruefte
    trotz ihres Docstrings nur `hasattr(canvas, "_gesture_last_scale")` --
    das waere auch bei komplett fehlendem Reset immer True gewesen, der
    Test haette also JEDE Regression durchgelassen. Echtes QPinchGesture
    laesst sich nicht direkt konstruieren (kommt nur vom Qt-Gesture-
    Recognizer), aber MagicMock(spec=QPinchGesture) besteht den
    isinstance()-Check in _handle_gesture() und macht so einen echten
    End-to-End-Test der Reset-Logik moeglich."""
    from unittest.mock import MagicMock

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QGestureEvent, QPinchGesture

    canvas = _make_canvas(qapp)
    canvas._gesture_last_scale = 2.5

    pinch = MagicMock(spec=QPinchGesture)
    pinch.state.return_value = Qt.GestureState.GestureStarted
    event = MagicMock(spec=QGestureEvent)
    event.gesture.return_value = pinch

    handled = canvas._handle_gesture(event)

    assert handled is True
    assert canvas._gesture_last_scale == 1.0, (
        "Regression: GestureStarted setzte _gesture_last_scale nicht auf 1.0 zurueck"
    )


def test_canvas_has_pinch_gesture_handler(qapp):
    """Canvas hat die _handle_gesture-Methode (von Mixin)."""
    canvas = _make_canvas(qapp)
    assert hasattr(canvas, "_handle_gesture")
    assert callable(canvas._handle_gesture)


def test_settings_dialog_applies_touch_setting_live(qapp, qtbot):
    """Regression (Runde 14): der Tooltip der Touch-Gesten-Checkbox
    verspricht "Aenderung wird sofort uebernommen", aber
    _apply_settings_from_dialog() (der zentrale Live-Reapply-Pfad nach
    Settings-Dialog-OK) rief canvas._apply_touch_setting() nie auf --
    nur Canvas.__init__ tat das, einmalig beim Programmstart. Toggle der
    Checkbox + OK hatte dadurch bis zum Neustart keine Wirkung, obwohl
    der Tooltip live-Wirkung versprach."""
    from PySide6.QtCore import QSettings, Qt

    from pysticky.ui.main_window import MainWindow

    s = QSettings()
    old = s.value("touch/gestures_enabled")
    try:
        s.setValue("touch/gestures_enabled", False)
        s.sync()

        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()
        assert w.canvas.testAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents) is False

        s.setValue("touch/gestures_enabled", True)
        s.sync()
        w._apply_settings_from_dialog()

        assert w.canvas.testAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents) is True
    finally:
        if old is None:
            s.remove("touch/gestures_enabled")
        else:
            s.setValue("touch/gestures_enabled", old)
