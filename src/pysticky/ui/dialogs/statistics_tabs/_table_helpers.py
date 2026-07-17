"""
Gemeinsame Tabellenzellen-Bausteine für die Statistik-Tabs.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import QTableWidgetItem

from ....core.thread import ThreadColor
from ...color_utils import to_qcolor


def color_swatch_item(color: ThreadColor) -> QTableWidgetItem:
    """Leere Tabellenzelle mit der Farbe als Hintergrund (Farb-Swatch-Spalte)."""
    item = QTableWidgetItem()
    item.setBackground(QBrush(to_qcolor(color)))
    return item


def sortable_count_item(value: int) -> QTableWidgetItem:
    """Tabellenzelle, die nach dem Zahlenwert statt textuell sortiert."""
    item = QTableWidgetItem()
    item.setData(Qt.ItemDataRole.DisplayRole, value)
    return item
