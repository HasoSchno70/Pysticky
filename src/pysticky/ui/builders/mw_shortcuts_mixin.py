"""
Tastenkürzel-Registry-Mixin für MainWindow.

Registriert alle anpassbaren QAction-/Werkzeug-Tastenkürzel in einer
`ShortcutRegistry` (siehe `ui/shortcuts_registry.py`), damit der
Tastenkürzel-Settings-Tab sie anzeigen und überschreiben kann. Der
Default-Wert wird dabei direkt vom jeweiligen QAction/ToolButton
abgelesen — diese Liste hier bestimmt nur, WELCHE Aktionen anpassbar
sind und WIE sie im Tab heißen, nicht deren Tastenkombination selbst.
"""

from typing import TYPE_CHECKING

from ...core.i18n import t
from ..shortcuts_registry import ShortcutRegistry
from ..tools.tool_enum import Tool

if TYPE_CHECKING:
    from ..main_window import MainWindow


class ShortcutsRegistryMixin:
    """Mixin zur Registrierung anpassbarer Tastenkürzel."""

    def _register_shortcut_targets(self: "MainWindow") -> None:
        """Baut die Tastenkürzel-Registry auf. Muss NACH _create_actions(),
        _create_menus() und _create_central_widget() (Toolbar) laufen."""
        self._shortcut_registry = ShortcutRegistry()
        reg = self._shortcut_registry

        action_entries = [
            ("action_new", t("Neu")),
            ("action_open", t("Öffnen")),
            ("action_save", t("Speichern")),
            ("action_save_as", t("Speichern unter")),
            ("action_import_image", t("Bild importieren")),
            ("action_import_xsd_pat", t("Muster importieren")),
            ("action_pattern_library", t("Muster-Bibliothek")),
            ("action_export_html", t("Als HTML exportieren")),
            ("action_export_pdf", t("Als PDF exportieren")),
            ("action_export_image", t("Als Bild exportieren")),
            ("action_print", t("Drucken")),
            ("action_pattern_properties", t("Eigenschaften")),
            ("action_pattern_versions", t("Versionen")),
            ("action_exit", t("Beenden")),
            ("action_undo", t("Rückgängig")),
            ("action_redo", t("Wiederholen")),
            ("action_replace_color", t("Farbe ersetzen")),
            ("action_swap_colors", t("Farben tauschen")),
            ("action_manage_colors", t("Farbpalette verwalten")),
            ("action_color_harmony", t("Farb-Harmonien")),
            ("action_auto_crop", t("Auto-Zuschneiden")),
            ("action_merge_similar", t("Ähnliche Farben zusammenführen")),
            ("action_convert_palette", t("Palette konvertieren")),
            ("action_statistics", t("Statistiken & Garnverbrauch")),
            ("action_inventory", t("Garn-Vorrat")),
            ("action_stitch_mode", t("Sticken-Modus")),
            ("action_isolate_color", t("Aktive Farbe hervorheben")),
            ("action_stitch_path", t("Stickpfad-Optimierung")),
            ("action_selection_copy", t("Kopieren")),
            ("action_selection_cut", t("Ausschneiden")),
            ("action_selection_paste", t("Einfügen")),
            ("action_selection_delete", t("Löschen")),
            ("action_zoom_in", t("Vergrößern")),
            ("action_zoom_out", t("Verkleinern")),
            ("action_zoom_fit", t("Einpassen")),
            ("action_zoom_100", t("100%")),
            ("action_diamond_view", t("Diamond-Ansicht")),
            ("action_pattern_preview", t("Vorlagen-Vorschau")),
            ("action_new_layer", t("Neue Ebene")),
            ("action_settings", t("Einstellungen")),
            ("action_shortcuts", t("Hilfe: Tastenkürzel")),
        ]
        for attr_name, label in action_entries:
            action = getattr(self, attr_name, None)
            if action is not None:
                reg.register(attr_name, action, label)

        tool_entries = [
            (Tool.PENCIL, "tool_pencil", t("Stift")),
            (Tool.ERASER, "tool_eraser", t("Radierer")),
            (Tool.FILL, "tool_fill", t("Füllen")),
            (Tool.PIPETTE, "tool_pipette", t("Pipette")),
            (Tool.LINE, "tool_line", t("Linie")),
            (Tool.RECT, "tool_rect", t("Rechteck")),
            (Tool.ELLIPSE, "tool_ellipse", t("Ellipse")),
            (Tool.POLYGON, "tool_polygon", t("Polygon")),
            (Tool.TEXT, "tool_text", t("Text")),
            (Tool.BACKSTITCH, "tool_backstitch", t("Rückstich")),
            (Tool.GRADIENT, "tool_gradient", t("Verlauf")),
            (Tool.PROGRESS, "tool_progress", t("Fortschritt")),
            (Tool.SELECT, "tool_select", t("Auswahl")),
            (Tool.MOVE, "tool_move", t("Bewegen")),
        ]
        tool_bar = getattr(self, "tool_bar", None)
        if tool_bar is not None:
            for tool, shortcut_id, label in tool_entries:
                btn = tool_bar.get_button(tool)
                if btn is not None:
                    reg.register(shortcut_id, btn, label)
