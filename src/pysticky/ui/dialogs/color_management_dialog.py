"""
Dialog zur Verwaltung der Farbpalette.

Features:
- Farben sortieren (nach Name, Hersteller, Helligkeit, Verwendung)
- Ungenutzte Farben entfernen
- Farben löschen/entfernen
- Farbreihenfolge per Drag & Drop ändern
- Farben zusammenführen
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import t
from ...core.layer import NO_STITCH
from ..color_utils import to_qcolor
from ..styles import THEME, Styles

if TYPE_CHECKING:
    from ...core import ColorEntry, Pattern


class ColorListItem(QListWidgetItem):
    """Listeneintrag für eine Farbe."""

    def __init__(self, index: int, entry: "ColorEntry", parent=None) -> None:
        super().__init__(parent)
        self.index = index
        self.entry = entry
        self._update_display()

    def _update_display(self) -> None:
        thread = self.entry.thread
        # Feste Spaltenbreiten (per ljust/rjust) + Monospace-Font auf der Liste
        # (siehe ColorListWidget) sorgen für echte Spalten statt nur durch
        # "│" getrennten, unterschiedlich breiten Text.
        symbol_col = f"{self.entry.symbol:<3}"
        name_col = f"{thread.name:<24}"
        mfr_col = f"{(thread.manufacturer or '-'):<12}"
        stitch_col = f"{self.entry.stitch_count:>6} Stiche"
        self.setText(f"{symbol_col}│ {name_col}│ {mfr_col}│ {stitch_col}")
        self.setToolTip(
            f"Symbol: {self.entry.symbol}\n"
            f"Name: {thread.name}\n"
            f"Hersteller: {thread.manufacturer or '-'}\n"
            f"Nr: {thread.catalog_number or '-'}\n"
            f"Fäden: {self.entry.strands}\n"
            f"Stiche: {self.entry.stitch_count}"
        )


class ColorPreviewWidget(QWidget):
    """Kleine Farbvorschau."""

    def __init__(self, color: QColor, size: int = 24, parent=None) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedSize(size, size)

    def set_color(self, color: QColor) -> None:
        self._color = color
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Rahmen
        painter.setPen(QPen(QColor(THEME.border_light), 1))
        painter.setBrush(QBrush(self._color))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)


class ColorListWidget(QListWidget):
    """Liste mit Drag & Drop für Farben."""

    order_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        # Monospace-Font, damit die per ljust/rjust ausgerichteten Spalten in
        # ColorListItem._update_display() auch tatsächlich untereinander stehen.
        self.setStyleSheet("QListWidget { font-family: Consolas, 'Courier New', monospace; }")

        self.model().rowsMoved.connect(lambda: self.order_changed.emit())

    def get_color_order(self) -> list[int]:
        """Gibt die aktuelle Reihenfolge der Farb-Indizes zurück."""
        order = []
        for i in range(self.count()):
            item = self.item(i)
            if isinstance(item, ColorListItem):
                order.append(item.index)
        return order


class ColorManagementDialog(QDialog):
    """Dialog zur Verwaltung der Farbpalette."""

    colors_changed = Signal()

    def __init__(self, pattern: "Pattern", parent=None) -> None:
        super().__init__(parent)
        self._pattern = pattern
        self._original_entries = list(pattern.color_entries)  # Backup
        self._changes_made = False

        self.setWindowTitle(t("Farbpalette verwalten"))
        self.setMinimumSize(700, 550)

        self._setup_ui()
        self._apply_theme()
        self._populate_list()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header
        header = QHBoxLayout()

        self._count_label = QLabel()
        self._count_label.setStyleSheet(f"color: {THEME.text_muted};")
        header.addWidget(self._count_label)

        header.addStretch()
        layout.addLayout(header)

        # Hauptbereich
        main_layout = QHBoxLayout()
        main_layout.setSpacing(15)

        # Linke Seite: Farbliste
        left_panel = QVBoxLayout()

        # Toolbar über der Liste
        toolbar = QHBoxLayout()
        toolbar.setSpacing(5)

        # Sortier-Dropdown
        toolbar.addWidget(QLabel(t("Sortieren:")))
        self._sort_combo = QComboBox()
        self._sort_combo.addItems(
            [
                t("Original"),
                t("Nach Name (A-Z)"),
                t("Nach Name (Z-A)"),
                t("Nach Hersteller"),
                t("Nach Helligkeit (hell → dunkel)"),
                t("Nach Helligkeit (dunkel → hell)"),
                t("Nach Verwendung (meiste zuerst)"),
                t("Nach Verwendung (wenigste zuerst)"),
            ]
        )
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        toolbar.addWidget(self._sort_combo)

        toolbar.addStretch()

        # Aktions-Buttons
        self._remove_unused_btn = QPushButton(t("🗑️ Ungenutzte entfernen"))
        self._remove_unused_btn.clicked.connect(self._on_remove_unused)
        toolbar.addWidget(self._remove_unused_btn)

        left_panel.addLayout(toolbar)

        # Suchfeld
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(t("🔍 Name, Hersteller oder Nummer..."))
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._on_search_changed)
        self._search_input.setStyleSheet(f"""
            QLineEdit {{
                background: {THEME.bg_medium};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {THEME.accent_primary};
            }}
        """)
        left_panel.addWidget(self._search_input)

        # Farbliste
        self._color_list = ColorListWidget()
        self._color_list.order_changed.connect(self._on_order_changed)
        self._color_list.itemSelectionChanged.connect(self._on_selection_changed)
        self._color_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._color_list.customContextMenuRequested.connect(self._show_context_menu)
        left_panel.addWidget(self._color_list, 1)

        # Info unter der Liste
        self._info_label = QLabel(t("💡 Tipp: Farben per Drag & Drop verschieben"))
        self._info_label.setStyleSheet(
            f"color: {THEME.text_muted}; font-size: 10px; font-style: italic;"
        )
        left_panel.addWidget(self._info_label)

        main_layout.addLayout(left_panel, 2)

        # Rechte Seite: Aktionen
        right_panel = QVBoxLayout()
        right_panel.setSpacing(10)

        # Ausgewählte Farbe
        selection_group = QGroupBox(t("Ausgewählte Farbe"))
        selection_layout = QVBoxLayout(selection_group)

        self._preview_widget = ColorPreviewWidget(QColor(128, 128, 128), 60)
        selection_layout.addWidget(self._preview_widget, 0, Qt.AlignmentFlag.AlignCenter)

        self._selected_info = QLabel(t("Keine Farbe ausgewählt"))
        self._selected_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._selected_info.setWordWrap(True)
        self._selected_info.setStyleSheet(f"color: {THEME.text_muted};")
        selection_layout.addWidget(self._selected_info)

        # Fadenstärke
        strands_row = QHBoxLayout()
        strands_row.addWidget(QLabel(t("Fäden:")))
        self._strands_spin = QSpinBox()
        self._strands_spin.setRange(1, 6)
        self._strands_spin.setValue(2)
        self._strands_spin.setEnabled(False)
        self._strands_spin.setToolTip(t("Anzahl Fäden (1-6)"))
        self._strands_spin.valueChanged.connect(self._on_strands_changed)
        strands_row.addWidget(self._strands_spin)
        selection_layout.addLayout(strands_row)

        right_panel.addWidget(selection_group)

        # Fadenstärke für alle Farben auf einmal setzen
        bulk_strands_group = QGroupBox(t("Fäden für alle Farben"))
        bulk_strands_layout = QHBoxLayout(bulk_strands_group)
        self._bulk_strands_spin = QSpinBox()
        self._bulk_strands_spin.setRange(1, 6)
        self._bulk_strands_spin.setValue(2)
        self._bulk_strands_spin.setToolTip(t("Anzahl Fäden (1-6)"))
        bulk_strands_layout.addWidget(self._bulk_strands_spin)
        self._bulk_strands_btn = QPushButton(t("Auf alle Farben anwenden"))
        self._bulk_strands_btn.clicked.connect(self._on_apply_strands_to_all)
        bulk_strands_layout.addWidget(self._bulk_strands_btn)
        right_panel.addWidget(bulk_strands_group)

        # Aktionen für ausgewählte Farbe
        actions_group = QGroupBox(t("Aktionen"))
        actions_layout = QVBoxLayout(actions_group)

        self._move_up_btn = QPushButton(t("⬆️ Nach oben"))
        self._move_up_btn.clicked.connect(self._on_move_up)
        self._move_up_btn.setEnabled(False)
        actions_layout.addWidget(self._move_up_btn)

        self._move_down_btn = QPushButton(t("⬇️ Nach unten"))
        self._move_down_btn.clicked.connect(self._on_move_down)
        self._move_down_btn.setEnabled(False)
        actions_layout.addWidget(self._move_down_btn)

        self._move_top_btn = QPushButton(t("⏫ An den Anfang"))
        self._move_top_btn.clicked.connect(self._on_move_top)
        self._move_top_btn.setEnabled(False)
        actions_layout.addWidget(self._move_top_btn)

        self._move_bottom_btn = QPushButton(t("⏬ An das Ende"))
        self._move_bottom_btn.clicked.connect(self._on_move_bottom)
        self._move_bottom_btn.setEnabled(False)
        actions_layout.addWidget(self._move_bottom_btn)

        actions_layout.addSpacing(10)

        self._delete_btn = QPushButton(t("🗑️ Farbe löschen"))
        self._delete_btn.clicked.connect(self._on_delete_color)
        self._delete_btn.setEnabled(False)
        # Roter Lösch-Button — bewusst abweichend vom Default-Stil, damit
        # destruktive Aktion klar erkennbar ist.
        self._delete_btn.setStyleSheet(Styles.button_danger())
        actions_layout.addWidget(self._delete_btn)

        right_panel.addWidget(actions_group)

        # Zusammenführen
        merge_group = QGroupBox(t("Farben zusammenführen"))
        merge_layout = QVBoxLayout(merge_group)

        merge_info = QLabel(t("Wählen Sie zwei Farben aus und führen Sie sie zusammen."))
        merge_info.setWordWrap(True)
        merge_info.setStyleSheet(f"color: {THEME.text_muted}; font-size: 10px;")
        merge_layout.addWidget(merge_info)

        self._merge_btn = QPushButton(t("🔗 Ausgewählte zusammenführen"))
        self._merge_btn.clicked.connect(self._on_merge_colors)
        self._merge_btn.setEnabled(False)
        merge_layout.addWidget(self._merge_btn)

        right_panel.addWidget(merge_group)

        right_panel.addStretch()

        main_layout.addLayout(right_panel, 1)
        layout.addLayout(main_layout, 1)

        # Footer mit Buttons
        footer = QHBoxLayout()

        self._reset_btn = QPushButton(t("↩️ Zurücksetzen"))
        self._reset_btn.clicked.connect(self._on_reset)
        footer.addWidget(self._reset_btn)

        footer.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)

        self._apply_btn = QPushButton(t("Übernehmen"))
        self._apply_btn.setDefault(True)
        self._apply_btn.clicked.connect(self.accept)
        # _apply_theme() setzt einen eigenen dialogweiten QPushButton-Stil,
        # der die globale :default-Hervorhebung überschreibt.
        self._apply_btn.setStyleSheet(Styles.button_primary())
        button_box.addButton(self._apply_btn, QDialogButtonBox.ButtonRole.AcceptRole)

        footer.addWidget(button_box)

        layout.addLayout(footer)

        # Alle anderen Buttons im Dialog haben autoDefault=True und könnten
        # sonst den Default-Status (Enter-Taste) von "Übernehmen" übernehmen.
        for btn in self.findChildren(QPushButton):
            if btn is not self._apply_btn and button_box.buttonRole(btn) == (
                QDialogButtonBox.ButtonRole.InvalidRole
            ):
                btn.setAutoDefault(False)
        self._apply_btn.setDefault(True)

    def _apply_theme(self) -> None:
        self.setStyleSheet(f"""
            QDialog {{
                background: {THEME.bg_dark};
            }}
            QGroupBox {{
                font-weight: bold;
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QListWidget {{
                background: {THEME.bg_medium};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }}
            QListWidget::item {{
                padding: 6px 8px;
                border-bottom: 1px solid {THEME.border_dark};
            }}
            QListWidget::item:selected {{
                background: {THEME.accent_primary};
                color: white;
            }}
            QListWidget::item:alternate {{
                background: {THEME.bg_light};
            }}
            QComboBox {{
                background: {THEME.bg_medium};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
                padding: 5px 10px;
                min-width: 180px;
            }}
            QPushButton {{
                background: {THEME.bg_medium};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background: {THEME.bg_light};
            }}
            QPushButton:disabled {{
                color: {THEME.text_disabled};
            }}
        """)

    def _populate_list(self) -> None:
        """Füllt die Liste mit Farben."""
        self._color_list.clear()

        for i, entry in enumerate(self._pattern.color_entries):
            # Icon mit Farbe erstellen
            pixmap = QPixmap(20, 20)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            color = to_qcolor(entry.thread.color)
            painter.setBrush(color)
            painter.setPen(QPen(QColor(THEME.border_light), 1))
            painter.drawRoundedRect(2, 2, 16, 16, 3, 3)
            painter.end()

            item = ColorListItem(i, entry)
            item.setIcon(QIcon(pixmap))
            item.setSizeHint(QSize(0, 32))
            self._color_list.addItem(item)

        self._update_count()

    def _update_count(self) -> None:
        """Aktualisiert die Farbanzahl."""
        count = len(self._pattern.color_entries)
        used = sum(1 for e in self._pattern.color_entries if e.stitch_count > 0)
        self._count_label.setText(f"{count} Farben ({used} verwendet)")

    def _on_search_changed(self, text: str) -> None:
        """Filtert die Farbliste nach Suchbegriff."""
        search = text.strip().lower()
        for i in range(self._color_list.count()):
            item = self._color_list.item(i)
            if not isinstance(item, ColorListItem):
                continue
            if not search:
                item.setHidden(False)
                continue
            entry = item.entry
            thread = entry.thread
            # Suche in Name, Hersteller, Katalognummer und Symbol
            searchable = " ".join(
                filter(
                    None,
                    [
                        thread.name.lower(),
                        (thread.manufacturer or "").lower(),
                        (thread.catalog_number or "").lower(),
                        entry.symbol.lower(),
                    ],
                )
            )
            item.setHidden(search not in searchable)

    def _on_selection_changed(self) -> None:
        """Auswahl geändert."""
        selected = self._color_list.selectedItems()
        has_selection = len(selected) > 0
        single_selection = len(selected) == 1
        multi_selection = len(selected) >= 2

        self._move_up_btn.setEnabled(single_selection)
        self._move_down_btn.setEnabled(single_selection)
        self._move_top_btn.setEnabled(single_selection)
        self._move_bottom_btn.setEnabled(single_selection)
        self._delete_btn.setEnabled(has_selection)
        self._merge_btn.setEnabled(multi_selection)

        if single_selection:
            item = selected[0]
            if isinstance(item, ColorListItem):
                entry = item.entry
                color = to_qcolor(entry.thread.color)
                self._preview_widget.set_color(color)
                self._selected_info.setText(
                    f"<b>{entry.symbol}</b> {entry.thread.name}<br>"
                    f"<span style='color: {THEME.text_muted};'>{entry.thread.manufacturer or '-'}</span><br>"
                    f"<span style='color: {THEME.accent_primary};'>{entry.stitch_count} Stiche</span>"
                )
                self._strands_spin.setEnabled(True)
                self._strands_spin.blockSignals(True)
                self._strands_spin.setValue(entry.strands)
                self._strands_spin.blockSignals(False)
        elif multi_selection:
            self._preview_widget.set_color(QColor(128, 128, 128))
            self._selected_info.setText(f"{len(selected)} Farben ausgewählt")
            # Fäden bleiben bei Mehrfachauswahl editierbar — _on_strands_changed
            # wendet den neuen Wert auf alle ausgewählten Farben an.
            self._strands_spin.setEnabled(True)
            first_entry = selected[0].entry if isinstance(selected[0], ColorListItem) else None
            if first_entry is not None:
                self._strands_spin.blockSignals(True)
                self._strands_spin.setValue(first_entry.strands)
                self._strands_spin.blockSignals(False)
        else:
            self._preview_widget.set_color(QColor(128, 128, 128))
            self._selected_info.setText("Keine Farbe ausgewählt")
            self._strands_spin.setEnabled(False)

    def _on_strands_changed(self, value: int) -> None:
        """Fadenstärke geändert — gilt für alle aktuell ausgewählten Farben."""
        selected = self._color_list.selectedItems()
        changed = False
        for item in selected:
            if isinstance(item, ColorListItem):
                item.entry.strands = value
                item._update_display()
                changed = True
        if changed:
            self._changes_made = True

    def _on_apply_strands_to_all(self) -> None:
        """Setzt die Fadenstärke für alle Farben der Palette auf einmal."""
        value = self._bulk_strands_spin.value()
        for entry in self._pattern.color_entries:
            entry.strands = value
        for i in range(self._color_list.count()):
            item = self._color_list.item(i)
            if isinstance(item, ColorListItem):
                item._update_display()
        self._changes_made = True
        if self._strands_spin.isEnabled():
            self._strands_spin.blockSignals(True)
            self._strands_spin.setValue(value)
            self._strands_spin.blockSignals(False)

    def _on_sort_changed(self, index: int) -> None:
        """Sortierung geändert."""
        entries = list(self._pattern.color_entries)

        if index == 0:  # Original
            entries = self._original_entries.copy()
        elif index == 1:  # Name A-Z
            entries.sort(key=lambda e: e.thread.name.lower())
        elif index == 2:  # Name Z-A
            entries.sort(key=lambda e: e.thread.name.lower(), reverse=True)
        elif index == 3:  # Hersteller
            entries.sort(key=lambda e: (e.thread.manufacturer or "ZZZ", e.thread.name.lower()))
        elif index == 4:  # Helligkeit hell→dunkel
            entries.sort(key=lambda e: e.thread.color.luminance, reverse=True)
        elif index == 5:  # Helligkeit dunkel→hell
            entries.sort(key=lambda e: e.thread.color.luminance)
        elif index == 6:  # Verwendung meiste
            entries.sort(key=lambda e: e.stitch_count, reverse=True)
        elif index == 7:  # Verwendung wenigste
            entries.sort(key=lambda e: e.stitch_count)

        self._pattern.color_entries = entries
        self._populate_list()
        self._changes_made = True

    def _on_order_changed(self) -> None:
        """Reihenfolge per Drag & Drop geändert."""
        new_order = self._color_list.get_color_order()

        # Neue Reihenfolge anwenden
        old_entries = list(self._pattern.color_entries)
        new_entries = [old_entries[i] for i in new_order]

        # Indizes in Layern aktualisieren
        index_map = {old: new for new, old in enumerate(new_order)}

        for layer in self._pattern.layer_stack:
            for y in range(self._pattern.height):
                for x in range(self._pattern.width):
                    old_index = layer.get_stitch(x, y)
                    if old_index is not None and old_index in index_map:
                        layer.set_stitch(x, y, index_map[old_index])

        # Backstitches aktualisieren
        for bs in self._pattern.backstitches:
            if bs.color_index in index_map:
                bs.color_index = index_map[bs.color_index]

        self._pattern.color_entries = new_entries
        self._populate_list()
        self._changes_made = True

    def _on_move_up(self) -> None:
        """Farbe nach oben verschieben."""
        row = self._color_list.currentRow()
        if row > 0:
            self._swap_colors(row, row - 1)
            self._color_list.setCurrentRow(row - 1)

    def _on_move_down(self) -> None:
        """Farbe nach unten verschieben."""
        row = self._color_list.currentRow()
        if row < self._color_list.count() - 1:
            self._swap_colors(row, row + 1)
            self._color_list.setCurrentRow(row + 1)

    def _on_move_top(self) -> None:
        """Farbe an den Anfang verschieben."""
        row = self._color_list.currentRow()
        if row > 0:
            for i in range(row, 0, -1):
                self._swap_colors(i, i - 1)
            self._color_list.setCurrentRow(0)

    def _on_move_bottom(self) -> None:
        """Farbe an das Ende verschieben."""
        row = self._color_list.currentRow()
        count = self._color_list.count()
        if row < count - 1:
            for i in range(row, count - 1):
                self._swap_colors(i, i + 1)
            self._color_list.setCurrentRow(count - 1)

    def _swap_colors(self, index1: int, index2: int) -> None:
        """Tauscht zwei Farben."""
        entries = self._pattern.color_entries
        entries[index1], entries[index2] = entries[index2], entries[index1]

        # Indizes in Layern aktualisieren
        for layer in self._pattern.layer_stack:
            for y in range(self._pattern.height):
                for x in range(self._pattern.width):
                    color_index = layer.get_stitch(x, y)
                    if color_index == index1:
                        layer.set_stitch(x, y, index2)
                    elif color_index == index2:
                        layer.set_stitch(x, y, index1)

        # Backstitches
        for bs in self._pattern.backstitches:
            if bs.color_index == index1:
                bs.color_index = index2
            elif bs.color_index == index2:
                bs.color_index = index1

        self._populate_list()
        self._changes_made = True

    def _on_delete_color(self) -> None:
        """Ausgewählte Farbe(n) löschen."""
        selected = self._color_list.selectedItems()
        if not selected:
            return

        # Prüfen ob Farben verwendet werden
        used_colors = []
        for item in selected:
            if isinstance(item, ColorListItem) and item.entry.stitch_count > 0:
                used_colors.append(item.entry)

        if used_colors:
            names = ", ".join(e.thread.name for e in used_colors[:3])
            if len(used_colors) > 3:
                names += f" (+{len(used_colors) - 3} weitere)"

            reply = QMessageBox.warning(
                self,
                t("Farben in Verwendung"),
                f"Folgende Farben werden noch verwendet:\n{names}\n\n"
                + t("Beim Löschen werden alle Stiche mit diesen Farben entfernt.\nFortfahren?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Indizes sammeln (absteigend sortieren für korrektes Löschen)
        indices_to_remove = sorted(
            [item.index for item in selected if isinstance(item, ColorListItem)], reverse=True
        )

        for index in indices_to_remove:
            self._remove_color_at_index(index)

        self._populate_list()
        self._changes_made = True

    def _on_remove_unused(self) -> None:
        """Entfernt alle ungenutzten Farben."""
        unused_indices = [
            i for i, e in enumerate(self._pattern.color_entries) if e.stitch_count == 0
        ]

        if not unused_indices:
            QMessageBox.information(
                self, t("Keine ungenutzten Farben"), t("Alle Farben werden verwendet.")
            )
            return

        reply = QMessageBox.question(
            self,
            t("Ungenutzte Farben entfernen"),
            f"{len(unused_indices)} ungenutzte Farbe(n) gefunden.\nDiese jetzt entfernen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            for index in sorted(unused_indices, reverse=True):
                self._remove_color_at_index(index)

            self._populate_list()
            self._changes_made = True

            QMessageBox.information(self, t("Fertig"), f"{len(unused_indices)} Farbe(n) entfernt.")

    def _remove_color_at_index(self, index: int) -> None:
        """Entfernt eine Farbe und aktualisiert alle Referenzen."""
        # Stiche mit dieser Farbe komplett entfernen, höhere Farbindizes
        # um 1 nach unten verschieben (vektorisiert über numpy statt
        # Pixel-für-Pixel-Python-Schleife).
        for layer in self._pattern.layer_stack:
            layer.replace_color(index, NO_STITCH)
            layer.shift_color_indices(index + 1, -1)

        # Rückstiche mit dieser Farbe entfernen, höhere Indizes anpassen
        self._pattern.backstitch_manager.update_color_indices(index)

        # Farbe entfernen
        del self._pattern.color_entries[index]

        # Stichzahlen neu berechnen -- set_stitch()-Aufrufe in _on_merge_colors()
        # aktualisieren entry.stitch_count nicht selbst, daher hier zentral
        # aus dem tatsächlichen Grid-Inhalt neu ableiten.
        self._pattern.recalculate_stitch_counts()

    def _on_merge_colors(self) -> None:
        """Führt ausgewählte Farben zusammen."""
        selected = [
            item for item in self._color_list.selectedItems() if isinstance(item, ColorListItem)
        ]

        if len(selected) < 2:
            return

        # Die erste Farbe wird beibehalten
        target = selected[0]
        sources = selected[1:]

        source_names = ", ".join(s.entry.thread.name for s in sources[:3])
        if len(sources) > 3:
            source_names += f" (+{len(sources) - 3})"

        reply = QMessageBox.question(
            self,
            t("Farben zusammenführen"),
            f"Alle Stiche von:\n{source_names}\n\n"
            f"werden zu '{target.entry.thread.name}' konvertiert.\n"
            "Die Quellfarben werden danach gelöscht.\n\n"
            "Fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        target_index = target.index
        source_indices = sorted([s.index for s in sources], reverse=True)

        # Stiche umfärben
        for layer in self._pattern.layer_stack:
            for y in range(self._pattern.height):
                for x in range(self._pattern.width):
                    color_index = layer.get_stitch(x, y)
                    if color_index in source_indices:
                        layer.set_stitch(x, y, target_index)

        # Backstitches umfärben
        for bs in self._pattern.backstitches:
            if bs.color_index in source_indices:
                bs.color_index = target_index

        # Quellfarben entfernen
        for index in source_indices:
            self._remove_color_at_index(index)

        self._populate_list()
        self._changes_made = True

    def _on_reset(self) -> None:
        """Setzt alle Änderungen zurück."""
        reply = QMessageBox.question(
            self,
            t("Zurücksetzen"),
            t("Alle Änderungen verwerfen und zur ursprünglichen Reihenfolge zurückkehren?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._pattern.color_entries = list(self._original_entries)
            self._populate_list()
            self._sort_combo.setCurrentIndex(0)
            self._changes_made = False

    def _show_context_menu(self, pos) -> None:
        """Zeigt das Kontextmenü."""
        item = self._color_list.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)

        move_up = menu.addAction(t("⬆️ Nach oben"))
        move_down = menu.addAction(t("⬇️ Nach unten"))
        menu.addSeparator()
        move_top = menu.addAction(t("⏫ An den Anfang"))
        move_bottom = menu.addAction(t("⏬ An das Ende"))
        menu.addSeparator()
        delete = menu.addAction(t("🗑️ Löschen"))

        action = menu.exec(self._color_list.mapToGlobal(pos))

        if action == move_up:
            self._on_move_up()
        elif action == move_down:
            self._on_move_down()
        elif action == move_top:
            self._on_move_top()
        elif action == move_bottom:
            self._on_move_bottom()
        elif action == delete:
            self._on_delete_color()

    def has_changes(self) -> bool:
        """Gibt zurück ob Änderungen gemacht wurden."""
        return self._changes_made
