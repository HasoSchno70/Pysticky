"""
Paletten-Panel zur Auswahl von Garnfarben - Listen-Layout mit Drag & Drop.
"""

from PySide6.QtCore import QByteArray, QMimeData, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QDrag,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core import Pattern, Thread, can_change_palette, get_palette_manager
from ...core.i18n import t
from ..styles import THEME, Styles


class PalettePanel(QWidget):
    """Panel zur Auswahl von Garnfarben aus Herstellerpaletten."""

    color_selected = Signal(object)  # Thread
    color_added = Signal(object)  # Thread
    palette_change_requested = Signal(str)  # Neuer Palettenname

    ICON_SIZE = 36
    ITEM_HEIGHT = 48

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._palette_manager = get_palette_manager()
        self._current_palette_name: str = "Anchor"
        self._current_palette_threads: list[Thread] = []
        self._current_pattern: Pattern | None = None
        self._used_thread_keys: set[str] = set()
        self._drag_start_pos = None
        self._setup_ui()
        self._load_palettes()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Palette-Auswahl
        self.palette_frame = QFrame()
        self.palette_frame.setStyleSheet(Styles.frame_accent())
        palette_layout = QVBoxLayout(self.palette_frame)
        palette_layout.setContentsMargins(10, 8, 10, 8)
        palette_layout.setSpacing(6)

        palette_header = QHBoxLayout()
        self.palette_icon = QLabel("🎨")
        self.palette_icon.setStyleSheet("font-size: 14px; background: transparent;")
        palette_header.addWidget(self.palette_icon)
        self.palette_label = QLabel(t("GARNPALETTE"))
        self.palette_label.setStyleSheet(f"{Styles.section_header()} background: transparent;")
        palette_header.addWidget(self.palette_label)
        palette_header.addStretch()
        palette_layout.addLayout(palette_header)

        self.combo_palette = QComboBox()
        self.combo_palette.setStyleSheet(Styles.combo_box())
        self.combo_palette.currentTextChanged.connect(self._on_palette_changed)
        palette_layout.addWidget(self.combo_palette)

        # Palettenwechsel-Button
        self.btn_apply_palette = QPushButton("🔄 " + t("Muster mit dieser Palette neu erstellen"))
        self.btn_apply_palette.setAutoDefault(False)
        self.btn_apply_palette.setStyleSheet(Styles.button_secondary())
        self.btn_apply_palette.setVisible(False)
        self.btn_apply_palette.clicked.connect(self._on_apply_palette_clicked)
        palette_layout.addWidget(self.btn_apply_palette)

        layout.addWidget(self.palette_frame)

        # Suche
        self.search_frame = QFrame()
        self.search_frame.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_medium};
                border: 1px solid {THEME.border_medium};
                border-radius: 6px;
            }}
        """)
        search_layout = QHBoxLayout(self.search_frame)
        search_layout.setContentsMargins(10, 6, 10, 6)
        search_layout.setSpacing(8)

        self.search_icon = QLabel("🔍")
        self.search_icon.setStyleSheet("font-size: 14px; background: transparent;")
        search_layout.addWidget(self.search_icon)

        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText(t("Suchen: Name oder Nummer..."))
        self.edit_search.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: {THEME.text_primary};
                font-size: 12px;
                padding: 4px;
            }}
            QLineEdit::placeholder {{
                color: {THEME.text_disabled};
            }}
        """)
        self.edit_search.textChanged.connect(self._on_search_changed)
        self.edit_search.setClearButtonEnabled(True)
        search_layout.addWidget(self.edit_search)

        layout.addWidget(self.search_frame)

        # Hinweis
        self.hint_label = QLabel("💡 " + t("Doppelklick = Hinzufügen | Ziehen zur Farbleiste"))
        self.hint_label.setStyleSheet(
            f"color: {THEME.text_muted}; font-size: 10px; background: transparent;"
        )
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hint_label)

        # Farb-Liste
        self.list_colors = QListWidget()
        self.list_colors.setStyleSheet(f"""
            {Styles.list_widget()}
            {Styles.scrollbar()}
        """)
        self.list_colors.setIconSize(QSize(self.ICON_SIZE, self.ICON_SIZE))
        self.list_colors.setSpacing(2)
        self.list_colors.setUniformItemSizes(True)
        self.list_colors.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_colors.setDragEnabled(True)
        self.list_colors.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.list_colors.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_colors.itemClicked.connect(self._on_item_clicked)
        self.list_colors.startDrag = self._start_drag

        layout.addWidget(self.list_colors, 1)

        # Info-Label
        self.label_info = QLabel("0 " + t("Farben"))
        self.label_info.setStyleSheet(
            f"color: {THEME.text_muted}; font-size: 11px; background: transparent;"
        )
        self.label_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_info)

        self.setMinimumWidth(280)
        self.setMaximumWidth(400)

    def _apply_theme(self) -> None:
        """Re-applies all stylesheets for theme switching."""
        self.palette_frame.setStyleSheet(Styles.frame_accent())
        self.palette_icon.setStyleSheet("font-size: 14px; background: transparent;")
        self.palette_label.setStyleSheet(f"{Styles.section_header()} background: transparent;")
        self.combo_palette.setStyleSheet(Styles.combo_box())
        self.btn_apply_palette.setStyleSheet(Styles.button_secondary())
        self.search_frame.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_medium};
                border: 1px solid {THEME.border_medium};
                border-radius: 6px;
            }}
        """)
        self.search_icon.setStyleSheet("font-size: 14px; background: transparent;")
        self.edit_search.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: {THEME.text_primary};
                font-size: 12px;
                padding: 4px;
            }}
            QLineEdit::placeholder {{
                color: {THEME.text_disabled};
            }}
        """)
        self.hint_label.setStyleSheet(
            f"color: {THEME.text_muted}; font-size: 10px; background: transparent;"
        )
        self.list_colors.setStyleSheet(f"""
            {Styles.list_widget()}
            {Styles.scrollbar()}
        """)
        self.label_info.setStyleSheet(
            f"color: {THEME.text_muted}; font-size: 11px; background: transparent;"
        )

    def _load_palettes(self) -> None:
        """Befüllt das Palette-Dropdown.

        Gruppiert visuell: Garn-Paletten (🧵) zuerst, dann Diamond-Painting
        (💎), dann Beads (🔮). Jede Palette trägt ihr Typ-Icon im
        Anzeigetext, damit man auf einen Blick weiss, was sie liefert.
        Der DATA-Wert des Items ist der reine Palette-Name (ohne Icon),
        damit existierende Lookups via `findText` / `currentText` weiter
        funktionieren — der View-Code prüft daher zusätzlich currentData.
        """
        self._palette_manager.load_all()
        self.combo_palette.clear()

        # Drei Buckets für die visuelle Gruppierung
        thread_palettes: list[str] = []
        diamond_palettes: list[str] = []
        bead_palettes: list[str] = []
        for name in sorted(self._palette_manager.available_palettes):
            p = self._palette_manager.get_palette(name)
            if p is None:
                continue
            if p.is_diamond:
                diamond_palettes.append(name)
            elif p.is_beads:
                bead_palettes.append(name)
            else:
                thread_palettes.append(name)

        def _add_group(palettes: list[str], icon: str) -> None:
            for name in palettes:
                # Anzeigetext mit Icon; userData = reiner Name für Lookup-
                # Kompatibilität (findText sucht den AnzeigeText, deshalb
                # speichern wir die Text-zu-Name-Map zusätzlich).
                self.combo_palette.addItem(f"{icon}  {name}", userData=name)

        _add_group(thread_palettes, "🧵")
        _add_group(diamond_palettes, "💎")
        _add_group(bead_palettes, "🔮")

        # Default-Auswahl: Anchor (Garn). Suche via userData, nicht Text,
        # weil Text jetzt das Icon enthält.
        for i in range(self.combo_palette.count()):
            if self.combo_palette.itemData(i) == "Anchor":
                self.combo_palette.setCurrentIndex(i)
                break
        self._refresh_color_list()

    def set_pattern(self, pattern: Pattern | None) -> None:
        """Setzt das aktuelle Muster für die Markierung verwendeter Farben."""
        self._current_pattern = pattern
        self._update_used_colors()
        self._update_palette_button()

        palette_name = None
        if pattern and pattern.source_palette_name:
            palette_name = pattern.source_palette_name
        elif pattern and pattern.color_entries:
            first_manufacturer = pattern.color_entries[0].thread.manufacturer
            if first_manufacturer:
                idx = self._find_palette_index(first_manufacturer)
                if idx >= 0:
                    palette_name = first_manufacturer

        if palette_name:
            idx = self._find_palette_index(palette_name)
            if idx >= 0:
                self.combo_palette.blockSignals(True)
                self.combo_palette.setCurrentIndex(idx)
                self._current_palette_name = palette_name
                self.combo_palette.blockSignals(False)

        self._refresh_color_list()

    def _find_palette_index(self, name: str) -> int:
        """Sucht den Combo-Index einer Palette anhand des reinen Namens
        (ohne Icon-Prefix). Liefert -1 wenn nicht gefunden.

        Wird benutzt statt ``findText``, weil der angezeigte Text seit der
        Gruppierung ein Typ-Icon enthält.
        """
        for i in range(self.combo_palette.count()):
            if self.combo_palette.itemData(i) == name:
                return i
        return -1

    def current_palette_name(self) -> str:
        """Aktuell gewählter Palette-Name (ohne Icon-Prefix)."""
        data = self.combo_palette.currentData()
        if isinstance(data, str):
            return data
        # Fallback wenn aus irgendeinem Grund kein userData gesetzt ist
        return self.combo_palette.currentText().split("  ", 1)[-1].strip()

    def set_mode(self, mode: str) -> None:
        """Modus-spezifisches Header-Label für das Palette-Panel."""
        if mode == "diamond":
            self.palette_icon.setText("💎")
            self.palette_label.setText(t("DIAMOND-PALETTE"))
        else:
            self.palette_icon.setText("🎨")
            self.palette_label.setText(t("GARNPALETTE"))

    def _update_used_colors(self) -> None:
        self._used_thread_keys.clear()
        if self._current_pattern:
            for entry in self._current_pattern.color_entries:
                key = self._get_thread_key(entry.thread)
                self._used_thread_keys.add(key)

    def _get_thread_key(self, thread: Thread) -> str:
        if thread.catalog_number:
            return f"{thread.manufacturer}_{thread.catalog_number}".lower()
        return f"{thread.name}_{thread.color.to_hex()}".lower()

    def _is_color_used(self, thread: Thread) -> bool:
        key = self._get_thread_key(thread)
        return key in self._used_thread_keys

    def _update_palette_button(self) -> None:
        if self._current_pattern and can_change_palette(self._current_pattern):
            self.btn_apply_palette.setVisible(True)
            same_palette = self._current_pattern.source_palette_name == self._current_palette_name
            self.btn_apply_palette.setEnabled(not same_palette)

            if same_palette:
                self.btn_apply_palette.setText("✓ " + t("Aktuelle Palette"))
            else:
                self.btn_apply_palette.setText(
                    f"🔄 {t('Mit')} {self._current_palette_name} {t('neu erstellen')}"
                )
        else:
            self.btn_apply_palette.setVisible(False)

    def _on_palette_changed(self, display_text: str) -> None:
        """Slot für ``currentTextChanged``. Der display_text enthält jetzt
        einen Icon-Prefix ("🧵  Anchor") — wir extrahieren den reinen Namen
        aus userData, um Pattern-Logik nicht zu brechen.
        """
        # userData enthält den reinen Namen (siehe _load_palettes).
        idx = self.combo_palette.currentIndex()
        name = self.combo_palette.itemData(idx) if idx >= 0 else display_text
        if not isinstance(name, str):
            name = display_text
        self._current_palette_name = name
        self._update_palette_button()
        self._refresh_color_list()

    def _on_apply_palette_clicked(self) -> None:
        if not self._current_pattern:
            return

        reply = QMessageBox.question(
            self,
            "Palette wechseln",
            f"Das Muster wird mit '{self._current_palette_name}' neu erstellt.\n\n"
            f"Alle manuellen Änderungen gehen verloren!\n\nFortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.palette_change_requested.emit(self._current_palette_name)

    def _on_search_changed(self, text: str) -> None:
        self._refresh_color_list()

    def _create_color_icon(self, thread: Thread, is_used: bool) -> QPixmap:
        size = self.ICON_SIZE
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = QColor(thread.color.r, thread.color.g, thread.color.b)
        gradient = QLinearGradient(0, 0, size, size)
        gradient.setColorAt(0, color.lighter(115))
        gradient.setColorAt(0.5, color)
        gradient.setColorAt(1, color.darker(115))

        painter.setBrush(QBrush(gradient))

        if is_used:
            painter.setPen(QPen(QColor(THEME.accent_primary), 3))
        else:
            painter.setPen(QPen(QColor(THEME.border_light), 1))

        margin = 2
        painter.drawRoundedRect(margin, margin, size - 2 * margin, size - 2 * margin, 6, 6)

        # Glanz-Effekt
        gloss_rect = (margin + 2, margin + 2, size - 2 * margin - 4, (size - 2 * margin) // 2 - 2)
        gloss = QLinearGradient(0, gloss_rect[1], 0, gloss_rect[1] + gloss_rect[3])
        gloss.setColorAt(0, QColor(255, 255, 255, 60))
        gloss.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gloss))
        painter.drawRoundedRect(*gloss_rect, 4, 4)

        if is_used:
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            cx, cy = size // 2, size // 2
            painter.drawLine(cx - 6, cy, cx - 2, cy + 4)
            painter.drawLine(cx - 2, cy + 4, cx + 6, cy - 4)

        painter.end()
        return pixmap

    def _refresh_color_list(self) -> None:
        # Bulk-Update: Repaint während der bis zu 450 addItem-Calls (DMC
        # Diamond Painting) aussetzen. Verhindert das kurze Phantom-Top-
        # Level-Fenster, das beim Palette-Wechsel sonst aufflackert.
        self.list_colors.setUpdatesEnabled(False)
        try:
            self._refresh_color_list_impl()
        finally:
            self.list_colors.setUpdatesEnabled(True)

    def _refresh_color_list_impl(self) -> None:
        self.list_colors.clear()
        self._current_palette_threads.clear()

        palette = self._palette_manager.get_palette(self._current_palette_name)
        if not palette:
            self.label_info.setText(t("Palette nicht gefunden"))
            return

        search = self.edit_search.text().lower().strip()
        count = 0
        used_count = 0

        for thread in palette:
            if search:
                if search not in thread.name.lower() and (
                    not thread.catalog_number or search not in thread.catalog_number.lower()
                ):
                    continue

            is_used = self._is_color_used(thread)
            if is_used:
                used_count += 1

            icon = self._create_color_icon(thread, is_used)
            catalog = thread.catalog_number or "-"
            text = f"✓ {catalog}  •  {thread.name}" if is_used else f"{catalog}  •  {thread.name}"

            item = QListWidgetItem(text)
            item.setIcon(icon)
            item.setSizeHint(QSize(0, self.ITEM_HEIGHT))
            item.setData(Qt.ItemDataRole.UserRole, len(self._current_palette_threads))

            item.setToolTip(
                f"<b style='color:{THEME.accent_primary}; font-size:14px;'>{thread.name}</b><br>"
                f"<span style='color:{THEME.text_primary};'>Nr: <b>{catalog}</b></span><br>"
                f"<span style='color:{THEME.text_muted};'>{thread.manufacturer}</span><br>"
                f"<span style='color:{THEME.info};'>{thread.color.to_hex()}</span><br>"
                f"<span style='color:{THEME.success if is_used else THEME.text_muted};'>"
                f"{'✓ Im Muster verwendet' if is_used else 'Doppelklick zum Hinzufügen'}</span>"
            )

            font = item.font()
            if is_used:
                font.setBold(True)
            item.setFont(font)

            self._current_palette_threads.append(thread)
            self.list_colors.addItem(item)
            count += 1

        total = len(palette)
        if search:
            self.label_info.setText(
                f"🔍 {count} {t('von')} {total} {t('Farben')} ({used_count} {t('verwendet')})"
            )
        else:
            self.label_info.setText(f"📋 {count} {t('Farben')} ({used_count} {t('im Muster')})")

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is not None and 0 <= idx < len(self._current_palette_threads):
            thread = self._current_palette_threads[idx]
            self.color_selected.emit(thread)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is not None and 0 <= idx < len(self._current_palette_threads):
            thread = self._current_palette_threads[idx]
            self.color_added.emit(thread)

    def _start_drag(self, supported_actions) -> None:
        item = self.list_colors.currentItem()
        if not item:
            return

        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is None or idx >= len(self._current_palette_threads):
            return

        thread = self._current_palette_threads[idx]
        drag = QDrag(self.list_colors)
        mime_data = QMimeData()

        data = (
            f"{thread.manufacturer}|{thread.catalog_number}|{thread.name}|{thread.color.to_hex()}"
        )
        mime_data.setData("application/x-pysticky-thread", QByteArray(data.encode()))
        mime_data.setText(f"{thread.catalog_number} - {thread.name}")

        drag.setMimeData(mime_data)
        pixmap = self._create_color_icon(thread, False)
        drag.setPixmap(
            pixmap.scaled(
                48,
                48,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        drag.setHotSpot(pixmap.rect().center())
        drag.exec(Qt.DropAction.CopyAction)

    def refresh_used_colors(self) -> None:
        self._update_used_colors()
        self._refresh_color_list()
