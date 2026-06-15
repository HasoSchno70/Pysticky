"""
Tablet- und Gesten-Event-Mixin für Canvas.

Behandelt alternative Eingabegeräte: Stift-Tablet (Druck-Aufnahme) und
Touch-Pinch-Gesten (Zoom).
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QTabletEvent
from PySide6.QtWidgets import QGestureEvent, QPinchGesture

if TYPE_CHECKING:
    from ..canvas import CrossStitchCanvas


class TabletGestureMixin:
    """Mixin für Tablet- und Touch-Gesten-Events."""

    def event(self: "CrossStitchCanvas", event: QEvent) -> bool:
        """Override fuer Gesture-Events. Maus/Tastatur lassen wir Qt durchreichen."""
        if event.type() == QEvent.Type.Gesture:
            return self._handle_gesture(event)
        return super().event(event)

    def _handle_gesture(self: "CrossStitchCanvas", event: QGestureEvent) -> bool:
        """Verarbeitet Pinch-Gesture fuer Touch-Zoom."""
        pinch = event.gesture(Qt.GestureType.PinchGesture)
        if pinch is None or not isinstance(pinch, QPinchGesture):
            return False

        state = pinch.state()
        if state == Qt.GestureState.GestureStarted:
            self._gesture_last_scale = 1.0
            event.accept()
            return True
        if state in (Qt.GestureState.GestureUpdated, Qt.GestureState.GestureFinished):
            total = float(pinch.totalScaleFactor())
            # Schwelle, damit nicht jeder Mikro-Pinch zoomt
            delta_ratio = total / max(self._gesture_last_scale, 1e-6)
            if delta_ratio > 1.15:
                self.zoom_in()
                self._gesture_last_scale = total
            elif delta_ratio < 1 / 1.15:
                self.zoom_out()
                self._gesture_last_scale = total
            event.accept()
            return True
        return False

    def tabletEvent(self: "CrossStitchCanvas", event: QTabletEvent) -> None:
        """Stift-Pressure aufnehmen.

        Qt sendet bei aktivem Tablet auch synthetische Maus-Events, die
        durch unsere bestehende `mousePressEvent`/`mouseMoveEvent`-Logik
        laufen. Wir speichern hier nur den Pressure-Wert, den das
        Pencil-Tool dann fuer die Brush-Groesse nutzt.
        """
        try:
            pressure = float(event.pressure())
        except (AttributeError, TypeError):
            pressure = 0.0
        self._tablet_pressure = max(0.0, min(1.0, pressure))

        etype = event.type()
        if etype == QEvent.Type.TabletPress:
            self._tablet_in_use = True
        elif etype == QEvent.Type.TabletRelease:
            self._tablet_in_use = False
            self._tablet_pressure = 0.0

        # NICHT accept() — Qt soll die synthetischen Mouse-Events weiter
        # generieren. Ohne ignore() wuerde die Maus-Pipeline ausbleiben.
        event.ignore()
