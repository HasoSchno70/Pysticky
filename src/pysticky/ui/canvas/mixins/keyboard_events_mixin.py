"""
Tastatur-Event-Mixin für Canvas.

Enthält die Tastatur-Logik: Tool-spezifische Tasten (Text bestätigen,
Select-Aktionen), Sticken-Modus-Navigation und Pfeiltasten-Pan.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

from ....core.i18n import t
from ...tools.tool_enum import Tool

if TYPE_CHECKING:
    from ..canvas import CrossStitchCanvas


class KeyboardEventsMixin:
    """Mixin für Tastatur-Event-Handler."""

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
        # Ctrl+C/X/V und Entf laufen über QActions im Bearbeiten-Menü —
        # damit sind sie auch aktiv, wenn ein anderes Tool gerade vorne ist.
        # F/R/H/V bleiben hier, weil sie sonst mit Tool-Shortcuts kollidieren
        # würden (R = Rect-Tool etc.) — nur das aktive Select-Tool will sie.
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

        # Sticken-Modus: Pfeiltasten springen zur nächsten/vorherigen
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
                        self.batch_started.emit(t("Fortschritt markieren"))
                    self.stitch_marked_completed.emit(cx, cy)
                    self._batch_active = False
                    self.batch_ended.emit()
                    # Direkt zur nächsten Zelle springen — Workflow-Beschleunigung
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
