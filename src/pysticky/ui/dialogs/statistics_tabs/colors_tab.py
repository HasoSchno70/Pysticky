"""
Farben-Details-Tab für den Statistik-Dialog.
"""

from typing import TYPE_CHECKING

from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ....core.i18n import t
from ...styles import THEME
from ._table_helpers import color_swatch_item, sortable_count_item, sortable_percent_item

if TYPE_CHECKING:
    from ....core import Pattern


class ColorsTab(QWidget):
    """Tab: Detail-Tabelle aller Farben mit Stichzahl und Prozentanteil."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Tabelle
        self._colors_table = QTableWidget()
        self._colors_table.setColumnCount(7)
        self._colors_table.setHorizontalHeaderLabels(
            [
                t("Farbe"),
                t("Symbol"),
                t("Name"),
                t("Hersteller"),
                t("Nr."),
                t("Stiche"),
                "%",
            ]
        )
        self._colors_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._colors_table.setAlternatingRowColors(True)
        self._colors_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._colors_table.setSortingEnabled(True)

        layout.addWidget(self._colors_table)

    def update_stats(self, pattern: "Pattern", stats: dict) -> None:
        """Füllt die Farben-Tabelle."""
        entries = pattern.color_entries
        # Nur nicht-übersprungene Farben für Prozentberechnung
        total = sum(e.stitch_count for e in entries if not e.skip_stitching) or 1

        self._colors_table.setRowCount(len(entries))

        for row, entry in enumerate(entries):
            # Farbe
            self._colors_table.setItem(row, 0, color_swatch_item(entry.thread.color))

            # Symbol (mit Skip-Markierung)
            symbol_text = f"⊘ {entry.symbol}" if entry.skip_stitching else entry.symbol
            symbol_item = QTableWidgetItem(symbol_text)
            if entry.skip_stitching:
                symbol_item.setForeground(QBrush(QColor(255, 152, 0)))  # Orange
            self._colors_table.setItem(row, 1, symbol_item)

            # Name (mit Skip-Markierung)
            name_text = (
                f"{entry.thread.name} ({t('nicht sticken')})"
                if entry.skip_stitching
                else entry.thread.name
            )
            name_item = QTableWidgetItem(name_text)
            if entry.skip_stitching:
                name_item.setForeground(QBrush(QColor(255, 152, 0)))
            self._colors_table.setItem(row, 2, name_item)

            # Hersteller
            self._colors_table.setItem(row, 3, QTableWidgetItem(entry.thread.manufacturer or "-"))

            # Katalognummer
            self._colors_table.setItem(row, 4, QTableWidgetItem(entry.thread.catalog_number or "-"))

            # Stiche
            stitch_item = sortable_count_item(entry.stitch_count)
            if entry.skip_stitching:
                stitch_item.setForeground(QBrush(QColor(THEME.text_muted)))
            self._colors_table.setItem(row, 5, stitch_item)

            # Prozent (nur für nicht-übersprungene)
            if entry.skip_stitching:
                percent_item = QTableWidgetItem("-")
                percent_item.setForeground(QBrush(QColor(THEME.text_muted)))
            else:
                percent = (entry.stitch_count / total) * 100
                percent_item = sortable_percent_item(percent)
            self._colors_table.setItem(row, 6, percent_item)
