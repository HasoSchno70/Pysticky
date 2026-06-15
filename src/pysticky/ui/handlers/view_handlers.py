"""
Ansicht-bezogene Handler für MainWindow.
"""

from typing import TYPE_CHECKING

from ...core.i18n import t

if TYPE_CHECKING:
    from ..main_window import MainWindow


class ViewHandlersMixin:
    """Mixin-Klasse für Ansicht-Operationen."""

    def _on_toggle_stitch_mode(self: "MainWindow", on: bool) -> None:
        """Sticken-Modus an/aus.

        Beim Aktivieren:
        - Werkzeug auf Progress-Tool umschalten (Klick = Stich erledigt/zurueck)
        - Side-Dock-Panels ausser dem Fortschritt-Panel verstecken
        - Stoff-aehnliches Rendering (Symbole + Backstitches dimmen)
        - Statusbar-Indikator
        - Optional: Session-Timer starten (Setting `stitch_timer_enabled`)
        Beim Deaktivieren: vorherigen Zustand wiederherstellen + Timer stoppen.
        """
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QDockWidget

        from ...core import session_timer
        from ..tools.tool_enum import Tool

        timer_enabled = QSettings().value("stitch_timer_enabled", True, type=bool)

        if on:
            # 1. Aktuellen Zustand fuer spaetere Wiederherstellung speichern
            self._stitch_mode_saved_state = {
                "tool": getattr(self.tool_bar, "_current_tool", Tool.PENCIL),
                "show_symbols": self.canvas.show_symbols,
                "show_completion": self.canvas._show_completion,
                "dock_visibility": {},
            }
            for dock in self.findChildren(QDockWidget):
                self._stitch_mode_saved_state["dock_visibility"][dock] = dock.isVisible()

            # 2. ProgressTool aktivieren
            self.tool_bar.select_tool(Tool.PROGRESS)

            # 3. Completion sichtbar machen, Symbole an damit User sieht wo er hin muss
            self.canvas._show_completion = True
            if hasattr(self, "action_show_completion"):
                self.action_show_completion.setChecked(True)

            # 4. Alle Dock-Panels ausser dem Fortschritts-Dock verstecken
            for dock in self.findChildren(QDockWidget):
                if dock.windowTitle() == "Fortschritt":
                    dock.show()
                    dock.raise_()
                else:
                    dock.hide()

            # 5. Session-Timer starten (wenn enabled)
            if timer_enabled and self.current_pattern is not None:
                session_timer.start_session(self.current_pattern)

            self.canvas.update()
            self.status_bar.showMessage(
                "Sticken-Modus aktiv — Klick = abhaken (Rechtsklick = zurück), "
                "Pfeiltasten = nächster Stich dieser Farbe, Enter = abhaken & weiter",
                7000,
            )
        else:
            # Wiederherstellen
            saved = getattr(self, "_stitch_mode_saved_state", None)
            if saved:
                self.tool_bar.select_tool(saved["tool"])
                self.canvas.show_symbols = saved["show_symbols"]
                self.canvas._show_completion = saved["show_completion"]
                for dock, was_visible in saved["dock_visibility"].items():
                    if was_visible:
                        dock.show()
                    else:
                        dock.hide()
                self._stitch_mode_saved_state = None

            # Sticken-Cursor (Pfeiltasten-Navigation) zuruecksetzen
            self.canvas.set_stitch_cursor(None)

            # Session-Timer stoppen + Toast in der Statusbar
            elapsed = 0
            if self.current_pattern is not None and session_timer.is_session_active(
                self.current_pattern
            ):
                elapsed = session_timer.stop_session(self.current_pattern)
                # Stop-Event markiert das Pattern als veraendert (Metadata
                # gehoert mitgespeichert), aber nur wenn Zeit > 0 vergangen.
                if elapsed > 0 and hasattr(self, "_mark_unsaved"):
                    self._mark_unsaved()

            self.canvas.update()
            if elapsed > 0:
                total = session_timer.get_total_seconds(self.current_pattern)
                self.status_bar.showMessage(
                    f"Sticken-Modus beendet — Sitzung {session_timer.format_duration(elapsed)}, "
                    f"insgesamt {session_timer.format_duration(total)}",
                    6000,
                )
            else:
                self.status_bar.showMessage("Sticken-Modus beendet", 3000)

        # Statusbar-Pill aktualisieren
        if hasattr(self, "_update_stitch_mode_indicator"):
            self._update_stitch_mode_indicator(on)
        # Panel-Toggle-Button synchron halten
        if hasattr(self, "progress_panel") and hasattr(
            self.progress_panel, "set_stitch_mode_active"
        ):
            self.progress_panel.set_stitch_mode_active(on)

    def _on_zoom_in(self: "MainWindow") -> None:
        self.canvas.zoom_in()

    def _on_zoom_out(self: "MainWindow") -> None:
        self.canvas.zoom_out()

    def _on_zoom_fit(self: "MainWindow") -> None:
        self.canvas.zoom_fit()

    def _on_zoom_100(self: "MainWindow") -> None:
        self.canvas.zoom_reset()

    def _on_toggle_grid(self: "MainWindow", checked: bool) -> None:
        self.canvas.show_grid = checked

    def _on_toggle_symbols(self: "MainWindow", checked: bool) -> None:
        self.canvas.show_symbols = checked
        self.action_show_symbols.setChecked(checked)
        self.chk_symbols.setChecked(checked)

    def _on_toggle_backstitches(self: "MainWindow", checked: bool) -> None:
        """Rückstiche ein-/ausblenden."""
        self.canvas.show_backstitches = checked
        self.action_show_backstitches.setChecked(checked)
        self.chk_backstitches.setChecked(checked)

    def _on_toggle_completion(self: "MainWindow", checked: bool) -> None:
        """Fortschritts-Overlay ein-/ausblenden."""
        self.canvas._show_completion = checked
        self.canvas.update()

    def _on_toggle_diamond_view(self: "MainWindow", checked: bool) -> None:
        """Diamond-Painting-Ansicht ein-/ausschalten (User-getriggert).

        Loest den vollen Modus-Wechsel aus inkl. Palette-Auto-Switch,
        Pattern.mode-Update und automatischer Farb-Konvertierung. Beim
        Laden eines Patterns aus Datei wird stattdessen
        ``_apply_pattern_mode`` benutzt — der schreibt nicht zurueck ins
        Pattern und konvertiert auch keine Farben.

        WICHTIG: Der ganze Mode-Switch laeuft in einem MainWindow-weiten
        setUpdatesEnabled(False)-Block, weil der Palette-Auto-Switch das
        Palette-Panel ein ``_refresh_color_list`` triggert (450 QListWidget-
        Items bei DMC Diamond Painting) und das Info-Panel die ganze
        ColorList neu baut (Symbol-Spalten-Wechsel) — beides zusammen
        koennte sonst ein leeres Phantom-Top-Level-Fenster flackern lassen.
        """
        pattern = self.current_pattern
        target_mode = "diamond" if checked else "stitch"

        self.setUpdatesEnabled(False)
        try:
            colors_changed = False
            if pattern is not None:
                # convert_to_mode() schreibt sowohl pattern.mode als auch (bei
                # Bedarf) die thread/is_diamond-Flags. Snapshot-Backup laeuft
                # darin transparent — sodass Stick→DP→Stick die Original-Codes
                # wiederherstellt statt sie durch doppeltes Lab-Match driften
                # zu lassen.
                colors_changed = pattern.convert_to_mode(target_mode)

            self._apply_pattern_mode(checked, palette_auto_switch=True)

            # Wenn Farben gewechselt wurden: ColorBar und Info-Panel sehen die
            # neuen Threads erst nach einem Refresh. update_info() laeuft
            # bereits in _apply_pattern_mode — wir muessen nur noch die
            # ColorBar-Swatches re-rendern (gleiche Anzahl Entries, andere
            # Thread-Daten -> update_swatches reicht).
            if colors_changed and pattern is not None:
                color_bar = getattr(self, "color_bar", None)
                if color_bar is not None:
                    color_bar.update_swatches()
                if hasattr(self, "_mark_unsaved"):
                    self._mark_unsaved()
        finally:
            self.setUpdatesEnabled(True)

    def _apply_pattern_mode(
        self: "MainWindow", diamond: bool, palette_auto_switch: bool = False
    ) -> None:
        """Setzt alle UI-Komponenten auf den gewuenschten Modus.

        Args:
            diamond: True = Diamond-Painting, False = Kreuzstich.
            palette_auto_switch: True bei User-Toggle (DMC Diamond Painting
                bzw. vorher genutzte Palette laden). False beim Pattern-Laden
                (Farben kommen schon aus der Datei).

        Wird sowohl bei User-Toggle als auch beim Pattern-Laden aufgerufen,
        damit alle Sichtwege denselben Zustand erzeugen.
        """
        self.canvas.diamond_view = diamond

        # Menue-Action und Toolbar-Button syncen (ohne Signal-Loops).
        for widget_attr in ("action_diamond_view", "btn_mode_switch"):
            w = getattr(self, widget_attr, None)
            if w is None:
                continue
            w.blockSignals(True)
            w.setChecked(diamond)
            w.blockSignals(False)
        refresh = getattr(self, "_refresh_mode_switch_button", None)
        if refresh is not None:
            refresh()

        # Info-Panel: Labels + Berechnungen anpassen
        panel_info = getattr(self, "info_panel", None)
        if panel_info is not None and hasattr(panel_info, "set_mode"):
            panel_info.set_mode("diamond" if diamond else "stitch")
            if self.current_pattern is not None:
                panel_info.update_info(self.current_pattern)

        # ColorBar: Symbol vs. Drill-Nummer unter den Swatches.
        color_bar = getattr(self, "color_bar", None)
        if color_bar is not None and hasattr(color_bar, "set_mode"):
            color_bar.set_mode("diamond" if diamond else "stitch")

        # PalettePanel: Header-Label + Dropdown-Icons anpassen.
        palette_panel = getattr(self, "palette_panel", None)
        if palette_panel is not None and hasattr(palette_panel, "set_mode"):
            palette_panel.set_mode("diamond" if diamond else "stitch")

        # Dock-Titel ("Garnpaletten" ↔ "Diamond-Paletten")
        palette_dock = getattr(self, "palette_dock", None)
        if palette_dock is not None:
            palette_dock.setWindowTitle(t("Diamond-Paletten") if diamond else t("Garnpaletten"))

        # Fortschritts-Dock im DP-Modus ausblenden — Diamond Painting hat
        # keinen etablierten "Stich abhaken"-Workflow.
        # WICHTIG: setFloating(False) VOR setVisible(True) erzwingen, damit
        # der zuvor versteckte tabified Dock nicht kurz als Top-Level-
        # Floating-Window aufpoppt (klassisches Qt-Verhalten bei
        # tabifyDockWidget + Re-Show).
        progress_dock = getattr(self, "progress_dock", None)
        if progress_dock is not None:
            if not diamond and progress_dock.isFloating():
                progress_dock.setFloating(False)
            progress_dock.setVisible(not diamond)

        # Symbol-Toggle umlabeln: im DP zeigt er Drill-Nummern statt Symbole.
        # Das Verhalten ist dasselbe (show_symbols-Flag), nur der visuelle
        # Output unterscheidet sich.
        chk_sym = getattr(self, "chk_symbols", None)
        action_sym = getattr(self, "action_show_symbols", None)
        if diamond:
            sym_text = t("Nummern")
            sym_tip = t("Drill-Nummern in den Zellen ein-/ausblenden")
            action_text = t("&Drill-Nummern anzeigen")
        else:
            sym_text = t("Symbole")
            sym_tip = t("Symbole anzeigen")
            action_text = t("&Symbole anzeigen")
        if chk_sym is not None:
            chk_sym.setText(sym_text)
            chk_sym.setToolTip(sym_tip)
        if action_sym is not None:
            action_sym.setText(action_text)

        # Stitch-Werkzeuge je nach Modus disablen
        self._apply_tool_availability_for_mode(diamond)

        # Palette-Auto-Switch nur bei User-Toggle
        if palette_auto_switch:
            panel = getattr(self, "palette_panel", None)
            combo = getattr(panel, "combo_palette", None) if panel else None
            if combo is not None and panel is not None:
                if diamond:
                    # Aktueller (Garn-)Name aus userData (Icon-Prefix
                    # ueberspringen — `current_palette_name()` macht das).
                    current = (
                        panel.current_palette_name()
                        if hasattr(panel, "current_palette_name")
                        else combo.currentText()
                    )
                    if current and "Diamond" not in current:
                        self._pre_diamond_palette = current
                    target = "DMC Diamond Painting"
                else:
                    target = getattr(self, "_pre_diamond_palette", None) or "DMC"
                # Suche per userData, nicht per Text (der Text hat Icon-Prefix).
                find = getattr(panel, "_find_palette_index", None)
                idx = find(target) if find is not None else combo.findText(target)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

    def _apply_tool_availability_for_mode(self: "MainWindow", diamond: bool) -> None:
        # Toolbar-Repaint waehrend der Action-Visibility-Wechsel aussetzen.
        # QWidgetActions, die in einer QToolBar verborgen werden und wieder
        # auftauchen, koennen sonst einen Frame lang Top-Level rendern
        # (Phantom-Fenster). Das ist besonders sichtbar beim DP→Stick-
        # Wechsel, wo gleich vier QWidgetActions in Folge re-sichtbar werden:
        # Symbol-Picker-Label, Combo, Backstitch-Toggle und der Backstitch-
        # Tool-Button.
        toolbar = getattr(self, "_toolbar", None)
        if toolbar is not None:
            toolbar.setUpdatesEnabled(False)
        tool_panel = getattr(self, "tool_bar", None)  # linkes Tool-Panel
        if tool_panel is not None:
            tool_panel.setUpdatesEnabled(False)
        try:
            self._apply_tool_availability_for_mode_impl(diamond)
        finally:
            if toolbar is not None:
                toolbar.setUpdatesEnabled(True)
            if tool_panel is not None:
                tool_panel.setUpdatesEnabled(True)

    def _apply_tool_availability_for_mode_impl(self: "MainWindow", diamond: bool) -> None:
        """Versteckt stick-spezifische Werkzeuge im DP-Modus (und umgekehrt).

        Im DP-Modus gibt's nur einen Drill-Typ — Halb-, Viertel-, Dreiviertel-
        Stiche und Franzoesischer Knoten ergeben dort keinen Sinn. Rueckstich-
        Werkzeug ebenfalls weg (DP hat keine Konturen).

        Strategie: **Ausblenden statt Disablen**. Disabled Items im QComboBox-
        Dropdown sind in PySide6 visuell schwer zu erkennen — sieht aus als
        waeren sie weiter waehlbar. Ausblenden ist eindeutig.
        """
        # Stick-only-Typen: halbe/Viertel/Dreiviertelstiche + Franzoesischer Knoten.
        # 0 (FULL) und 10 (BEAD) bleiben in beiden Modi nutzbar — BEAD ist
        # ein valider Akzent auch in DP-Patterns.
        STITCH_ONLY_TYPES = (1, 2, 3, 4, 5, 6, 7, 9)

        # Stitch-Type-Menue-Actions: im DP-Modus ausblenden.
        actions = getattr(self, "actions_stitch_type", {})
        for stype, action in actions.items():
            if stype in STITCH_ONLY_TYPES:
                action.setVisible(not diamond)

        # Stitch-Type-Picker in der Toolbar: Combo + Label komplett ausblenden,
        # weil's im DP-Modus eh nur einen Drill-Typ gibt.
        # WICHTIG: QToolBar.addWidget gibt eine QWidgetAction zurueck. setVisible
        # auf das Widget selbst hat in QToolBar oft keine Wirkung — man muss
        # die zurueckgegebene Action verbergen. Die Actions wurden beim Aufbau
        # unter `*_action` gespeichert.
        combo = getattr(self, "combo_stitch_type", None)
        if combo is not None:
            cur = combo.itemData(combo.currentIndex())
            if diamond and cur is not None and int(cur) in STITCH_ONLY_TYPES:
                for i in range(combo.count()):
                    if combo.itemData(i) == 0:
                        combo.setCurrentIndex(i)
                        break
        for action_attr in ("combo_stitch_type_action", "combo_stitch_type_label_action"):
            act = getattr(self, action_attr, None)
            if act is not None:
                act.setVisible(not diamond)

        # Rueckstich-View-Toggle im Toolbar (gleiche QWidgetAction-Story).
        bs_toggle_action = getattr(self, "chk_backstitches_action", None)
        if bs_toggle_action is not None:
            bs_toggle_action.setVisible(not diamond)
        # Wenn die View-Backstitch-Anzeige aktiv war, im DP-Modus auch
        # ausschalten — sonst rendert der Canvas weiter Rueckstich-Linien
        # die da nicht hingehoeren.
        if diamond and getattr(self.canvas, "show_backstitches", False):
            self.canvas.show_backstitches = False
            chk_bs = getattr(self, "chk_backstitches", None)
            if chk_bs is not None:
                chk_bs.blockSignals(True)
                chk_bs.setChecked(False)
                chk_bs.blockSignals(False)
            act = getattr(self, "action_show_backstitches", None)
            if act is not None:
                act.blockSignals(True)
                act.setChecked(False)
                act.blockSignals(False)

        # Rueckstich-Werkzeug im linken Tool-Bar-Panel: das ist ein direktes
        # QWidget, kein QToolBar-Member, also klappt setVisible darauf.
        tool_bar = getattr(self, "tool_bar", None)
        if tool_bar is not None:
            from ..tools.tool_enum import Tool

            buttons = getattr(tool_bar, "_buttons", {})
            bs_btn = buttons.get(Tool.BACKSTITCH)
            if bs_btn is not None:
                bs_btn.setVisible(not diamond)

        # Fenstertitel + Statusleiste mit neuem Modus refreshen.
        if hasattr(self, "_update_title"):
            self._update_title()
        if hasattr(self, "_update_status") and self.current_pattern is not None:
            self._update_status()

    def _on_toggle_only_active(self: "MainWindow", checked: bool) -> None:
        self.canvas.show_only_active_layer = checked
        self.action_show_only_active.setChecked(checked)
        self.chk_only_active.setChecked(checked)

    def _on_toggle_dim_layers(self: "MainWindow", checked: bool) -> None:
        self.canvas.dim_other_layers = checked

    def _on_grid_options(self: "MainWindow") -> None:
        """Zeigt den Dialog für Raster-Optionen."""
        from ..dialogs import GridOptionsDialog

        dialog = GridOptionsDialog(self.canvas, self)
        dialog.exec()

    def _on_pattern_preview(self: "MainWindow") -> None:
        """Öffnet die Muster-Vorschau."""
        from ..dialogs import PatternPreviewDialog

        dialog = PatternPreviewDialog(self.current_pattern, self)
        dialog.exec()

    def _on_symmetry_h_changed(self: "MainWindow", enabled: bool) -> None:
        """Horizontale Symmetrie (Spiegelachse) ein/aus."""
        self.canvas.mirror_horizontal = enabled
        self._update_symmetry_mode()
        self._sync_symmetry_combo()
        msg = "Symmetrie horizontal aktiviert" if enabled else "Symmetrie horizontal deaktiviert"
        self.status_bar.showMessage(msg, 2000)

    def _on_symmetry_v_changed(self: "MainWindow", enabled: bool) -> None:
        """Vertikale Symmetrie (Spiegelachse) ein/aus."""
        self.canvas.mirror_vertical = enabled
        self._update_symmetry_mode()
        self._sync_symmetry_combo()
        msg = "Symmetrie vertikal aktiviert" if enabled else "Symmetrie vertikal deaktiviert"
        self.status_bar.showMessage(msg, 2000)

    def _update_symmetry_mode(self: "MainWindow") -> None:
        """Aktualisiert den Spiegelmodus basierend auf den Checkbox-Werten."""
        from ..canvas import MirrorMode

        h = self.canvas.mirror_horizontal
        v = self.canvas.mirror_vertical

        # Wenn beide aktiv → 4-fach
        if h and v:
            self.canvas.mirror_mode = MirrorMode.QUAD
        elif h:
            self.canvas.mirror_mode = MirrorMode.HORIZONTAL
        elif v:
            self.canvas.mirror_mode = MirrorMode.VERTICAL
        else:
            self.canvas.mirror_mode = MirrorMode.NONE

    def _sync_symmetry_combo(self: "MainWindow") -> None:
        """Synchronisiert die ComboBox mit dem aktuellen Modus."""
        from ..canvas import MirrorMode

        mode = self.canvas.mirror_mode

        # ComboBox Index: 0=Aus, 1=Horiz, 2=Vert, 3=4-fach, 4=8-fach
        mode_to_index = {
            MirrorMode.NONE: 0,
            MirrorMode.HORIZONTAL: 1,
            MirrorMode.VERTICAL: 2,
            MirrorMode.QUAD: 3,
            MirrorMode.OCTAL: 4,
        }

        self.combo_symmetry.blockSignals(True)
        self.combo_symmetry.setCurrentIndex(mode_to_index.get(mode, 0))
        self.combo_symmetry.blockSignals(False)

    def _on_symmetry_mode_changed(self: "MainWindow", mode_index: int) -> None:
        """Setzt den Symmetrie-Modus direkt (für Dropdown/ComboBox)."""
        from ..canvas import MirrorMode

        modes = [
            MirrorMode.NONE,
            MirrorMode.HORIZONTAL,
            MirrorMode.VERTICAL,
            MirrorMode.QUAD,
            MirrorMode.OCTAL,
        ]

        if 0 <= mode_index < len(modes):
            mode = modes[mode_index]
            self.canvas.mirror_mode = mode

            # Checkboxen synchronisieren
            self.chk_symmetry_h.blockSignals(True)
            self.chk_symmetry_v.blockSignals(True)

            self.chk_symmetry_h.setChecked(
                mode in (MirrorMode.HORIZONTAL, MirrorMode.QUAD, MirrorMode.OCTAL)
            )
            self.chk_symmetry_v.setChecked(
                mode in (MirrorMode.VERTICAL, MirrorMode.QUAD, MirrorMode.OCTAL)
            )
            self.canvas.mirror_horizontal = self.chk_symmetry_h.isChecked()
            self.canvas.mirror_vertical = self.chk_symmetry_v.isChecked()

            self.chk_symmetry_h.blockSignals(False)
            self.chk_symmetry_v.blockSignals(False)

            mode_names = {
                MirrorMode.NONE: "Keine Symmetrie",
                MirrorMode.HORIZONTAL: "2-fach (Horizontal)",
                MirrorMode.VERTICAL: "2-fach (Vertikal)",
                MirrorMode.QUAD: "4-fach (Quadrant)",
                MirrorMode.OCTAL: "8-fach (Oktagonal)",
            }
            self.status_bar.showMessage(f"Symmetrie: {mode_names.get(mode, '?')}", 2000)

    def _on_center_crosshair_changed(self: "MainWindow", enabled: bool) -> None:
        """Zentrierhilfe ein/aus."""
        self.canvas.show_center_crosshair = enabled
        msg = "Zentrierhilfe aktiviert" if enabled else "Zentrierhilfe deaktiviert"
        self.status_bar.showMessage(msg, 2000)

    def _on_snap_grid_changed(self: "MainWindow", enabled: bool) -> None:
        """Magnetisches Raster ein/aus."""
        self.canvas.snap_to_grid = enabled
        self.canvas.snap_interval = self.canvas.minor_grid_interval
        if enabled:
            self.status_bar.showMessage(
                f"Magnetisches Raster aktiviert (alle {self.canvas.snap_interval} Zellen)", 2000
            )
        else:
            self.status_bar.showMessage("Magnetisches Raster deaktiviert", 2000)

    def _on_canvas_position_changed(self: "MainWindow", x: int, y: int) -> None:
        """Position auf Canvas hat sich geändert."""
        self.label_position.setText(f"X: {x}  Y: {y}")

        color_idx = self.current_pattern.get_stitch(x, y)
        if color_idx is not None:
            entry = self.current_pattern.get_color_entry(color_idx)
            if entry:
                self.label_color_info.setText(f"■ {entry.symbol} {entry.thread.name}")
                r, g, b = entry.thread.color.r, entry.thread.color.g, entry.thread.color.b
                text_color = "#ffffff" if entry.thread.color.luminance < 0.5 else "#000000"
                self.label_color_info.setStyleSheet(
                    f"background-color: rgb({r},{g},{b}); "
                    f"color: {text_color}; "
                    f"padding: 2px 6px; "
                    f"border-radius: 3px; "
                    f"font-weight: bold;"
                )
            else:
                self._clear_color_info()
        else:
            self._clear_color_info()

    def _clear_color_info(self: "MainWindow") -> None:
        """Setzt die Farbinfo-Anzeige auf den neutralen Leer-Zustand."""
        from ...core.i18n import t
        from ..styles import THEME

        self.label_color_info.setText(t("— leer —"))
        # gleiches Padding/Border-Radius wie im belegten Zustand,
        # damit das Label nicht zucken kann
        self.label_color_info.setStyleSheet(
            f"padding: 2px 6px; border-radius: 3px; color: {THEME.text_muted};"
        )

    def _on_canvas_zoom_changed(self: "MainWindow", factor: float) -> None:
        """Zoom-Level hat sich geändert."""
        # Zoom-Slider aktualisieren (ohne Signal auszulösen)
        if hasattr(self, "zoom_slider"):
            self.zoom_slider.set_zoom_from_factor(factor)

    def _on_zoom_slider_changed(self: "MainWindow", percent: int) -> None:
        """Zoom-Slider wurde bewegt."""
        factor = percent / 100.0
        self.canvas.set_zoom(factor)

    def _on_minimap_navigate(self: "MainWindow", rel_x: float, rel_y: float) -> None:
        """Navigiert zu einer Position in der Minimap."""
        if not self.current_pattern:
            return

        pattern_w = self.current_pattern.width * self.canvas._cell_size
        pattern_h = self.current_pattern.height * self.canvas._cell_size

        target_x = rel_x * pattern_w
        target_y = rel_y * pattern_h

        canvas_w = self.canvas.width()
        canvas_h = self.canvas.height()

        new_offset_x = int(canvas_w / 2 - target_x)
        new_offset_y = int(canvas_h / 2 - target_y)

        self.canvas.set_offset(new_offset_x, new_offset_y)
        self._update_minimap_viewport()

    def _update_minimap_viewport(
        self: "MainWindow", offset_x: int = None, offset_y: int = None
    ) -> None:
        """Aktualisiert den Viewport in der Minimap."""
        if not self.current_pattern:
            return

        if offset_x is None:
            offset_x = self.canvas._offset_x
        if offset_y is None:
            offset_y = self.canvas._offset_y

        cell_size = self.canvas._cell_size
        canvas_w = self.canvas.width()
        canvas_h = self.canvas.height()

        pattern_w = self.current_pattern.width * cell_size
        pattern_h = self.current_pattern.height * cell_size

        if pattern_w == 0 or pattern_h == 0:
            return

        vp_x = -offset_x / pattern_w
        vp_y = -offset_y / pattern_h
        vp_w = canvas_w / pattern_w
        vp_h = canvas_h / pattern_h

        self.minimap_panel.set_viewport(vp_x, vp_y, vp_w, vp_h)
