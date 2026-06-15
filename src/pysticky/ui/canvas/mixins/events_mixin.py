"""
Event-Handler-Mixin für Canvas.

Enthält alle Maus- und Tastatur-Event-Handler.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QMouseEvent, QTabletEvent, QWheelEvent
from PySide6.QtWidgets import QGestureEvent, QPinchGesture

from ...tools.progress_tool import MARK_COMPLETED, UNMARK_COMPLETED
from ...tools.tool_enum import Tool

if TYPE_CHECKING:
    from ..canvas import CrossStitchCanvas


class EventsMixin:
    """Mixin für Event-Handler."""

    def wheelEvent(self: "CrossStitchCanvas", event: QWheelEvent) -> None:
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()

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

    def mousePressEvent(self: "CrossStitchCanvas", event: QMouseEvent) -> None:
        # WICHTIG: event.accept() bei Middle-Klick verhindert Windows
        # AutoScroll-Modus (das flackernde "Scrollen deaktiviert"-Toast).
        # Sonst leitet Qt das Event weiter und Windows interpretiert es als
        # Auto-Scroll-Versuch in einem nicht-scrollbaren Widget.
        event.accept()

        # Pan mit Mittlerer Maustaste — oder mit Linksklick wenn MOVE-Tool aktiv
        is_move_tool = self._tool_manager.current_tool == Tool.MOVE
        if event.button() == Qt.MouseButton.MiddleButton or (
            is_move_tool and event.button() == Qt.MouseButton.LeftButton
        ):
            self._panning = True
            self._last_pan_point = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        ctx = self._create_tool_context(event.pos().x(), event.pos().y())
        if not ctx:
            return

        current_tool = self._tool_manager.current_tool
        is_polygon_tool = current_tool in (Tool.POLYGON, Tool.POLYGON_FILLED)
        is_backstitch_tool = current_tool == Tool.BACKSTITCH
        is_select_tool = current_tool in (Tool.SELECT, Tool.SELECT_LASSO)
        is_progress_tool = current_tool == Tool.PROGRESS

        # Progress-Tool hat eigenes Rechts-/Linksklick-Handling
        if is_progress_tool:
            if not self._batch_active:
                self._batch_active = True
                self.batch_started.emit("Fortschritt markieren")
            changes = self._tool_manager.on_mouse_press(ctx, event)
            for x, y, marker in changes:
                if marker == MARK_COMPLETED:
                    self.stitch_marked_completed.emit(x, y)
                elif marker == UNMARK_COMPLETED:
                    self.stitch_unmarked_completed.emit(x, y)
            self.update()
            return

        # Rechtsklick = Löschen (außer bei Polygon/Backstitch)
        if (
            event.button() == Qt.MouseButton.RightButton
            and not is_polygon_tool
            and not is_backstitch_tool
        ):
            if self._is_valid_grid_pos(ctx.grid_x, ctx.grid_y):
                if not self._batch_active:
                    self._batch_active = True
                    self.batch_started.emit("Löschen")

                for mx, my in self.get_mirrored_positions(ctx.grid_x, ctx.grid_y):
                    self.stitch_removed.emit(mx, my)
                self.update()
            return

        # Batch starten
        if (
            not self._batch_active
            and not is_polygon_tool
            and not is_select_tool
            and not is_backstitch_tool
        ):
            self._batch_active = True
            self.batch_started.emit(current_tool.batch_description)

        # Werkzeug-Event
        changes = self._tool_manager.on_mouse_press(ctx, event)

        # Spezialbehandlung für verschiedene Werkzeuge
        if is_polygon_tool and changes:
            if not self._batch_active:
                self._batch_active = True
                self.batch_started.emit("Polygon")
            self._apply_changes_with_mirror(changes)
            self._batch_active = False
            self.batch_ended.emit()
        elif is_select_tool and changes:
            self.batch_started.emit("Einfügen")
            self._apply_changes(changes)
            self.batch_ended.emit()
        else:
            self._apply_changes_with_mirror(changes)

        # Pipette: Farbe weitergeben
        if current_tool == Tool.PIPETTE:
            color_idx = self._tool_manager.get_pipette_color()
            if color_idx is not None:
                self.color_picked.emit(color_idx)

        # Backstitch: Aktion weitergeben
        if current_tool == Tool.BACKSTITCH:
            backstitch_tool = self._tool_manager.get_backstitch_tool()
            if backstitch_tool:
                action = backstitch_tool.pending_action
                if action is not None:
                    if action.action == "add":
                        self.backstitch_added.emit(
                            action.x1, action.y1, action.x2, action.y2, action.color_index
                        )
                    elif action.action == "remove":
                        self.backstitch_removed.emit(
                            action.x1, action.y1, action.x2, action.y2, action.color_index
                        )

        self.update()

    def mouseMoveEvent(self: "CrossStitchCanvas", event: QMouseEvent) -> None:
        self._cursor_pos = event.pos()

        # Pan
        if self._panning:
            delta = event.pos() - self._last_pan_point
            self._offset_x += delta.x()
            self._offset_y += delta.y()
            self._last_pan_point = event.pos()
            self.offset_changed.emit(self._offset_x, self._offset_y)
            self.update()
            return

        # Position-Signal
        grid_x, grid_y = self._screen_to_grid(event.pos().x(), event.pos().y())
        if self._is_valid_grid_pos(grid_x, grid_y):
            self.position_changed.emit(grid_x, grid_y)

        # Werkzeug-Event
        ctx = self._create_tool_context(event.pos().x(), event.pos().y())
        if ctx:
            changes = self._tool_manager.on_mouse_move(ctx, event)

            # Progress-Tool: Completion-Signals statt Stich-Signals
            if self._tool_manager.current_tool == Tool.PROGRESS:
                for x, y, marker in changes:
                    if marker == MARK_COMPLETED:
                        self.stitch_marked_completed.emit(x, y)
                    elif marker == UNMARK_COMPLETED:
                        self.stitch_unmarked_completed.emit(x, y)
            else:
                self._apply_changes_with_mirror(changes)

        self.update()

    def mouseReleaseEvent(self: "CrossStitchCanvas", event: QMouseEvent) -> None:
        # Pan beenden (Mittlere Maus oder Linksklick im MOVE-Tool)
        if self._panning and event.button() in (
            Qt.MouseButton.MiddleButton,
            Qt.MouseButton.LeftButton,
        ):
            self._panning = False
            self.setCursor(self._tool_manager.get_cursor())
            return

        current_tool = self._tool_manager.current_tool
        is_polygon_tool = current_tool in (Tool.POLYGON, Tool.POLYGON_FILLED)
        is_select_tool = current_tool in (Tool.SELECT, Tool.SELECT_LASSO)
        is_progress_tool = current_tool == Tool.PROGRESS

        # Progress-Tool: Batch beenden bei beliebigem Button
        if is_progress_tool:
            ctx = self._create_tool_context(event.pos().x(), event.pos().y())
            if ctx:
                self._tool_manager.on_mouse_release(ctx, event)
            if self._batch_active:
                self._batch_active = False
                self.batch_ended.emit()
            self.update()
            return

        # Rechtsklick Batch beenden
        if event.button() == Qt.MouseButton.RightButton and not is_polygon_tool:
            if self._batch_active:
                self._batch_active = False
                self.batch_ended.emit()
            return

        # Werkzeug-Event
        ctx = self._create_tool_context(event.pos().x(), event.pos().y())
        if ctx:
            changes = self._tool_manager.on_mouse_release(ctx, event)

            if is_select_tool and changes:
                self.batch_started.emit("Verschieben")
                self._apply_changes(changes)
                self.batch_ended.emit()
            else:
                self._apply_changes_with_mirror(changes)

        # Batch beenden
        if self._batch_active and not is_polygon_tool and not is_select_tool:
            self._batch_active = False
            self.batch_ended.emit()

        self.update()

    def leaveEvent(self: "CrossStitchCanvas", event) -> None:
        self._cursor_pos = None
        self.update()

    def keyPressEvent(self: "CrossStitchCanvas", event) -> None:
        key = event.key()
        modifiers = event.modifiers()
        ctrl = modifiers & Qt.KeyboardModifier.ControlModifier
        shift = modifiers & Qt.KeyboardModifier.ShiftModifier

        current_tool = self._tool_manager.current_tool

        # Text-Tool: Enter bestätigt
        if current_tool == Tool.TEXT and key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.text_confirmed.emit()
            return

        # Select-Tool: Tool-spezifische Tasten (F/R/H/V).
        # Ctrl+C/X/V und Entf laufen ueber QActions im Bearbeiten-Menue —
        # damit sind sie auch aktiv, wenn ein anderes Tool gerade vorne ist.
        # F/R/H/V bleiben hier, weil sie sonst mit Tool-Shortcuts kollidieren
        # wuerden (R = Rect-Tool etc.) — nur das aktive Select-Tool will sie.
        if current_tool in (Tool.SELECT, Tool.SELECT_LASSO):
            if key == Qt.Key.Key_F:
                self.selection_fill.emit()
                return
            if key == Qt.Key.Key_R:
                (self.selection_rotate_ccw if shift else self.selection_rotate_cw).emit()
                return
            if key == Qt.Key.Key_H:
                self.selection_flip_h.emit()
                return
            if key == Qt.Key.Key_V and not ctrl:
                self.selection_flip_v.emit()
                return

        # Werkzeug-Event
        ctx = self._create_tool_context(0, 0)
        if ctx and self._tool_manager.on_key_press(ctx, event):
            self.update()
            return

        # Sticken-Modus: Pfeiltasten springen zur naechsten/vorherigen
        # ungehakten Zelle der aktuell aktiven Farbe (Reading-Order).
        if current_tool == Tool.PROGRESS:
            if key in (Qt.Key.Key_Right, Qt.Key.Key_Down):
                if self.jump_to_next_stitch(forward=True):
                    return
            elif key in (Qt.Key.Key_Left, Qt.Key.Key_Up):
                if self.jump_to_next_stitch(forward=False):
                    return
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
                # Aktuelle Cursor-Zelle abhaken
                if self._stitch_cursor is not None:
                    cx, cy = self._stitch_cursor
                    if not self._batch_active:
                        self._batch_active = True
                        self.batch_started.emit("Fortschritt markieren")
                    self.stitch_marked_completed.emit(cx, cy)
                    self._batch_active = False
                    self.batch_ended.emit()
                    # Direkt zur naechsten Zelle springen — Workflow-Beschleunigung
                    self.jump_to_next_stitch(forward=True)
                    return

        # Pan mit Pfeiltasten
        pan_amount = 20
        if key == Qt.Key.Key_Left:
            self._offset_x += pan_amount
        elif key == Qt.Key.Key_Right:
            self._offset_x -= pan_amount
        elif key == Qt.Key.Key_Up:
            self._offset_y += pan_amount
        elif key == Qt.Key.Key_Down:
            self._offset_y -= pan_amount
        else:
            from PySide6.QtWidgets import QWidget

            QWidget.keyPressEvent(self, event)
            return

        self.offset_changed.emit(self._offset_x, self._offset_y)
        self.update()

    def resizeEvent(self: "CrossStitchCanvas", event) -> None:
        from PySide6.QtWidgets import QWidget

        QWidget.resizeEvent(self, event)
        self.offset_changed.emit(self._offset_x, self._offset_y)
