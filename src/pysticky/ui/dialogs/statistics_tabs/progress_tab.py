"""
Fortschritts-Tab für den Statistik-Dialog.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ....core.i18n import t
from ...styles import THEME
from ...widgets.statistics_widgets import StatCard

if TYPE_CHECKING:
    from ....core import Pattern


class ProgressTab(QWidget):
    """Tab: Stick-Fortschritt gesamt und pro Farbe."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Gesamt-Fortschritt
        overall_group = QGroupBox(t("Gesamtfortschritt"))
        overall_layout = QVBoxLayout(overall_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximum(1000)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%p%")
        self._progress_bar.setMinimumHeight(30)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {THEME.bg_medium};
                border: 1px solid {THEME.border_dark};
                border-radius: 6px;
                text-align: center;
                color: {THEME.text_primary};
                font-size: 14px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2ecc71, stop:1 #27ae60);
                border-radius: 5px;
            }}
        """)
        overall_layout.addWidget(self._progress_bar)

        self._progress_label = QLabel(t("0 / 0 Stiche gestickt"))
        self._diamond = False
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 12px;")
        overall_layout.addWidget(self._progress_label)

        layout.addWidget(overall_group)

        # Fortschrittskarten
        cards_layout = QGridLayout()
        cards_layout.setSpacing(10)

        self._card_progress_done = StatCard(t("Erledigt"), "0", "✅")
        cards_layout.addWidget(self._card_progress_done, 0, 0)

        self._card_progress_remaining = StatCard(t("Verbleibend"), "0", "📋")
        cards_layout.addWidget(self._card_progress_remaining, 0, 1)

        self._card_progress_colors_done = StatCard(t("Farben fertig"), "0", "🎨")
        cards_layout.addWidget(self._card_progress_colors_done, 0, 2)

        layout.addLayout(cards_layout)

        # Pro-Farbe-Tabelle
        color_group = QGroupBox(t("Fortschritt pro Farbe"))
        color_layout = QVBoxLayout(color_group)

        self._progress_table = QTableWidget()
        self._progress_table.setColumnCount(6)
        self._progress_table.setHorizontalHeaderLabels(
            [t("Farbe"), t("Name"), t("Erledigt"), t("Gesamt"), "%", t("Status")]
        )
        self._progress_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._progress_table.setAlternatingRowColors(True)
        self._progress_table.setSortingEnabled(True)

        color_layout.addWidget(self._progress_table)

        layout.addWidget(color_group, 1)

    def update_stats(self, pattern: "Pattern", stats: dict) -> None:
        """Berechnet den Fortschritt."""
        progress = pattern.get_progress_statistics()
        self._diamond = pattern.mode == "diamond"

        total = progress["total_stitches"]
        completed = progress["completed_stitches"]
        percent = progress["progress_percent"]

        # Gesamt-Fortschrittsbalken
        self._progress_bar.setValue(int(percent * 10))
        self._progress_bar.setFormat(f"{percent:.1f}%")
        unit = t("Diamanten gesetzt") if self._diamond else t("Stiche gestickt")
        self._progress_label.setText(f"{completed:,} / {total:,} {unit}")

        # Karten
        self._card_progress_done.set_value(f"{completed:,}")
        self._card_progress_remaining.set_value(f"{total - completed:,}")

        # Farben komplett fertig zählen
        colors_done = sum(
            1
            for c in progress["per_color"]
            if c["total"] > 0
            and c["completed"] == c["total"]
            and not c.get("skip_stitching", False)
        )
        colors_total = sum(
            1
            for c in progress["per_color"]
            if c["total"] > 0 and not c.get("skip_stitching", False)
        )
        self._card_progress_colors_done.set_value(f"{colors_done} / {colors_total}")

        # Pro-Farbe-Tabelle
        per_color = [
            c
            for c in progress["per_color"]
            if c["total"] > 0 and not c.get("skip_stitching", False)
        ]
        self._progress_table.setRowCount(len(per_color))

        for row, color_info in enumerate(per_color):
            # Farbe
            color = QColor(color_info["color_hex"])
            color_item = QTableWidgetItem()
            color_item.setBackground(QBrush(color))
            self._progress_table.setItem(row, 0, color_item)

            # Name
            self._progress_table.setItem(row, 1, QTableWidgetItem(color_info["thread_name"]))

            # Erledigt
            done_item = QTableWidgetItem()
            done_item.setData(Qt.ItemDataRole.DisplayRole, color_info["completed"])
            self._progress_table.setItem(row, 2, done_item)

            # Gesamt
            total_item = QTableWidgetItem()
            total_item.setData(Qt.ItemDataRole.DisplayRole, color_info["total"])
            self._progress_table.setItem(row, 3, total_item)

            # Prozent
            pct = color_info["percent"]
            pct_item = QTableWidgetItem(f"{pct:.1f}%")
            pct_item.setData(Qt.ItemDataRole.UserRole, pct)
            self._progress_table.setItem(row, 4, pct_item)

            # Status
            if color_info["completed"] == color_info["total"]:
                status = t("✅ Fertig")
                status_item = QTableWidgetItem(status)
                status_item.setForeground(QBrush(QColor("#2ecc71")))
            elif color_info["completed"] > 0:
                status = t("🔄 In Arbeit")
                status_item = QTableWidgetItem(status)
                status_item.setForeground(QBrush(QColor("#f39c12")))
            else:
                status = t("⬜ Offen")
                status_item = QTableWidgetItem(status)
                status_item.setForeground(QBrush(QColor(THEME.text_muted)))
            self._progress_table.setItem(row, 5, status_item)
