"""
Signal-Connector-Mixin für MainWindow.

Enthält die Verbindung aller Signale.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main_window import MainWindow


class SignalsConnectorMixin:
    """Mixin für Signal-Verbindungen."""

    def _connect_signals(self: "MainWindow") -> None:
        """Verbindet alle Signale."""
        self._connect_canvas_signals()
        self._connect_undo_signals()
        self._connect_panel_signals()
        self._connect_tool_signals()
        self._connect_minimap_signals()
        self._connect_text_options_signals()
        self._connect_gradient_options_signals()
        self._connect_backstitch_options_signals()
        self._connect_progress_signals()

    def _connect_canvas_signals(self: "MainWindow") -> None:
        """Verbindet Canvas-Signale."""
        # Position & Zoom -> ViewHandlersMixin
        self.canvas.position_changed.connect(self._on_canvas_position_changed)
        self.canvas.zoom_changed.connect(self._on_canvas_zoom_changed)

        # Farbpipette
        self.canvas.color_picked.connect(self._on_color_picked)

        # Text-Tool
        self.canvas.text_confirmed.connect(self._on_text_confirm)

        # Auswahl-Signale -> SelectionHandlersMixin.
        # Copy/Cut/Paste/Delete kommen direkt aus den QActions im Bearbeiten-Menü;
        # die Signale hier sind nur für die Tool-spezifischen Tasten F/R/H/V im Canvas.
        self.canvas.selection_fill.connect(self._on_selection_fill)
        self.canvas.selection_rotate_cw.connect(self._on_selection_rotate_cw)
        self.canvas.selection_rotate_ccw.connect(self._on_selection_rotate_ccw)
        self.canvas.selection_flip_h.connect(self._on_selection_flip_h)
        self.canvas.selection_flip_v.connect(self._on_selection_flip_v)

    def _connect_undo_signals(self: "MainWindow") -> None:
        """Verbindet Undo-Signale."""
        self.canvas.batch_started.connect(self._on_batch_started)
        self.canvas.batch_ended.connect(self._on_batch_ended)
        self.canvas.stitch_placed.connect(self._on_stitch_placed)
        self.canvas.stitch_removed.connect(self._on_stitch_removed)
        self.canvas.backstitch_added.connect(self._on_backstitch_added)
        self.canvas.backstitch_removed.connect(self._on_backstitch_removed)

    def _connect_panel_signals(self: "MainWindow") -> None:
        """Verbindet Panel-Signale."""
        # Palette-Panel
        self.palette_panel.color_added.connect(self._on_palette_color_added)
        self.palette_panel.palette_change_requested.connect(self._on_palette_change_requested)

        # Color-Bar
        self.color_bar.color_selected.connect(self._on_color_selected)
        self.color_bar.color_double_clicked.connect(self._on_color_double_clicked)
        self.color_bar.color_right_clicked.connect(self._on_color_right_clicked)
        self.color_bar.color_dropped.connect(self._on_color_dropped)
        self.color_bar.color_swap_requested.connect(self._on_color_swap_dropped)

        # Klick in der Info-Panel-Farbübersicht selektiert die Farbe in der
        # Musterfarben-Bar (und damit als aktive Zeichenfarbe).
        self.info_panel.color_clicked.connect(self._on_info_color_clicked)

        # Layer-Panel
        self.layer_panel.layer_selected.connect(self._on_layer_selected)
        self.layer_panel.layers_changed.connect(self._on_layers_changed)
        self.layer_panel.layer_structure_changed.connect(self._on_layer_structure_changed)
        self.layer_panel.clear_layer_requested.connect(self._on_clear_layer_requested)

    def _connect_tool_signals(self: "MainWindow") -> None:
        """Verbindet Werkzeug-Signale."""
        self.tool_bar.tool_changed.connect(self._on_tool_changed)
        self.tool_bar.mirror_h_clicked.connect(self._on_mirror_h)
        self.tool_bar.mirror_v_clicked.connect(self._on_mirror_v)

    def _connect_minimap_signals(self: "MainWindow") -> None:
        """Verbindet Minimap-Signale."""
        self.minimap_panel.viewport_changed.connect(self._on_minimap_navigate)
        self.canvas.offset_changed.connect(self._update_minimap_viewport)
        self.canvas.zoom_changed.connect(lambda _: self._update_minimap_viewport(0, 0))

    def _connect_text_options_signals(self: "MainWindow") -> None:
        """Verbindet Text-Options-Panel-Signale."""
        self.text_options_panel.text_changed.connect(self._on_text_changed)
        self.text_options_panel.font_changed.connect(self._on_text_font_changed)
        self.text_options_panel.size_changed.connect(self._on_text_size_changed)
        self.text_options_panel.bold_changed.connect(self._on_text_bold_changed)
        self.text_options_panel.italic_changed.connect(self._on_text_italic_changed)
        self.text_options_panel.confirm_clicked.connect(self._on_text_confirm)
        self.text_options_panel.cancel_clicked.connect(self._on_text_cancel)

    def _connect_gradient_options_signals(self: "MainWindow") -> None:
        """Verbindet Gradient-Options-Panel-Signale."""
        self.gradient_options_panel.start_color_changed.connect(self._on_gradient_start_changed)
        self.gradient_options_panel.end_color_changed.connect(self._on_gradient_end_changed)

    def _connect_backstitch_options_signals(self: "MainWindow") -> None:
        """Verbindet Rückstich-Options-Panel-Signale."""
        self.backstitch_options_panel.thickness_changed.connect(
            self._on_backstitch_thickness_changed
        )
        self.backstitch_options_panel.line_style_changed.connect(self._on_backstitch_style_changed)
        self.backstitch_options_panel.cap_style_changed.connect(self._on_backstitch_cap_changed)
        self.backstitch_options_panel.snap_enabled_changed.connect(self._on_backstitch_snap_changed)

    def _connect_progress_signals(self: "MainWindow") -> None:
        """Verbindet Fortschritts-Signale."""
        # Canvas -> MainWindow
        self.canvas.stitch_marked_completed.connect(self._on_stitch_marked_completed)
        self.canvas.stitch_unmarked_completed.connect(self._on_stitch_unmarked_completed)
        # Progress-Panel -> MainWindow
        self.progress_panel.mark_color_completed.connect(self._on_mark_color_completed)
        self.progress_panel.reset_progress.connect(self._on_reset_progress)
        # Stick-Modus-Toggle aus dem Panel — leitet auf die Action weiter,
        # damit Panel + Menü-Eintrag synchron bleiben.
        self.progress_panel.toggle_stitch_mode_requested.connect(self.action_stitch_mode.setChecked)
