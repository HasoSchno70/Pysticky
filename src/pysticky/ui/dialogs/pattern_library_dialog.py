"""
Muster-Bibliothek mit Thumbnail-Ansicht und Kategorisierung.

Die Bibliothek verwaltet eine Sammlung von Kreuzstich-Mustern
mit Vorschaubildern, Kategorien und Suchfunktion.
"""

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...utils.logging import get_logger

logger = get_logger(__name__)

from ...core.file_io import load_pattern
from ...core.i18n import t
from ..styles import THEME, Styles
from .pattern_library_data import LibraryData, LibraryEntry
from .thumbnail_widget import ThumbnailWidget


class PatternLibraryDialog(QDialog):
    """
    Dialog für die Muster-Bibliothek.

    Features:
    - Thumbnail-Ansicht
    - Kategorisierung
    - Suchfunktion
    - Favoriten
    - Import aus Verzeichnis
    """

    pattern_selected = Signal(str)  # Filepath

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("Muster-Bibliothek"))
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)

        self._library: LibraryData = LibraryData()
        self._library_path = self._get_library_path()
        self._selected_entry: LibraryEntry | None = None
        self._thumbnail_widgets: list[ThumbnailWidget] = []

        # Debounce-Timer für Suche
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._update_thumbnails)

        # Debounce-Timer für Notizen-Speicherung
        self._notes_save_timer = QTimer()
        self._notes_save_timer.setSingleShot(True)
        self._notes_save_timer.setInterval(500)
        self._notes_save_timer.timeout.connect(self._save_notes)

        self._setup_ui()
        self._load_library()

    def _get_library_path(self) -> Path:
        """Gibt den Pfad zur Bibliotheks-Datei zurück.

        Nutzt den in Einstellungen → Dateien → "Bibliothek" konfigurierten
        Ordner, falls gesetzt -- sonst den bisherigen Default im
        Anwendungsverzeichnis.
        """
        from PySide6.QtCore import QSettings

        from ...config import APP_NAME, ORG_NAME

        configured = QSettings(ORG_NAME, APP_NAME).value("library_path", "", type=str).strip()
        default_dir = Path(__file__).parent.parent.parent.parent.parent / "Muster"
        library_dir = Path(configured) if configured else default_dir
        try:
            library_dir.mkdir(exist_ok=True, parents=True)
        except OSError as exc:
            # Konfigurierter Ordner nicht (mehr) erreichbar (z.B. abgestecktes
            # Netzlaufwerk/USB-Stick, fehlende Berechtigung) -- Dialog darf
            # dadurch nicht komplett abstuerzen, sonst kommt der Nutzer gar
            # nicht mehr an die Einstellungen heran, um den Pfad zu korrigieren.
            logger.warning(
                "Bibliotheks-Ordner '%s' nicht erreichbar (%s), falle auf Standard zurueck",
                library_dir,
                exc,
            )
            library_dir = default_dir
            library_dir.mkdir(exist_ok=True, parents=True)
        # Thumbnail-Cache Ordner
        self._thumbnails_dir = library_dir / ".thumbnails"
        self._thumbnails_dir.mkdir(exist_ok=True)
        return library_dir / "library.json"

    def _setup_ui(self) -> None:
        """Erstellt die UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header
        header_layout = QHBoxLayout()

        header_layout.addStretch()

        # Import-Button
        import_btn = QPushButton(t("➕ Hinzufügen..."))
        import_btn.setStyleSheet(Styles.button_primary())
        import_btn.clicked.connect(self._add_patterns)
        header_layout.addWidget(import_btn)

        # Verzeichnis scannen
        scan_btn = QPushButton(t("📁 Verzeichnis scannen..."))
        scan_btn.setStyleSheet(Styles.button_secondary())
        scan_btn.clicked.connect(self._scan_directory)
        header_layout.addWidget(scan_btn)

        layout.addLayout(header_layout)

        # Hauptbereich mit Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Linke Seite: Kategorien
        left_panel = QFrame()
        left_panel.setMinimumWidth(180)
        left_panel.setMaximumWidth(250)
        left_panel.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_medium};
                border: 1px solid {THEME.border_medium};
                border-radius: 8px;
            }}
        """)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)

        cat_label = QLabel(t("Kategorien"))
        cat_label.setStyleSheet(Styles.section_header())
        left_layout.addWidget(cat_label)

        self._category_list = QListWidget()
        self._category_list.setStyleSheet(Styles.list_widget())
        self._category_list.currentRowChanged.connect(self._on_category_changed)
        left_layout.addWidget(self._category_list)

        # Kategorie-Buttons
        cat_btn_layout = QHBoxLayout()

        add_cat_btn = QToolButton()
        add_cat_btn.setText("+")
        add_cat_btn.setToolTip(t("Kategorie hinzufügen"))
        add_cat_btn.setStyleSheet(Styles.tool_button())
        add_cat_btn.clicked.connect(self._add_category)
        cat_btn_layout.addWidget(add_cat_btn)

        del_cat_btn = QToolButton()
        del_cat_btn.setText("−")
        del_cat_btn.setToolTip(t("Kategorie löschen"))
        del_cat_btn.setStyleSheet(Styles.tool_button())
        del_cat_btn.clicked.connect(self._delete_category)
        cat_btn_layout.addWidget(del_cat_btn)

        cat_btn_layout.addStretch()
        left_layout.addLayout(cat_btn_layout)

        splitter.addWidget(left_panel)

        # Rechte Seite: Thumbnails
        right_panel = QFrame()
        right_panel.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_medium};
                border: 1px solid {THEME.border_medium};
                border-radius: 8px;
            }}
        """)

        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)

        # Suchleiste
        search_layout = QHBoxLayout()

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(t("🔍 Suchen..."))
        self._search_edit.setStyleSheet(Styles.input_field())
        self._search_edit.textChanged.connect(self._filter_thumbnails)
        search_layout.addWidget(self._search_edit)

        # Sortierung -- itemData traegt den unuebersetzten Schluessel fuer
        # _sort_changed(), der sichtbare Text ist uebersetzt.
        sort_combo = QComboBox()
        for sort_key in ("Name", "Datum", "Größe", "Farben"):
            sort_combo.addItem(t(sort_key), sort_key)
        sort_combo.setStyleSheet(Styles.combo_box())
        sort_combo.setFixedWidth(100)
        sort_combo.currentIndexChanged.connect(
            lambda _index: self._sort_changed(sort_combo.currentData())
        )
        search_layout.addWidget(sort_combo)

        right_layout.addLayout(search_layout)

        # Info-Leiste
        self._info_label = QLabel(t("0 Muster"))
        self._info_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        right_layout.addWidget(self._info_label)

        # Thumbnail-Grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            {Styles.scrollbar()}
        """)

        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(12)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll.setWidget(self._grid_widget)
        right_layout.addWidget(scroll)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        # Detail-Bereich
        self._detail_frame = QFrame()
        self._detail_frame.setFixedHeight(160)
        self._detail_frame.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_light};
                border: 1px solid {THEME.border_medium};
                border-radius: 8px;
            }}
        """)

        detail_outer = QVBoxLayout(self._detail_frame)
        detail_outer.setContentsMargins(10, 8, 10, 8)
        detail_outer.setSpacing(6)

        # Obere Zeile: Info + Öffnen-Button
        top_row = QHBoxLayout()
        self._detail_label = QLabel(t("Wähle ein Muster aus"))
        self._detail_label.setStyleSheet(f"color: {THEME.text_muted};")
        top_row.addWidget(self._detail_label)
        top_row.addStretch()
        self._open_btn = QPushButton(t("Öffnen"))
        self._open_btn.setStyleSheet(Styles.button_primary())
        self._open_btn.setEnabled(False)
        self._open_btn.clicked.connect(self._open_selected)
        top_row.addWidget(self._open_btn)
        detail_outer.addLayout(top_row)

        # Untere Zeile: Tags + Notizen
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        # Tags
        tags_layout = QVBoxLayout()
        tags_label = QLabel(t("Tags:"))
        tags_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 10px;")
        tags_layout.addWidget(tags_label)
        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText(t("Tags (kommagetrennt)..."))
        self._tags_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {THEME.bg_medium}; color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark}; border-radius: 4px;
                padding: 4px 8px; font-size: 11px;
            }}
            QLineEdit:focus {{ border-color: {THEME.accent_primary}; }}
        """)
        self._tags_edit.setEnabled(False)
        self._tags_edit.editingFinished.connect(self._on_tags_changed)
        tags_layout.addWidget(self._tags_edit)
        bottom_row.addLayout(tags_layout, 1)

        # Notizen
        notes_layout = QVBoxLayout()
        notes_label = QLabel(t("Notizen:"))
        notes_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 10px;")
        notes_layout.addWidget(notes_label)
        self._notes_edit = QTextEdit()
        self._notes_edit.setPlaceholderText(t("Notizen..."))
        self._notes_edit.setMaximumHeight(50)
        self._notes_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {THEME.bg_medium}; color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark}; border-radius: 4px;
                padding: 4px 8px; font-size: 11px;
            }}
            QTextEdit:focus {{ border-color: {THEME.accent_primary}; }}
        """)
        self._notes_edit.setEnabled(False)
        self._notes_edit.textChanged.connect(self._on_notes_changed)
        notes_layout.addWidget(self._notes_edit)
        bottom_row.addLayout(notes_layout, 1)

        detail_outer.addLayout(bottom_row)

        layout.addWidget(self._detail_frame)

        # Dialog-Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn = button_box.button(QDialogButtonBox.StandardButton.Close)
        close_btn.clicked.connect(self.reject)
        # Andere Buttons im Dialog haben autoDefault=True und können den
        # Default-Status übernehmen — daher hier den sanktionierten
        # Primary-Button-Stil unabhängig von isDefault() setzen (konsistent
        # mit dem Close-Button-Look der anderen Dialoge).
        close_btn.setStyleSheet(Styles.button_primary())
        btn_layout.addWidget(button_box)

        layout.addLayout(btn_layout)

    def _load_library(self) -> None:
        """Lädt die Bibliothek aus der JSON-Datei."""
        if self._library_path.exists():
            try:
                with open(self._library_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._library = LibraryData.from_dict(data)
            except (OSError, json.JSONDecodeError, ValueError) as e:
                logger.error("Fehler beim Laden der Bibliothek: %s", e)
                self._library = LibraryData()

        self._update_category_list()
        self._update_thumbnails()

    def _save_library(self) -> None:
        """Speichert die Bibliothek in die JSON-Datei."""
        try:
            with open(self._library_path, "w", encoding="utf-8") as f:
                json.dump(self._library.to_dict(), f, indent=2, ensure_ascii=False)
        except (OSError, ValueError) as e:
            logger.error("Fehler beim Speichern der Bibliothek: %s", e)

    def _update_category_list(self) -> None:
        """Aktualisiert die Kategorie-Liste.

        Behaelt die aktuell ausgewaehlte Kategorie bei (z.B. "Favoriten"),
        statt bei jedem Aufruf (Favorit umschalten, Eintrag entfernen, Tag
        aendern) stumm auf "Alle" zurueckzuspringen -- sonst verliert der
        Nutzer nach fast jeder Aktion die gerade aktive Filteransicht.
        """
        current_category = None
        current_row = self._category_list.currentRow()
        if 0 <= current_row < len(self._library.categories):
            current_category = self._library.categories[current_row]

        self._category_list.clear()

        for cat in self._library.categories:
            count = self._count_entries_in_category(cat)
            item = QListWidgetItem(f"{cat} ({count})")
            self._category_list.addItem(item)

        new_row = (
            self._library.categories.index(current_category)
            if current_category in self._library.categories
            else 0
        )
        self._category_list.setCurrentRow(new_row)

    def _count_entries_in_category(self, category: str) -> int:
        """Zählt Einträge in einer Kategorie."""
        if category == "Alle":
            return len(self._library.entries)
        elif category == "Favoriten":
            return sum(1 for e in self._library.entries if e.favorite)
        else:
            return sum(1 for e in self._library.entries if category in e.categories)

    def _update_thumbnails(self) -> None:
        """Aktualisiert die Thumbnail-Ansicht."""
        # Alte Widgets entfernen
        for widget in self._thumbnail_widgets:
            widget.deleteLater()
        self._thumbnail_widgets.clear()

        # Aktuelle Kategorie ermitteln
        current_row = self._category_list.currentRow()
        if current_row < 0:
            return

        category = self._library.categories[current_row]
        search_text = self._search_edit.text().lower()

        # Einträge filtern
        entries = self._get_filtered_entries(category, search_text)

        # Info aktualisieren
        total = len(self._library.entries)
        if search_text:
            self._info_label.setText(f"{len(entries)} von {total} Muster")
        else:
            self._info_label.setText(f"{len(entries)} Muster")

        # Thumbnails erstellen
        cols = 5
        thumb_dir = getattr(self, "_thumbnails_dir", None)
        for i, entry in enumerate(entries):
            widget = ThumbnailWidget(entry, thumbnails_dir=thumb_dir)
            widget.clicked.connect(self._on_thumbnail_clicked)
            widget.double_clicked.connect(self._on_thumbnail_double_clicked)
            widget.context_menu_requested.connect(self._show_context_menu)
            widget.thumbnail_saved.connect(self._save_library)

            row = i // cols
            col = i % cols
            self._grid_layout.addWidget(widget, row, col)
            self._thumbnail_widgets.append(widget)

    def _get_filtered_entries(self, category: str, search_text: str) -> list[LibraryEntry]:
        """Gibt gefilterte Einträge zurück."""
        entries = []

        for entry in self._library.entries:
            # Kategorie-Filter
            if category == "Alle":
                pass
            elif category == "Favoriten":
                if not entry.favorite:
                    continue
            else:
                if category not in entry.categories:
                    continue

            # Such-Filter
            if search_text:
                searchable = (
                    f"{entry.name} {' '.join(entry.tags)} {' '.join(entry.categories)}".lower()
                )
                if search_text not in searchable:
                    continue

            entries.append(entry)

        return entries

    def _on_category_changed(self, row: int) -> None:
        """Handler für Kategorie-Wechsel."""
        self._update_thumbnails()

    def _filter_thumbnails(self, text: str) -> None:
        """Filtert Thumbnails nach Suchtext (debounced)."""
        self._search_timer.start()

    def _sort_changed(self, sort_by: str) -> None:
        """Sortiert die Einträge."""
        if sort_by == "Name":
            self._library.entries.sort(key=lambda e: e.name.lower())
        elif sort_by == "Datum":
            self._library.entries.sort(key=lambda e: e.added_date, reverse=True)
        elif sort_by == "Größe":
            self._library.entries.sort(key=lambda e: e.width * e.height, reverse=True)
        elif sort_by == "Farben":
            self._library.entries.sort(key=lambda e: e.color_count, reverse=True)

        self._update_thumbnails()

    def _on_thumbnail_clicked(self, entry: LibraryEntry) -> None:
        """Handler für Thumbnail-Klick."""
        # Ausstehende Notizen-Aenderung am VORHERIGEN Eintrag sofort sichern,
        # bevor _selected_entry umgehaengt wird -- sonst wuerde der Debounce-
        # Timer spaeter auf den neu ausgewaehlten Eintrag feuern und die
        # Notizen des vorherigen Eintrags gehen verloren.
        if self._notes_save_timer.isActive():
            self._notes_save_timer.stop()
            self._save_notes()

        self._selected_entry = entry

        # Selektion aktualisieren
        for widget in self._thumbnail_widgets:
            widget.set_selected(widget.entry == entry)

        # Details anzeigen
        w_cm = entry.width / entry.fabric_count * 2.54
        h_cm = entry.height / entry.fabric_count * 2.54

        self._detail_label.setText(
            f"<b>{entry.name}</b> | "
            f"{entry.width}×{entry.height} Stiche ({w_cm:.1f}×{h_cm:.1f} cm) | "
            f"{entry.color_count} Farben | "
            f"{entry.stitch_count:,} Stiche"
        )
        self._open_btn.setEnabled(True)

        # Tags & Notizen laden
        self._tags_edit.setEnabled(True)
        self._notes_edit.setEnabled(True)
        self._tags_edit.blockSignals(True)
        self._tags_edit.setText(", ".join(entry.tags) if entry.tags else "")
        self._tags_edit.blockSignals(False)
        self._notes_edit.blockSignals(True)
        self._notes_edit.setPlainText(entry.notes or "")
        self._notes_edit.blockSignals(False)

    def _on_thumbnail_double_clicked(self, entry: LibraryEntry) -> None:
        """Handler für Thumbnail-Doppelklick."""
        self._selected_entry = entry
        self._open_selected()

    def _open_selected(self) -> None:
        """Öffnet das ausgewählte Muster."""
        if self._selected_entry:
            # Letztes Öffnen aktualisieren
            self._selected_entry.last_opened = datetime.now().isoformat()
            self._save_library()

            self.pattern_selected.emit(self._selected_entry.filepath)
            self.accept()

    def _show_context_menu(self, entry: LibraryEntry, pos: QPoint) -> None:
        """Zeigt das Kontextmenü."""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {THEME.bg_light};
                border: 1px solid {THEME.border_medium};
                border-radius: 4px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                color: {THEME.text_primary};
            }}
            QMenu::item:selected {{
                background: {THEME.accent_primary};
                color: {THEME.bg_dark};
            }}
        """)

        # Öffnen
        open_action = menu.addAction(t("Öffnen"))
        open_action.triggered.connect(lambda: self._open_entry(entry))

        menu.addSeparator()

        # Favorit
        if entry.favorite:
            fav_action = menu.addAction(t("★ Aus Favoriten entfernen"))
        else:
            fav_action = menu.addAction(t("☆ Zu Favoriten hinzufügen"))
        fav_action.triggered.connect(lambda: self._toggle_favorite(entry))

        # Kategorie
        cat_menu = menu.addMenu(t("Kategorie zuweisen"))
        for cat in self._library.categories[2:]:  # "Alle" und "Favoriten" überspringen
            action = cat_menu.addAction(cat)
            action.setCheckable(True)
            action.setChecked(cat in entry.categories)
            action.triggered.connect(lambda checked, c=cat: self._toggle_category(entry, c))

        # Tags bearbeiten
        tags_action = menu.addAction(t("🏷️ Tags bearbeiten..."))
        tags_action.triggered.connect(lambda: self._edit_tags_dialog(entry))

        menu.addSeparator()

        # Im Explorer öffnen
        explorer_action = menu.addAction(t("Im Explorer anzeigen"))
        explorer_action.triggered.connect(lambda: self._show_in_explorer(entry))

        menu.addSeparator()

        # Entfernen
        remove_action = menu.addAction(t("Aus Bibliothek entfernen"))
        remove_action.triggered.connect(lambda: self._remove_entry(entry))

        menu.exec(pos)

    def _open_entry(self, entry: LibraryEntry) -> None:
        """Öffnet einen Eintrag (z.B. übers Kontextmenü, ohne vorherigen Klick)."""
        # Wie in _on_thumbnail_clicked: `entry` kann ein ANDERER Eintrag sein
        # als der aktuell in _notes_edit angezeigte -- ohne diesen Flush
        # wuerde eine ausstehende Notizen-Aenderung sonst dem falschen
        # (neuen) Eintrag zugeschrieben.
        if self._notes_save_timer.isActive():
            self._notes_save_timer.stop()
            self._save_notes()

        self._selected_entry = entry
        self._open_selected()

    def _toggle_favorite(self, entry: LibraryEntry) -> None:
        """Schaltet Favoriten-Status um."""
        entry.favorite = not entry.favorite
        self._save_library()
        self._update_category_list()
        self._update_thumbnails()

    def _toggle_category(self, entry: LibraryEntry, category: str) -> None:
        """Fügt/entfernt eine Kategorie."""
        if category in entry.categories:
            entry.categories.remove(category)
        else:
            entry.categories.append(category)
        self._save_library()
        self._update_category_list()
        self._update_thumbnails()

    def _show_in_explorer(self, entry: LibraryEntry) -> None:
        """Öffnet den Ordner im Explorer."""
        import os
        import subprocess

        filepath = Path(entry.filepath)
        if filepath.exists():
            if os.name == "nt":
                subprocess.run(["explorer", "/select,", str(filepath)])
            else:
                subprocess.run(["xdg-open", str(filepath.parent)])

    def _remove_entry(self, entry: LibraryEntry) -> None:
        """Entfernt einen Eintrag aus der Bibliothek."""
        reply = QMessageBox.question(
            self,
            t("Eintrag entfernen"),
            t(
                "'{name}' aus der Bibliothek entfernen?\n\nDie Datei selbst wird nicht gelöscht."
            ).format(name=entry.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._library.entries.remove(entry)
            self._save_library()
            self._update_category_list()
            self._update_thumbnails()

    def _add_patterns(self) -> None:
        """Fügt neue Muster hinzu."""
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            t("Muster hinzufügen"),
            "",
            "PySticky Muster (*.pxs);;Alle Muster (*.pxs *.xsd *.pat *.oxs);;Alle (*.*)",
        )

        for path in paths:
            self._add_pattern_file(Path(path))

        self._save_library()
        self._update_category_list()
        self._update_thumbnails()

    def _scan_directory(self) -> None:
        """Scannt ein Verzeichnis nach Mustern."""
        directory = QFileDialog.getExistingDirectory(self, t("Verzeichnis scannen"), "")

        if directory:
            dir_path = Path(directory)
            added = 0

            for pattern_file in dir_path.rglob("*.pxs"):
                if self._add_pattern_file(pattern_file):
                    added += 1

            for pattern_file in dir_path.rglob("*.xsd"):
                if self._add_pattern_file(pattern_file):
                    added += 1

            for pattern_file in dir_path.rglob("*.pat"):
                if self._add_pattern_file(pattern_file):
                    added += 1

            for pattern_file in dir_path.rglob("*.oxs"):
                if self._add_pattern_file(pattern_file):
                    added += 1

            self._save_library()
            self._update_category_list()
            self._update_thumbnails()

            QMessageBox.information(
                self,
                t("Scan abgeschlossen"),
                t("{added} neue Muster zur Bibliothek hinzugefügt.").format(added=added),
            )

    # Auto-Kategorisierung Keywords
    _AUTO_CATEGORIES = {
        "Blumen": ["blum", "flower", "rose", "tulpe", "lilie", "gänseblümchen"],
        "Tiere": ["tier", "animal", "katze", "hund", "vogel", "bird", "cat", "dog", "pferd"],
        "Landschaften": ["landschaft", "landscape", "natur", "wald", "berg", "meer", "see"],
        "Weihnachten": ["weihnacht", "christmas", "xmas", "advent", "nikolaus", "schneemann"],
        "Ostern": ["oster", "easter", "hase", "bunny", "ei"],
        "Bordüren": ["bordür", "border", "rand", "leiste", "streifen"],
        "Alphabete": ["alphabet", "buchstab", "letter", "abc", "schrift", "font"],
    }

    def _auto_categorize(self, filepath: Path) -> list[str]:
        """Ermittelt automatisch Kategorien basierend auf Datei-/Ordnernamen."""
        searchable = f"{filepath.stem} {filepath.parent.name}".lower()
        categories = []
        for cat, keywords in self._AUTO_CATEGORIES.items():
            if any(kw in searchable for kw in keywords):
                categories.append(cat)
        return categories if categories else ["Sonstiges"]

    def _add_pattern_file(self, filepath: Path) -> bool:
        """Fügt eine Muster-Datei zur Bibliothek hinzu."""
        # Prüfen ob bereits vorhanden
        str_path = str(filepath)
        for entry in self._library.entries:
            if entry.filepath == str_path:
                return False

        # Pattern laden
        try:
            suffix = filepath.suffix.lower()

            if suffix == ".pxs":
                pattern = load_pattern(filepath)
            elif suffix == ".xsd":
                from ...io.formats import import_xsd

                pattern, _, _ = import_xsd(filepath)
            elif suffix == ".pat":
                from ...io.formats import import_pat

                pattern, _, _ = import_pat(filepath)
            elif suffix == ".oxs":
                from ...io.formats import import_oxs

                pattern, _, _ = import_oxs(filepath)
            else:
                return False

            if not pattern:
                return False

            # Auto-Kategorisierung
            categories = self._auto_categorize(filepath)

            # Eintrag erstellen
            entry = LibraryEntry(
                filepath=str_path,
                name=pattern.name or filepath.stem,
                width=pattern.width,
                height=pattern.height,
                color_count=pattern.color_count,
                stitch_count=pattern.total_stitches,
                fabric_count=pattern.fabric_count,
                categories=categories,
            )

            self._library.entries.append(entry)
            return True

        except (OSError, ValueError) as e:
            logger.warning("Fehler beim Hinzufügen von %s: %s", filepath, e)
            return False

    def _edit_tags_dialog(self, entry: LibraryEntry) -> None:
        """Öffnet einen Dialog zum Bearbeiten der Tags."""
        current_tags = ", ".join(entry.tags) if entry.tags else ""
        text, ok = QInputDialog.getText(
            self,
            t("Tags bearbeiten"),
            t("Tags für '{name}' (kommagetrennt):").format(name=entry.name),
            QLineEdit.EchoMode.Normal,
            current_tags,
        )
        if ok:
            entry.tags = [t.strip() for t in text.split(",") if t.strip()]
            self._save_library()
            # Tags-Feld aktualisieren falls selber Eintrag gewählt
            if self._selected_entry == entry:
                self._tags_edit.blockSignals(True)
                self._tags_edit.setText(", ".join(entry.tags))
                self._tags_edit.blockSignals(False)

    def _on_tags_changed(self) -> None:
        """Tags wurden bearbeitet."""
        if self._selected_entry:
            text = self._tags_edit.text()
            self._selected_entry.tags = [t.strip() for t in text.split(",") if t.strip()]
            self._save_library()

    def _on_notes_changed(self) -> None:
        """Notizen werden bearbeitet (debounced)."""
        self._notes_save_timer.start()

    def _save_notes(self) -> None:
        """Speichert die Notizen des ausgewählten Eintrags."""
        if self._selected_entry:
            self._selected_entry.notes = self._notes_edit.toPlainText().strip()
            self._save_library()

    def closeEvent(self, event) -> None:
        """Sichert eine noch ausstehende, debouncte Notizen-Aenderung sofort.

        _notes_save_timer feuert erst 500ms nach der letzten Eingabe --
        ohne diesen Flush geht ein Edit verloren, wenn der Dialog (Button/
        Escape/Fenster-X) innerhalb dieses Fensters geschlossen wird.
        """
        if self._notes_save_timer.isActive():
            self._notes_save_timer.stop()
            self._save_notes()
        super().closeEvent(event)

    def _add_category(self) -> None:
        """Fügt eine neue Kategorie hinzu."""
        name, ok = QInputDialog.getText(
            self, t("Neue Kategorie"), t("Name der Kategorie:"), QLineEdit.EchoMode.Normal
        )

        if ok and name:
            if name not in self._library.categories:
                self._library.categories.append(name)
                self._save_library()
                self._update_category_list()

    def _delete_category(self) -> None:
        """Löscht eine Kategorie."""
        current_row = self._category_list.currentRow()
        if current_row < 2:  # "Alle" und "Favoriten" nicht löschen
            QMessageBox.warning(
                self, t("Nicht möglich"), t("Diese Kategorie kann nicht gelöscht werden.")
            )
            return

        category = self._library.categories[current_row]

        reply = QMessageBox.question(
            self,
            t("Kategorie löschen"),
            t(
                "Kategorie '{category}' wirklich löschen?\n\n"
                "Die Muster werden nicht gelöscht, nur die Kategorie-Zuordnung."
            ).format(category=category),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Aus allen Einträgen entfernen
            for entry in self._library.entries:
                if category in entry.categories:
                    entry.categories.remove(category)

            self._library.categories.remove(category)
            self._save_library()
            self._update_category_list()
            self._update_thumbnails()
