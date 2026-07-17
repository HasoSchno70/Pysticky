"""
Actions-Mixin für MainWindow.

Enthält die Definition aller QActions.
"""

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QKeySequence

from ...core.i18n import t

if TYPE_CHECKING:
    from ..main_window import MainWindow


class ActionsBuilderMixin:
    """Mixin für Action-Erstellung."""

    def _create_actions(self: "MainWindow") -> None:
        """Erstellt alle Aktionen."""
        self._create_file_actions()
        self._create_edit_actions()
        self._create_view_actions()
        self._create_layer_actions()
        self._create_extras_actions()
        self._create_help_actions()

    def _create_file_actions(self: "MainWindow") -> None:
        """Datei-Aktionen (Handler in FileHandlersMixin)."""
        self.action_new = QAction(t("&Neu..."), self)
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.setToolTip(t("Neues Muster (Ctrl+N)"))
        self.action_new.triggered.connect(self._on_new)

        self.action_open = QAction(t("&Öffnen..."), self)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.setToolTip(t("Muster öffnen (Ctrl+O)"))
        self.action_open.triggered.connect(self._on_open)

        self.action_save = QAction(t("&Speichern"), self)
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save.setToolTip(t("Muster speichern (Ctrl+S)"))
        self.action_save.triggered.connect(self._on_save)

        self.action_save_as = QAction(t("Speichern &unter..."), self)
        self.action_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.action_save_as.setToolTip(t("Speichern unter (Ctrl+Shift+S)"))
        self.action_save_as.triggered.connect(self._on_save_as)

        self.action_import_image = QAction(t("Bild importieren..."), self)
        self.action_import_image.setShortcut("Ctrl+I")
        self.action_import_image.setToolTip(t("Bild importieren (Ctrl+I)"))
        self.action_import_image.triggered.connect(self._on_import_image)

        self.action_reimport_image = QAction(t("Bildimport wiederholen..."), self)
        self.action_reimport_image.setToolTip(
            t("Bildimport des aktuellen Musters mit angepassten Einstellungen wiederholen")
        )
        self.action_reimport_image.triggered.connect(self._on_reimport_image)

        self.action_import_xsd_pat = QAction(t("Muster importieren (XSD/PAT/OXS)..."), self)
        self.action_import_xsd_pat.setShortcut("Ctrl+Alt+I")
        self.action_import_xsd_pat.setToolTip(t("Muster importieren (XSD/PAT/OXS)..."))
        self.action_import_xsd_pat.triggered.connect(self._on_import_xsd_pat)

        self.action_pattern_library = QAction(t("Muster-&Bibliothek..."), self)
        self.action_pattern_library.setShortcut("Ctrl+L")
        self.action_pattern_library.setToolTip(t("Muster-Bibliothek (Ctrl+L)"))
        self.action_pattern_library.triggered.connect(self._on_pattern_library)

        self.action_export_html = QAction(t("Als &HTML exportieren..."), self)
        self.action_export_html.setShortcut("Ctrl+E")
        self.action_export_html.setToolTip(t("HTML exportieren (Ctrl+E)"))
        self.action_export_html.triggered.connect(self._on_export_html)

        self.action_export_pdf = QAction(t("Als &PDF exportieren..."), self)
        self.action_export_pdf.setShortcut("Ctrl+Shift+E")
        self.action_export_pdf.setToolTip(t("PDF exportieren (Ctrl+Shift+E)"))
        self.action_export_pdf.triggered.connect(self._on_export_pdf)

        self.action_export_image = QAction(t("Als &Bild exportieren..."), self)
        self.action_export_image.setShortcut("Ctrl+Alt+E")
        self.action_export_image.setToolTip(t("Als Bild exportieren (Ctrl+Alt+E)"))
        self.action_export_image.triggered.connect(self._on_export_image)

        self.action_export_oxs = QAction(t("Als &OXS exportieren..."), self)
        self.action_export_oxs.setToolTip(
            t(
                "Open Cross Stitch (XML) — offener Austauschstandard, "
                "lesbar von Pattern Maker, MacStitch/WinStitch, Stitch Fiddle"
            )
        )
        self.action_export_oxs.triggered.connect(self._on_export_oxs)

        self.action_export_bundle = QAction(t("Als Bundle (ZIP) exportieren..."), self)
        self.action_export_bundle.setToolTip(
            t(
                "Komplettes Bundle (.pxs + HTML + PNG + PDF + Garnliste + Original) "
                "als ZIP — ideal zum Teilen oder als Backup"
            )
        )
        self.action_export_bundle.triggered.connect(self._on_export_bundle)

        self.action_open_demo = QAction(t("🎨 Demo-Muster öffnen"), self)
        self.action_open_demo.setToolTip(
            t(
                "Lädt ein Beispiel-Muster (Herz mit Rahmen, 3 Layer, 6 Farben) "
                "zum Ausprobieren der Features"
            )
        )
        self.action_open_demo.triggered.connect(self._on_open_demo)

        self.action_print = QAction(t("&Drucken..."), self)
        self.action_print.setShortcut(QKeySequence.StandardKey.Print)
        self.action_print.setToolTip(t("Drucken (Ctrl+P)"))
        self.action_print.triggered.connect(self._on_print)

        self.action_pattern_properties = QAction(t("&Eigenschaften..."), self)
        self.action_pattern_properties.setShortcut("Ctrl+Alt+P")
        self.action_pattern_properties.setToolTip(
            t("Autor, Copyright, Stickdatum und Notizen bearbeiten (Ctrl+Alt+P)")
        )
        self.action_pattern_properties.triggered.connect(self._on_pattern_properties)

        self.action_pattern_versions = QAction(t("&Versionen..."), self)
        self.action_pattern_versions.setShortcut("Ctrl+Alt+V")
        self.action_pattern_versions.setToolTip(
            t("Versionierte Snapshots des Musters anzeigen und wiederherstellen (Ctrl+Alt+V)")
        )
        self.action_pattern_versions.triggered.connect(self._on_pattern_versions)

        self.action_save_as_template = QAction(t("Als &Template speichern..."), self)
        self.action_save_as_template.triggered.connect(self._on_save_as_template)

        self.action_manage_templates = QAction(t("Templates &verwalten..."), self)
        self.action_manage_templates.triggered.connect(self._on_manage_templates)

        self.action_autosave_settings = QAction(t("&Autosave-Einstellungen..."), self)
        self.action_autosave_settings.triggered.connect(self._on_autosave_settings)

        self.action_exit = QAction(t("&Beenden"), self)
        self.action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_exit.setToolTip(t("Beenden (Ctrl+Q)"))
        self.action_exit.triggered.connect(self.close)

    def _create_edit_actions(self: "MainWindow") -> None:
        """Bearbeiten-Aktionen (Handler in EditHandlersMixin)."""
        self.action_undo = QAction(t("&Rückgängig"), self)
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_undo.setToolTip(t("Rückgängig (Ctrl+Z)"))
        self.action_undo.triggered.connect(self._on_undo)
        self.action_undo.setEnabled(False)

        self.action_redo = QAction(t("&Wiederholen"), self)
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.action_redo.setToolTip(t("Wiederholen (Ctrl+Y)"))
        self.action_redo.triggered.connect(self._on_redo)
        self.action_redo.setEnabled(False)

        self.action_resize = QAction(t("Größe ändern..."), self)
        self.action_resize.triggered.connect(self._on_resize_pattern)

        self.action_replace_color = QAction(t("Farbe &ersetzen..."), self)
        self.action_replace_color.setShortcut("Ctrl+R")
        self.action_replace_color.setToolTip(t("Farbe ersetzen (Ctrl+R)"))
        self.action_replace_color.triggered.connect(self._on_replace_color)

        self.action_swap_colors = QAction(t("Farben &tauschen..."), self)
        self.action_swap_colors.setShortcut("Ctrl+Shift+T")
        self.action_swap_colors.setToolTip(t("Zwei Farben gegenseitig tauschen (Ctrl+Shift+T)"))
        self.action_swap_colors.triggered.connect(self._on_swap_colors)

        self.action_manage_colors = QAction(t("Farbpalette &verwalten..."), self)
        self.action_manage_colors.setShortcut("Ctrl+Shift+P")
        self.action_manage_colors.setToolTip(t("Farbpalette verwalten (Ctrl+Shift+P)"))
        self.action_manage_colors.triggered.connect(self._on_manage_colors)

        self.action_color_harmony = QAction(t("Farb-&Harmonien..."), self)
        self.action_color_harmony.setShortcut("Ctrl+Shift+H")
        self.action_color_harmony.setToolTip(t("Farb-Harmonien (Ctrl+Shift+H)"))
        self.action_color_harmony.triggered.connect(self._on_color_harmony_current)

        self.action_screen_eyedropper = QAction(t("Farbe vom &Bildschirm picken..."), self)
        self.action_screen_eyedropper.setToolTip(
            t(
                "Erfasst den Bildschirm und lässt dich eine Farbe von überall "
                "(Browser, Foto-Viewer, anderer Editor) picken. Die nahe gelegene "
                "Garn-Entsprechung wird automatisch zur Pattern-Palette hinzugefuegt."
            )
        )
        self.action_screen_eyedropper.triggered.connect(self._on_screen_eyedropper)

        self.action_plugins = QAction(t("&Plugins..."), self)
        self.action_plugins.setToolTip(
            t(
                "Plugins durchsuchen und ausführen — eigene Python-Skripte, "
                "die das Pattern manipulieren (Rahmen, Schachbrett, Symmetrie, ...)."
            )
        )
        self.action_plugins.triggered.connect(self._on_show_plugins)

        self.action_blend_threads = QAction(t("&Tweed-Blend erzeugen..."), self)
        self.action_blend_threads.setToolTip(
            t(
                "Zwei Garne kombinieren (z.B. 1 Strang DMC 310 + 1 Strang DMC 745) "
                "für Salt&Pepper-/Tweed-Effekte. Perzeptueller Mix in CIE-Lab."
            )
        )
        self.action_blend_threads.triggered.connect(self._on_blend_threads)

        self.action_auto_crop = QAction(t("Auto-&Zuschneiden"), self)
        self.action_auto_crop.setShortcut("Ctrl+Shift+C")
        self.action_auto_crop.setToolTip(t("Auto-Zuschneiden (Ctrl+Shift+C)"))
        self.action_auto_crop.triggered.connect(self._on_auto_crop)

        self.action_merge_similar = QAction(t("Ähnliche Farben &zusammenführen..."), self)
        self.action_merge_similar.setShortcut("Ctrl+Shift+M")
        self.action_merge_similar.setToolTip(t("Ähnliche Farben zusammenführen (Ctrl+Shift+M)"))
        self.action_merge_similar.triggered.connect(self._on_merge_similar_colors)

        # Palette-Aktionen
        self.action_convert_palette = QAction(t("Palette &konvertieren..."), self)
        self.action_convert_palette.setShortcut("Ctrl+Shift+K")
        self.action_convert_palette.setToolTip(t("Palette konvertieren (Ctrl+Shift+K)"))
        self.action_convert_palette.triggered.connect(self._on_convert_palette)

        self.action_export_palette = QAction(t("Palette &exportieren..."), self)
        self.action_export_palette.triggered.connect(self._on_export_palette)

        self.action_import_palette = QAction(t("Palette &importieren..."), self)
        self.action_import_palette.triggered.connect(self._on_import_palette)

        self.action_statistics = QAction(t("&Statistiken && Garnverbrauch..."), self)
        # War "Ctrl+Shift+S" -- kollidierte mit action_save_as, dessen
        # QKeySequence.StandardKey.SaveAs sich auf dieser Plattform auf
        # genau dieselbe Kombination auflöst (im Quellcode nicht sichtbar,
        # da dort nur die StandardKey-Konstante steht -- gefunden per
        # Laufzeit-Check der Tastenkürzel-Registry, nicht per Text-Suche).
        self.action_statistics.setShortcut("Ctrl+Shift+G")
        self.action_statistics.setToolTip(t("Statistiken & Garnverbrauch (Ctrl+Shift+G)"))
        self.action_statistics.triggered.connect(self._on_show_statistics)

        self.action_inventory = QAction(t("&Garn-Vorrat..."), self)
        self.action_inventory.setShortcut("Ctrl+Shift+I")
        self.action_inventory.setToolTip(
            t("Eigenen Garn-Vorrat pflegen — Einkaufsliste im Statistik-Dialog (Ctrl+Shift+I)")
        )
        self.action_inventory.triggered.connect(self._on_show_inventory)

        self.action_stitch_mode = QAction(t("✓ &Sticken-Modus"), self)
        self.action_stitch_mode.setCheckable(True)
        self.action_stitch_mode.setShortcut("Ctrl+M")
        self.action_stitch_mode.setToolTip(
            t("Sticken-Modus an/aus — klick auf Zellen markiert/entfernt den Fortschritt (Ctrl+M)")
        )
        self.action_stitch_mode.toggled.connect(self._on_toggle_stitch_mode)

        self.action_isolate_color = QAction(t("🔍 Aktive Farbe &hervorheben"), self)
        self.action_isolate_color.setShortcut("Ctrl+H")
        self.action_isolate_color.setToolTip(
            t(
                "Nur die aktuelle Farbe hervorheben — andere Farben werden "
                "stark gedimmt (Ctrl+H zum Aufheben)"
            )
        )
        self.action_isolate_color.triggered.connect(self._on_toggle_isolate_current_color)

        self.action_hoop_planner = QAction(t("&Rahmenaufteilung..."), self)
        self.action_hoop_planner.setToolTip(t("Großes Muster auf mehrere Stickrahmen aufteilen"))
        self.action_hoop_planner.triggered.connect(self._on_show_hoop_planner)

        self.action_heatmap = QAction(t("&Heatmap..."), self)
        self.action_heatmap.setToolTip(t("Pattern-Heatmap anzeigen (Stichdichte/Farbenvielfalt)"))
        self.action_heatmap.triggered.connect(self._on_show_heatmap)

        self.action_stitch_path = QAction(t("Stick&pfad-Optimierung..."), self)
        self.action_stitch_path.setShortcut("Ctrl+Shift+O")
        self.action_stitch_path.setToolTip(t("Stickpfad-Optimierung (Ctrl+Shift+O)"))
        self.action_stitch_path.triggered.connect(self._on_stitch_path_optimizer)

        # Transformieren (auf gesamtem Muster)
        self.action_rotate_cw = QAction(t("90° &rechts drehen"), self)
        self.action_rotate_cw.triggered.connect(self._on_rotate_cw)

        self.action_rotate_ccw = QAction(t("90° &links drehen"), self)
        self.action_rotate_ccw.triggered.connect(self._on_rotate_ccw)

        self.action_rotate_180 = QAction(t("&180° drehen"), self)
        self.action_rotate_180.triggered.connect(self._on_rotate_180)

        self.action_flip_h = QAction(t("&Horizontal spiegeln"), self)
        self.action_flip_h.triggered.connect(self._on_flip_horizontal)

        self.action_flip_v = QAction(t("&Vertikal spiegeln"), self)
        self.action_flip_v.triggered.connect(self._on_flip_vertical)

        # Auswahl-Operationen (Handler in SelectionHandlersMixin).
        # Die Handler prüfen selbst, ob eine Auswahl existiert — fehlt sie,
        # ist die Aktion ein No-Op. Shortcuts sind als QAction registriert,
        # damit sie unabhängig vom aktiven Tool und Canvas-Fokus funktionieren.
        self.action_selection_copy = QAction(t("&Kopieren"), self)
        self.action_selection_copy.setShortcut(QKeySequence.StandardKey.Copy)
        self.action_selection_copy.setToolTip(t("Auswahl kopieren (Ctrl+C)"))
        self.action_selection_copy.triggered.connect(self._on_selection_copy)

        self.action_selection_cut = QAction(t("&Ausschneiden"), self)
        self.action_selection_cut.setShortcut(QKeySequence.StandardKey.Cut)
        self.action_selection_cut.setToolTip(t("Auswahl ausschneiden (Ctrl+X)"))
        self.action_selection_cut.triggered.connect(self._on_selection_cut)

        self.action_selection_paste = QAction(t("&Einfügen"), self)
        self.action_selection_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self.action_selection_paste.setToolTip(t("Aus Zwischenablage einfügen (Ctrl+V)"))
        self.action_selection_paste.triggered.connect(self._on_selection_paste)

        self.action_selection_delete = QAction(t("Auswahl &löschen"), self)
        self.action_selection_delete.setShortcut(QKeySequence.StandardKey.Delete)
        self.action_selection_delete.setToolTip(t("Stiche in Auswahl löschen (Entf)"))
        self.action_selection_delete.triggered.connect(self._on_selection_delete)

        self.action_selection_fill = QAction(t("Auswahl &füllen"), self)
        self.action_selection_fill.setToolTip(t("Auswahl mit aktueller Farbe füllen"))
        self.action_selection_fill.triggered.connect(self._on_selection_fill)

        self.action_selection_rotate_cw = QAction(t("Auswahl 90° rechts &drehen"), self)
        self.action_selection_rotate_cw.triggered.connect(self._on_selection_rotate_cw)

        self.action_selection_rotate_ccw = QAction(t("Auswahl 90° links drehen"), self)
        self.action_selection_rotate_ccw.triggered.connect(self._on_selection_rotate_ccw)

        self.action_selection_flip_h = QAction(t("Auswahl horizontal spiegeln"), self)
        self.action_selection_flip_h.triggered.connect(self._on_selection_flip_h)

        self.action_selection_flip_v = QAction(t("Auswahl vertikal spiegeln"), self)
        self.action_selection_flip_v.triggered.connect(self._on_selection_flip_v)

    def _create_view_actions(self: "MainWindow") -> None:
        """Ansicht-Aktionen (Handler in ViewHandlersMixin)."""
        self.action_zoom_in = QAction(t("Ver&größern"), self)
        self.action_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.action_zoom_in.setToolTip(t("Vergrößern (Ctrl++)"))
        self.action_zoom_in.triggered.connect(self._on_zoom_in)

        self.action_zoom_out = QAction(t("Ver&kleinern"), self)
        self.action_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.action_zoom_out.setToolTip(t("Verkleinern (Ctrl+-)"))
        self.action_zoom_out.triggered.connect(self._on_zoom_out)

        self.action_zoom_fit = QAction(t("&Einpassen"), self)
        self.action_zoom_fit.setShortcut("Ctrl+0")
        self.action_zoom_fit.setToolTip(t("Einpassen (Ctrl+0)"))
        self.action_zoom_fit.triggered.connect(self._on_zoom_fit)

        self.action_zoom_100 = QAction(t("&100%"), self)
        self.action_zoom_100.setShortcut("Ctrl+1")
        self.action_zoom_100.setToolTip(t("100% (Ctrl+1)"))
        self.action_zoom_100.triggered.connect(self._on_zoom_100)

        self.action_show_grid = QAction(t("&Gitter anzeigen"), self)
        self.action_show_grid.setCheckable(True)
        self.action_show_grid.setChecked(True)
        self.action_show_grid.triggered.connect(self._on_toggle_grid)

        self.action_show_symbols = QAction(t("&Symbole anzeigen"), self)
        self.action_show_symbols.setCheckable(True)
        self.action_show_symbols.setChecked(False)
        self.action_show_symbols.triggered.connect(self._on_toggle_symbols)

        self.action_show_backstitches = QAction(t("&Rückstiche anzeigen"), self)
        self.action_show_backstitches.setCheckable(True)
        self.action_show_backstitches.setChecked(False)
        self.action_show_backstitches.triggered.connect(self._on_toggle_backstitches)

        self.action_show_only_active = QAction(t("Nur &aktive Ebene"), self)
        self.action_show_only_active.setCheckable(True)
        self.action_show_only_active.setChecked(False)
        self.action_show_only_active.triggered.connect(self._on_toggle_only_active)

        self.action_dim_layers = QAction(t("Andere Ebenen &abdunkeln"), self)
        self.action_dim_layers.setCheckable(True)
        self.action_dim_layers.setChecked(False)
        self.action_dim_layers.triggered.connect(self._on_toggle_dim_layers)

        self.action_show_completion = QAction(t("&Fortschritt anzeigen"), self)
        self.action_show_completion.setCheckable(True)
        self.action_show_completion.setChecked(True)
        self.action_show_completion.triggered.connect(self._on_toggle_completion)

        self.action_diamond_view = QAction(t("&Diamond-Painting-Ansicht"), self)
        self.action_diamond_view.setCheckable(True)
        self.action_diamond_view.setChecked(False)
        self.action_diamond_view.setShortcut("Ctrl+D")
        self.action_diamond_view.setToolTip(
            t(
                "Rendert volle Stiche als facettierte Drills und zeigt "
                "DMC-Nummern statt Symbolen (Ctrl+D)"
            )
        )
        self.action_diamond_view.triggered.connect(self._on_toggle_diamond_view)

        self.action_grid_options = QAction(t("Raster-&Optionen..."), self)
        self.action_grid_options.triggered.connect(self._on_grid_options)

        self.action_pattern_preview = QAction(t("Muster-&Vorschau..."), self)
        self.action_pattern_preview.setShortcut("F5")
        self.action_pattern_preview.setToolTip(t("Muster-Vorschau (F5)"))
        self.action_pattern_preview.triggered.connect(self._on_pattern_preview)

        self.action_save_workspace = QAction(t("Arbeitsbereich &speichern..."), self)
        self.action_save_workspace.triggered.connect(self._on_save_workspace)

        self.action_load_workspace = QAction(t("Arbeitsbereich &laden..."), self)
        self.action_load_workspace.triggered.connect(self._on_load_workspace)

        self.action_reset_workspace = QAction(t("Layout &zurücksetzen"), self)
        self.action_reset_workspace.triggered.connect(self._on_reset_workspace)

    def _create_layer_actions(self: "MainWindow") -> None:
        """Ebenen-Aktionen."""
        self.action_new_layer = QAction(t("Neue &Ebene"), self)
        self.action_new_layer.setShortcut("Ctrl+Shift+N")
        self.action_new_layer.setToolTip(t("Neue Ebene (Ctrl+Shift+N)"))
        self.action_new_layer.triggered.connect(self._on_new_layer)

        self.action_flatten = QAction(t("Alle Ebenen &vereinen"), self)
        self.action_flatten.triggered.connect(self._on_flatten_layers)

    def _create_extras_actions(self: "MainWindow") -> None:
        """Extras-Aktionen."""
        self.action_settings = QAction(t("&Einstellungen..."), self)
        self.action_settings.setShortcut("Ctrl+,")
        self.action_settings.setToolTip(t("Einstellungen (Ctrl+,)"))
        self.action_settings.triggered.connect(self._on_settings)

    def _create_help_actions(self: "MainWindow") -> None:
        """Hilfe-Aktionen."""
        self.action_shortcuts = QAction(t("&Tastenkürzel..."), self)
        self.action_shortcuts.setShortcut("F1")
        self.action_shortcuts.setToolTip(t("Tastenkürzel (F1)"))
        self.action_shortcuts.triggered.connect(self._on_show_shortcuts)

        self.action_whats_new = QAction(t("🆕 &Neu in dieser Version..."), self)
        self.action_whats_new.setToolTip(
            t("Übersicht der Features und Änderungen in der aktuellen Version")
        )
        self.action_whats_new.triggered.connect(self._on_whats_new)

        self.action_about = QAction(t("Ü&ber PySticky"), self)
        self.action_about.triggered.connect(self._on_about)
