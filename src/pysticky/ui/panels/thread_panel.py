"""
Garn-Panel zur Farbverwaltung mit Paletten-Unterstützung.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...core import Thread, get_palette_manager
from ...core.i18n import t
from ..color_utils import color_swatch_icon, from_qcolor, to_qcolor


class ThreadPanel(QWidget):
    """
    Panel zur Verwaltung der Garnfarben.

    Features:
    - Aktuelle Musterfarben anzeigen/bearbeiten
    - Paletten durchsuchen (DMC, Madeira, etc.)
    - Farben aus Paletten zum Muster hinzufügen
    """

    thread_selected = Signal(int)  # Index der ausgewählten Farbe
    threads_changed = Signal(list)  # Liste der Threads

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._threads: list[Thread] = []
        self._palette_manager = get_palette_manager()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Erstellt die UI-Elemente."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Tab-Widget für Muster/Paletten
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Tab 1: Aktuelle Musterfarben
        pattern_tab = QWidget()
        self._setup_pattern_tab(pattern_tab)
        self.tab_widget.addTab(pattern_tab, t("Muster"))

        # Tab 2: Paletten-Browser
        palette_tab = QWidget()
        self._setup_palette_tab(palette_tab)
        self.tab_widget.addTab(palette_tab, t("Paletten"))

        self.setMinimumWidth(250)

    def _setup_pattern_tab(self, parent: QWidget) -> None:
        """Erstellt den Tab für Musterfarben."""
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 8, 0, 0)

        # Farbliste
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(4)

        self.btn_add = QPushButton("+")
        self.btn_add.setFixedSize(32, 32)
        self.btn_add.setToolTip(t("Farbe hinzufügen"))
        self.btn_add.clicked.connect(self._on_add_color)
        button_layout.addWidget(self.btn_add)

        self.btn_remove = QPushButton("−")
        self.btn_remove.setFixedSize(32, 32)
        self.btn_remove.setToolTip(t("Farbe entfernen"))
        self.btn_remove.clicked.connect(self._on_remove_color)
        button_layout.addWidget(self.btn_remove)

        self.btn_up = QPushButton("↑")
        self.btn_up.setFixedSize(32, 32)
        self.btn_up.setToolTip(t("Nach oben"))
        self.btn_up.clicked.connect(self._on_move_up)
        button_layout.addWidget(self.btn_up)

        self.btn_down = QPushButton("↓")
        self.btn_down.setFixedSize(32, 32)
        self.btn_down.setToolTip(t("Nach unten"))
        self.btn_down.clicked.connect(self._on_move_down)
        button_layout.addWidget(self.btn_down)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Info-Label
        self.label_info = QLabel("0 " + t("Farben"))
        self.label_info.setObjectName("subtitleLabel")
        layout.addWidget(self.label_info)

    def _setup_palette_tab(self, parent: QWidget) -> None:
        """Erstellt den Tab für Paletten-Browser."""
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 8, 0, 0)

        # Palette auswählen
        palette_row = QHBoxLayout()
        palette_row.addWidget(QLabel(t("Palette:")))

        self.palette_combo = QComboBox()
        self.palette_combo.addItem("Alle")
        for name in sorted(self._palette_manager.available_palettes):
            self.palette_combo.addItem(name)
        self.palette_combo.currentTextChanged.connect(self._on_palette_changed)
        palette_row.addWidget(self.palette_combo, 1)
        layout.addLayout(palette_row)

        # Suche
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel(t("Suche:")))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("Name oder Nummer..."))
        self.search_input.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self.search_input, 1)
        layout.addLayout(search_row)

        # Palette-Liste
        self.palette_list = QListWidget()
        self.palette_list.setAlternatingRowColors(True)
        self.palette_list.itemDoubleClicked.connect(self._on_palette_item_double_clicked)
        layout.addWidget(self.palette_list)

        # Hinzufügen-Button
        self.btn_add_from_palette = QPushButton(t("Zum Muster hinzufügen"))
        self.btn_add_from_palette.clicked.connect(self._on_add_from_palette)
        layout.addWidget(self.btn_add_from_palette)

        # Info
        self.palette_info = QLabel("")
        self.palette_info.setObjectName("subtitleLabel")
        layout.addWidget(self.palette_info)

        # Initial laden
        self._refresh_palette_list()

    def set_threads(self, threads: list[Thread]) -> None:
        """Setzt die Farbliste des Musters."""
        self._threads = threads
        self._update_list()

    def _update_list(self) -> None:
        """Aktualisiert die Muster-Farbliste."""
        self.list_widget.clear()

        for i, thread in enumerate(self._threads):
            item = QListWidgetItem()
            text = f"{i + 1}. {thread.name}"
            if thread.catalog_number:
                text += f" ({thread.catalog_number})"
            item.setText(text)
            item.setIcon(color_swatch_icon(thread.color, 16, border=False))
            item.setToolTip(f"{thread.manufacturer or 'Unbekannt'}\n{thread.color.to_hex()}")
            self.list_widget.addItem(item)

        self.label_info.setText(f"{len(self._threads)} Farbe(n)")

    def _refresh_palette_list(self) -> None:
        """Aktualisiert die Paletten-Liste basierend auf Auswahl und Suche."""
        self.palette_list.clear()

        selected_palette = self.palette_combo.currentText()
        search_text = self.search_input.text().lower().strip()

        threads_to_show: list[tuple[Thread, str]] = []  # (thread, palette_name)

        if selected_palette == "Alle":
            for name in self._palette_manager.available_palettes:
                palette = self._palette_manager.get_palette(name)
                if palette:
                    for thread in palette.threads:
                        threads_to_show.append((thread, name))
        else:
            palette = self._palette_manager.get_palette(selected_palette)
            if palette:
                for thread in palette.threads:
                    threads_to_show.append((thread, selected_palette))

        # Filter nach Suchtext
        if search_text:
            filtered = []
            for thread, pname in threads_to_show:
                if search_text in thread.name.lower() or (
                    thread.catalog_number and search_text in thread.catalog_number.lower()
                ):
                    filtered.append((thread, pname))
            threads_to_show = filtered

        # Maximal 500 anzeigen
        show_count = min(len(threads_to_show), 500)

        for thread, pname in threads_to_show[:show_count]:
            item = QListWidgetItem()
            text = thread.name
            if thread.catalog_number:
                text = f"{thread.catalog_number} - {text}"
            item.setText(text)
            item.setIcon(color_swatch_icon(thread.color, 16, border=False))
            item.setData(Qt.ItemDataRole.UserRole, thread)
            item.setToolTip(f"{pname}\n{thread.color.to_hex()}")
            self.palette_list.addItem(item)

        total = len(threads_to_show)
        if total > show_count:
            self.palette_info.setText(f"{show_count} von {total} Farben (Filter verwenden)")
        else:
            self.palette_info.setText(f"{total} Farben")

    # === Event-Handler für Muster-Tab ===

    def _on_selection_changed(self, index: int) -> None:
        if index >= 0:
            self.thread_selected.emit(index)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        index = self.list_widget.row(item)
        if 0 <= index < len(self._threads):
            self._edit_color(index)

    def _on_add_color(self) -> None:
        color = QColorDialog.getColor(QColor(128, 128, 128), self, t("Neue Garnfarbe wählen"))
        if color.isValid():
            thread = Thread(
                name=f"Farbe {len(self._threads) + 1}",
                color=from_qcolor(color),
            )
            self._threads.append(thread)
            self._update_list()
            self.threads_changed.emit(self._threads)

    def _on_remove_color(self) -> None:
        index = self.list_widget.currentRow()
        if 0 <= index < len(self._threads) and len(self._threads) > 1:
            del self._threads[index]
            self._update_list()
            self.threads_changed.emit(self._threads)

    def _on_move_up(self) -> None:
        index = self.list_widget.currentRow()
        if index > 0:
            self._threads[index], self._threads[index - 1] = (
                self._threads[index - 1],
                self._threads[index],
            )
            self._update_list()
            self.list_widget.setCurrentRow(index - 1)
            self.threads_changed.emit(self._threads)

    def _on_move_down(self) -> None:
        index = self.list_widget.currentRow()
        if 0 <= index < len(self._threads) - 1:
            self._threads[index], self._threads[index + 1] = (
                self._threads[index + 1],
                self._threads[index],
            )
            self._update_list()
            self.list_widget.setCurrentRow(index + 1)
            self.threads_changed.emit(self._threads)

    def _edit_color(self, index: int) -> None:
        thread = self._threads[index]
        current_color = to_qcolor(thread.color)

        color = QColorDialog.getColor(current_color, self, f"Farbe bearbeiten: {thread.name}")

        if color.isValid():
            self._threads[index] = Thread(
                name=thread.name,
                color=from_qcolor(color),
                manufacturer=thread.manufacturer,
                catalog_number=thread.catalog_number,
            )
            self._update_list()
            self.list_widget.setCurrentRow(index)
            self.threads_changed.emit(self._threads)

    # === Event-Handler für Paletten-Tab ===

    def _on_palette_changed(self, text: str) -> None:
        self._refresh_palette_list()

    def _on_search_changed(self, text: str) -> None:
        self._refresh_palette_list()

    def _on_palette_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Fügt Farbe bei Doppelklick zum Muster hinzu."""
        self._add_thread_from_item(item)

    def _on_add_from_palette(self) -> None:
        """Fügt ausgewählte Paletten-Farbe zum Muster hinzu."""
        item = self.palette_list.currentItem()
        if item:
            self._add_thread_from_item(item)

    def _add_thread_from_item(self, item: QListWidgetItem) -> None:
        """Fügt ein Thread aus einem ListWidgetItem zum Muster hinzu."""
        thread: Thread = item.data(Qt.ItemDataRole.UserRole)
        if thread:
            # Kopie erstellen
            new_thread = Thread(
                name=thread.name,
                color=thread.color,
                manufacturer=thread.manufacturer,
                catalog_number=thread.catalog_number,
            )
            self._threads.append(new_thread)
            self._update_list()
            self.threads_changed.emit(self._threads)

            # Zum Muster-Tab wechseln
            self.tab_widget.setCurrentIndex(0)
            self.list_widget.setCurrentRow(len(self._threads) - 1)
