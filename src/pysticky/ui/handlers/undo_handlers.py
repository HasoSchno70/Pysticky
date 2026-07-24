"""
Undo/Redo- und Fortschritts-Handler für MainWindow.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

from ...core.i18n import t

if TYPE_CHECKING:
    from ..main_window import MainWindow

from ..notify_scope import NotifyScope


class UndoHandlersMixin:
    """Mixin für Undo/Redo-Signalverarbeitung und Fortschritts-Handler."""

    def _execute_command(self: "MainWindow", command, *, scope: str = "stitch") -> None:
        """Führt ein Undo-Command aus (batch-aware)."""
        if self.undo_manager.in_batch:
            self.undo_manager.add_to_batch(command)
            # Panel-Updates aufschieben: _notify_panels("stitch") rechnet die
            # komplette Muster-Statistik neu — pro Stich aufgerufen macht das
            # große Batches (Farbe ersetzen, Füllen, Spiegeln) quadratisch
            # langsam (40.000 Stiche => minutenlanger UI-Freeze).
            self._pending_batch_scopes = getattr(self, "_pending_batch_scopes", set())
            self._pending_batch_scopes.add(scope)
            # _mark_unsaved() NICHT auf Batch-Ende aufschieben (anders als
            # die Panel-Benachrichtigung oben) -- add_to_batch() fuehrt den
            # Command sofort aus, die Grid-Mutation liegt also schon vor,
            # waehrend die Batch noch offen ist. Ein Drag-Zeichnen spannt
            # mehrere Maus-Move-Events (= mehrere Event-Loop-Durchlaeufe)
            # auf, zwischen denen der Autosave-QTimer feuern kann. Ohne
            # dieses _mark_unsaved() blieb _unsaved_changes waehrend der
            # gesamten Batch False, wenn sie die erste Aenderung seit dem
            # letzten Speichern war -- _on_autosave() gab dann sofort auf
            # (_unsaved_changes==False) und liess bereits ausgefuehrte
            # Grid-Mutationen bei einem Absturz mitten im Drag ohne jede
            # Recovery-Moeglichkeit zurueck.
            self._mark_unsaved()
        else:
            self.undo_manager.execute(command)
            self._update_undo_actions()
            self._mark_unsaved()
            self._notify_panels(scope)

    def _on_batch_started(self: "MainWindow", description: str) -> None:
        """Batch-Undo beginnen."""
        self.undo_manager.begin_batch(description)
        self._pending_batch_scopes: set = set()

    def _on_batch_ended(self: "MainWindow") -> None:
        """Batch-Undo beenden."""
        self.undo_manager.end_batch()
        self._update_undo_actions()
        self._mark_unsaved()
        # Aufgeschobene Panel-Updates jetzt genau einmal ausführen
        for scope in getattr(self, "_pending_batch_scopes", set()):
            self._notify_panels(scope)
        self._pending_batch_scopes = set()
        QTimer.singleShot(100, self.minimap_panel.refresh)
        QTimer.singleShot(100, self.tile_preview_panel.refresh)

    def _on_stitch_placed(self: "MainWindow", x: int, y: int, color_index: int) -> None:
        """Stich platziert (normale Zeichen-Werkzeuge -- Stichtyp kommt vom
        globalen canvas._active_stitch_type)."""
        stitch_type = getattr(self.canvas, "_active_stitch_type", 0)
        self._place_stitch(x, y, color_index, stitch_type)

    def _on_stitch_placed_typed(
        self: "MainWindow", x: int, y: int, color_index: int, stitch_type: int
    ) -> None:
        """Stich platziert MIT explizitem Stichtyp.

        Genutzt von Select/Lasso-Tool-Operationen (Verschieben/Drehen/
        Spiegeln/Einfuegen), die den urspruenglichen Stichtyp einer Zelle
        bewahren wollen -- vorher landete hier IMMER der globale
        _active_stitch_type, wodurch z.B. ein Halb-/Viertelstich nach dem
        Verschieben als voller Stich wieder auftauchte.
        """
        self._place_stitch(x, y, color_index, stitch_type)

    def _place_stitch(
        self: "MainWindow", x: int, y: int, color_index: int, stitch_type: int
    ) -> None:
        from ...core import PlaceStitchCommand

        # Werkzeuge kennen nur canvas._current_color_index, nicht ob die
        # Palette ueberhaupt eine Farbe an diesem Index hat (z.B. neues
        # Muster ohne hinzugefuegte Farbe). Ohne diese Pruefung landet ein
        # Stich mit ungueltigem Farbindex im Layer-Grid: er zaehlt zur
        # Stichzahl, wird aber nirgends gerendert -- "leere Zeichnung" trotz
        # steigendem Stich-Zaehler.
        if not (0 <= color_index < len(self.current_pattern.color_entries)):
            self.status_bar.showMessage(
                t("Bitte zuerst eine Farbe aus der Palette hinzufügen"), self._status_timeout_ms
            )
            return

        layer_index = self.current_pattern.layer_stack.active_index
        self._execute_command(
            PlaceStitchCommand(
                self.current_pattern, x, y, color_index, layer_index, stitch_type=stitch_type
            )
        )

    def _on_stitch_removed(self: "MainWindow", x: int, y: int) -> None:
        """Stich entfernt.

        Guard VOR dem Erzeugen des Commands: eine bereits leere Zelle oder
        eine gesperrte Ebene macht RemoveStitchCommand.execute() ohnehin zu
        einem echten No-Op (kein Grid-Schreibzugriff, alle Zaehler
        unveraendert) -- ohne diesen Guard landete trotzdem ein wirkungsloser
        Eintrag auf dem Undo-Stack (bzw. im laufenden Batch), den man per
        Strg+Z durchklicken musste, ohne dass sich je etwas sichtbar
        aenderte. Gleiche Fehlerklasse wie der Lasso-Klick-ohne-Drag-No-Op
        aus einer frueheren Audit-Runde.
        """
        from ...core import RemoveStitchCommand

        layer_index = self.current_pattern.layer_stack.active_index
        layer = self.current_pattern.layer_stack[layer_index]
        if layer.locked or layer.get_stitch(x, y) is None:
            return
        self._execute_command(RemoveStitchCommand(self.current_pattern, x, y, layer_index))

    def _on_backstitch_added(
        self: "MainWindow", x1: int, y1: int, x2: int, y2: int, color_index: int
    ) -> None:
        """Rückstich hinzugefügt."""
        from ...core import AddBackstitchCommand

        # Batch-aware (wie _on_stitch_placed/_on_stitch_removed) -- noetig
        # seit Spiegel-Modus mehrere Rueckstich-Linien pro Klick erzeugen
        # kann, die als EINE Undo-Aktion zusammengefasst werden muessen.
        command = AddBackstitchCommand(self.current_pattern, x1, y1, x2, y2, color_index)
        self._execute_command(command)
        self.canvas.update()

    def _on_backstitch_removed(
        self: "MainWindow", x1: int, y1: int, x2: int, y2: int, color_index: int
    ) -> None:
        """Rückstich entfernt."""
        from ...core import RemoveBackstitchCommand

        for bs in self.current_pattern.backstitches:
            if (
                bs.x1 == x1
                and bs.y1 == y1
                and bs.x2 == x2
                and bs.y2 == y2
                and bs.color_index == color_index
            ):
                command = RemoveBackstitchCommand(self.current_pattern, bs)
                self._execute_command(command)
                self.canvas.update()
                break

    # === Fortschritts-Handler ===

    def _on_stitch_marked_completed(self: "MainWindow", x: int, y: int) -> None:
        """Stich als erledigt markiert.

        Sucht automatisch die oberste sichtbare Ebene mit einem Stich an (x, y).
        Vorher war nur die aktive Ebene möglich — verwirrend wenn der User auf
        einen Stich klickt der auf einer anderen Ebene liegt.
        """
        from ...core import MarkStitchCompletedCommand

        layer_index = self._find_layer_with_stitch_at(x, y)
        if layer_index is None:
            # Leere Zelle — kein Stich da. Bei sehr vielen Drag-Events nicht
            # spammen, aber im Sticken-Modus dem User Feedback geben.
            if getattr(self, "action_stitch_mode", None) and self.action_stitch_mode.isChecked():
                self.status_bar.showMessage(
                    f"Keine Stiche bei ({x}, {y}) — Ebene leer oder versteckt", 2000
                )
            return
        # Gesperrte Ebene: MarkStitchCompletedCommand waere ohnehin
        # wirkungslos (layer.mark_completed() blockt das jetzt intern wie
        # set_stitch()), aber ohne diesen Guard landete trotzdem ein
        # wirkungsloser Eintrag auf dem Undo-Stack -- gleiche Fehlerklasse wie
        # der Radiergummi-Guard in _on_stitch_removed().
        if self.current_pattern.layer_stack[layer_index].locked:
            return
        self._execute_command(
            MarkStitchCompletedCommand(self.current_pattern, x, y, layer_index),
            scope="progress",
        )

    def _on_stitch_unmarked_completed(self: "MainWindow", x: int, y: int) -> None:
        """Stich-Markierung entfernt.

        Sucht automatisch die oberste sichtbare Ebene mit einem Stich an (x, y).
        """
        from ...core import UnmarkStitchCompletedCommand

        layer_index = self._find_layer_with_stitch_at(x, y)
        if layer_index is None:
            return
        # Siehe Kommentar in _on_stitch_marked_completed() -- derselbe Guard
        # gegen einen wirkungslosen Undo-Eintrag auf einer gesperrten Ebene.
        if self.current_pattern.layer_stack[layer_index].locked:
            return
        self._execute_command(
            UnmarkStitchCompletedCommand(self.current_pattern, x, y, layer_index),
            scope="progress",
        )

    def _find_layer_with_stitch_at(self: "MainWindow", x: int, y: int) -> int | None:
        """Liefert den Index der obersten sichtbaren Ebene mit einem Stich an (x, y),
        oder None wenn dort kein Stich ist."""
        stack = self.current_pattern.layer_stack
        # Layer von oben nach unten — top wins
        for idx in range(len(stack) - 1, -1, -1):
            layer = stack[idx]
            if not layer.visible:
                continue
            if layer.get_stitch(x, y) is not None:
                return idx
        return None

    def _on_mark_color_completed(self: "MainWindow", color_index: int) -> None:
        """Alle Stiche einer Farbe als erledigt markieren."""
        from ...core import MarkColorCompletedCommand

        command = MarkColorCompletedCommand(self.current_pattern, color_index)
        self.undo_manager.execute(command)
        self._update_undo_actions()
        self._mark_unsaved()
        self._notify_panels(NotifyScope.PROGRESS)
        self.canvas.update()
        # Statusbar-Feedback — sonst wirkt der Klick „passiert nichts"
        if 0 <= color_index < len(self.current_pattern.color_entries):
            entry = self.current_pattern.color_entries[color_index]
            self.status_bar.showMessage(
                f"Farbe '{entry.thread.name}' komplett als erledigt markiert", 3000
            )

    def _on_reset_progress(self: "MainWindow") -> None:
        """Gesamten Fortschritt zurücksetzen."""
        reply = QMessageBox.question(
            self,
            t("Fortschritt zurücksetzen"),
            t(
                "Gesamten Stickfortschritt zurücksetzen?\n"
                "Dies kann nicht rückgängig gemacht werden."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.current_pattern.reset_progress()
            self.undo_manager.clear()
            self._update_undo_actions()
            self._mark_unsaved()
            self._update_progress_displays()
            self.canvas.update()
            self.status_bar.showMessage("Fortschritt zurückgesetzt", self._status_timeout_ms)

    def _update_progress_displays(self: "MainWindow") -> None:
        """Aktualisiert alle UI-Elemente die den Fortschritt anzeigen."""
        self._notify_panels(NotifyScope.PROGRESS)
