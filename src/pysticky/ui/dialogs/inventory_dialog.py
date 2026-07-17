"""
Garn-Vorratsliste-Dialog: User kann pro Hersteller-Farbe hinterlegen,
wieviele Stränge er noch im Schrank hat.

Datenquelle / -ziel: core.inventory.Inventory (JSON in App-Daten).

Drei Tabs:
1. "Im Muster" — nur die Farben des aktuellen Musters (schneller Einstieg)
2. "Alle Einträge" — komplette Vorratsliste mit Suchfeld, ohne Pattern-Bezug
3. "Mehrere Projekte" — registrierte .pxs-Dateien + kombinierte Einkaufsliste
   über alle registrierten Projekte hinweg (core.project_list.ProjectList)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import t
from ...core.inventory import Inventory, compute_shopping_list, compute_shopping_list_multi
from ...core.project_list import ProjectList
from ..color_utils import color_swatch_icon
from ..styles import THEME

PATTERN_SWATCH_SIZE = 26

if TYPE_CHECKING:
    from ...core import Pattern


class InventoryDialog(QDialog):
    """Dialog zur Pflege der Garn-Vorratsliste."""

    def __init__(self, pattern: "Pattern", parent=None, current_file: Path | None = None) -> None:
        super().__init__(parent)
        self._pattern = pattern
        self._current_file = current_file
        self._inventory = Inventory()
        self._project_list = ProjectList()
        self._dirty = False

        self.setWindowTitle(t("Garn-Vorratsliste"))
        self.setMinimumSize(680, 520)
        self._setup_ui()
        self._populate_pattern_tab()
        self._populate_all_tab()
        self._populate_projects_tab()

    def _style_table(self, table: QTableWidget) -> None:
        """Etwas mehr visuelle Ruhe/Kontrast als das nackte Standard-Theme:
        Zebra-Streifen + farbig abgesetzter Header statt einheitlichem Grau."""
        table.setStyleSheet(f"""
            QTableWidget {{
                alternate-background-color: {THEME.bg_medium};
                gridline-color: {THEME.border_medium};
            }}
            QHeaderView::section {{
                background: {THEME.bg_light};
                color: {THEME.accent_primary};
                font-weight: 600;
                padding: 4px;
                border: none;
                border-bottom: 2px solid {THEME.accent_primary};
            }}
        """)

    def _make_intro_card(self, text: str, accent: str) -> QFrame:
        """Info-Karte mit farbigem Akzentrand statt schlichtem grauen Text —
        gleiches Muster wie der Detail-Frame im Snapshot-Verlauf-Dialog."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_medium};
                border: 1px solid {THEME.border_medium};
                border-left: 3px solid {accent};
                border-radius: 6px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {THEME.text_secondary}; border: none;")
        card_layout.addWidget(label)
        return card

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        intro = self._make_intro_card(
            t(
                "Trage hier ein, wieviele Stränge du von jeder Farbe noch besitzt. "
                "„Benötigt“ und „Zu kaufen“ zeigen direkt, wie viel das aktuelle "
                "Muster braucht — die gleiche Rechnung wie im Statistik-Dialog."
            ),
            THEME.accent_primary,
        )
        layout.addWidget(intro)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        layout.addWidget(self._tabs, 1)

        # === Tab 1: Im Muster ===
        pattern_tab = QWidget()
        pl = QVBoxLayout(pattern_tab)
        pl.setContentsMargins(0, 8, 0, 0)

        self._pattern_table = QTableWidget()
        self._pattern_table.setColumnCount(7)
        self._pattern_table.setHorizontalHeaderLabels(
            [
                "",
                t("Farbe"),
                t("Hersteller"),
                t("Nr."),
                t("Benötigt"),
                t("Bestand (Stränge)"),
                t("Zu kaufen"),
            ]
        )
        self._pattern_table.verticalHeader().setVisible(False)
        self._pattern_table.verticalHeader().setDefaultSectionSize(36)
        self._pattern_table.setIconSize(QSize(PATTERN_SWATCH_SIZE, PATTERN_SWATCH_SIZE))
        self._pattern_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._pattern_table.setAlternatingRowColors(True)
        self._style_table(self._pattern_table)
        hdr = self._pattern_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in (2, 3, 4, 5, 6):
            hdr.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self._pattern_table.setColumnWidth(0, PATTERN_SWATCH_SIZE + 12)
        pl.addWidget(self._pattern_table)
        self._tabs.addTab(pattern_tab, "🧵 " + t("Im Muster"))

        # === Tab 2: Alle Einträge ===
        all_tab = QWidget()
        al = QVBoxLayout(all_tab)
        al.setContentsMargins(0, 8, 0, 0)
        al.setSpacing(8)

        all_intro = self._make_intro_card(
            t(
                "Dein kompletter Garn-Vorrat, unabhängig vom gerade geöffneten Muster. "
                "Farben aus dem aktuellen Muster landen hier automatisch, sobald du im "
                "Tab „Im Muster“ einen Bestand einträgst. Vorrat für Farben, die du "
                "noch in keinem Muster benutzt hast, kannst du unten manuell hinzufügen."
            ),
            THEME.accent_secondary,
        )
        al.addWidget(all_intro)

        self._search = QLineEdit()
        self._search.setPlaceholderText(t("🔍 Hersteller oder Nr. suchen…"))
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter_all_table)
        al.addWidget(self._search)

        self._all_table = QTableWidget()
        self._all_table.setColumnCount(4)
        self._all_table.setHorizontalHeaderLabels(
            ["", t("Hersteller"), t("Nr."), t("Bestand (Stränge)")]
        )
        self._all_table.verticalHeader().setVisible(False)
        self._all_table.verticalHeader().setDefaultSectionSize(34)
        self._all_table.setIconSize(QSize(PATTERN_SWATCH_SIZE, PATTERN_SWATCH_SIZE))
        self._all_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._all_table.setAlternatingRowColors(True)
        self._style_table(self._all_table)
        hdr2 = self._all_table.horizontalHeader()
        hdr2.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr2.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr2.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr2.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._all_table.setColumnWidth(0, PATTERN_SWATCH_SIZE + 12)
        al.addWidget(self._all_table, 1)

        bottom = QHBoxLayout()
        btn_add_entry = QPushButton(t("➕ Farbe hinzufügen…"))
        btn_add_entry.setToolTip(
            t("Vorrat für eine Farbe eintragen, die noch in keinem Muster vorkommt.")
        )
        btn_add_entry.setStyleSheet(f"""
            QPushButton {{
                background: {THEME.accent_primary};
                color: {THEME.bg_dark};
                font-weight: 600;
                border-radius: 5px;
                padding: 5px 12px;
            }}
            QPushButton:hover {{ background: {THEME.accent_secondary}; }}
        """)
        btn_add_entry.clicked.connect(self._add_manual_entry)
        bottom.addWidget(btn_add_entry)
        btn_remove_zero = QPushButton(t("🗑 Leere Einträge entfernen"))
        btn_remove_zero.setToolTip(t("Einträge mit 0 Strängen aus der Liste loeschen."))
        btn_remove_zero.clicked.connect(self._remove_zero_entries)
        bottom.addWidget(btn_remove_zero)
        bottom.addStretch(1)
        al.addLayout(bottom)

        self._tabs.addTab(all_tab, "📋 " + t("Alle Einträge"))

        # === Tab 3: Mehrere Projekte ===
        projects_tab = QWidget()
        prl = QVBoxLayout(projects_tab)
        prl.setContentsMargins(0, 8, 0, 0)
        prl.setSpacing(8)

        projects_intro = self._make_intro_card(
            t(
                "Registriere hier deine aktuell laufenden Projekte (.pxs-Dateien). "
                "Darunter siehst du eine kombinierte Einkaufsliste über alle "
                "registrierten Projekte hinweg, verglichen mit deinem Vorrat."
            ),
            THEME.accent_purple,
        )
        prl.addWidget(projects_intro)

        self._project_listwidget = QListWidget()
        self._project_listwidget.setMaximumHeight(120)
        prl.addWidget(self._project_listwidget)

        project_buttons = QHBoxLayout()
        btn_add_project = QPushButton(t("➕ Muster hinzufügen…"))
        btn_add_project.clicked.connect(self._add_project_file)
        project_buttons.addWidget(btn_add_project)

        self._btn_add_current = QPushButton(t("📌 Aktuelles Muster hinzufügen"))
        self._btn_add_current.clicked.connect(self._add_current_pattern)
        self._btn_add_current.setEnabled(self._current_file is not None)
        project_buttons.addWidget(self._btn_add_current)

        btn_remove_project = QPushButton(t("✖ Entfernen"))
        btn_remove_project.clicked.connect(self._remove_selected_project)
        project_buttons.addWidget(btn_remove_project)

        project_buttons.addStretch(1)
        prl.addLayout(project_buttons)

        self._projects_warning = QLabel("")
        self._projects_warning.setWordWrap(True)
        self._projects_warning.setStyleSheet(f"color: {THEME.warning};")
        self._projects_warning.hide()
        prl.addWidget(self._projects_warning)

        self._multi_shopping_table = QTableWidget()
        self._multi_shopping_table.setColumnCount(5)
        self._multi_shopping_table.setHorizontalHeaderLabels(
            ["", t("Farbe"), t("Nr."), t("Benötigt"), t("Zu kaufen")]
        )
        self._multi_shopping_table.verticalHeader().setVisible(False)
        self._multi_shopping_table.verticalHeader().setDefaultSectionSize(34)
        self._multi_shopping_table.setIconSize(QSize(PATTERN_SWATCH_SIZE, PATTERN_SWATCH_SIZE))
        self._multi_shopping_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._multi_shopping_table.setAlternatingRowColors(True)
        self._style_table(self._multi_shopping_table)
        mhdr = self._multi_shopping_table.horizontalHeader()
        mhdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        mhdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in (2, 3, 4):
            mhdr.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self._multi_shopping_table.setColumnWidth(0, PATTERN_SWATCH_SIZE + 12)
        prl.addWidget(self._multi_shopping_table, 1)

        self._multi_summary = QLabel("")
        self._multi_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._multi_summary.setStyleSheet(f"font-size: 13px; padding: 6px; color: {THEME.error};")
        prl.addWidget(self._multi_summary)

        self._tabs.addTab(projects_tab, "📁 " + t("Mehrere Projekte"))

        # === Dialog-Buttons ===
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    # === Tab 1 Pattern ===

    def _populate_pattern_tab(self) -> None:
        from .statistics_tabs import STITCHES_PER_SKEIN

        entries = self._pattern.color_entries
        needed_by_key = {
            (item["thread"].manufacturer, item["thread"].catalog_number): item["needed_skeins"]
            for item in compute_shopping_list(self._pattern, self._inventory, STITCHES_PER_SKEIN)
        }

        self._pattern_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            thread = entry.thread
            c = thread.color
            needed = needed_by_key.get((thread.manufacturer, thread.catalog_number), 0)

            icon_item = QTableWidgetItem("")
            icon_item.setIcon(color_swatch_icon(c, PATTERN_SWATCH_SIZE))
            icon_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._pattern_table.setItem(row, 0, icon_item)

            name_item = QTableWidgetItem(thread.name)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._pattern_table.setItem(row, 1, name_item)

            mfr_item = QTableWidgetItem(thread.manufacturer or "")
            mfr_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._pattern_table.setItem(row, 2, mfr_item)

            num_item = QTableWidgetItem(thread.catalog_number or "")
            num_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._pattern_table.setItem(row, 3, num_item)

            needed_item = QTableWidgetItem(str(needed) if needed else "–")
            needed_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            needed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._pattern_table.setItem(row, 4, needed_item)

            on_hand = self._inventory.get(thread.manufacturer, thread.catalog_number)
            spin = QSpinBox()
            spin.setRange(0, 999)
            spin.setValue(on_hand)
            spin.setSuffix(t(" Strang"))
            spin.valueChanged.connect(lambda val, t=thread: self._on_pattern_value_changed(t, val))
            self._pattern_table.setCellWidget(row, 5, spin)

            self._set_pattern_to_buy_cell(row, needed, on_hand)

    def _set_pattern_to_buy_cell(self, row: int, needed: int, on_hand: int) -> None:
        """Setzt/aktualisiert die "Zu kaufen"-Zelle (Spalte 6) farblich."""
        to_buy = max(0, needed - on_hand)
        item = QTableWidgetItem(str(to_buy) if needed else "–")
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if to_buy > 0:
            item.setForeground(QColor(THEME.error))
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        elif needed:
            item.setForeground(QColor(THEME.accent_primary))
        self._pattern_table.setItem(row, 6, item)

    def _on_pattern_value_changed(self, thread, value: int) -> None:
        self._inventory.set(thread.manufacturer, thread.catalog_number, value)
        self._dirty = True
        # "Zu kaufen"-Spalte für diese Zeile neu einfärben, ohne die
        # komplette Einkaufsliste neu zu berechnen.
        for row in range(self._pattern_table.rowCount()):
            if self._pattern_table.item(row, 2).text() == (
                thread.manufacturer or ""
            ) and self._pattern_table.item(row, 3).text() == (thread.catalog_number or ""):
                needed_text = self._pattern_table.item(row, 4).text()
                needed = 0 if needed_text == "–" else int(needed_text)
                self._set_pattern_to_buy_cell(row, needed, value)
                break
        # Auch die "Alle"-Tabelle ggf. updaten
        self._refresh_all_table_for(thread.manufacturer, thread.catalog_number, value)

    # === Tab 2 Alle ===

    def _swatch_icon_for(self, mfr: str, num: str) -> QIcon:
        """Farbquadrat aus der passenden Palette, sonst neutraler Platzhalter
        (z.B. bei manuell getipptem Hersteller/Nr. ohne bekannte Palette)."""
        from ...core.palette import get_palette_manager

        palette = get_palette_manager().get_palette(mfr)
        thread = palette.find_by_number(num) if palette is not None else None
        if thread is not None:
            c = thread.color
            return QIcon(color_swatch_icon(c, PATTERN_SWATCH_SIZE))
        return self._unknown_swatch_icon()

    def _unknown_swatch_icon(self) -> QIcon:
        size = PATTERN_SWATCH_SIZE
        pm = QPixmap(size, size)
        pm.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(1, 1, size - 2, size - 2, QColor(THEME.bg_lighter))
        painter.setPen(QColor(THEME.border_medium))
        painter.drawRect(0, 0, size - 1, size - 1)
        font = painter.font()
        font.setBold(True)
        font.setPointSize(max(7, size // 3))
        painter.setFont(font)
        painter.setPen(QColor(THEME.text_muted))
        painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "?")
        painter.end()
        return QIcon(pm)

    def _populate_all_tab(self) -> None:
        items = sorted(self._inventory.items(), key=lambda kv: kv[0])
        self._all_table.setRowCount(len(items))
        for row, (key, strands) in enumerate(items):
            mfr, num = (key.split("::", 1) + ["", ""])[:2]

            icon_item = QTableWidgetItem("")
            icon_item.setIcon(self._swatch_icon_for(mfr, num))
            icon_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._all_table.setItem(row, 0, icon_item)

            mfr_item = QTableWidgetItem(mfr)
            mfr_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._all_table.setItem(row, 1, mfr_item)

            num_item = QTableWidgetItem(num)
            num_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._all_table.setItem(row, 2, num_item)

            spin = QSpinBox()
            spin.setRange(0, 999)
            spin.setValue(strands)
            spin.setSuffix(t(" Strang"))
            spin.valueChanged.connect(
                lambda val, m=mfr, n=num: self._on_all_value_changed(m, n, val)
            )
            self._all_table.setCellWidget(row, 3, spin)

    def _on_all_value_changed(self, mfr: str, num: str, value: int) -> None:
        self._inventory.set(mfr, num, value)
        self._dirty = True
        # Auch Tab 1 ggf. updaten
        for row in range(self._pattern_table.rowCount()):
            thread_mfr = self._pattern_table.item(row, 2).text()
            thread_num = self._pattern_table.item(row, 3).text()
            if thread_mfr == mfr and thread_num == num:
                spin = self._pattern_table.cellWidget(row, 5)
                if spin is not None and spin.value() != value:
                    spin.blockSignals(True)
                    spin.setValue(value)
                    spin.blockSignals(False)
                    needed_text = self._pattern_table.item(row, 4).text()
                    needed = 0 if needed_text == "–" else int(needed_text)
                    self._set_pattern_to_buy_cell(row, needed, value)
                break

    def _refresh_all_table_for(self, mfr: str | None, num: str | None, value: int) -> None:
        target_mfr = (mfr or "unknown").strip()
        target_num = (num or "unknown").strip()
        for row in range(self._all_table.rowCount()):
            if (
                self._all_table.item(row, 1).text() == target_mfr
                and self._all_table.item(row, 2).text() == target_num
            ):
                spin = self._all_table.cellWidget(row, 3)
                if spin is not None and spin.value() != value:
                    spin.blockSignals(True)
                    spin.setValue(value)
                    spin.blockSignals(False)
                return
        # Nicht gefunden — neue Zeile anhängen (nur wenn value > 0)
        if value > 0:
            row = self._all_table.rowCount()
            self._all_table.insertRow(row)
            icon_item = QTableWidgetItem("")
            icon_item.setIcon(self._swatch_icon_for(target_mfr, target_num))
            icon_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._all_table.setItem(row, 0, icon_item)
            mfr_item = QTableWidgetItem(target_mfr)
            mfr_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._all_table.setItem(row, 1, mfr_item)
            num_item = QTableWidgetItem(target_num)
            num_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._all_table.setItem(row, 2, num_item)
            spin = QSpinBox()
            spin.setRange(0, 999)
            spin.setValue(value)
            spin.setSuffix(t(" Strang"))
            spin.valueChanged.connect(
                lambda val, m=target_mfr, n=target_num: self._on_all_value_changed(m, n, val)
            )
            self._all_table.setCellWidget(row, 3, spin)

    def _filter_all_table(self, query: str) -> None:
        q = query.strip().lower()
        for row in range(self._all_table.rowCount()):
            mfr = self._all_table.item(row, 1).text().lower()
            num = self._all_table.item(row, 2).text().lower()
            visible = (not q) or (q in mfr) or (q in num)
            self._all_table.setRowHidden(row, not visible)

    def _add_manual_entry(self) -> None:
        """Trägt Vorrat für eine Farbe ein, die noch in keinem Muster vorkommt.

        Ohne dies wäre "Alle Einträge" reiner Lesemodus: Einträge
        entstehen sonst nur indirekt über den "Im Muster"-Tab, wenn ein
        Bestand > 0 gesetzt wird.

        Hersteller ist eine Auswahlliste aus den geladenen Paletten (DMC,
        Anchor, ...) — Garn von anderen Herstellern ist selten, daher bleibt
        das Feld editierbar für den Ausnahmefall. Ist der Hersteller
        erkannt, kann die Farbe direkt aus der Palette gewählt werden statt
        die Katalognummer selbst nachschlagen zu müssen.
        """
        from ...core.palette import get_palette_manager

        palette_mgr = get_palette_manager()
        known_mfrs = sorted(
            set(palette_mgr.available_palettes)
            | {(k.split("::", 1) + [""])[0] for k, _ in self._inventory.items()}
        )

        dlg = QDialog(self)
        dlg.setWindowTitle(t("Farbe hinzufügen"))
        form = QVBoxLayout(dlg)

        mfr_row = QHBoxLayout()
        mfr_row.addWidget(QLabel(t("Hersteller:")))
        mfr_combo = QComboBox()
        mfr_combo.setEditable(True)
        mfr_combo.addItems(known_mfrs)
        mfr_combo.setCurrentIndex(-1)
        mfr_row.addWidget(mfr_combo, 1)
        form.addLayout(mfr_row)

        color_row = QHBoxLayout()
        color_row.addWidget(QLabel(t("Farbe:")))
        color_combo = QComboBox()
        color_combo.setEnabled(False)
        color_combo.setToolTip(t("Verfuegbar, sobald ein bekannter Hersteller gewählt ist."))
        color_row.addWidget(color_combo, 1)
        form.addLayout(color_row)

        num_row = QHBoxLayout()
        num_row.addWidget(QLabel(t("Nr.:")))
        num_edit = QLineEdit()
        num_edit.setToolTip(t("Wird beim Waehlen einer Farbe automatisch ausgefüllt."))
        num_row.addWidget(num_edit, 1)
        form.addLayout(num_row)

        stock_row = QHBoxLayout()
        stock_row.addWidget(QLabel(t("Bestand:")))
        stock_spin = QSpinBox()
        stock_spin.setRange(0, 999)
        stock_spin.setSuffix(t(" Strang"))
        stock_row.addWidget(stock_spin, 1)
        form.addLayout(stock_row)

        def _find_palette_ci(name: str):
            name = name.strip()
            for mfr_name in known_mfrs:
                if mfr_name.lower() == name.lower():
                    palette = palette_mgr.get_palette(mfr_name)
                    if palette is not None:
                        return palette
            return None

        def _on_mfr_changed(text: str) -> None:
            palette = _find_palette_ci(text)
            color_combo.blockSignals(True)
            color_combo.clear()
            if palette is not None:
                for thread in sorted(palette.threads, key=lambda th: th.catalog_number or ""):
                    c = thread.color
                    color_combo.addItem(
                        QIcon(color_swatch_icon(c, 16)),
                        f"{thread.catalog_number or '?'} — {thread.name}",
                        thread,
                    )
            color_combo.setEnabled(palette is not None)
            color_combo.setCurrentIndex(-1)
            color_combo.blockSignals(False)

        def _on_color_selected(index: int) -> None:
            thread = color_combo.itemData(index)
            if thread is not None:
                num_edit.setText(thread.catalog_number or "")

        mfr_combo.currentTextChanged.connect(_on_mfr_changed)
        color_combo.currentIndexChanged.connect(_on_color_selected)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        mfr = mfr_combo.currentText().strip()
        num = num_edit.text().strip()
        if not mfr and not num:
            return
        self._inventory.set(mfr, num, stock_spin.value())
        self._dirty = True
        self._populate_all_tab()
        self._populate_pattern_tab()

    def _remove_zero_entries(self) -> None:
        # Sammle alle Keys mit Value 0
        to_remove: list[tuple[str, str]] = []
        for key, val in self._inventory.items():
            if val <= 0:
                mfr, num = (key.split("::", 1) + ["", ""])[:2]
                to_remove.append((mfr, num))
        for mfr, num in to_remove:
            self._inventory.set(mfr, num, 0)
        # Tabellen neu aufbauen
        self._populate_all_tab()
        self._dirty = True

    # === Tab 3 Mehrere Projekte ===

    def _populate_projects_tab(self) -> None:
        self._project_listwidget.clear()
        for path in self._project_list.items():
            item = QListWidgetItem(Path(path).name)
            item.setToolTip(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self._project_listwidget.addItem(item)
        self._refresh_multi_shopping()

    def _add_project_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("Muster hinzufügen"), "", t("PySticky-Muster (*.pxs)")
        )
        if not path:
            return
        if self._project_list.add(path):
            self._dirty = True
            self._populate_projects_tab()

    def _add_current_pattern(self) -> None:
        if self._current_file is None:
            return
        if self._project_list.add(self._current_file):
            self._dirty = True
            self._populate_projects_tab()

    def _remove_selected_project(self) -> None:
        item = self._project_listwidget.currentItem()
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        self._project_list.remove(path)
        self._dirty = True
        self._populate_projects_tab()

    def _refresh_multi_shopping(self) -> None:
        """Lädt alle registrierten Projekte und berechnet die kombinierte
        Einkaufsliste. Dateien, die nicht geladen werden können (gelöscht,
        verschoben, beschädigt), werden übersprungen und aufgelistet."""
        from ...core import load_pattern
        from .statistics_tabs import STITCHES_PER_SKEIN

        patterns = []
        failed: list[str] = []
        for path in self._project_list.items():
            try:
                patterns.append(load_pattern(path))
            except (OSError, ValueError) as e:
                failed.append(f"{Path(path).name}: {e}")

        if failed:
            self._projects_warning.setText(t("⚠ Nicht ladbar: ") + " · ".join(failed))
            self._projects_warning.show()
        else:
            self._projects_warning.hide()

        if not patterns:
            self._multi_shopping_table.setRowCount(0)
            self._multi_summary.setText("")
            return

        items = compute_shopping_list_multi(patterns, self._inventory, STITCHES_PER_SKEIN)

        self._multi_shopping_table.setRowCount(len(items))
        total_to_buy = 0
        for row, item in enumerate(items):
            thread = item["thread"]
            c = thread.color
            icon = QTableWidgetItem("")
            icon.setIcon(color_swatch_icon(c, PATTERN_SWATCH_SIZE))
            self._multi_shopping_table.setItem(row, 0, icon)
            self._multi_shopping_table.setItem(row, 1, QTableWidgetItem(thread.name))
            self._multi_shopping_table.setItem(
                row, 2, QTableWidgetItem(thread.catalog_number or "")
            )
            self._multi_shopping_table.setItem(row, 3, QTableWidgetItem(f"{item['needed_skeins']}"))
            to_buy_item = QTableWidgetItem(f"{item['to_buy']}")
            if item["to_buy"] > 0:
                to_buy_item.setForeground(QColor(THEME.error))
                font = to_buy_item.font()
                font.setBold(True)
                to_buy_item.setFont(font)
                total_to_buy += item["to_buy"]
            else:
                to_buy_item.setForeground(QColor(THEME.accent_primary))
            self._multi_shopping_table.setItem(row, 4, to_buy_item)

        if total_to_buy > 0:
            self._multi_summary.setStyleSheet(
                f"font-size: 13px; padding: 6px; color: {THEME.error};"
            )
            self._multi_summary.setText(
                f"<b>{total_to_buy}</b> " + t("Stränge insgesamt zu kaufen")
            )
        else:
            self._multi_summary.setStyleSheet(
                f"font-size: 13px; padding: 6px; color: {THEME.success};"
            )
            self._multi_summary.setText(t("✓ Du hast alles im Vorrat!"))

    def _on_save(self) -> None:
        self._inventory.save()
        self._project_list.save()
        self.accept()

    def reject(self) -> None:
        if self._dirty:
            reply = QMessageBox.question(
                self,
                t("Änderungen verwerfen?"),
                t("Es gibt ungespeicherte Änderungen. Wirklich verwerfen?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        super().reject()
