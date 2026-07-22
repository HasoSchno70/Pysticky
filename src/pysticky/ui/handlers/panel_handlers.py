"""
Panel/Color-Handler für MainWindow.
"""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from ..main_window import MainWindow

from ...core.i18n import t
from ...utils import get_logger
from ..notify_scope import NotifyScope

logger = get_logger(__name__)


class PanelHandlersMixin:
    """Mixin für Panel- und Farb-bezogene Handler."""

    def _on_color_selected(self: "MainWindow", index: int) -> None:
        """Farbe ausgewählt — sync zwischen Canvas, ColorBar und InfoPanel."""
        self.canvas.set_current_color(index)
        # InfoPanel-Farbübersicht: aktive Farbe markieren
        if hasattr(self.info_panel, "set_selected_color"):
            self.info_panel.set_selected_color(index)
        # Einstellungen → Farben → "Ausgewählte Farbe hervorheben": isoliert
        # automatisch jede neu zum Zeichnen gewaehlte Farbe (gleicher Effekt
        # wie Strg+H, nur automatisch statt manuell ausgeloest).
        if self._settings.value("highlight_selected", True, type=bool):
            self._on_isolate_color(index)
        # Rueckstich-Vorschau im Options-Panel mitziehen, falls sichtbar.
        if self.backstitch_options_dock.isVisible():
            entry = self.current_pattern.get_color_entry(index)
            if entry:
                from ..color_utils import to_qcolor

                self.backstitch_options_panel._preview.set_color(to_qcolor(entry.thread.color))

    def _on_info_color_clicked(self: "MainWindow", index: int) -> None:
        """Klick auf eine Farbe in der Info-Panel-Übersicht."""
        # ColorBar selektieren (das emittiert color_selected → _on_color_selected)
        self.color_bar.select_color(index)
        self.canvas.set_current_color(index)
        if hasattr(self.info_panel, "set_selected_color"):
            self.info_panel.set_selected_color(index)

    def _on_color_double_clicked(self: "MainWindow", index: int) -> None:
        """Öffnet den Symbol-Editor für die Farbe."""
        from ..dialogs import SymbolEditorDialog

        if not (0 <= index < len(self.current_pattern.color_entries)):
            return

        dialog = SymbolEditorDialog(self.current_pattern, index, self)
        entry = self.current_pattern.color_entries[index]
        self._exec_edit_dialog(
            dialog,
            NotifyScope.PALETTE,
            f"Symbol geändert: {entry.thread.name} → {entry.symbol}",
        )

    def _on_color_right_clicked(self: "MainWindow", index: int, global_pos) -> None:
        """Zeigt Kontextmenü für Farbe an."""
        from PySide6.QtCore import QPoint
        from PySide6.QtWidgets import QMenu

        if not (0 <= index < len(self.current_pattern.color_entries)):
            return

        entry = self.current_pattern.color_entries[index]
        menu = QMenu(self)

        action_symbol = menu.addAction("🔤 Symbol ändern...")
        action_symbol.triggered.connect(lambda: self._on_color_double_clicked(index))

        action_harmony = menu.addAction("🎨 Farb-Harmonien suchen...")
        action_harmony.triggered.connect(lambda: self._on_color_harmony(index))

        menu.addSeparator()

        # Farb-Isolation: nur diese Farbe voll, andere gedimmt
        is_isolated = self.canvas.isolate_color_index == index
        if is_isolated:
            action_iso = menu.addAction("❌ Farb-Hervorhebung aufheben")
            action_iso.triggered.connect(lambda: self._on_isolate_color(None))
        else:
            action_iso = menu.addAction("🔍 Nur diese Farbe hervorheben")
            action_iso.triggered.connect(lambda: self._on_isolate_color(index))

        menu.addSeparator()

        if entry.skip_stitching:
            action_skip = menu.addAction("✓ Farbe sticken")
            action_skip.triggered.connect(lambda: self._toggle_skip_stitching(index, False))
        else:
            action_skip = menu.addAction("⊘ Nicht sticken (Stofffarbe)")
            action_skip.triggered.connect(lambda: self._toggle_skip_stitching(index, True))

        menu.addSeparator()

        action_replace = menu.addAction("⇄ Farbe ersetzen...")
        action_replace.triggered.connect(lambda: self._on_replace_color_for(index))

        if len(self.current_pattern.color_entries) >= 2:
            action_swap = menu.addAction("⇅ Mit anderer Farbe tauschen...")
            action_swap.triggered.connect(lambda: self._on_swap_color_for(index))

        if isinstance(global_pos, QPoint):
            menu.exec(global_pos)
        else:
            menu.exec(QPoint(int(global_pos.x()), int(global_pos.y())))

    def _on_isolate_color(self: "MainWindow", index: "int | None") -> None:
        """Isoliert eine Farbe (None = Isolation aufheben).

        Wenn isoliert: andere Farben werden im Canvas mit ~20% Alpha gerendert,
        die ColorBar zeigt einen Lupen-Indikator am Swatch.
        """
        self.canvas.set_isolate_color(index)
        # Swatch-Visualisierung aktualisieren
        if hasattr(self.color_bar, "set_isolated_index"):
            self.color_bar.set_isolated_index(index)
        if index is None:
            self.status_bar.showMessage("Farb-Hervorhebung aufgehoben", 2500)
        else:
            entry = self.current_pattern.color_entries[index]
            self.status_bar.showMessage(
                f"Hervorgehoben: {entry.thread.name} (Strg+H zum Aufheben)", 3500
            )

    def _on_toggle_isolate_current_color(self: "MainWindow") -> None:
        """Toggle: aktive Farbe isolieren / Isolation aufheben (Strg+H)."""
        if not self.current_pattern or not self.current_pattern.color_entries:
            return
        current = self.color_bar.current_index
        if self.canvas.isolate_color_index == current:
            self._on_isolate_color(None)
        else:
            self._on_isolate_color(current)

    def _toggle_skip_stitching(self: "MainWindow", index: int, skip: bool) -> None:
        """Schaltet 'Nicht sticken' für eine Farbe um."""
        if 0 <= index < len(self.current_pattern.color_entries):
            entry = self.current_pattern.color_entries[index]
            entry.skip_stitching = skip
            self.color_bar.refresh()
            self.info_panel.update_info(self.current_pattern)
            self._mark_unsaved()
            msg = f"Farbe '{entry.thread.name}' wird {'nicht ' if skip else ''}gestickt"
            self.status_bar.showMessage(msg, self._status_timeout_ms)

    def _on_color_harmony(self: "MainWindow", index: int) -> None:
        """Öffnet den Farb-Harmonien-Dialog."""
        from ..dialogs import ColorHarmonyDialog

        if not (0 <= index < len(self.current_pattern.color_entries)):
            return

        dialog = ColorHarmonyDialog(self.current_pattern, index, self)
        dialog.colors_selected.connect(self._on_harmony_colors_selected)
        dialog.exec()

    def _on_color_harmony_current(self: "MainWindow") -> None:
        """Öffnet Farb-Harmonien für die aktuell ausgewählte Farbe."""
        if self.current_pattern.color_entries:
            self._on_color_harmony(self.color_bar.current_index)
        else:
            QMessageBox.information(
                self, "Keine Farbe", "Bitte fügen Sie zuerst eine Farbe zum Muster hinzu."
            )

    def _on_harmony_colors_selected(self: "MainWindow", threads: list) -> None:
        """Fügt ausgewählte harmonische Farben zum Muster hinzu."""
        added = 0
        for thread in threads:
            self.add_color_to_pattern(thread)
            added += 1

        if added > 0:
            self.color_bar.refresh()
            self.info_panel.update_info(self.current_pattern)
            self._mark_unsaved()
            self.status_bar.showMessage(
                f"{added} harmonische Farbe(n) hinzugefügt", self._status_timeout_ms
            )

    def _on_replace_color_for(self: "MainWindow", index: int) -> None:
        """Ersetzt eine bestimmte Farbe."""
        self.color_bar.select_color(index)
        self._on_replace_color()

    def _on_swap_color_for(self: "MainWindow", index: int) -> None:
        """Öffnet den Tauschen-Dialog mit vorgewählter Farbe A."""
        self.color_bar.select_color(index)
        self._on_swap_colors()

    def _on_color_swap_dropped(self: "MainWindow", src: int, dst: int) -> None:
        """Drag&Drop: Farbe src wurde auf Farbe dst fallen gelassen — direkt tauschen."""
        n = len(self.current_pattern.color_entries)
        if not (0 <= src < n) or not (0 <= dst < n) or src == dst:
            return
        self._swap_color_pair(src, dst)
        self.color_bar.refresh()
        self._mark_unsaved()

    def _on_palette_color_added(self: "MainWindow", thread) -> None:
        """Farbe aus Palette hinzugefügt."""
        index = self.add_color_to_pattern(thread)
        self.color_bar.refresh()
        self.canvas.set_current_color(index)
        self.color_bar.select_color(index)
        self.palette_panel.refresh_used_colors()
        self.info_panel.update_info(self.current_pattern)
        self._mark_unsaved()
        self.status_bar.showMessage(f"Farbe hinzugefügt: {thread.name}", self._status_timeout_ms)

    def _on_color_dropped(self: "MainWindow", thread) -> None:
        """Farbe per Drag&Drop hinzugefügt."""
        self._on_palette_color_added(thread)

    def _on_palette_change_requested(self: "MainWindow", new_palette_name: str) -> None:
        """Palette wechseln angefordert."""
        from ...core import can_change_palette, change_palette

        if not can_change_palette(self.current_pattern):
            QMessageBox.warning(
                self,
                "Palettenwechsel nicht möglich",
                "Das Muster wurde nicht aus einem Bild importiert\noder das Originalbild ist nicht mehr verfügbar.",
            )
            return
        self.status_bar.showMessage(f"Erstelle Muster mit {new_palette_name}...")
        self.repaint()
        try:
            new_pattern = change_palette(self.current_pattern, new_palette_name)
            if new_pattern:
                self.current_file = None
                self.set_pattern(new_pattern)
                self._mark_unsaved()
                self.status_bar.showMessage(
                    f"Muster mit {new_palette_name} erstellt: {len(new_pattern.color_entries)} Farben",
                    5000,
                )
            else:
                logger.warning("Palettenwechsel lieferte kein Muster")
                QMessageBox.critical(self, t("Fehler"), t("Palettenwechsel fehlgeschlagen."))
        except (ValueError, OSError) as e:
            logger.exception("Palettenwechsel fehlgeschlagen")
            QMessageBox.critical(self, t("Fehler"), f"Palettenwechsel fehlgeschlagen:\n{e}")

    def _on_layer_selected(self: "MainWindow", index: int) -> None:
        """Ebene ausgewählt."""
        self._update_status()
        self.canvas.update()

    def _on_layers_changed(self: "MainWindow") -> None:
        """Ebenen geändert."""
        self._update_status()
        self.info_panel.update_info(self.current_pattern)
        self._notify_panels(NotifyScope.VISUAL)
        self._mark_unsaved()

    def _on_layer_structure_changed(self: "MainWindow") -> None:
        """Ebene hinzugefügt/entfernt/dupliziert/verschoben/vereint.

        Bereits ausgeführte Undo-Commands (PlaceStitchCommand etc.) halten
        einen fest eingebrannten `layer_index` und würden nach einer
        Struktur-Änderung entweder auf eine falsche Ebene zeigen (bei
        Verschieben/Hinzufügen/Duplizieren) oder mit IndexError crashen (bei
        Entfernen/Vereinen, wenn der Stack dadurch kürzer wird) -- Undo-
        Verlauf muss daher geleert werden, exakt wie bei "Ebenen vereinen"
        (misc_handlers.py::_on_flatten_layers) bereits gehandhabt.
        """
        self.undo_manager.clear()
        self._update_undo_actions()

    def _on_clear_layer_requested(self: "MainWindow", layer_index: int) -> None:
        """Leert eine Ebene ueber ClearLayerCommand (undoable, respektiert
        layer.locked, aktualisiert stitch_count) statt layer.clear() direkt
        aus dem Panel aufzurufen -- LayerPanel kennt nur den LayerStack,
        nicht das volle Pattern."""
        from ...core import ClearLayerCommand

        cmd = ClearLayerCommand(self.current_pattern, layer_index)
        self.undo_manager.execute(cmd)
        self._update_undo_actions()
        self._mark_unsaved()
        self.layer_panel._refresh_list()
        self.info_panel.update_info(self.current_pattern)
        self._notify_panels(NotifyScope.VISUAL)

    def _on_color_picked(self: "MainWindow", color_index: int) -> None:
        """Farbe mit Pipette aufgenommen."""
        from ..tools.tool_enum import Tool

        if 0 <= color_index < len(self.current_pattern.color_entries):
            self.canvas.set_current_color(color_index)
            self.color_bar.select_color(color_index)
            if self._settings.value("pipette_show_info", True, type=bool):
                entry = self.current_pattern.color_entries[color_index]
                self.status_bar.showMessage(
                    f"Farbe aufgenommen: {entry.thread.name} ({entry.symbol})",
                    self._status_timeout_ms,
                )
            # Einstellungen → Werkzeuge → "Nach Aufnahme": 0=Stift (Default,
            # bisheriges Verhalten), 1=beim Werkzeug bleiben, 2=Auswahl.
            behavior = self._settings.value("pipette_behavior", 0, type=int)
            if behavior == 1:
                pass  # Pipette bleibt aktiv
            elif behavior == 2:
                self.tool_bar.select_tool(Tool.SELECT)
            else:
                self.tool_bar.select_tool(Tool.PENCIL)
