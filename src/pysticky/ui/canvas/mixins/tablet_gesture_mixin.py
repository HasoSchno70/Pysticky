"""
Tablet- und Gesten-Event-Mixin für Canvas.

Behandelt alternative Eingabegeräte: Stift-Tablet (Druck-Aufnahme) und
Touch-Pinch-Gesten (Zoom).
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QTabletEvent
from PySide6.QtWidgets import QGestureEvent, QPinchGesture

from ....utils import clamp

if TYPE_CHECKING:
    from ..canvas import CrossStitchCanvas


class TabletGestureMixin:
    """Mixin für Tablet- und Touch-Gesten-Events."""

    def event(self: "CrossStitchCanvas", event: QEvent) -> bool:
        """Override für Gesture-Events. Maus/Tastatur lassen wir Qt durchreichen."""
        if event.type() == QEvent.Type.Gesture:
            return self._handle_gesture(event)
        if event.type() == QEvent.Type.TabletLeaveProximity:
            # Der Stift verlaesst den Erkennungsbereich -- Treiber senden
            # das zuverlaessig auch bei einem abrupt unterbrochenen Strich
            # (Stift kippt aus dem Sensorbereich, Fokuswechsel waehrend
            # gedrueckt), OHNE dass danach zwingend ein TabletRelease folgt.
            # Ohne diesen Reset blieb _tablet_in_use/_tablet_pressure auf
            # dem letzten Stand haengen -- ein spaeterer normaler Maus-Klick
            # wurde dadurch faelschlich als druckbasierter (Brush-)Stich
            # interpretiert.
            self._tablet_in_use = False
            self._tablet_pressure = 0.0
        return super().event(event)

    def _handle_gesture(self: "CrossStitchCanvas", event: QGestureEvent) -> bool:
        """Verarbeitet Pinch-Gesture für Touch-Zoom."""
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
        Pencil-Tool dann für die Brush-Größe nutzt.
        """
        try:
            pressure = float(event.pressure())
        except (AttributeError, TypeError):
            pressure = 0.0
        self._tablet_pressure = clamp(pressure, 0.0, 1.0)

        etype = event.type()
        if etype == QEvent.Type.TabletPress:
            self._tablet_in_use = True
        elif etype == QEvent.Type.TabletRelease:
            self._tablet_in_use = False
            self._tablet_pressure = 0.0

        # NICHT accept() — Qt soll die synthetischen Mouse-Events weiter
        # generieren. Ohne ignore() würde die Maus-Pipeline ausbleiben.
        event.ignore()
