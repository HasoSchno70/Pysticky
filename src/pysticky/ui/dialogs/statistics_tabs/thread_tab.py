"""
Garnverbrauch-Rechner-Tab für den Statistik-Dialog.
"""

import math
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ....core.constants import COMMON_FABRIC_COUNTS
from ....core.i18n import t
from ...styles import THEME
from ._constants import STITCHES_PER_SKEIN
from ._table_helpers import color_swatch_item, sortable_count_item

if TYPE_CHECKING:
    from ....core import Pattern


class ThreadTab(QWidget):
    """Tab: Garnverbrauch-Rechner mit Stoffart, Zuschlag und Kosten."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pattern: "Pattern | None" = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Einstellungen
        settings_group = QGroupBox(t("Berechnungs-Einstellungen"))
        settings_layout = QGridLayout(settings_group)

        settings_layout.addWidget(QLabel(t("Stoffart:")), 0, 0)
        self._fabric_combo = QComboBox()
        self._fabric_combo.addItems(
            [
                t("Aida 11 (4,3 St/cm)"),
                t("Aida 14 (5,5 St/cm)"),
                t("Aida 16 (6,3 St/cm)"),
                t("Aida 18 (7,1 St/cm)"),
                t("Evenweave 28 (11 St/cm)"),
                t("Leinen 32 (12,6 St/cm)"),
            ]
        )
        self._fabric_combo.setCurrentIndex(1)  # Aida 14
        self._fabric_combo.currentIndexChanged.connect(self._recalculate_thread)
        settings_layout.addWidget(self._fabric_combo, 0, 1)

        settings_layout.addWidget(QLabel(t("Sicherheitszuschlag:")), 1, 0)
        self._waste_spin = QSpinBox()
        self._waste_spin.setRange(0, 50)
        self._waste_spin.setValue(20)
        self._waste_spin.setSuffix(" %")
        self._waste_spin.valueChanged.connect(self._recalculate_thread)
        settings_layout.addWidget(self._waste_spin, 1, 1)

        settings_layout.addWidget(QLabel(t("Preis pro Strang:")), 2, 0)
        self._price_spin = QDoubleSpinBox()
        self._price_spin.setRange(0, 50)
        self._price_spin.setValue(1.50)
        self._price_spin.setSuffix(" €")
        self._price_spin.setDecimals(2)
        self._price_spin.valueChanged.connect(self._recalculate_thread)
        settings_layout.addWidget(self._price_spin, 2, 1)

        layout.addWidget(settings_group)

        # Ergebnis-Tabelle
        self._thread_table = QTableWidget()
        self._thread_table.setColumnCount(6)
        self._thread_table.setHorizontalHeaderLabels(
            [
                t("Farbe"),
                t("Name"),
                t("Stiche"),
                t("Stränge"),
                t("Stränge (+Zuschlag)"),
                t("Kosten"),
            ]
        )
        self._thread_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._thread_table.setAlternatingRowColors(True)
        self._thread_table.setSortingEnabled(True)

        layout.addWidget(self._thread_table, 1)

        # Zusammenfassung
        summary_frame = QFrame()
        summary_frame.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_light};
                border: 1px solid {THEME.border_dark};
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        summary_layout = QHBoxLayout(summary_frame)

        self._total_skeins_label = QLabel(t("Gesamt: - Stränge"))
        self._total_skeins_label.setStyleSheet(f"font-weight: bold; color: {THEME.text_primary};")
        summary_layout.addWidget(self._total_skeins_label)

        summary_layout.addStretch()

        self._total_cost_label = QLabel(t("Geschätzte Kosten: - €"))
        self._total_cost_label.setStyleSheet(
            f"font-weight: bold; color: {THEME.accent_primary}; font-size: 14px;"
        )
        summary_layout.addWidget(self._total_cost_label)

        layout.addWidget(summary_frame)

    def update_stats(self, pattern: "Pattern", stats: dict) -> None:
        """Merkt sich das Muster und berechnet den Garnverbrauch."""
        self._pattern = pattern
        self._recalculate_thread()

    def calculator_settings(self) -> tuple[int, float, float]:
        """Aktuelle Rechner-Einstellungen für den CSV-Export des Dialogs.

        Returns:
            (fabric_count, waste_percent, price_per_skein)
        """
        fabric_count = COMMON_FABRIC_COUNTS[self._fabric_combo.currentIndex()]
        return fabric_count, float(self._waste_spin.value()), self._price_spin.value()

    def _recalculate_thread(self) -> None:
        """Berechnet den Garnverbrauch neu."""
        if self._pattern is None:
            return

        fabric_counts = COMMON_FABRIC_COUNTS
        fabric_count = fabric_counts[self._fabric_combo.currentIndex()]
        stitches_per_skein = STITCHES_PER_SKEIN.get(fabric_count, 500)
        waste_factor = 1 + (self._waste_spin.value() / 100)
        price = self._price_spin.value()

        # Nur nicht-übersprungene Farben
        entries = [e for e in self._pattern.color_entries if not e.skip_stitching]
        self._thread_table.setRowCount(len(entries))

        total_skeins = 0
        total_cost = 0

        for row, entry in enumerate(entries):
            # Farbe
            self._thread_table.setItem(row, 0, color_swatch_item(entry.thread.color))

            # Name
            self._thread_table.setItem(row, 1, QTableWidgetItem(entry.thread.name))

            # Stiche
            self._thread_table.setItem(row, 2, sortable_count_item(entry.stitch_count))

            # Stränge (genau)
            if entry.stitch_count > 0:
                exact_skeins = entry.stitch_count / stitches_per_skein
                self._thread_table.setItem(row, 3, QTableWidgetItem(f"{exact_skeins:.2f}"))

                # Stränge mit Zuschlag (aufgerundet)
                with_waste = math.ceil(exact_skeins * waste_factor)
                self._thread_table.setItem(row, 4, QTableWidgetItem(str(with_waste)))

                # Kosten
                cost = with_waste * price
                self._thread_table.setItem(row, 5, QTableWidgetItem(f"{cost:.2f} €"))

                total_skeins += with_waste
                total_cost += cost
            else:
                self._thread_table.setItem(row, 3, QTableWidgetItem("0"))
                self._thread_table.setItem(row, 4, QTableWidgetItem("0"))
                self._thread_table.setItem(row, 5, QTableWidgetItem("0.00 €"))

        # Info über übersprungene Farben
        skipped_count = sum(
            1 for e in self._pattern.color_entries if e.skip_stitching and e.stitch_count > 0
        )
        if skipped_count > 0:
            self._total_skeins_label.setText(
                f"Gesamt: {total_skeins} Stränge ({skipped_count} Farbe(n) übersprungen)"
            )
        else:
            self._total_skeins_label.setText(f"Gesamt: {total_skeins} Stränge")
        self._total_cost_label.setText(f"Geschätzte Kosten: {total_cost:.2f} €")
