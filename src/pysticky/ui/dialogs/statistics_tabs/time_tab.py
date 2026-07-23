"""
Zeitschätzung-Tab für den Statistik-Dialog.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ....core.i18n import t
from ...widgets.statistics_widgets import StatCard
from ._table_helpers import color_swatch_item, sortable_count_item

if TYPE_CHECKING:
    from ....core import Pattern


class TimeTab(QWidget):
    """Tab: Zeitschätzung nach Erfahrungslevel und Stunden pro Tag."""

    # Durchschnittliche Stickzeit pro Stich (Sekunden)
    SECONDS_PER_STITCH = {
        "Anfänger": 8,
        "Fortgeschritten": 5,
        "Erfahren": 3,
        "Profi": 2,
    }

    # Diamond Painting: feste Rate ohne Skill-Abstufung (Hand-Tool-Tempo),
    # identisch zu info_panel.py::_calculate_stitch_time()'s etablierter
    # DP-Konvention -- dort ist Kreuzstich-Zeit allerdings ein einzelner
    # fixer 20s-Wert statt der hier skill-abgestuften 2-8s-Spanne; ein
    # gemeinsames Skalierungsmodell fuer beide Modi existiert nicht, DP
    # bekommt daher bewusst die eigene feste Rate statt einer erfundenen
    # Skalierung.
    SECONDS_PER_DRILL = 3.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pattern: "Pattern | None" = None
        self._diamond = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Einstellungen
        settings_group = QGroupBox(t("Erfahrungslevel"))
        settings_layout = QHBoxLayout(settings_group)

        settings_layout.addWidget(QLabel(t("Stickerfahrung:")))
        self._skill_combo = QComboBox()
        for skill in self.SECONDS_PER_STITCH:
            self._skill_combo.addItem(t(skill), skill)
        self._skill_combo.setCurrentIndex(1)  # Fortgeschritten
        self._skill_combo.currentIndexChanged.connect(self._recalculate_time)
        settings_layout.addWidget(self._skill_combo)

        settings_layout.addStretch()

        settings_layout.addWidget(QLabel(t("Stunden pro Tag:")))
        self._hours_spin = QDoubleSpinBox()
        # Siehe thread_tab.py::_price_spin -- erzwingt Punkt-Dezimaltrennzeichen
        # unabhaengig von der OS-Locale, statt unter einer deutschen
        # Windows-Regionaleinstellung "2,0 h" zu zeigen.
        self._hours_spin.setLocale(QLocale.c())
        self._hours_spin.setRange(0.5, 12)
        self._hours_spin.setValue(2)
        self._hours_spin.setSuffix(" h")
        self._hours_spin.setDecimals(1)
        self._hours_spin.valueChanged.connect(self._recalculate_time)
        settings_layout.addWidget(self._hours_spin)

        layout.addWidget(settings_group)

        # Zeitschätzung-Karten
        time_cards = QGridLayout()

        self._card_total_time = StatCard(t("Geschätzte Gesamtzeit"), "-", "⏱️")
        time_cards.addWidget(self._card_total_time, 0, 0)

        self._card_days = StatCard(t("Bei täglichem Sticken"), "-", "📅")
        time_cards.addWidget(self._card_days, 0, 1)

        self._card_speed = StatCard(t("Stiche pro Stunde"), "-", "⚡")
        time_cards.addWidget(self._card_speed, 1, 0)

        self._card_per_color = StatCard(t("Durchschn. pro Farbe"), "-", "🎨")
        time_cards.addWidget(self._card_per_color, 1, 1)

        layout.addLayout(time_cards)

        # Detaillierte Aufschlüsselung
        detail_group = QGroupBox(t("Zeitaufwand pro Farbe (geschätzt)"))
        detail_layout = QVBoxLayout(detail_group)

        self._time_table = QTableWidget()
        self._time_table.setColumnCount(4)
        self._time_table.setHorizontalHeaderLabels(
            [t("Farbe"), t("Name"), t("Stiche"), t("Geschätzte Zeit")]
        )
        self._time_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._time_table.setAlternatingRowColors(True)
        self._time_table.setSortingEnabled(True)

        detail_layout.addWidget(self._time_table)

        layout.addWidget(detail_group, 1)

    def update_stats(self, pattern: "Pattern", stats: dict) -> None:
        """Merkt sich das Muster und berechnet die Zeitschätzung."""
        self._pattern = pattern
        was_diamond = self._diamond
        self._diamond = pattern.mode == "diamond"
        if self._diamond != was_diamond:
            self._apply_mode_labels()
        self._recalculate_time()

    def _apply_mode_labels(self) -> None:
        """Passt Vokabular/Bedienelemente an den Muster-Modus an (analog
        info_panel.py::set_mode() und progress_tab.py's DP-Branching).
        Skill-Level hat im DP-Modus keine etablierte Entsprechung (feste
        Hand-Tool-Rate statt Erfahrungsstufen) -- Combo wird deaktiviert
        statt wirkungslos anklickbar zu bleiben (gleiches Muster wie
        Sticken-Modus/Tweed-Blend in view_handlers.py)."""
        self._skill_combo.setEnabled(not self._diamond)
        self._card_speed.set_label(
            t("Drills pro Stunde") if self._diamond else t("Stiche pro Stunde")
        )
        self._card_days.set_label(
            t("Bei täglichem Kleben") if self._diamond else t("Bei täglichem Sticken")
        )
        self._time_table.setHorizontalHeaderLabels(
            [
                t("Farbe"),
                t("Name"),
                t("Drills") if self._diamond else t("Stiche"),
                t("Geschätzte Zeit"),
            ]
        )

    def _recalculate_time(self) -> None:
        """Berechnet die Zeitschätzung neu."""
        if self._pattern is None:
            return

        if self._diamond:
            seconds_per_stitch = self.SECONDS_PER_DRILL
        else:
            skill = self._skill_combo.currentData()
            seconds_per_stitch = self.SECONDS_PER_STITCH.get(skill, 5)
        hours_per_day = self._hours_spin.value()

        # Nur nicht-übersprungene Farben zählen
        entries_to_stitch = [e for e in self._pattern.color_entries if not e.skip_stitching]
        total_stitches = sum(e.stitch_count for e in entries_to_stitch)
        total_seconds = total_stitches * seconds_per_stitch

        # Gesamtzeit
        hours = total_seconds / 3600
        if hours < 1:
            time_str = f"{int(total_seconds / 60)} Minuten"
        elif hours < 24:
            time_str = f"{hours:.1f} Stunden"
        else:
            time_str = f"{hours:.0f} Stunden"
        self._card_total_time.set_value(time_str)

        # Tage
        days = hours / hours_per_day
        if days < 1:
            days_str = "< 1 Tag"
        elif days < 7:
            days_str = f"{days:.1f} Tage"
        elif days < 30:
            weeks = days / 7
            days_str = f"{weeks:.1f} Wochen"
        else:
            months = days / 30
            days_str = f"{months:.1f} Monate"
        self._card_days.set_value(days_str)

        # Stiche pro Stunde
        stitches_per_hour = 3600 / seconds_per_stitch
        self._card_speed.set_value(f"{int(stitches_per_hour)}")

        # Durchschnitt pro Farbe
        if entries_to_stitch:
            avg_per_color = total_stitches / len(entries_to_stitch)
            avg_time = (avg_per_color * seconds_per_stitch) / 60
            self._card_per_color.set_value(f"{avg_time:.0f} min")
        else:
            self._card_per_color.set_value("-")

        # Zeit-Tabelle (nur nicht-übersprungene Farben)
        self._time_table.setRowCount(len(entries_to_stitch))

        for row, entry in enumerate(entries_to_stitch):
            # Farbe
            self._time_table.setItem(row, 0, color_swatch_item(entry.thread.color))

            # Name
            self._time_table.setItem(row, 1, QTableWidgetItem(entry.thread.name))

            # Stiche
            self._time_table.setItem(row, 2, sortable_count_item(entry.stitch_count))

            # Zeit
            color_seconds = entry.stitch_count * seconds_per_stitch
            if color_seconds < 60:
                time_str = f"{color_seconds:.0f} s"
            elif color_seconds < 3600:
                time_str = f"{color_seconds / 60:.0f} min"
            else:
                time_str = f"{color_seconds / 3600:.1f} h"
            self._time_table.setItem(row, 3, QTableWidgetItem(time_str))
