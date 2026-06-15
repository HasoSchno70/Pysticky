"""
Auswahl-bezogene Handler fuer MainWindow.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..main_window import MainWindow


class SelectionHandlersMixin:
    """
    Mixin-Klasse fuer Auswahl-Operationen.

    Die meisten Handler folgen demselben Pattern:
    1) aktives Select-Tool holen, Auswahl pruefen
    2) Tool-Methode aufrufen, Change-Liste bekommen
    3) als Undo-Batch alle Changes emittieren
    4) Canvas neu zeichnen, Status melden

    Diese Logik wohnt in `_run_selection_op`. Copy/Paste haben abweichende
    Patterns (kein Batch / Tool-Wechsel) und bleiben als eigene Methoden.
    """

    # =========================================================================
    # Gemeinsamer Helper
    # =========================================================================

    def _run_selection_op(
        self: "MainWindow",
        method_name: str,
        batch_message: str,
        status_template: str,
        **method_kwargs,
    ) -> None:
        """
        Fuehrt eine Selection-Methode aus, die eine Change-Liste produziert.

        Args:
            method_name: Name der Methode auf SelectTool/LassoSelectTool
                (z.B. "delete_selection", "rotate_selection")
            batch_message: Label fuer den Undo-Batch
            status_template: Status-Text mit optionalem `{n}` fuer die
                Change-Anzahl (z.B. "Auswahl gefuellt: {n} Stiche")
            **method_kwargs: zusaetzliche Argumente fuer die Tool-Methode
        """
        select_tool = self.canvas._tool_manager.get_active_select_tool()
        if not select_tool or not select_tool.selection:
            return

        ctx = self.canvas._create_tool_context(0, 0)
        if not ctx:
            return

        method = getattr(select_tool, method_name)
        changes = method(ctx, **method_kwargs) if method_kwargs else method(ctx)
        if not changes:
            return

        self.canvas.batch_started.emit(batch_message)
        for x, y, color_idx in changes:
            if color_idx is None:
                self.canvas.stitch_removed.emit(x, y)
            else:
                self.canvas.stitch_placed.emit(x, y, color_idx)
        self.canvas.batch_ended.emit()
        self.canvas.update()
        self.status_bar.showMessage(status_template.format(n=len(changes)), 3000)

    # =========================================================================
    # Selection-Operationen (Change-produzierend)
    # =========================================================================

    def _on_selection_delete(self: "MainWindow") -> None:
        """Loescht den Inhalt der Auswahl."""
        self._run_selection_op(
            "delete_selection", "Auswahl loeschen", "Auswahl geloescht: {n} Stiche"
        )

    def _on_selection_fill(self: "MainWindow") -> None:
        """Fuellt die Auswahl mit der aktuellen Farbe."""
        self._run_selection_op("fill_selection", "Auswahl fuellen", "Auswahl gefuellt: {n} Stiche")

    def _on_selection_cut(self: "MainWindow") -> None:
        """Schneidet die Auswahl aus (kopiert + loescht)."""
        self._run_selection_op("cut_selection", "Ausschneiden", "Ausgeschnitten")

    def _on_selection_rotate_cw(self: "MainWindow") -> None:
        """Dreht die Auswahl 90° rechts."""
        self._run_selection_op(
            "rotate_selection",
            "90° rechts gedreht",
            "90° rechts gedreht",
            clockwise=True,
        )

    def _on_selection_rotate_ccw(self: "MainWindow") -> None:
        """Dreht die Auswahl 90° links."""
        self._run_selection_op(
            "rotate_selection",
            "90° links gedreht",
            "90° links gedreht",
            clockwise=False,
        )

    def _on_selection_flip_h(self: "MainWindow") -> None:
        """Spiegelt die Auswahl horizontal."""
        self._run_selection_op(
            "flip_selection_horizontal", "Horizontal gespiegelt", "Horizontal gespiegelt"
        )

    def _on_selection_flip_v(self: "MainWindow") -> None:
        """Spiegelt die Auswahl vertikal."""
        self._run_selection_op(
            "flip_selection_vertical", "Vertikal gespiegelt", "Vertikal gespiegelt"
        )

    # =========================================================================
    # Selection-Operationen mit abweichendem Pattern
    # =========================================================================

    def _on_selection_copy(self: "MainWindow") -> None:
        """Kopiert die Auswahl ins Clipboard (kein Batch, kein Canvas-Update)."""
        select_tool = self.canvas._tool_manager.get_active_select_tool()
        if not select_tool or not select_tool.selection:
            return
        ctx = self.canvas._create_tool_context(0, 0)
        if ctx and select_tool.copy_selection(ctx):
            w = select_tool.selection.width()
            h = select_tool.selection.height()
            self.status_bar.showMessage(f"Kopiert: {w} × {h}", 3000)

    def _on_selection_paste(self: "MainWindow") -> None:
        """Startet das Einfuegen — wechselt ggf. auf das Select-Tool."""
        from ..tools.tool_enum import Tool

        # Sonst gibt's keine Paste-Vorschau und der Klick zeichnet stattdessen.
        if self.canvas._tool_manager.current_tool not in (Tool.SELECT, Tool.SELECT_LASSO):
            self.tool_bar.select_tool(Tool.SELECT)

        select_tool = self.canvas._tool_manager.get_active_select_tool()
        if not select_tool:
            return

        ctx = self.canvas._create_tool_context(0, 0)
        if ctx:
            if select_tool.start_paste(ctx):
                self.canvas.update()
                self.status_bar.showMessage("Klicke zum Einfuegen...", 5000)
            else:
                self.status_bar.showMessage("Nichts zum Einfuegen", 3000)

    # =========================================================================
    # Spiegel-Aktionen (operieren auf gesamtem Muster, nicht Auswahl)
    # =========================================================================

    def _on_mirror_h(self: "MainWindow") -> None:
        """Horizontal spiegeln (ueber `Canvas.mirror_selection_horizontal`)."""
        if self.canvas.mirror_selection_horizontal():
            self._mark_unsaved()
            self.canvas.update()
            self.minimap_panel.refresh()
            self.tile_preview_panel.refresh()
            self.status_bar.showMessage("Horizontal gespiegelt", 2000)
        else:
            self.status_bar.showMessage("Keine Auswahl zum Spiegeln", 2000)

    def _on_mirror_v(self: "MainWindow") -> None:
        """Vertikal spiegeln."""
        if self.canvas.mirror_selection_vertical():
            self._mark_unsaved()
            self.canvas.update()
            self.minimap_panel.refresh()
            self.tile_preview_panel.refresh()
            self.status_bar.showMessage("Vertikal gespiegelt", 2000)
        else:
            self.status_bar.showMessage("Keine Auswahl zum Spiegeln", 2000)
