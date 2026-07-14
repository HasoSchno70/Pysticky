"""
Garn-Vorratsliste-Dialog: User kann pro Hersteller-Farbe hinterlegen,
wieviele Straenge er noch im Schrank hat.

Datenquelle / -ziel: core.inventory.Inventory (JSON in App-Daten).

Drei Tabs:
1. "Im Muster" — nur die Farben des aktuellen Musters (schneller Einstieg)
2. "Alle Eintraege" — komplette Vorratsliste mit Suchfeld, ohne Pattern-Bezug
3. "Mehrere Projekte" — registrierte .pxs-Dateien + kombinierte Einkaufsliste
   ueber alle registrierten Projekte hinweg (core.project_list.ProjectList)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
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
from ...core.inventory import Inventory, compute_shopping_list_multi
from ...core.project_list import ProjectList
from ..styles import THEME
from .swap_colors_dialog import _color_icon

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

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        intro = QLabel(
            t(
                "Trage hier ein, wieviele Stränge du von jeder Farbe noch besitzt. "
                "Im Statistik-Dialog wird daraus automatisch eine Einkaufsliste "
                "für das aktuelle Muster berechnet."
            )
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
            ["", t("Farbe"), t("Hersteller"), t("Nr."), t("Bestand (Stränge)")]
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
        self._tabs.addTab(pattern_tab, t("Im Muster"))

        # === Tab 2: Alle Eintraege ===
        all_tab = QWidget()
        al = QVBoxLayout(all_tab)
        al.setContentsMargins(0, 8, 0, 0)
        al.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText(t("🔍 Hersteller oder Nr. suchen…"))
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter_all_table)
        al.addWidget(self._search)

        self._all_table = QTableWidget()
        self._all_table.setColumnCount(3)
        self._all_table.setHorizontalHeaderLabels(
            [t("Hersteller"), t("Nr."), t("Bestand (Stränge)")]
        )
        self._all_table.verticalHeader().setVisible(False)
        self._all_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hdr2 = self._all_table.horizontalHeader()
        hdr2.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr2.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr2.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        al.addWidget(self._all_table, 1)

        bottom = QHBoxLayout()
        btn_remove_zero = QPushButton(t("Leere Einträge entfernen"))
        btn_remove_zero.setToolTip(t("Eintraege mit 0 Straengen aus der Liste loeschen."))
        btn_remove_zero.clicked.connect(self._remove_zero_entries)
        bottom.addWidget(btn_remove_zero)
        bottom.addStretch(1)
        al.addLayout(bottom)

        self._tabs.addTab(all_tab, t("Alle Einträge"))

        # === Tab 3: Mehrere Projekte ===
        projects_tab = QWidget()
        prl = QVBoxLayout(projects_tab)
        prl.setContentsMargins(0, 8, 0, 0)
        prl.setSpacing(8)

        projects_intro = QLabel(
            t(
                "Registriere hier deine aktuell laufenden Projekte (.pxs-Dateien). "
                "Darunter siehst du eine kombinierte Einkaufsliste über alle "
                "registrierten Projekte hinweg, verglichen mit deinem Vorrat."
            )
        )
        projects_intro.setWordWrap(True)
        projects_intro.setStyleSheet(f"color: {THEME.text_muted};")
        prl.addWidget(projects_intro)

        self._project_listwidget = QListWidget()
        self._project_listwidget.setMaximumHeight(120)
        prl.addWidget(self._project_listwidget)

        project_buttons = QHBoxLayout()
        btn_add_project = QPushButton(t("+ Muster hinzufügen…"))
        btn_add_project.clicked.connect(self._add_project_file)
        project_buttons.addWidget(btn_add_project)

        self._btn_add_current = QPushButton(t("Aktuelles Muster hinzufügen"))
        self._btn_add_current.clicked.connect(self._add_current_pattern)
        self._btn_add_current.setEnabled(self._current_file is not None)
        project_buttons.addWidget(self._btn_add_current)

        btn_remove_project = QPushButton(t("Entfernen"))
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
        self._multi_shopping_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        mhdr = self._multi_shopping_table.horizontalHeader()
        mhdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        mhdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in (2, 3, 4):
            mhdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._multi_shopping_table.setColumnWidth(0, 28)
        prl.addWidget(self._multi_shopping_table, 1)

        self._multi_summary = QLabel("")
        self._multi_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._multi_summary.setStyleSheet(f"font-size: 13px; padding: 6px; color: {THEME.error};")
        prl.addWidget(self._multi_summary)

        self._tabs.addTab(projects_tab, t("Mehrere Projekte"))

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
            spin.setSuffix(t(" Strang"))
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
            spin.setSuffix(t(" Strang"))
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
            spin.setSuffix(t(" Strang"))
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
        """Laedt alle registrierten Projekte und berechnet die kombinierte
        Einkaufsliste. Dateien, die nicht geladen werden koennen (geloescht,
        verschoben, beschaedigt), werden uebersprungen und aufgelistet."""
        from ...core import load_pattern
        from .statistics_dialog import PatternStatisticsDialog

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

        items = compute_shopping_list_multi(
            patterns, self._inventory, PatternStatisticsDialog.STITCHES_PER_SKEIN
        )

        self._multi_shopping_table.setRowCount(len(items))
        total_to_buy = 0
        for row, item in enumerate(items):
            thread = item["thread"]
            c = thread.color
            icon = QTableWidgetItem("")
            icon.setIcon(_color_icon(c.r, c.g, c.b, size=18))
            self._multi_shopping_table.setItem(row, 0, icon)
            self._multi_shopping_table.setItem(row, 1, QTableWidgetItem(thread.name))
            self._multi_shopping_table.setItem(
                row, 2, QTableWidgetItem(thread.catalog_number or "")
            )
            self._multi_shopping_table.setItem(row, 3, QTableWidgetItem(f"{item['needed_skeins']}"))
            to_buy_item = QTableWidgetItem(f"{item['to_buy']}")
            if item["to_buy"] > 0:
                to_buy_item.setForeground(QColor(THEME.error))
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
