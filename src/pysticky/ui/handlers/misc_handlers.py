"""
Verschiedene Handler für MainWindow.

Enthält: Layer-Verwaltung, Recent Files, Templates, Autosave,
Shortcuts-Dialog, About-Dialog, Einstellungen.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from ..main_window import MainWindow


class MiscHandlersMixin:
    """Mixin für verschiedene Handler (Layer, Recent Files, Templates, Settings, etc.)."""

    # =========================================================================
    # Layer Handler
    # =========================================================================

    def _on_new_layer(self: "MainWindow") -> None:
        """Neue Ebene erstellen."""
        self.layer_panel._on_add_layer()

    def _on_flatten_layers(self: "MainWindow") -> None:
        """Alle Ebenen vereinen."""
        reply = QMessageBox.question(
            self,
            "Vereinen",
            "Alle Ebenen vereinen?\nDies kann nicht rückgängig gemacht werden.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.current_pattern.flatten_layers()
            self.layer_panel.set_layer_stack(self.current_pattern.layer_stack)
            self.canvas.update()
            self._update_status()
            self.undo_manager.clear()
            self._update_undo_actions()
            self._mark_unsaved()

    # =========================================================================
    # Recent Files
    # =========================================================================

    def _load_recent_files(self: "MainWindow") -> list[str]:
        """Lädt die Liste der zuletzt geöffneten Dateien."""
        from ...config import FILE_CONFIG

        files = self._settings.value("recent_files", [], type=list)
        return [f for f in files if Path(f).exists()][: FILE_CONFIG.max_recent_files]

    def _save_recent_files(self: "MainWindow") -> None:
        """Speichert die Liste der zuletzt geöffneten Dateien."""
        self._settings.setValue("recent_files", self._recent_files)

    def _add_recent_file(self: "MainWindow", path: str) -> None:
        """Fügt eine Datei zur Liste hinzu."""
        from ...config import FILE_CONFIG

        path = str(Path(path).resolve())
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._recent_files.insert(0, path)
        self._recent_files = self._recent_files[: FILE_CONFIG.max_recent_files]
        self._save_recent_files()
        self._update_recent_menu()

    def _update_recent_menu(self: "MainWindow") -> None:
        """Aktualisiert das Menü 'Kürzlich geöffnet'."""
        from PySide6.QtGui import QAction

        self.recent_menu.clear()
        if not self._recent_files:
            action = QAction("(keine)", self)
            action.setEnabled(False)
            self.recent_menu.addAction(action)
            return
        for i, path in enumerate(self._recent_files):
            name = Path(path).name
            action = QAction(f"&{i + 1}. {name}", self)
            action.setToolTip(path)
            action.setData(path)
            action.triggered.connect(lambda checked, p=path: self._open_recent_file(p))
            self.recent_menu.addAction(action)
        self.recent_menu.addSeparator()
        clear_action = QAction("Liste &leeren", self)
        clear_action.triggered.connect(self._clear_recent_files)
        self.recent_menu.addAction(clear_action)

    def _open_recent_file(self: "MainWindow", path: str) -> None:
        """Öffnet eine kürzlich geöffnete Datei."""
        if not self._check_save_changes():
            return
        if not Path(path).exists():
            QMessageBox.warning(
                self, "Datei nicht gefunden", f"Die Datei existiert nicht mehr:\n{path}"
            )
            self._recent_files.remove(path)
            self._save_recent_files()
            self._update_recent_menu()
            return
        try:
            from ...core import load_pattern

            pattern = load_pattern(path)
            self.current_file = Path(path)
            self.set_pattern(pattern)
            self._mark_saved()
            self._add_recent_file(path)
            self.status_bar.showMessage(f"Geöffnet: {path}", 3000)
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, "Fehler", f"Datei konnte nicht geöffnet werden:\n{e}")

    def _clear_recent_files(self: "MainWindow") -> None:
        """Löscht die Liste der zuletzt geöffneten Dateien."""
        self._recent_files.clear()
        self._save_recent_files()
        self._update_recent_menu()

    # =========================================================================
    # Template-Verwaltung
    # =========================================================================

    def _on_save_as_template(self: "MainWindow") -> None:
        """Speichert das aktuelle Projekt als Template."""
        from ..dialogs import SaveTemplateDialog, load_user_templates, save_user_templates

        dialog = SaveTemplateDialog(
            width=self.current_pattern.width,
            height=self.current_pattern.height,
            fabric_count=self.current_pattern.fabric_count,
            parent=self,
        )

        if dialog.exec():
            template = dialog.template
            if template:
                templates = load_user_templates()
                templates.append(template)
                if save_user_templates(templates):
                    self.status_bar.showMessage(f"Template '{template.name}' gespeichert", 3000)
                else:
                    QMessageBox.warning(self, "Fehler", "Template konnte nicht gespeichert werden.")

    def _on_manage_templates(self: "MainWindow") -> None:
        """Öffnet den Template-Verwaltungsdialog."""
        from ..dialogs import ManageTemplatesDialog

        dialog = ManageTemplatesDialog(self)
        dialog.exec()

    # =========================================================================
    # Autosave Settings
    # =========================================================================

    def _on_autosave_settings(self: "MainWindow") -> None:
        """Öffnet Autosave-Einstellungen."""
        from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QSpinBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Autosave-Einstellungen")
        dialog.setMinimumWidth(300)
        layout = QFormLayout(dialog)

        chk_enabled = QCheckBox("Autosave aktivieren")
        chk_enabled.setChecked(self._autosave_enabled)
        layout.addRow(chk_enabled)

        spin_interval = QSpinBox()
        spin_interval.setRange(1, 60)
        spin_interval.setValue(self._autosave_interval)
        spin_interval.setSuffix(" Minuten")
        layout.addRow("Intervall:", spin_interval)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._autosave_enabled = chk_enabled.isChecked()
            self._autosave_interval = spin_interval.value()
            self._settings.setValue("autosave_enabled", self._autosave_enabled)
            self._settings.setValue("autosave_interval", self._autosave_interval)
            self._autosave_timer.stop()
            if self._autosave_enabled and self._autosave_interval > 0:
                self._autosave_timer.start(self._autosave_interval * 60 * 1000)
            self.status_bar.showMessage(
                f"Autosave: {'aktiviert' if self._autosave_enabled else 'deaktiviert'}", 3000
            )

    # =========================================================================
    # Shortcuts & About
    # =========================================================================

    def _on_show_shortcuts(self: "MainWindow") -> None:
        """Zeigt Tastenkürzel-Dialog."""
        from PySide6.QtWidgets import (
            QDialog,
            QDialogButtonBox,
            QHeaderView,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Tastenkürzel")
        dialog.setMinimumSize(500, 600)
        layout = QVBoxLayout(dialog)

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Aktion", "Tastenkürzel"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)

        shortcuts = [
            ("— Datei —", ""),
            ("Neu", "Ctrl+N"),
            ("Öffnen", "Ctrl+O"),
            ("Speichern", "Ctrl+S"),
            ("— Bearbeiten —", ""),
            ("Rückgängig", "Ctrl+Z"),
            ("Wiederholen", "Ctrl+Y"),
            ("— Ansicht —", ""),
            ("Vergrößern", "Ctrl++"),
            ("Verkleinern", "Ctrl+-"),
            ("Muster-Vorschau", "F5"),
            ("— Werkzeuge —", ""),
            ("Stift", "P"),
            ("Radierer", "E"),
            ("Füllen", "G"),
            ("Pipette", "I"),
            ("Linie", "L"),
            ("Rechteck", "R"),
            ("Ellipse", "O"),
            ("Text", "T"),
            ("Rückstich", "B"),
            ("Auswahl", "S"),
            ("Fortschritt", "K"),
            ("— Auswahl —", ""),
            ("Kopieren", "Ctrl+C"),
            ("Ausschneiden", "Ctrl+X"),
            ("Einfügen", "Ctrl+V"),
            ("Löschen", "Entf"),
        ]

        table.setRowCount(len(shortcuts))
        for row, (action, shortcut) in enumerate(shortcuts):
            item_action = QTableWidgetItem(action)
            item_shortcut = QTableWidgetItem(shortcut)
            if action.startswith("—"):
                font = item_action.font()
                font.setBold(True)
                item_action.setFont(font)
            table.setItem(row, 0, item_action)
            table.setItem(row, 1, item_shortcut)
        layout.addWidget(table)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def _on_whats_new(self: "MainWindow") -> None:
        """Zeigt die Neuigkeiten der aktuellen Version."""
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import (
            QDialog,
            QFrame,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QScrollArea,
            QVBoxLayout,
            QWidget,
        )

        from ...config import APP_VERSION
        from ..styles import THEME, Styles

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Neu in PySticky {APP_VERSION}")
        dialog.setMinimumSize(640, 580)
        dialog.setStyleSheet(f"""
            QDialog {{ background: {THEME.bg_dark}; }}
            QLabel {{ background: transparent; color: {THEME.text_primary}; }}
            QScrollArea {{ background: transparent; border: none; }}
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 24, 28, 18)
        layout.setSpacing(14)

        # Header
        title = QLabel(f"Neu in Version {APP_VERSION}")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {THEME.accent_primary}; padding-bottom: 4px;")
        layout.addWidget(title)

        sub = QLabel("Eine kompakte Übersicht der wichtigsten Änderungen")
        sub.setStyleSheet(f"color: {THEME.text_muted}; font-size: 12px; font-style: italic;")
        layout.addWidget(sub)

        # Inhalts-Bereich (scrollbar)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 8, 4, 8)
        content_layout.setSpacing(18)

        sections = [
            (
                "📝 Layer-Notizen",
                [
                    "Pro Ebene kannst du jetzt eine freie Notiz hinterlegen "
                    "(z.B. 'Vordergrund-Schatten', 'Backstitch-Linien'). "
                    "Wird im .pxs-Format gespeichert.",
                ],
            ),
            (
                "⏱ Stick-Session-Timer",
                [
                    "Beim Sticken-Modus läuft ein Timer im Hintergrund. Beim Beenden "
                    "siehst du die Sitzungs- und Gesamtzeit. Toggle in Einstellungen → "
                    "Allgemein → 'Sticken & Snapshots'.",
                ],
            ),
            (
                "⚙ Snapshot-Intervall einstellbar",
                [
                    "Versionierte Snapshots werden jetzt im konfigurierbaren Intervall "
                    "(5–240 min) angelegt. Default 30 min.",
                ],
            ),
            (
                "🔍 Farb-Hervorhebung",
                [
                    "Eine Farbe isolieren — andere werden im Canvas stark gedimmt. "
                    "Über Rechtsklick auf einen Farb-Swatch oder Strg+H auf die "
                    "aktive Farbe.",
                ],
            ),
            (
                "⌨ Pfeiltasten-Navigation im Sticken-Modus",
                [
                    "Pfeiltasten springen zur nächsten/vorherigen ungehakten Zelle "
                    "der aktiven Farbe. Enter/Space hakt ab und springt direkt weiter.",
                ],
            ),
            (
                "🎯 Schwierigkeits-Anzeige",
                [
                    "Heuristik aus Farbanzahl, Größe, Sonderstichen und Backstitches → "
                    "Anfänger / Mittel / Fortgeschritten / Profi. Sichtbar im Info-"
                    "Panel und im Statistik-Dialog.",
                ],
            ),
            (
                "📦 Bundle-Export (ZIP)",
                [
                    "Datei → 'Als Bundle (ZIP) exportieren…' packt .pxs, HTML, PNG, "
                    "PDF (wenn reportlab installiert), Garnliste und Originalbild "
                    "in eine ZIP — ideal zum Teilen.",
                ],
            ),
        ]

        for header, paragraphs in sections:
            sec = QFrame()
            sec.setStyleSheet(f"""
                QFrame {{
                    background: {THEME.bg_light};
                    border-radius: 8px;
                    padding: 12px 14px;
                }}
            """)
            sl = QVBoxLayout(sec)
            sl.setContentsMargins(10, 8, 10, 10)
            sl.setSpacing(6)

            head_lbl = QLabel(header)
            head_font = QFont()
            head_font.setPointSize(13)
            head_font.setBold(True)
            head_lbl.setFont(head_font)
            head_lbl.setStyleSheet(f"color: {THEME.accent_primary}; background: transparent;")
            sl.addWidget(head_lbl)

            for p in paragraphs:
                t = QLabel(p)
                t.setWordWrap(True)
                t.setStyleSheet(
                    f"color: {THEME.text_secondary}; font-size: 12px; line-height: 1.5; background: transparent;"
                )
                sl.addWidget(t)

            content_layout.addWidget(sec)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # Footer
        footer = QHBoxLayout()
        footer.addStretch()
        btn = QPushButton("Schließen")
        btn.setDefault(True)
        btn.clicked.connect(dialog.accept)
        btn.setStyleSheet(Styles.button_primary())
        footer.addWidget(btn)
        layout.addLayout(footer)

        dialog.exec()

    def _on_about(self: "MainWindow") -> None:
        """Zeigt Über-Dialog."""
        import sys
        from pathlib import Path

        from PySide6.QtGui import QFont, QPainter, QPixmap
        from PySide6.QtSvg import QSvgRenderer
        from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

        from ...config import APP_NAME, APP_VERSION
        from ..styles import THEME, Styles

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Über {APP_NAME}")
        dialog.setFixedSize(480, 480)
        dialog.setStyleSheet(f"""
            QDialog {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {THEME.bg_light}, stop:0.5 {THEME.bg_dark},
                    stop:1 {THEME.bg_dark});
            }}
            QLabel {{ background: transparent; }}
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(6)
        layout.setContentsMargins(40, 25, 40, 25)

        # App-Icon (SVG)
        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        svg_path = (
            Path(__file__).parent.parent.parent / "resources" / "icons" / "pysticky_about.svg"
        )
        if svg_path.exists():
            renderer = QSvgRenderer(str(svg_path))
            pixmap = QPixmap(140, 140)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            icon_lbl.setPixmap(pixmap)
        else:
            icon_lbl.setText("🧵")
            icon_lbl.setStyleSheet("font-size: 52px;")
        layout.addWidget(icon_lbl)

        # App-Name
        name_lbl = QLabel(APP_NAME)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_font = QFont()
        name_font.setPointSize(28)
        name_font.setBold(True)
        name_lbl.setFont(name_font)
        name_lbl.setStyleSheet(f"""
            color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {THEME.accent_primary}, stop:1 {THEME.accent_blue});
            /* Fallback für Gradient-Text: */
            color: {THEME.accent_primary};
        """)
        layout.addWidget(name_lbl)

        # Untertitel
        sub_lbl = QLabel("Kreuzstich-Design-Software")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl.setStyleSheet(f"color: {THEME.text_muted}; font-size: 13px; font-style: italic;")
        layout.addWidget(sub_lbl)

        # Version
        ver_lbl = QLabel(f"Version {APP_VERSION}")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_lbl.setStyleSheet(f"""
            color: {THEME.accent_primary};
            font-size: 12px;
            font-weight: bold;
            background: {THEME.bg_light};
            border-radius: 10px;
            padding: 4px 16px;
            margin: 8px 120px;
        """)
        layout.addWidget(ver_lbl)

        layout.addSpacing(12)

        # Trennlinie
        from PySide6.QtWidgets import QFrame

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {THEME.border_medium}; max-height: 1px;")
        layout.addWidget(sep)

        layout.addSpacing(8)

        # Autor
        author_lbl = QLabel("Entwickelt von\nHans Schnorrenberger")
        author_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author_lbl.setStyleSheet(
            f"color: {THEME.text_secondary}; font-size: 13px; line-height: 1.5;"
        )
        layout.addWidget(author_lbl)

        layout.addSpacing(4)

        # Technologie
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        tech_lbl = QLabel(f"Python {py_ver}  ·  PySide6 (Qt6)")
        tech_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tech_lbl.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        layout.addWidget(tech_lbl)

        layout.addSpacing(8)

        # Copyright
        copy_lbl = QLabel("© 2026 Hans Schnorrenberger. Alle Rechte vorbehalten.")
        copy_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copy_lbl.setStyleSheet(f"color: {THEME.text_disabled}; font-size: 10px;")
        layout.addWidget(copy_lbl)

        layout.addStretch()

        # Schließen-Button
        from PySide6.QtWidgets import QPushButton

        btn = QPushButton("Schließen")
        btn.setAutoDefault(True)
        btn.setDefault(True)
        btn.clicked.connect(dialog.accept)
        btn.setStyleSheet(Styles.button_primary())
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        dialog.exec()

    # =========================================================================
    # Arbeitsbereiche (Workspace-Profile)
    # =========================================================================

    def _on_save_workspace(self: "MainWindow") -> None:
        """Speichert das aktuelle Layout als Profil."""
        from PySide6.QtWidgets import QInputDialog

        from ..workspace_profiles import WorkspaceProfileManager

        mgr = WorkspaceProfileManager(self._settings)
        existing = mgr.list_profiles()

        name, ok = QInputDialog.getText(
            self,
            "Arbeitsbereich speichern",
            "Name für den Arbeitsbereich:",
        )
        if not ok or not name.strip():
            return
        name = name.strip()

        if name in existing:
            reply = QMessageBox.question(
                self,
                "Überschreiben?",
                f"Arbeitsbereich '{name}' existiert bereits. Überschreiben?",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        mgr.save_profile(name, self)
        self.status_bar.showMessage(f"Arbeitsbereich '{name}' gespeichert", 3000)

    def _on_load_workspace(self: "MainWindow") -> None:
        """Lädt ein gespeichertes Layout-Profil."""
        from PySide6.QtWidgets import QInputDialog

        from ..workspace_profiles import WorkspaceProfileManager

        mgr = WorkspaceProfileManager(self._settings)
        profiles = mgr.list_profiles()

        if not profiles:
            self.status_bar.showMessage("Keine gespeicherten Arbeitsbereiche", 3000)
            return

        name, ok = QInputDialog.getItem(
            self,
            "Arbeitsbereich laden",
            "Arbeitsbereich auswählen:",
            profiles,
            0,
            False,
        )
        if not ok:
            return

        if mgr.load_profile(name, self):
            self.status_bar.showMessage(f"Arbeitsbereich '{name}' geladen", 3000)

    def _on_reset_workspace(self: "MainWindow") -> None:
        """Setzt das Layout auf den Standard zurück."""
        # Alle Dock-Widgets sichtbar machen und an Standard-Positionen setzen
        for dock in self.findChildren(self.__class__.__mro__[0]):
            pass  # findChildren gibt MainWindow selbst zurück, skip

        from PySide6.QtWidgets import QDockWidget

        for dock in self.findChildren(QDockWidget):
            dock.setVisible(True)
            dock.setFloating(False)

        self.status_bar.showMessage("Layout zurückgesetzt", 3000)

    # =========================================================================
    # Einstellungen
    # =========================================================================

    def _on_settings(self: "MainWindow") -> None:
        """Öffnet den zentralen Einstellungs-Dialog."""
        from ..dialogs import SettingsDialog

        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self._apply_settings_from_dialog)

        if dialog.exec():
            self._apply_settings_from_dialog()
            self.status_bar.showMessage("Einstellungen gespeichert", 3000)

    def _apply_settings_from_dialog(self: "MainWindow") -> None:
        """Wendet die Einstellungen aus dem Dialog auf die UI an."""
        from ...config import CANVAS_CONFIG, FILE_CONFIG

        self._settings.sync()

        # Theme-Wechsel (live, ohne Neustart)
        from ..styles import get_current_theme_name, reapply_theme, set_theme

        new_theme = self._settings.value("theme", "dark", type=str)
        if new_theme != get_current_theme_name():
            set_theme(new_theme)
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app:
                reapply_theme(app)
            self._reapply_all_widget_styles()

        # Autosave-Einstellungen
        self._autosave_enabled = self._settings.value("autosave_enabled", True, type=bool)
        self._autosave_interval = self._settings.value(
            "autosave_interval", FILE_CONFIG.autosave_interval_minutes, type=int
        )
        self._autosave_timer.stop()
        if self._autosave_enabled and self._autosave_interval > 0:
            self._autosave_timer.start(self._autosave_interval * 60 * 1000)

        # Grid-Einstellungen
        show_grid = self._settings.value("show_grid", True, type=bool)
        self.action_show_grid.setChecked(show_grid)
        self.canvas.show_grid = show_grid

        # Snap-Einstellungen
        snap_enabled = self._settings.value("snap_enabled", False, type=bool)
        self.chk_snap_grid.setChecked(snap_enabled)
        self.canvas.snap_to_grid = snap_enabled
        snap_interval = self._settings.value(
            "snap_interval", CANVAS_CONFIG.default_snap_interval, type=int
        )
        self.canvas.snap_interval = snap_interval

        # Stoff-Textur (Aida-Optik)
        self.canvas.show_fabric_texture = self._settings.value("fabric_texture", True, type=bool)

        self.canvas.update()

    def _reapply_all_widget_styles(self: "MainWindow") -> None:
        """Setzt alle Widget-Stylesheets neu nach Theme-Wechsel."""
        from PySide6.QtWidgets import QToolBar, QWidget

        # 1) Haupt-Toolbar (oben) — hat eigenes Stylesheet
        for toolbar in self.findChildren(QToolBar):
            toolbar.setStyleSheet(self._get_toolbar_stylesheet())

        # 1b) Emoji-Icons neu rendern mit aktueller Theme-Farbe
        self._refresh_toolbar_icons()

        # 2) Symmetrie-ComboBox
        if hasattr(self, "combo_symmetry"):
            self.combo_symmetry.setStyleSheet(self._get_combobox_stylesheet())

        # 3) Tool-Sidebar (links) — hat reapply_styles
        if hasattr(self, "tool_bar") and hasattr(self.tool_bar, "reapply_styles"):
            self.tool_bar.reapply_styles()

        # 4) Canvas-Container (Scrollbars, Ecken)
        if hasattr(self, "canvas_container") and hasattr(self.canvas_container, "reapply_styles"):
            self.canvas_container.reapply_styles()

        # 5) Statusbar-Pill-Styles neu setzen
        if hasattr(self, "_apply_statusbar_styles"):
            self._apply_statusbar_styles()

        # 6) Alle Widgets mit _apply_theme() aufrufen
        for w in self.findChildren(QWidget):
            if hasattr(w, "_apply_theme"):
                w._apply_theme()

        # 7) Canvas neu zeichnen
        self.canvas.update()
        self.update()
