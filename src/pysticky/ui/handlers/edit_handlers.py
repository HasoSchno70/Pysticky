"""
Bearbeiten-bezogene Handler für MainWindow.
"""

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from ..main_window import MainWindow

from ...core.constants import MAX_PATTERN_SIZE
from ...core.i18n import t
from ...utils import get_logger
from ..notify_scope import NotifyScope

logger = get_logger(__name__)


class EditHandlersMixin:
    """Mixin-Klasse für Bearbeiten-Operationen."""

    def _on_undo(self: "MainWindow") -> None:
        """Undo ausführen."""
        if self.undo_manager.undo():
            self._notify_panels(NotifyScope.STITCH_VISUAL)
            self._update_undo_actions()
            self._mark_unsaved()
            self.status_bar.showMessage(t("Rückgängig"), 2000)

    def _on_redo(self: "MainWindow") -> None:
        """Redo ausführen."""
        if self.undo_manager.redo():
            self._notify_panels(NotifyScope.STITCH_VISUAL)
            self._update_undo_actions()
            self._mark_unsaved()
            self.status_bar.showMessage(t("Wiederholt"), 2000)

    def _on_replace_color(self: "MainWindow") -> None:
        """Zeigt den Dialog zum Farbe ersetzen."""
        from ..dialogs import ReplaceColorDialog

        current_color = self.color_bar.current_index if hasattr(self, "color_bar") else 0

        dialog = ReplaceColorDialog(self.current_pattern, current_color, self)

        if dialog.exec():
            # Dialog liefert 1..n Ersetzungen: eine beim manuellen Ersetzen,
            # mehrere beim Auto-Reduzieren seltener Farben.
            mapping = dict(dialog.get_replacements())
            if not mapping:
                return

            changes = [
                (x, y, mapping[color_idx])
                for x, y, color_idx in self.current_pattern.iterate_composite_stitches()
                if color_idx in mapping
            ]

            if changes:
                from PySide6.QtGui import QCursor
                from PySide6.QtWidgets import QApplication

                QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
                try:
                    self.canvas.batch_started.emit(t("Farbe ersetzen"))
                    # _apply_changes() statt manuellem Signal-Loop -- ruft
                    # u.a. invalidate_cell() auf, sonst bleibt der
                    # Chunk-Pixmap-Cache (>200x200 Muster) beim alten Bild
                    # haengen (gleicher Bug wie Runde 4 bei Selection-Ops,
                    # hier an einer bis Runde 13 uebersehenen Stelle).
                    self.canvas._apply_changes(cast("list[tuple[int, int, int | None]]", changes))
                    self.canvas.batch_ended.emit()
                finally:
                    QApplication.restoreOverrideCursor()

                self.canvas.update()
                self.info_panel.update_info(self.current_pattern)
                if len(mapping) == 1:
                    self.status_bar.showMessage(
                        f"{len(changes)} Stiche ersetzt", self._status_timeout_ms
                    )
                else:
                    self.status_bar.showMessage(
                        f"{len(changes)} Stiche in {len(mapping)} Farben ersetzt", 3000
                    )
            else:
                self.status_bar.showMessage(
                    t("Keine Stiche zum Ersetzen gefunden"), self._status_timeout_ms
                )

    def _on_swap_colors(self: "MainWindow") -> None:
        """Zeigt den Dialog zum Tauschen zweier Farben."""
        if len(self.current_pattern.color_entries) < 2:
            self.status_bar.showMessage(t("Mindestens 2 Farben benötigt"), self._status_timeout_ms)
            return

        from ..dialogs import SwapColorsDialog

        current_color = self.color_bar.current_index if hasattr(self, "color_bar") else 0

        dialog = SwapColorsDialog(self.current_pattern, current_color, self)
        if not dialog.exec():
            return

        a = dialog.get_first_index()
        b = dialog.get_second_index()
        self._swap_color_pair(a, b)

    def _swap_color_pair(self: "MainWindow", a: int, b: int) -> None:
        """Tauscht alle Stiche der Farben a und b kreuzweise."""
        if a == b:
            return

        a_positions: list[tuple[int, int]] = []
        b_positions: list[tuple[int, int]] = []
        for x, y, color_idx in self.current_pattern.iterate_composite_stitches():
            if color_idx == a:
                a_positions.append((x, y))
            elif color_idx == b:
                b_positions.append((x, y))

        total = len(a_positions) + len(b_positions)
        if total == 0:
            self.status_bar.showMessage(t("Keine Stiche zum Tauschen"), self._status_timeout_ms)
            return

        self.canvas.batch_started.emit(t("Farben tauschen"))
        # _apply_changes() statt manuellem Signal-Loop -- siehe _on_replace_color.
        changes = [(x, y, b) for x, y in a_positions] + [(x, y, a) for x, y in b_positions]
        self.canvas._apply_changes(cast("list[tuple[int, int, int | None]]", changes))
        self.canvas.batch_ended.emit()

        self.canvas.update()
        self.info_panel.update_info(self.current_pattern)
        self.status_bar.showMessage(
            f"{len(a_positions)} ↔ {len(b_positions)} Stiche getauscht",
            3000,
        )

    def _on_merge_similar_colors(self: "MainWindow") -> None:
        """Zeigt den Dialog zum Zusammenführen ähnlicher Farben."""
        from ..dialogs import SimilarColorsDialog

        if len(self.current_pattern.color_entries) < 2:
            self.status_bar.showMessage(t("Mindestens 2 Farben benötigt"), self._status_timeout_ms)
            return

        dialog = SimilarColorsDialog(self.current_pattern, self)

        if dialog.exec():
            self._notify_panels(NotifyScope.PALETTE)
            self._update_status()
            self.undo_manager.clear()
            self._update_undo_actions()
            self._mark_unsaved()
            self.status_bar.showMessage(
                t("Ähnliche Farben zusammengeführt"), self._status_timeout_ms
            )

    def _on_manage_colors(self: "MainWindow") -> None:
        """Zeigt den Dialog zur Farbpaletten-Verwaltung."""
        from ..dialogs import ColorManagementDialog

        dialog = ColorManagementDialog(self.current_pattern, self)

        if dialog.exec() and dialog.has_changes():
            self._notify_panels(NotifyScope.PALETTE)
            self._update_status()
            self.undo_manager.clear()
            self._update_undo_actions()
            self._mark_unsaved()
            self.status_bar.showMessage(t("Farbpalette aktualisiert"), self._status_timeout_ms)

    def _on_screen_eyedropper(self: "MainWindow") -> None:
        """Öffnet den Vollbild-Screen-Eyedropper."""
        from ..dialogs import ScreenEyedropperDialog

        # Match auf die aktuell im Palette-Panel gewählte Palette
        # einschränken, statt über alle Hersteller zu suchen -- sonst
        # landet leicht eine Farbe eines fremden Herstellers im Muster.
        current_palette = self.palette_panel.current_palette_name()
        palette_names = [current_palette] if current_palette else None
        dialog = ScreenEyedropperDialog(self, palette_names=palette_names)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        thread = dialog.picked_thread
        if thread is None:
            color = dialog.picked_color
            if color is None:
                return
            # Fallback: Ad-hoc-Thread aus reiner Farbe
            from ...core import Thread
            from ..color_utils import from_qcolor

            thread = Thread(
                name=f"#{color.red():02X}{color.green():02X}{color.blue():02X}",
                color=from_qcolor(color),
            )

        self.add_color_to_pattern(thread)
        self._notify_panels(NotifyScope.PALETTE)
        self._update_status()
        self._mark_unsaved()
        self.status_bar.showMessage(
            f"Farbe gepickt: {thread.manufacturer or '?'} {thread.catalog_number or ''} — {thread.name}",
            5000,
        )

    def _on_show_plugins(self: "MainWindow") -> None:
        """Zeigt den Plugin-Picker- und -Runner-Dialog."""
        from ..dialogs import PluginDialog

        dialog = PluginDialog(self.current_pattern, self.undo_manager, self)
        dialog.exec()
        if dialog.executed:
            # Pattern wurde mutiert — UI neu rendern
            self._notify_panels(NotifyScope.PALETTE)
            self.canvas.update()
            self._update_status()
            self._mark_unsaved()
            self.status_bar.showMessage(t("Plugin ausgeführt"), self._status_timeout_ms)

    def _on_blend_threads(self: "MainWindow") -> None:
        """Zeigt den Dialog zur Erzeugung eines Tweed-Blends."""
        from ..dialogs import BlendThreadsDialog

        dialog = BlendThreadsDialog(self)
        if dialog.exec() and dialog.result_thread is not None:
            blend = dialog.result_thread
            self.current_pattern.add_color(blend)
            self._notify_panels(NotifyScope.PALETTE)
            self._update_status()
            self._mark_unsaved()
            self.status_bar.showMessage(f"Tweed-Blend hinzugefuegt: {blend.name}", 5000)

    def _on_show_statistics(self: "MainWindow") -> None:
        """Zeigt den Dialog für Muster-Statistiken und Garnverbrauch."""
        from ..dialogs import PatternStatisticsDialog

        dialog = PatternStatisticsDialog(self.current_pattern, self)
        dialog.exec()

    def _on_show_heatmap(self: "MainWindow") -> None:
        """Zeigt die Pattern-Heatmap (Stichdichte/Farbenvielfalt)."""
        from ..dialogs import HeatmapDialog

        dialog = HeatmapDialog(self.current_pattern, self)
        dialog.exec()

    def _on_show_inventory(self: "MainWindow") -> None:
        """Öffnet die Garn-Vorratsliste."""
        from ..dialogs import InventoryDialog

        dialog = InventoryDialog(self.current_pattern, self, current_file=self.current_file)
        dialog.exec()

    def _on_show_hoop_planner(self: "MainWindow") -> None:
        """Öffnet die Rahmenaufteilung."""
        from ..dialogs import HoopPlannerDialog

        dialog = HoopPlannerDialog(self.current_pattern, self)
        dialog.exec()

    def _on_auto_crop(self: "MainWindow") -> None:
        """Schneidet leere Ränder automatisch ab."""
        old_width = self.current_pattern.width
        old_height = self.current_pattern.height

        result = self.current_pattern.auto_crop()

        if result is None:
            self.status_bar.showMessage(
                t("Keine leeren Ränder zum Entfernen"), self._status_timeout_ms
            )
            return

        left, top, right, bottom = result
        new_width = self.current_pattern.width
        new_height = self.current_pattern.height

        self._notify_panels(NotifyScope.FULL)
        self.undo_manager.clear()
        self._update_undo_actions()
        self._mark_unsaved()

        self.status_bar.showMessage(
            f"Zugeschnitten: {old_width}×{old_height} → {new_width}×{new_height} "
            f"(L:{left} O:{top} R:{right} U:{bottom} entfernt)",
            5000,
        )

    def _on_resize_pattern(self: "MainWindow") -> None:
        """Zeigt einen Dialog zum Ändern der Mustergröße."""
        from PySide6.QtWidgets import (
            QCheckBox,
            QDialog,
            QDialogButtonBox,
            QFormLayout,
            QSpinBox,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle(t("Mustergröße ändern"))
        dialog.setMinimumWidth(340)

        layout = QFormLayout(dialog)

        current_width = self.current_pattern.width
        current_height = self.current_pattern.height
        # DP/Stitch-Terminologie -- Runde 23: dieser Dialog zeigte bisher
        # immer "Stiche", auch fuer Diamond-Painting-Muster, anders als
        # z.B. file_handlers.py::_on_new()s bereits etablierte
        # Modus-abhaengige Einheit.
        is_dp = self.current_pattern.mode == "diamond"
        unit = t("Drills") if is_dp else t("Stiche")

        spin_width = QSpinBox()
        spin_width.setRange(10, MAX_PATTERN_SIZE)
        spin_width.setValue(current_width)
        spin_width.setSuffix(f" {unit}")
        layout.addRow(t("Breite:"), spin_width)

        spin_height = QSpinBox()
        spin_height.setRange(10, MAX_PATTERN_SIZE)
        spin_height.setValue(current_height)
        spin_height.setSuffix(f" {unit}")
        layout.addRow(t("Höhe:"), spin_height)

        chk_smart = QCheckBox(t("Stiche neu verteilen (Smart-Resize)"))
        chk_smart.setToolTip(
            t(
                "Aktiv: Pattern wird wie ein Pixelbild per Nearest-Neighbor\n"
                "skaliert, Stiche neu auf die Zellgröße verteilt. Ideal beim\n"
                "Hochskalieren.\n\n"
                "Aus: klassisches Croppen/Padding mit leeren Zellen am Rand."
            )
        )
        layout.addRow(chk_smart)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_width = spin_width.value()
            new_height = spin_height.value()
            smart = chk_smart.isChecked()

            if new_width != current_width or new_height != current_height:
                if not smart and (new_width < current_width or new_height < current_height):
                    reply = QMessageBox.warning(
                        self,
                        t("Größe ändern"),
                        t(
                            "Das Muster wird verkleinert. {unit} außerhalb des neuen Bereichs gehen verloren.\n\nFortfahren?"
                        ).format(unit=unit),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        return

                if smart:
                    from ...core.smart_resize import smart_resize

                    smart_resize(self.current_pattern, new_width, new_height)
                else:
                    self.current_pattern.resize(new_width, new_height)
                self._notify_panels(NotifyScope.FULL)
                self.undo_manager.clear()
                self._update_undo_actions()
                self._mark_unsaved()
                self.status_bar.showMessage(
                    f"Größe geändert: {new_width} × {new_height}" + (" (smart)" if smart else ""),
                    3000,
                )

    # === Transformationen ===

    def _on_rotate_cw(self: "MainWindow") -> None:
        """Dreht das Muster 90° im Uhrzeigersinn."""
        self.current_pattern.rotate_90_cw()
        self._after_transform(t("90° rechts gedreht"))

    def _on_rotate_ccw(self: "MainWindow") -> None:
        """Dreht das Muster 90° gegen den Uhrzeigersinn."""
        self.current_pattern.rotate_90_ccw()
        self._after_transform(t("90° links gedreht"))

    def _on_rotate_180(self: "MainWindow") -> None:
        """Dreht das Muster um 180°."""
        self.current_pattern.rotate_180()
        self._after_transform(t("180° gedreht"))

    def _on_flip_horizontal(self: "MainWindow") -> None:
        """Spiegelt das Muster horizontal."""
        self.current_pattern.flip_horizontal()
        self._after_transform(t("Horizontal gespiegelt"))

    def _on_flip_vertical(self: "MainWindow") -> None:
        """Spiegelt das Muster vertikal."""
        self.current_pattern.flip_vertical()
        self._after_transform(t("Vertikal gespiegelt"))

    def _after_transform(self: "MainWindow", message: str) -> None:
        """Aktualisiert die UI nach einer Transformation."""
        self._notify_panels(NotifyScope.FULL)
        self.undo_manager.clear()
        self._update_undo_actions()
        self._mark_unsaved()

        self.status_bar.showMessage(
            f"{message}: {self.current_pattern.width}×{self.current_pattern.height}", 3000
        )

    # === Palette Export/Import/Konvertierung ===

    def _on_export_palette(self: "MainWindow") -> None:
        """Exportiert die aktuelle Farbpalette als JSON."""
        import json

        from PySide6.QtWidgets import QFileDialog

        if not self.current_pattern.color_entries:
            QMessageBox.information(
                self, t("Keine Farben"), t("Das Muster enthält keine Farben zum Exportieren.")
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            t("Palette exportieren"),
            f"{self.current_pattern.name}_palette.json",
            t("JSON-Dateien (*.json)"),
        )
        if not path:
            return

        colors = []
        for entry in self.current_pattern.color_entries:
            thread = entry.thread
            colors.append(
                {
                    "name": thread.name,
                    "color": {"r": thread.color.r, "g": thread.color.g, "b": thread.color.b},
                    "manufacturer": thread.manufacturer or "",
                    "catalog_number": thread.catalog_number or "",
                    "symbol": entry.symbol,
                }
            )

        data = {
            "format": "pysticky_palette",
            "version": "1.0",
            "name": self.current_pattern.name,
            "colors": colors,
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.status_bar.showMessage(f"Palette exportiert: {len(colors)} Farben → {path}", 5000)
        except OSError as e:
            logger.exception("Paletten-Export fehlgeschlagen: %s", path)
            QMessageBox.critical(self, t("Fehler"), f"Palette konnte nicht exportiert werden:\n{e}")

    def _on_import_palette(self: "MainWindow") -> None:
        """Importiert eine Farbpalette aus einer JSON-Datei."""
        import json

        from PySide6.QtWidgets import QFileDialog

        from ...core import Thread
        from ...core.thread import ThreadColor

        path, _ = QFileDialog.getOpenFileName(
            self, t("Palette importieren"), "", t("JSON-Dateien (*.json)")
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.exception("Paletten-Import fehlgeschlagen: %s", path)
            QMessageBox.critical(self, t("Fehler"), f"Datei konnte nicht gelesen werden:\n{e}")
            return

        if data.get("format") != "pysticky_palette":
            QMessageBox.warning(
                self,
                t("Ungültiges Format"),
                t("Die Datei ist keine gültige PySticky-Palettendatei."),
            )
            return

        colors = data.get("colors", [])
        if not colors:
            QMessageBox.information(self, t("Leer"), t("Die Palettendatei enthält keine Farben."))
            return

        added = 0
        for c in colors:
            color_data = c.get("color", {})
            thread = Thread(
                name=c.get("name", "Unbekannt"),
                color=ThreadColor(
                    r=color_data.get("r", 128),
                    g=color_data.get("g", 128),
                    b=color_data.get("b", 128),
                ),
                manufacturer=c.get("manufacturer") or None,
                catalog_number=c.get("catalog_number") or None,
            )
            index = self.add_color_to_pattern(thread)
            # Symbol setzen falls vorhanden
            symbol = c.get("symbol")
            if symbol and index < len(self.current_pattern.color_entries):
                self.current_pattern.color_entries[index].symbol = symbol
            added += 1

        self._notify_panels(NotifyScope.PALETTE)
        self._mark_unsaved()
        self.status_bar.showMessage(
            f"Palette importiert: {added} Farben aus {data.get('name', 'Unbekannt')}", 5000
        )

    def _on_convert_palette(self: "MainWindow") -> None:
        """Öffnet den Dialog zur Paletten-Konvertierung."""
        from ..dialogs import PaletteConversionDialog

        if not self.current_pattern.color_entries:
            QMessageBox.information(
                self, t("Keine Farben"), t("Das Muster enthält keine Farben zum Konvertieren.")
            )
            return

        dialog = PaletteConversionDialog(self.current_pattern, self)
        if dialog.exec():
            self._notify_panels(NotifyScope.PALETTE)
            self._update_status()
            self.undo_manager.clear()
            self._update_undo_actions()
            self._mark_unsaved()
            self.status_bar.showMessage(t("Palette konvertiert"), self._status_timeout_ms)

    # === Stickpfad-Optimierung ===

    def _on_stitch_path_optimizer(self: "MainWindow") -> None:
        """Öffnet den Stickpfad-Optimierungs-Dialog."""
        from ..dialogs import StitchPathDialog

        # Prüfen ob Stiche vorhanden sind
        stats = self.current_pattern.get_statistics()
        if stats["total_stitches"] == 0:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                t("Keine Stiche"),
                t(
                    "Das Muster enthält keine Stiche.\n"
                    "Fügen Sie zuerst Stiche hinzu, um den Pfad zu optimieren."
                ),
            )
            return

        dialog = StitchPathDialog(self.current_pattern, self)
        dialog.exec()

        self.status_bar.showMessage(
            t("Stickpfad-Optimierung abgeschlossen"), self._status_timeout_ms
        )
