"""
Einkaufslisten-Tab für den Statistik-Dialog.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ....core.i18n import t
from ....core.inventory import Inventory, compute_shopping_list
from ...color_utils import color_swatch_icon
from ...styles import THEME
from ._constants import STITCHES_PER_SKEIN

if TYPE_CHECKING:
    from ....core import Pattern


class ShoppingTab(QWidget):
    """Tab: Einkaufsliste auf Basis der Garn-Vorratsliste."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._populated = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(12)

        intro = QLabel(
            t(
                "Vergleich des Garnbedarfs für dieses Muster mit deinem hinterlegten "
                "Vorrat. Pflege den Vorrat über Bearbeiten → Garn-Vorrat… (Ctrl+Shift+I)."
            )
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {THEME.text_muted};")
        self._layout.addWidget(intro)

    def update_stats(self, pattern: "Pattern", stats: dict, waste_percent: float = 20.0) -> None:
        """Baut die Einkaufsliste auf (einmalig — der Dialog ruft dies genau
        einmal nach der Konstruktion auf, wie zuvor beim Tab-Aufbau).

        waste_percent: derselbe Verschnitt-Zuschlag wie im Garnverbrauch-Tab
        (statistics_dialog.py liest ihn dort aus und reicht ihn hier durch)
        -- vorher rechnete dieser Tab mit einer eigenen, davon unabhaengigen
        Pauschal-Formel, wodurch beide Tabs fuer dasselbe Muster
        unterschiedliche "benoetigte Straenge"-Zahlen zeigten.
        """
        if self._populated:
            return
        self._populated = True

        inv = Inventory()
        items = compute_shopping_list(
            pattern,
            inv,
            STITCHES_PER_SKEIN,
            waste_percent,
        )

        if not items:
            empty = QLabel(t("Das Muster enthält keine gestickte Farbe — keine Einkaufsliste."))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {THEME.text_muted}; font-style: italic; padding: 20px;")
            self._layout.addWidget(empty)
            self._layout.addStretch(1)
            return

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["", t("Farbe"), t("Nr."), t("Benötigt"), t("Vorrat"), t("Zu kaufen")]
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in (2, 3, 4, 5):
            hdr.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        table.setColumnWidth(0, 28)
        table.setRowCount(len(items))

        total_to_buy = 0
        for row, item in enumerate(items):
            thread = item["thread"]
            c = thread.color
            icon = QTableWidgetItem("")
            icon.setIcon(color_swatch_icon(c, 18))
            table.setItem(row, 0, icon)
            table.setItem(row, 1, QTableWidgetItem(thread.name))
            table.setItem(row, 2, QTableWidgetItem(thread.catalog_number or ""))
            table.setItem(row, 3, QTableWidgetItem(f"{item['needed_skeins']}"))
            table.setItem(row, 4, QTableWidgetItem(f"{item['on_hand']}"))
            to_buy_item = QTableWidgetItem(f"{item['to_buy']}")
            if item["to_buy"] > 0:
                to_buy_item.setForeground(QColor(THEME.error))
                total_to_buy += item["to_buy"]
            else:
                to_buy_item.setForeground(QColor(THEME.accent_primary))
            table.setItem(row, 5, to_buy_item)
        self._layout.addWidget(table, 1)

        summary = QLabel(
            f"<b>{total_to_buy}</b> {t('Stränge insgesamt zu kaufen')}"
            if total_to_buy > 0
            else t("✓ Du hast alles im Vorrat!")
        )
        summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary.setStyleSheet(
            f"font-size: 14px; padding: 8px; "
            f"color: {THEME.error if total_to_buy > 0 else THEME.success};"
        )
        self._layout.addWidget(summary)
