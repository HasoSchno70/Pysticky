"""
Menü-Builder-Mixin für MainWindow.

Enthält die Erstellung der Menüleiste.
"""

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QActionGroup

from ...core.i18n import t

if TYPE_CHECKING:
    from ..main_window import MainWindow


class MenuBuilderMixin:
    """Mixin für Menü-Erstellung."""

    def _create_menus(self: "MainWindow") -> None:
        """Erstellt die Menüleiste."""
        menubar = self.menuBar()

        self._create_file_menu(menubar)
        self._create_edit_menu(menubar)
        self._create_view_menu(menubar)
        self._create_layer_menu(menubar)
        self._create_extras_menu(menubar)
        self._create_help_menu(menubar)

    def _create_file_menu(self: "MainWindow", menubar) -> None:
        """Erstellt das Datei-Menü."""
        file_menu = menubar.addMenu(t("&Datei"))
        file_menu.addAction(self.action_new)
        file_menu.addAction(self.action_open)

        self.recent_menu = file_menu.addMenu(t("Zuletzt geöffnet"))
        self._update_recent_menu()

        file_menu.addSeparator()
        file_menu.addAction(self.action_save)
        file_menu.addAction(self.action_save_as)

        file_menu.addSeparator()
        file_menu.addAction(self.action_import_image)
        file_menu.addAction(self.action_reimport_image)
        file_menu.addAction(self.action_import_xsd_pat)
        file_menu.addAction(self.action_open_demo)

        file_menu.addSeparator()
        file_menu.addAction(self.action_pattern_library)

        file_menu.addSeparator()
        file_menu.addAction(self.action_export_html)
        file_menu.addAction(self.action_export_pdf)
        file_menu.addAction(self.action_export_image)
        file_menu.addAction(self.action_export_oxs)
        file_menu.addAction(self.action_export_bundle)

        file_menu.addSeparator()
        file_menu.addAction(self.action_print)

        file_menu.addSeparator()
        file_menu.addAction(self.action_pattern_properties)
        file_menu.addAction(self.action_pattern_versions)

        file_menu.addSeparator()
        file_menu.addAction(self.action_save_as_template)
        file_menu.addAction(self.action_manage_templates)

        file_menu.addSeparator()
        file_menu.addAction(self.action_autosave_settings)

        file_menu.addSeparator()
        file_menu.addAction(self.action_exit)

    def _create_edit_menu(self: "MainWindow", menubar) -> None:
        """Erstellt das Bearbeiten-Menü."""
        edit_menu = menubar.addMenu(t("&Bearbeiten"))
        edit_menu.addAction(self.action_undo)
        edit_menu.addAction(self.action_redo)

        edit_menu.addSeparator()
        # Stichtyp — direkt sichtbar, weil es das Zeichnen direkt beeinflusst
        self._stitch_type_menu = edit_menu.addMenu(t("&Stichtyp"))
        self._create_stitch_type_actions(self._stitch_type_menu)

        edit_menu.addSeparator()
        edit_menu.addAction(self.action_selection_cut)
        edit_menu.addAction(self.action_selection_copy)
        edit_menu.addAction(self.action_selection_paste)
        edit_menu.addAction(self.action_selection_delete)

        selection_menu = edit_menu.addMenu(t("Aus&wahl"))
        selection_menu.addAction(self.action_selection_fill)
        selection_menu.addSeparator()
        selection_menu.addAction(self.action_selection_rotate_cw)
        selection_menu.addAction(self.action_selection_rotate_ccw)
        selection_menu.addSeparator()
        selection_menu.addAction(self.action_selection_flip_h)
        selection_menu.addAction(self.action_selection_flip_v)

        edit_menu.addSeparator()
        edit_menu.addAction(self.action_resize)
        edit_menu.addAction(self.action_replace_color)
        edit_menu.addAction(self.action_swap_colors)
        edit_menu.addAction(self.action_manage_colors)
        edit_menu.addAction(self.action_color_harmony)
        edit_menu.addAction(self.action_merge_similar)
        edit_menu.addAction(self.action_auto_crop)

        edit_menu.addSeparator()
        palette_menu = edit_menu.addMenu(t("&Palette"))
        palette_menu.addAction(self.action_convert_palette)
        palette_menu.addAction(self.action_blend_threads)
        palette_menu.addSeparator()
        palette_menu.addAction(self.action_export_palette)
        palette_menu.addAction(self.action_import_palette)

        edit_menu.addSeparator()
        edit_menu.addAction(self.action_statistics)
        edit_menu.addAction(self.action_inventory)
        edit_menu.addAction(self.action_hoop_planner)
        edit_menu.addAction(self.action_heatmap)
        edit_menu.addAction(self.action_stitch_path)

        edit_menu.addSeparator()
        transform_menu = edit_menu.addMenu(t("&Transformieren"))
        transform_menu.addAction(self.action_rotate_cw)
        transform_menu.addAction(self.action_rotate_ccw)
        transform_menu.addAction(self.action_rotate_180)
        transform_menu.addSeparator()
        transform_menu.addAction(self.action_flip_h)
        transform_menu.addAction(self.action_flip_v)

    def _create_view_menu(self: "MainWindow", menubar) -> None:
        """Erstellt das Ansicht-Menü."""
        view_menu = menubar.addMenu(t("&Ansicht"))
        view_menu.addAction(self.action_stitch_mode)
        view_menu.addAction(self.action_isolate_color)
        view_menu.addSeparator()
        view_menu.addAction(self.action_zoom_in)
        view_menu.addAction(self.action_zoom_out)

        view_menu.addSeparator()
        view_menu.addAction(self.action_zoom_fit)
        view_menu.addAction(self.action_zoom_100)

        view_menu.addSeparator()
        view_menu.addAction(self.action_show_grid)
        view_menu.addAction(self.action_show_symbols)
        view_menu.addAction(self.action_show_backstitches)
        view_menu.addAction(self.action_show_completion)
        view_menu.addAction(self.action_diamond_view)

        view_menu.addSeparator()
        view_menu.addAction(self.action_show_only_active)
        view_menu.addAction(self.action_dim_layers)

        view_menu.addSeparator()
        view_menu.addAction(self.action_grid_options)

        view_menu.addSeparator()
        view_menu.addAction(self.action_pattern_preview)

        view_menu.addSeparator()
        self._colorblind_menu = view_menu.addMenu(t("&Farbblindheit"))
        self._create_colorblind_actions(self._colorblind_menu)

        view_menu.addSeparator()
        workspace_menu = view_menu.addMenu(t("&Arbeitsbereiche"))
        workspace_menu.addAction(self.action_save_workspace)
        workspace_menu.addAction(self.action_load_workspace)
        workspace_menu.addSeparator()
        workspace_menu.addAction(self.action_reset_workspace)

    def _create_layer_menu(self: "MainWindow", menubar) -> None:
        """Erstellt das Ebenen-Menü."""
        layer_menu = menubar.addMenu(t("Ebenen"))
        layer_menu.addAction(self.action_new_layer)
        layer_menu.addSeparator()
        layer_menu.addAction(self.action_flatten)

    def _create_extras_menu(self: "MainWindow", menubar) -> None:
        """Erstellt das Extras-Menü."""
        extras_menu = menubar.addMenu(t("&Werkzeuge"))
        extras_menu.addAction(self.action_plugins)
        extras_menu.addAction(self.action_screen_eyedropper)
        extras_menu.addSeparator()
        extras_menu.addAction(self.action_settings)

    # Stichtyp-Konfiguration. Reihenfolge bestimmt Menü + Status-Label.
    # (stitch_type_id, Glyphe für Status, Menü-Label, Alt-Nummer)
    STITCH_TYPE_ENTRIES = (
        (0, "✕", "Voller Kreuzstich (X)", "1"),
        (1, "◤", "Halber Stich / (oben-links)", "2"),
        (2, "◥", "Halber Stich \\ (oben-rechts)", "3"),
        (3, "◰", "Viertelstich oben-links", "4"),
        (4, "◳", "Viertelstich oben-rechts", "5"),
        (5, "◱", "Viertelstich unten-links", "6"),
        (6, "◲", "Viertelstich unten-rechts", "7"),
        (7, "◧", "Dreiviertelstich", "8"),
        (9, "●", "Französischer Knoten", "9"),
        (10, "⬤", "Perle (Bead)", "0"),
    )

    def _create_stitch_type_actions(self: "MainWindow", menu) -> None:
        """Erstellt die Stichtyp-Auswahl-Aktionen + speichert sie unter `self.actions_stitch_type`."""
        group = QActionGroup(self)
        group.setExclusive(True)
        self.actions_stitch_type: dict[int, QAction] = {}

        for stype, _glyph, label, shortcut in self.STITCH_TYPE_ENTRIES:
            action = QAction(t(label), self)
            action.setCheckable(True)
            action.setChecked(stype == 0)
            if shortcut:
                action.setShortcut(f"Alt+{shortcut}")
            action.triggered.connect(lambda checked, t=stype: self._on_stitch_type_changed(t))
            group.addAction(action)
            menu.addAction(action)
            self.actions_stitch_type[stype] = action

    def _on_stitch_type_changed(self: "MainWindow", stype: int) -> None:
        """Wechselt den aktiven Stichtyp + synchronisiert Statusleiste."""
        self.canvas._active_stitch_type = stype

        # Status-Label aktualisieren
        glyph, label = "✕", "Voll"
        for entry_stype, entry_glyph, entry_label, _shortcut in self.STITCH_TYPE_ENTRIES:
            if entry_stype == stype:
                glyph = entry_glyph
                # Label kompakter: nur den interessanten Teil
                label = (
                    entry_label.split("(")[0].strip().replace("Kreuzstich", "").strip()
                    or entry_label
                )
                break

        if hasattr(self, "label_stitch_type"):
            self.label_stitch_type.setText(f"{glyph} {label}")

        # Menü-Action checked-State synchronisieren
        if hasattr(self, "actions_stitch_type"):
            action = self.actions_stitch_type.get(stype)
            if action and not action.isChecked():
                action.setChecked(True)

        # Toolbar-Combobox synchronisieren (Signals blockieren, sonst Endlosschleife)
        if hasattr(self, "combo_stitch_type"):
            combo = self.combo_stitch_type
            target_index = combo.findData(stype)
            if target_index >= 0 and combo.currentIndex() != target_index:
                combo.blockSignals(True)
                combo.setCurrentIndex(target_index)
                combo.blockSignals(False)

        self.status_bar.showMessage(f"Stichtyp: {label}", 3000)

    def _create_colorblind_actions(self: "MainWindow", menu) -> None:
        """Erstellt die Farbblindheits-Simulations-Aktionen."""
        from ...core.color_blindness import ColorBlindType

        group = QActionGroup(self)
        group.setExclusive(True)

        labels = {
            ColorBlindType.NONE: "Keine Simulation",
            ColorBlindType.PROTANOPIA: "Protanopie (Rot-Blindheit)",
            ColorBlindType.DEUTERANOPIA: "Deuteranopie (Grün-Blindheit)",
            ColorBlindType.TRITANOPIA: "Tritanopie (Blau-Blindheit)",
        }

        for cb_type, label in labels.items():
            action = QAction(t(label), self)
            action.setCheckable(True)
            action.setChecked(cb_type == ColorBlindType.NONE)
            action.setData(cb_type)
            action.triggered.connect(lambda checked, cbt=cb_type: self._on_colorblind_changed(cbt))
            group.addAction(action)
            menu.addAction(action)

    def _on_colorblind_changed(self: "MainWindow", cb_type) -> None:
        """Wechselt den Farbblindheits-Modus."""
        self.canvas.colorblind_mode = cb_type
        name = cb_type.value if cb_type.value != "none" else "keine"
        self.status_bar.showMessage(f"Farbblindheits-Simulation: {name}", 3000)

    def _create_help_menu(self: "MainWindow", menubar) -> None:
        """Erstellt das Hilfe-Menü."""
        help_menu = menubar.addMenu(t("&Hilfe"))
        help_menu.addAction(self.action_shortcuts)
        help_menu.addAction(self.action_whats_new)
        help_menu.addSeparator()
        help_menu.addAction(self.action_about)
