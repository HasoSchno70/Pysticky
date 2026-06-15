"""
Garn-Vorratsliste-Dialog: User kann pro Hersteller-Farbe hinterlegen,
wieviele Straenge er noch im Schrank hat.

Datenquelle / -ziel: core.inventory.Inventory (JSON in App-Daten).

Zwei Tabs:
1. "Im Muster" — nur die Farben des aktuellen Musters (schneller Einstieg)
2. "Alle Eintraege" — komplette Vorratsliste mit Suchfeld, ohne Pattern-Bezug
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.inventory import Inventory
from ..styles import THEME
from .swap_colors_dialog import _color_icon

if TYPE_CHECKING:
    from ...core import Pattern


class InventoryDialog(QDialog):
    """Dialog zur Pflege der Garn-Vorratsliste."""

    def __init__(self, pattern: "Pattern", parent=None) -> None:
        super().__init__(parent)
        self._pattern = pattern
        self._inventory = Inventory()
        self._dirty = False

        self.setWindowTitle("Garn-Vorratsliste")
        self.setMinimumSize(680, 520)
        self._setup_ui()
        self._populate_pattern_tab()
        self._populate_all_tab()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        intro = QLabel(
            "Trage hier ein, wieviele Stränge du von jeder Farbe noch besitzt. "
            "Im Statistik-Dialog wird daraus automatisch eine Einkaufsliste "
            "für das aktuelle Muster berechnet."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {THEME.text_muted};")
        layout.addWidget(intro)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs, 1)

        # === Tab 1: Im Muster ===
        pattern_tab = QWidget()
        pl = QVBoxLayout(pattern_tab)
        pl.setContentsMargins(0, 8, 0, 0)

        self._pattern_table = QTableWidget()
        self._pattern_table.setColumnCount(5)
        self._pattern_table.setHorizontalHeaderLabels(
            ["", "Farbe", "Hersteller", "Nr.", "Bestand (Stränge)"]
        )
        self._pattern_table.verticalHeader().setVisible(False)
        self._pattern_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hdr = self._pattern_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._pattern_table.setColumnWidth(0, 30)
        pl.addWidget(self._pattern_table)
        self._tabs.addTab(pattern_tab, "Im Muster")

        # === Tab 2: Alle Eintraege ===
        all_tab = QWidget()
        al = QVBoxLayout(all_tab)
        al.setContentsMargins(0, 8, 0, 0)
        al.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 Hersteller oder Nr. suchen…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter_all_table)
        al.addWidget(self._search)

        self._all_table = QTableWidget()
        self._all_table.setColumnCount(3)
        self._all_table.setHorizontalHeaderLabels(["Hersteller", "Nr.", "Bestand (Stränge)"])
        self._all_table.verticalHeader().setVisible(False)
        self._all_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hdr2 = self._all_table.horizontalHeader()
        hdr2.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr2.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr2.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        al.addWidget(self._all_table, 1)

        bottom = QHBoxLayout()
        btn_remove_zero = QPushButton("Leere Einträge entfernen")
        btn_remove_zero.setToolTip("Eintraege mit 0 Straengen aus der Liste loeschen.")
        btn_remove_zero.clicked.connect(self._remove_zero_entries)
        bottom.addWidget(btn_remove_zero)
        bottom.addStretch(1)
        al.addLayout(bottom)

        self._tabs.addTab(all_tab, "Alle Einträge")

        # === Dialog-Buttons ===
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    # === Tab 1 Pattern ===

    def _populate_pattern_tab(self) -> None:
        entries = self._pattern.color_entries
        self._pattern_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            thread = entry.thread
            c = thread.color

            icon_item = QTableWidgetItem("")
            icon_item.setIcon(_color_icon(c.r, c.g, c.b, size=20))
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

            spin = QSpinBox()
            spin.setRange(0, 999)
            spin.setValue(self._inventory.get(thread.manufacturer, thread.catalog_number))
            spin.setSuffix(" Strang")
            spin.valueChanged.connect(lambda val, t=thread: self._on_pattern_value_changed(t, val))
            self._pattern_table.setCellWidget(row, 4, spin)

    def _on_pattern_value_changed(self, thread, value: int) -> None:
        self._inventory.set(thread.manufacturer, thread.catalog_number, value)
        self._dirty = True
        # Auch die "Alle"-Tabelle ggf. updaten
        self._refresh_all_table_for(thread.manufacturer, thread.catalog_number, value)

    # === Tab 2 Alle ===

    def _populate_all_tab(self) -> None:
        items = sorted(self._inventory.items(), key=lambda kv: kv[0])
        self._all_table.setRowCount(len(items))
        for row, (key, strands) in enumerate(items):
            mfr, num = (key.split("::", 1) + ["", ""])[:2]
            mfr_item = QTableWidgetItem(mfr)
            mfr_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._all_table.setItem(row, 0, mfr_item)

            num_item = QTableWidgetItem(num)
            num_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._all_table.setItem(row, 1, num_item)

            spin = QSpinBox()
            spin.setRange(0, 999)
            spin.setValue(strands)
            spin.setSuffix(" Strang")
            spin.valueChanged.connect(
                lambda val, m=mfr, n=num: self._on_all_value_changed(m, n, val)
            )
            self._all_table.setCellWidget(row, 2, spin)

    def _on_all_value_changed(self, mfr: str, num: str, value: int) -> None:
        self._inventory.set(mfr, num, value)
        self._dirty = True
        # Auch Tab 1 ggf. updaten
        for row in range(self._pattern_table.rowCount()):
            thread_mfr = self._pattern_table.item(row, 2).text()
            thread_num = self._pattern_table.item(row, 3).text()
            if thread_mfr == mfr and thread_num == num:
                spin = self._pattern_table.cellWidget(row, 4)
                if spin is not None and spin.value() != value:
                    spin.blockSignals(True)
                    spin.setValue(value)
                    spin.blockSignals(False)
                break

    def _refresh_all_table_for(self, mfr: str | None, num: str | None, value: int) -> None:
        target_mfr = (mfr or "unknown").strip()
        target_num = (num or "unknown").strip()
        for row in range(self._all_table.rowCount()):
            if (
                self._all_table.item(row, 0).text() == target_mfr
                and self._all_table.item(row, 1).text() == target_num
            ):
                spin = self._all_table.cellWidget(row, 2)
                if spin is not None and spin.value() != value:
                    spin.blockSignals(True)
                    spin.setValue(value)
                    spin.blockSignals(False)
                return
        # Nicht gefunden — neue Zeile anhaengen (nur wenn value > 0)
        if value > 0:
            row = self._all_table.rowCount()
            self._all_table.insertRow(row)
            mfr_item = QTableWidgetItem(target_mfr)
            mfr_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._all_table.setItem(row, 0, mfr_item)
            num_item = QTableWidgetItem(target_num)
            num_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._all_table.setItem(row, 1, num_item)
            spin = QSpinBox()
            spin.setRange(0, 999)
            spin.setValue(value)
            spin.setSuffix(" Strang")
            spin.valueChanged.connect(
                lambda val, m=target_mfr, n=target_num: self._on_all_value_changed(m, n, val)
            )
            self._all_table.setCellWidget(row, 2, spin)

    def _filter_all_table(self, query: str) -> None:
        q = query.strip().lower()
        for row in range(self._all_table.rowCount()):
            mfr = self._all_table.item(row, 0).text().lower()
            num = self._all_table.item(row, 1).text().lower()
            visible = (not q) or (q in mfr) or (q in num)
            self._all_table.setRowHidden(row, not visible)

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

    def _on_save(self) -> None:
        self._inventory.save()
        self.accept()

    def reject(self) -> None:
        if self._dirty:
            reply = QMessageBox.question(
                self,
                "Änderungen verwerfen?",
                "Es gibt ungespeicherte Änderungen. Wirklich verwerfen?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        super().reject()
