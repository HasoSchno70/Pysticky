"""
Maus-Event-Mixin für Canvas.

Enthält die Maus- und Viewport-Event-Handler: Zeichnen/Tool-Delegation,
Pan, Undo-Batching, Wheel-Zoom und Resize.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent

from ...tools.progress_tool import MARK_COMPLETED, UNMARK_COMPLETED
from ...tools.tool_enum import Tool

if TYPE_CHECKING:
    from ..canvas import CrossStitchCanvas


class MouseEventsMixin:
    """Mixin für Maus- und Viewport-Event-Handler."""

    def wheelEvent(self: "CrossStitchCanvas", event: QWheelEvent) -> None:
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()

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

    def resizeEvent(self: "CrossStitchCanvas", event) -> None:
        from PySide6.QtWidgets import QWidget

        QWidget.resizeEvent(self, event)
        self.offset_changed.emit(self._offset_x, self._offset_y)
