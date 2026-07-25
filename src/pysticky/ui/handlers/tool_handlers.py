"""
Tool-bezogene Handler für MainWindow.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main_window import MainWindow


class ToolHandlersMixin:
    """Mixin für Werkzeug-bezogene Handler."""

    def _apply_default_tool(self: "MainWindow") -> None:
        """Wählt das Start-Werkzeug (Einstellungen → Werkzeuge): entweder
        das zuletzt verwendete (wenn "Letztes Werkzeug merken" aktiv und
        vorhanden) oder das konfigurierte Standard-Werkzeug. Nur beim
        App-Start aufrufen, siehe MainWindow.__init__."""
        from ..tools.tool_enum import Tool

        tool_name = None
        if self._settings.value("remember_tool", False, type=bool):
            tool_name = self._settings.value("last_tool", None, type=str)
        if not tool_name:
            tool_name = self._settings.value("default_tool", Tool.PENCIL.name, type=str)
        try:
            tool = Tool[tool_name]
        except KeyError:
            tool = Tool.PENCIL
        self.tool_bar.select_tool(tool)

    def _on_tool_changed(self: "MainWindow", tool) -> None:
        """Werkzeug geändert."""
        from ...core.i18n import t
        from ..tools.tool_enum import Tool

        name = t(tool.display_name)
        self.label_tool.setText(f"🛠 {name}")
        self.canvas.set_tool(tool)

        # Einstellungen → Werkzeuge → "Letztes Werkzeug merken"
        if self._settings.value("remember_tool", False, type=bool):
            self._settings.setValue("last_tool", tool.name)

        self.text_options_dock.setVisible(tool == Tool.TEXT)
        self.gradient_options_dock.setVisible(tool == Tool.GRADIENT)
        self.backstitch_options_dock.setVisible(tool == Tool.BACKSTITCH)

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
        elif tool == Tool.BACKSTITCH:
            if not self.canvas.show_backstitches:
                self._on_toggle_backstitches(True)
            # Panel auf den lebenden Canvas/Tool-Zustand synchronisieren
            # (Canvas -> Panel). Lief vorher umgekehrt (Panel -> Canvas)
            # und ueberschrieb dabei bei JEDEM Werkzeugwechsel den bereits
            # korrekten, aus QSettings geladenen Canvas-Zustand
            # (backstitch_width/backstitch_snap, siehe
            # _apply_settings_from_dialog() in misc_handlers.py) mit den
            # hartcodierten Konstruktor-Defaults des Panels (Dicke 2,
            # Solid, Round, Snap an) -- das Panel selbst wird nie aus
            # QSettings initialisiert. Eine persistierte Einstellung ging
            # dadurch beim naechsten Anwaehlen des Werkzeugs sofort wieder
            # verloren. sync_from_state() aktualisiert nur die Anzeige
            # (blockSignals), ohne selbst wieder in den Canvas zu
            # schreiben.
            panel = self.backstitch_options_panel
            backstitch_tool = self.canvas._tool_manager.get_backstitch_tool()
            snap_enabled = backstitch_tool.snap_to_grid if backstitch_tool else panel.snap_enabled
            panel.sync_from_state(
                thickness=self.canvas._backstitch_width_offset,
                line_style=self.canvas._backstitch_line_style,
                cap_style=self.canvas._backstitch_cap_style,
                snap_enabled=snap_enabled,
            )
            entry = self.current_pattern.get_color_entry(self.canvas._current_color_index)
            if entry:
                from ..color_utils import to_qcolor

                panel._preview.set_color(to_qcolor(entry.thread.color))
            self.canvas.update()
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
        from ...core.i18n import t

        text_tool = self.canvas._tool_manager.get_text_tool()
        if text_tool and text_tool.has_preview:
            ctx = self.canvas._create_tool_context(0, 0)
            if ctx:
                changes = text_tool.confirm_text(ctx)
                if changes:
                    self.canvas.batch_started.emit(t("Text"))
                    # _apply_changes() statt manuellem Signal-Loop -- siehe
                    # edit_handlers.py::_on_replace_color.
                    self.canvas._apply_changes(changes)
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

    # === Backstitch-Tool Handler ===

    def _on_backstitch_thickness_changed(self: "MainWindow", value: int) -> None:
        self.canvas._backstitch_width_offset = value
        self.canvas.update()

    def _on_backstitch_style_changed(self: "MainWindow", style: int) -> None:
        from PySide6.QtCore import Qt

        self.canvas._backstitch_line_style = Qt.PenStyle(style)
        self.canvas.update()

    def _on_backstitch_cap_changed(self: "MainWindow", cap: int) -> None:
        from PySide6.QtCore import Qt

        self.canvas._backstitch_cap_style = Qt.PenCapStyle(cap)
        self.canvas.update()

    def _on_backstitch_snap_changed(self: "MainWindow", enabled: bool) -> None:
        backstitch_tool = self.canvas._tool_manager.get_backstitch_tool()
        if backstitch_tool:
            backstitch_tool.snap_to_grid = enabled


def resync_gradient_tool_after_palette_shift(window: "MainWindow") -> None:
    """Aktualisiert Farbverlauf-Panel + -Tool nach einer Farbindex-
    Verschiebung im AKTIVEN Pattern (Farbe loeschen/zusammenfuehren).

    GradientTool._start_color_index/_end_color_index (gesetzt ueber die
    Panel-Comboboxen) sind rohe Farb-INDIZES, exakt wie
    SelectTool._clipboard -- siehe dessen Reset zwei Zeilen weiter oben
    in edit_handlers.py::_on_manage_colors()/_on_merge_similar_colors().
    ColorManagementDialog (Loeschen/"Ungenutzte entfernen"/
    Zusammenfuehren) und SimilarColorsDialog verschieben nachfolgende
    Farbindizes um -1 nach unten (Pattern.remove_color()); ohne diesen
    Resync zeigte der eingefrorene Start-/End-Index nach so einem
    Dialog lautlos auf eine andere Farbe -- oder, war der hoechste
    Index betroffen, ins Leere (out of range). _calculate_gradient()
    faengt den Out-of-Range-Fall zwar ab (get_color_entry() liefert
    None), das Werkzeug wurde dadurch aber zu einem stillen No-Op:
    Ziehen einer Linie erzeugte ueberhaupt keine Aenderungen, ohne
    jede Fehlermeldung.

    Modulfunktion statt Methode auf ToolHandlersMixin, damit hier kein
    weiteres self:"MainWindow"-Mixin-Methodensignatur-Muster entsteht
    (jede solche Methode erzeugt einen zusaetzlichen mypy-"erased type
    of self"-Fehler -- bekanntes, akzeptiertes Rauschen in diesem
    Projekt, siehe Runde 71/_offer_single_autosave_recovery() fuer
    dasselbe Muster).

    set_pattern() setzt die Panel-Comboboxen auf Index 0/1 zurueck (wie
    beim erstmaligen Aktivieren des Werkzeugs, siehe _on_tool_changed())
    -- das Tool wird anschliessend explizit auf diese neuen Panel-Werte
    resynchronisiert, da _update_combos() die Comboboxen mit
    blockSignals(True) befuellt und start_color_changed/end_color_
    changed deshalb NICHT feuert.
    """
    window.gradient_options_panel.set_pattern(window.current_pattern)
    gradient_tool = window.canvas._tool_manager.get_gradient_tool()
    if gradient_tool:
        gradient_tool.set_start_color(window.gradient_options_panel.start_color_index)
        gradient_tool.set_end_color(window.gradient_options_panel.end_color_index)
