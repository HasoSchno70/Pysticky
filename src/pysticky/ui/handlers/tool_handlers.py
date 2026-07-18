"""
Tool-bezogene Handler für MainWindow.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main_window import MainWindow


class ToolHandlersMixin:
    """Mixin für Werkzeug-bezogene Handler."""

    def _on_tool_changed(self: "MainWindow", tool) -> None:
        """Werkzeug geändert."""
        from ...core.i18n import t
        from ..tools.tool_enum import Tool

        name = t(tool.display_name)
        self.label_tool.setText(f"🛠 {name}")
        self.canvas.set_tool(tool)

        self.text_options_dock.setVisible(tool == Tool.TEXT)
        self.gradient_options_dock.setVisible(tool == Tool.GRADIENT)

        if tool == Tool.TEXT:
            self.text_options_panel.focus_text_input()
            text_tool = self.canvas._tool_manager.get_text_tool()
            if text_tool:
                text_tool.set_text(self.text_options_panel.text)
                text_tool.set_font_family(self.text_options_panel.font_family)
                text_tool.set_font_size(self.text_options_panel.font_size)
                text_tool.set_bold(self.text_options_panel.bold)
                text_tool.set_italic(self.text_options_panel.italic)
        elif tool == Tool.GRADIENT:
            self.gradient_options_panel.set_pattern(self.current_pattern)
            gradient_tool = self.canvas._tool_manager.get_gradient_tool()
            if gradient_tool:
                start_idx = self.color_bar.current_index
                gradient_tool.set_start_color(start_idx)
                self.gradient_options_panel.set_start_color(start_idx)
                end_idx = (start_idx + 1) % max(1, len(self.current_pattern.color_entries))
                gradient_tool.set_end_color(end_idx)
                self.gradient_options_panel.set_end_color(end_idx)
        elif tool == Tool.BACKSTITCH and not self.canvas.show_backstitches:
            self._on_toggle_backstitches(True)
        elif tool == Tool.PROGRESS:
            if not self.canvas._show_completion:
                self.canvas._show_completion = True
                self.action_show_completion.setChecked(True)
                self.canvas.update()

        self.status_bar.showMessage(f"Werkzeug: {name}", 2000)

    # === Text-Tool Handler ===

    def _on_text_changed(self: "MainWindow", text: str) -> None:
        text_tool = self.canvas._tool_manager.get_text_tool()
        if text_tool:
            text_tool.set_text(text)
            self.canvas.update()

    def _on_text_font_changed(self: "MainWindow", font_family: str) -> None:
        text_tool = self.canvas._tool_manager.get_text_tool()
        if text_tool:
            text_tool.set_font_family(font_family)
            self.canvas.update()

    def _on_text_size_changed(self: "MainWindow", size: int) -> None:
        text_tool = self.canvas._tool_manager.get_text_tool()
        if text_tool:
            text_tool.set_font_size(size)
            self.canvas.update()

    def _on_text_bold_changed(self: "MainWindow", bold: bool) -> None:
        text_tool = self.canvas._tool_manager.get_text_tool()
        if text_tool:
            text_tool.set_bold(bold)
            self.canvas.update()

    def _on_text_italic_changed(self: "MainWindow", italic: bool) -> None:
        text_tool = self.canvas._tool_manager.get_text_tool()
        if text_tool:
            text_tool.set_italic(italic)
            self.canvas.update()

    def _on_text_confirm(self: "MainWindow") -> None:
        text_tool = self.canvas._tool_manager.get_text_tool()
        if text_tool and text_tool.has_preview:
            ctx = self.canvas._create_tool_context(0, 0)
            if ctx:
                changes = text_tool.confirm_text(ctx)
                if changes:
                    self.canvas.batch_started.emit("Text")
                    for x, y, color_idx in changes:
                        self.canvas.stitch_placed.emit(x, y, color_idx)
                    self.canvas.batch_ended.emit()
                    self.canvas.update()
                    self.status_bar.showMessage(
                        f"Text platziert: {len(changes)} Stiche", self._status_timeout_ms
                    )
        else:
            self.status_bar.showMessage("Kein Text zum Platzieren", self._status_timeout_ms)

    def _on_text_cancel(self: "MainWindow") -> None:
        from ..tools.tool_enum import Tool

        text_tool = self.canvas._tool_manager.get_text_tool()
        if text_tool:
            text_tool.deactivate()
            text_tool.activate()
            self.canvas.update()
        self.tool_bar.select_tool(Tool.PENCIL)
        self.status_bar.showMessage("Text abgebrochen", 2000)

    # === Gradient-Tool Handler ===

    def _on_gradient_start_changed(self: "MainWindow", color_index: int) -> None:
        gradient_tool = self.canvas._tool_manager.get_gradient_tool()
        if gradient_tool:
            gradient_tool.set_start_color(color_index)

    def _on_gradient_end_changed(self: "MainWindow", color_index: int) -> None:
        gradient_tool = self.canvas._tool_manager.get_gradient_tool()
        if gradient_tool:
            gradient_tool.set_end_color(color_index)
