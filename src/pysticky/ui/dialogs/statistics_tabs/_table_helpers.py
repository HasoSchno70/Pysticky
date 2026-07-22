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


class _NumericSortItem(QTableWidgetItem):
    """QTableWidgetItem mit frei formatiertem Anzeigetext (z.B. "45.3%",
    "12.00 €"), das aber nach einem gespeicherten Zahlenwert sortiert.

    Regression: mehrere Statistik-Tabs setzten hier Qt.ItemDataRole.UserRole
    auf den Zahlenwert, in der Annahme, setSortingEnabled(True) wuerde
    danach sortieren -- Qt's QTableWidgetItem.operator<() vergleicht aber
    nur Qt.ItemDataRole.DisplayRole (den angezeigten Text), UserRole wird
    fuer die Sortierung schlicht ignoriert. "45.3%" sortierte dadurch
    lexikographisch VOR "9.5%" (falsch). sortable_count_item() (oben) hat
    dasselbe Problem nicht, weil DisplayRole dort direkt der rohe int ist
    (kein Prozent-/Waehrungssuffix noetig).
    """

    def __init__(self, display_text: str, sort_value: float) -> None:
        super().__init__(display_text)
        self._sort_value = sort_value

    def __lt__(self, other: QTableWidgetItem) -> bool:  # noqa: D105
        if isinstance(other, _NumericSortItem):
            return self._sort_value < other._sort_value
        return super().__lt__(other)


def sortable_percent_item(percent: float, decimals: int = 1) -> QTableWidgetItem:
    """Tabellenzelle mit '<x.y>%'-Text, sortiert aber numerisch nach percent."""
    return _NumericSortItem(f"{percent:.{decimals}f}%", percent)


def sortable_decimal_item(value: float, suffix: str = "") -> QTableWidgetItem:
    """Tabellenzelle mit '<x.yz><suffix>'-Text, sortiert aber numerisch nach value."""
    return _NumericSortItem(f"{value:.2f}{suffix}", value)
