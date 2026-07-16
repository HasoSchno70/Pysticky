"""
Wheel-Guard: globaler EventFilter, der Mausrad-Events auf SpinBox /
ComboBox / Slider nur durchlässt, wenn das Widget Tastatur-Fokus hat.

Hintergrund: Qt's Default-Verhalten leitet jedes Wheel-Event an das Widget
unter dem Mauszeiger weiter — auch wenn der User nur scrollen wollte und
gar nicht das Eingabefeld ändern. In Settings-Dialogen mit ScrollArea
führt das zu versehentlichen Wert-Änderungen.

Lösung: WheelGuard wird als ApplicationEventFilter installiert. Bei jedem
Wheel-Event auf einem SpinBox/ComboBox/Slider:
- Wenn das Widget hasFocus(): normal verarbeiten.
- Sonst: Event blockieren und an das Parent weitergeben (ScrollArea kann scrollen).
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QSlider,
    QWidget,
)


class WheelGuard(QObject):
    """ApplicationEventFilter gegen versehentliche Wheel-Änderungen."""

    # Widget-Typen, die vom Guard betroffen sind. Andere Widgets (z.B. Canvas)
    # bekommen ihre Wheel-Events wie gewohnt.
    GUARDED_TYPES: tuple[type, ...] = (
        QAbstractSpinBox,
        QComboBox,
        QSlider,
    )

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() != QEvent.Type.Wheel:
            return False
        if not isinstance(obj, self.GUARDED_TYPES):
            return False
        # Nur akzeptieren wenn Tastatur-Fokus aktiv ist. Sonst blockieren —
        # Qt leitet das Event dann ans Parent (typischerweise ein
        # ScrollArea, was den gewünschten Scroll-Effekt liefert).
        if isinstance(obj, QWidget) and obj.hasFocus():
            return False
        # Verarbeitet als "behandelt" markieren -> nicht weiter an das Widget,
        # aber Event nicht akzeptieren, damit das Parent es bekommt.
        event.ignore()
        return True


_guard_instance: WheelGuard | None = None


def install_wheel_guard(app) -> WheelGuard:
    """Installiert den WheelGuard auf der gegebenen QApplication.

    Idempotent — wiederholte Aufrufe registrieren den Guard nicht mehrfach.
    Returns:
        Die WheelGuard-Instanz (z.B. für Teardown in Tests).
    """
    global _guard_instance
    if _guard_instance is None:
        _guard_instance = WheelGuard()
    # installEventFilter ist idempotent — Qt verhindert Mehrfach-Installation
    # desselben Filter-Objekts.
    app.installEventFilter(_guard_instance)
    return _guard_instance


def uninstall_wheel_guard(app) -> None:
    """Entfernt den globalen WheelGuard (vor allem für Tests)."""
    global _guard_instance
    if _guard_instance is not None:
        app.removeEventFilter(_guard_instance)
