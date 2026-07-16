"""
Muster-Statistik und Garnverbrauch-Rechner Dialog.

Features:
- Detaillierte Stich-Statistiken pro Farbe
- Zeitschätzung für das Sticken
- Garnverbrauch mit Strangberechnung
- Kostenberechnung
- Export als Text/CSV
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.constants import COMMON_FABRIC_COUNTS
from ...core.i18n import t
from ..color_utils import color_swatch_icon, to_qcolor
from ..styles import THEME, Styles
from ..widgets.statistics_widgets import StatCard
from .dialog_sizing import auto_size_dialog

if TYPE_CHECKING:
    from ...core import Pattern


class PatternStatisticsDialog(QDialog):
    """Dialog für Muster-Statistiken und Garnverbrauch."""

    # Stiche pro Strang für verschiedene Stofftypen
    STITCHES_PER_SKEIN = {
        11: 780,  # Aida 11
        14: 500,  # Aida 14
        16: 380,  # Aida 16
        18: 300,  # Aida 18
        28: 190,  # Evenweave 28
        32: 145,  # Leinen 32
    }

    # Durchschnittliche Stickzeit pro Stich (Sekunden)
    SECONDS_PER_STITCH = {
        "Anfänger": 8,
        "Fortgeschritten": 5,
        "Erfahren": 3,
        "Profi": 2,
    }

    def __init__(self, pattern: "Pattern", parent=None) -> None:
        super().__init__(parent)
        self._pattern = pattern

        self.setWindowTitle(t("Muster-Statistiken & Garnverbrauch"))
        # Breit genug für alle 6 Tabs (inkl. "Einkaufsliste") gewählt, damit
        # die Tab-Leiste auch dann nicht abgeschnitten wird, wenn
        # _auto_size_to_content() aus irgendeinem Grund (Bildschirm/DPI-
        # Eigenheiten) nicht ausreichend vergrößert -- diese Mindestbreite
        # ist der harte Boden, unter den auto_size_dialog() nie geht.
        self.setMinimumSize(1200, 650)

        self._setup_ui()
        self._apply_styles()
        self._calculate_statistics()
        self._auto_size_to_content()

    def _auto_size_to_content(self) -> None:
        """Größe so wählen, dass möglichst alle Tabs ohne Scrollen passen
        (gleiches Muster wie SettingsDialog — 6 Tabs mit Emoji brauchen bei
        fixer Default-Größe oft mehr Breite als die Tab-Leiste hat)."""
        tabbar_w = self._tabs.tabBar().sizeHint().width() + 40
        auto_size_dialog(self, self._tab_widgets, min_width=tabbar_w)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Tabs
        tabs = QTabWidget()
        self._tabs = tabs

        # Tab 1: Übersicht
        overview_tab = QWidget()
        self._setup_overview_tab(overview_tab)
        tabs.addTab(overview_tab, t("📊 Übersicht"))

        # Tab 2: Farben-Details
        colors_tab = QWidget()
        self._setup_colors_tab(colors_tab)
        tabs.addTab(colors_tab, t("🎨 Farben"))

        # Tab 3: Garnverbrauch-Rechner
        thread_tab = QWidget()
        self._setup_thread_tab(thread_tab)
        tabs.addTab(thread_tab, t("🧵 Garnverbrauch"))

        # Tab 4: Zeitschätzung
        time_tab = QWidget()
        self._setup_time_tab(time_tab)
        tabs.addTab(time_tab, t("⏱️ Zeitschätzung"))

        # Tab 5: Fortschritt
        progress_tab = QWidget()
        self._setup_progress_tab(progress_tab)
        tabs.addTab(progress_tab, t("✅ Fortschritt"))

        # Tab 6: Einkaufsliste (aus Garn-Vorrat)
        shopping_tab = QWidget()
        self._setup_shopping_tab(shopping_tab)
        tabs.addTab(shopping_tab, t("🛒 Einkaufsliste"))

        self._tab_widgets = [
            overview_tab,
            colors_tab,
            thread_tab,
            time_tab,
            progress_tab,
            shopping_tab,
        ]
        layout.addWidget(tabs, 1)

        # Footer
        footer = QHBoxLayout()

        export_btn = QPushButton(t("📄 Als CSV exportieren"))
        export_btn.clicked.connect(self._on_export_csv)
        # Verhindert, dass dieser Button den Default-Status (Enter-Taste)
        # des Close-Buttons unten übernimmt.
        export_btn.setAutoDefault(False)
        footer.addWidget(export_btn)

        footer.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn = button_box.button(QDialogButtonBox.StandardButton.Close)
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        # Diese Datei setzt in _apply_styles() einen eigenen dialogweiten
        # QPushButton-Stil, der die globale :default-Hervorhebung überschreibt
        # — daher hier explizit den sanktionierten Primary-Button-Stil setzen.
        close_btn.setStyleSheet(Styles.button_primary())
        footer.addWidget(button_box)

        layout.addLayout(footer)

    def _setup_overview_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setSpacing(15)

        # Statistik-Karten
        cards_layout = QGridLayout()
        cards_layout.setSpacing(10)

        self._card_size = StatCard(t("Größe"), "- × -", "📐")
        cards_layout.addWidget(self._card_size, 0, 0)

        self._card_stitches = StatCard(t("Gesamtstiche"), "-", "🧵")
        cards_layout.addWidget(self._card_stitches, 0, 1)

        self._card_colors = StatCard(t("Farben"), "-", "🎨")
        cards_layout.addWidget(self._card_colors, 0, 2)

        self._card_backstitches = StatCard(t("Rückstiche"), "-", "↙️")
        cards_layout.addWidget(self._card_backstitches, 1, 0)

        self._card_coverage = StatCard(t("Abdeckung"), "-", "📊")
        cards_layout.addWidget(self._card_coverage, 1, 1)

        self._card_layers = StatCard(t("Ebenen"), "-", "🗂️")
        cards_layout.addWidget(self._card_layers, 1, 2)

        # Schwierigkeits-Karte mit Tooltip-Detail (Faktor-Aufschlüsselung)
        self._card_difficulty = StatCard(t("Schwierigkeit"), "-", "🎯")
        cards_layout.addWidget(self._card_difficulty, 2, 0, 1, 3)

        layout.addLayout(cards_layout)

        # Farbverteilung (Top 5)
        dist_group = QGroupBox(t("Top 5 Farben"))
        dist_layout = QVBoxLayout(dist_group)

        self._color_bars: list[tuple[QWidget, QLabel, QProgressBar]] = []
        for _ in range(5):
            row = QHBoxLayout()

            color_preview = QWidget()
            color_preview.setFixedSize(20, 20)
            row.addWidget(color_preview)

            name_label = QLabel("-")
            name_label.setMinimumWidth(150)
            row.addWidget(name_label)

            bar = QProgressBar()
            bar.setMaximum(100)
            bar.setTextVisible(True)
            bar.setFormat("%v%")
            row.addWidget(bar, 1)

            dist_layout.addLayout(row)
            self._color_bars.append((color_preview, name_label, bar))

        layout.addWidget(dist_group)
        layout.addStretch()

    def _setup_colors_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)

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

    def _setup_thread_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
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

    def _setup_time_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setSpacing(15)

        # Einstellungen
        settings_group = QGroupBox(t("Erfahrungslevel"))
        settings_layout = QHBoxLayout(settings_group)

        settings_layout.addWidget(QLabel(t("Stickerfahrung:")))
        self._skill_combo = QComboBox()
        self._skill_combo.addItems(list(self.SECONDS_PER_STITCH.keys()))
        self._skill_combo.setCurrentIndex(1)  # Fortgeschritten
        self._skill_combo.currentIndexChanged.connect(self._recalculate_time)
        settings_layout.addWidget(self._skill_combo)

        settings_layout.addStretch()

        settings_layout.addWidget(QLabel(t("Stunden pro Tag:")))
        self._hours_spin = QDoubleSpinBox()
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

    def _setup_shopping_tab(self, parent: QWidget) -> None:
        """Einkaufsliste auf Basis der Garn-Vorratsliste."""
        from ...core.inventory import Inventory, compute_shopping_list

        layout = QVBoxLayout(parent)
        layout.setSpacing(12)

        intro = QLabel(
            t(
                "Vergleich des Garnbedarfs für dieses Muster mit deinem hinterlegten "
                "Vorrat. Pflege den Vorrat über Bearbeiten → Garn-Vorrat… (Ctrl+Shift+I)."
            )
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {THEME.text_muted};")
        layout.addWidget(intro)

        inv = Inventory()
        items = compute_shopping_list(
            self._pattern,
            inv,
            self.STITCHES_PER_SKEIN,
        )

        if not items:
            empty = QLabel(t("Das Muster enthält keine gestickte Farbe — keine Einkaufsliste."))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {THEME.text_muted}; font-style: italic; padding: 20px;")
            layout.addWidget(empty)
            layout.addStretch(1)
            return

        from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

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
        for col in (2, 3, 4, 5):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
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
        layout.addWidget(table, 1)

        summary = QLabel(
            f"<b>{total_to_buy}</b> Stränge insgesamt zu kaufen"
            if total_to_buy > 0
            else t("✓ Du hast alles im Vorrat!")
        )
        summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary.setStyleSheet(
            f"font-size: 14px; padding: 8px; "
            f"color: {THEME.error if total_to_buy > 0 else THEME.success};"
        )
        layout.addWidget(summary)

    def _setup_progress_tab(self, parent: QWidget) -> None:
        """Erstellt den Fortschritts-Tab."""
        layout = QVBoxLayout(parent)
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

    def _apply_styles(self) -> None:
        self.setStyleSheet(f"""
            QDialog {{
                background: {THEME.bg_dark};
            }}
            QGroupBox {{
                font-weight: bold;
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QTableWidget {{
                background: {THEME.bg_medium};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
                gridline-color: {THEME.border_dark};
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
            QTableWidget::item:alternate {{
                background: {THEME.bg_light};
            }}
            QHeaderView::section {{
                background: {THEME.bg_light};
                color: {THEME.text_primary};
                padding: 6px;
                border: none;
                border-bottom: 1px solid {THEME.border_dark};
                font-weight: bold;
            }}
            QComboBox, QSpinBox, QDoubleSpinBox {{
                background: {THEME.bg_medium};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
                padding: 5px;
                min-width: 120px;
            }}
            QPushButton {{
                background: {THEME.bg_medium};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
                padding: 8px 15px;
            }}
            QPushButton:hover {{
                background: {THEME.bg_light};
            }}
            QProgressBar {{
                background: {THEME.bg_medium};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
                text-align: center;
                color: {THEME.text_primary};
            }}
            QProgressBar::chunk {{
                background: {THEME.accent_primary};
                border-radius: 3px;
            }}
            QTabWidget::pane {{
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
            }}
            QTabBar::tab {{
                background: {THEME.bg_medium};
                color: {THEME.text_muted};
                padding: 8px 16px;
                border: 1px solid {THEME.border_dark};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background: {THEME.bg_light};
                color: {THEME.text_primary};
            }}
        """)

    def _calculate_statistics(self) -> None:
        """Berechnet alle Statistiken."""
        stats = self._pattern.get_statistics()

        # Übersicht-Tab
        self._card_size.set_value(f"{stats['width']} × {stats['height']}")

        # Stiche: Zeige zu stickende Stiche (ohne übersprungene)
        if stats.get("skipped_stitches", 0) > 0:
            self._card_stitches.set_value(f"{stats['stitches_to_do']:,}")
        else:
            self._card_stitches.set_value(f"{stats['total_stitches']:,}")

        # Farben: Zeige verwendete - übersprungene
        used = stats["used_colors"]
        skipped = stats.get("skipped_colors", 0)
        if skipped > 0:
            self._card_colors.set_value(f"{used - skipped} (+{skipped} übersp.)")
        else:
            self._card_colors.set_value(str(stats["color_count"]))

        self._card_backstitches.set_value(str(len(self._pattern.backstitches)))

        # Abdeckung berechnen
        total_cells = stats["width"] * stats["height"]
        if total_cells > 0:
            coverage = (stats["total_stitches"] / total_cells) * 100
            self._card_coverage.set_value(f"{coverage:.1f}%")
        else:
            self._card_coverage.set_value("0%")

        self._card_layers.set_value(str(len(self._pattern.layer_stack)))

        # Schwierigkeit
        from ...core.difficulty import compute_difficulty

        diff = compute_difficulty(self._pattern)
        self._card_difficulty.set_value(diff["level"])
        f = diff["factors"]
        d = diff["details"]
        tip = (
            f"Score: {diff['score']} / 12\n"
            f"  Farben: {f['colors']}/3 ({d['used_colors']} verwendet)\n"
            f"  Stiche: {f['size']}/3 ({d['stitches_to_do']:,} zu sticken)\n"
            f"  Sonderstiche: {f['special']}/3 "
            f"({d['special_ratio'] * 100:.1f}% Anteil)\n"
            f"  Backstitches: {f['backstitches']}/3 ({d['backstitches']} Linien)"
        )
        self._card_difficulty.setToolTip(tip)

        # Top 5 Farben (ohne übersprungene)
        entries = sorted(
            [e for e in self._pattern.color_entries if not e.skip_stitching],
            key=lambda e: e.stitch_count,
            reverse=True,
        )[:5]

        total = stats.get("stitches_to_do", stats["total_stitches"]) or 1
        for i, (widgets, entry) in enumerate(zip(self._color_bars, entries + [None] * 5)):
            color_widget, name_label, bar = widgets

            if i < len(entries) and entry:
                # Farbe setzen
                color = to_qcolor(entry.thread.color)
                color_widget.setStyleSheet(f"""
                    background: {color.name()};
                    border: 1px solid {THEME.border_light};
                    border-radius: 3px;
                """)

                name_label.setText(f"{entry.symbol} {entry.thread.name}")
                percent = int((entry.stitch_count / total) * 100)
                bar.setValue(percent)
                bar.setFormat(f"{entry.stitch_count:,} ({percent}%)")
            else:
                color_widget.setStyleSheet(f"background: {THEME.bg_medium}; border-radius: 3px;")
                name_label.setText("-")
                bar.setValue(0)
                bar.setFormat("")

        # Farben-Tab füllen
        self._populate_colors_table()

        # Garnverbrauch berechnen
        self._recalculate_thread()

        # Zeit berechnen
        self._recalculate_time()

        # Fortschritt berechnen
        self._calculate_progress()

    def _calculate_progress(self) -> None:
        """Berechnet den Fortschritt."""
        progress = self._pattern.get_progress_statistics()

        total = progress["total_stitches"]
        completed = progress["completed_stitches"]
        percent = progress["progress_percent"]

        # Gesamt-Fortschrittsbalken
        self._progress_bar.setValue(int(percent * 10))
        self._progress_bar.setFormat(f"{percent:.1f}%")
        self._progress_label.setText(f"{completed:,} / {total:,} Stiche gestickt")

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

    def _populate_colors_table(self) -> None:
        """Füllt die Farben-Tabelle."""
        entries = self._pattern.color_entries
        # Nur nicht-übersprungene Farben für Prozentberechnung
        total = sum(e.stitch_count for e in entries if not e.skip_stitching) or 1

        self._colors_table.setRowCount(len(entries))

        for row, entry in enumerate(entries):
            # Farbe
            color = to_qcolor(entry.thread.color)
            color_item = QTableWidgetItem()
            color_item.setBackground(QBrush(color))
            self._colors_table.setItem(row, 0, color_item)

            # Symbol (mit Skip-Markierung)
            symbol_text = f"⊘ {entry.symbol}" if entry.skip_stitching else entry.symbol
            symbol_item = QTableWidgetItem(symbol_text)
            if entry.skip_stitching:
                symbol_item.setForeground(QBrush(QColor(255, 152, 0)))  # Orange
            self._colors_table.setItem(row, 1, symbol_item)

            # Name (mit Skip-Markierung)
            name_text = (
                f"{entry.thread.name} (nicht sticken)"
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
            stitch_item = QTableWidgetItem()
            stitch_item.setData(Qt.ItemDataRole.DisplayRole, entry.stitch_count)
            if entry.skip_stitching:
                stitch_item.setForeground(QBrush(QColor(THEME.text_muted)))
            self._colors_table.setItem(row, 5, stitch_item)

            # Prozent (nur für nicht-übersprungene)
            if entry.skip_stitching:
                percent_item = QTableWidgetItem("-")
                percent_item.setForeground(QBrush(QColor(THEME.text_muted)))
            else:
                percent = (entry.stitch_count / total) * 100
                percent_item = QTableWidgetItem(f"{percent:.1f}%")
                percent_item.setData(Qt.ItemDataRole.UserRole, percent)
            self._colors_table.setItem(row, 6, percent_item)

    def _recalculate_thread(self) -> None:
        """Berechnet den Garnverbrauch neu."""
        fabric_counts = COMMON_FABRIC_COUNTS
        fabric_count = fabric_counts[self._fabric_combo.currentIndex()]
        stitches_per_skein = self.STITCHES_PER_SKEIN.get(fabric_count, 500)
        waste_factor = 1 + (self._waste_spin.value() / 100)
        price = self._price_spin.value()

        # Nur nicht-übersprungene Farben
        entries = [e for e in self._pattern.color_entries if not e.skip_stitching]
        self._thread_table.setRowCount(len(entries))

        total_skeins = 0
        total_cost = 0

        for row, entry in enumerate(entries):
            # Farbe
            color = to_qcolor(entry.thread.color)
            color_item = QTableWidgetItem()
            color_item.setBackground(QBrush(color))
            self._thread_table.setItem(row, 0, color_item)

            # Name
            self._thread_table.setItem(row, 1, QTableWidgetItem(entry.thread.name))

            # Stiche
            stitch_item = QTableWidgetItem()
            stitch_item.setData(Qt.ItemDataRole.DisplayRole, entry.stitch_count)
            self._thread_table.setItem(row, 2, stitch_item)

            # Stränge (genau)
            if entry.stitch_count > 0:
                exact_skeins = entry.stitch_count / stitches_per_skein
                self._thread_table.setItem(row, 3, QTableWidgetItem(f"{exact_skeins:.2f}"))

                # Stränge mit Zuschlag (aufgerundet)
                import math

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

    def _recalculate_time(self) -> None:
        """Berechnet die Zeitschätzung neu."""
        skill = self._skill_combo.currentText()
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
            color = to_qcolor(entry.thread.color)
            color_item = QTableWidgetItem()
            color_item.setBackground(QBrush(color))
            self._time_table.setItem(row, 0, color_item)

            # Name
            self._time_table.setItem(row, 1, QTableWidgetItem(entry.thread.name))

            # Stiche
            stitch_item = QTableWidgetItem()
            stitch_item.setData(Qt.ItemDataRole.DisplayRole, entry.stitch_count)
            self._time_table.setItem(row, 2, stitch_item)

            # Zeit
            color_seconds = entry.stitch_count * seconds_per_stitch
            if color_seconds < 60:
                time_str = f"{color_seconds:.0f} s"
            elif color_seconds < 3600:
                time_str = f"{color_seconds / 60:.0f} min"
            else:
                time_str = f"{color_seconds / 3600:.1f} h"
            self._time_table.setItem(row, 3, QTableWidgetItem(time_str))

    def _on_export_csv(self) -> None:
        """Exportiert die Statistiken als CSV."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            t("Statistiken exportieren"),
            f"{self._pattern.name}_statistik.csv",
            t("CSV-Dateien (*.csv)"),
        )

        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                # Header
                f.write(
                    "Symbol,Name,Hersteller,Katalognummer,Stiche,Prozent,Stränge,Kosten,Nicht sticken\n"
                )

                # Daten
                fabric_counts = COMMON_FABRIC_COUNTS
                fabric_count = fabric_counts[self._fabric_combo.currentIndex()]
                stitches_per_skein = self.STITCHES_PER_SKEIN.get(fabric_count, 500)
                waste_factor = 1 + (self._waste_spin.value() / 100)
                price = self._price_spin.value()

                # Nur nicht-übersprungene für Prozent
                total = (
                    sum(e.stitch_count for e in self._pattern.color_entries if not e.skip_stitching)
                    or 1
                )

                import math

                for entry in self._pattern.color_entries:
                    if entry.skip_stitching:
                        percent = "-"
                        with_waste = 0
                        cost = 0
                    else:
                        percent = f"{(entry.stitch_count / total) * 100:.1f}%"
                        exact_skeins = entry.stitch_count / stitches_per_skein
                        with_waste = (
                            math.ceil(exact_skeins * waste_factor) if entry.stitch_count > 0 else 0
                        )
                        cost = with_waste * price

                    skip_flag = "Ja" if entry.skip_stitching else "Nein"

                    f.write(
                        f"{entry.symbol},{entry.thread.name},"
                        f"{entry.thread.manufacturer or '-'},"
                        f"{entry.thread.catalog_number or '-'},"
                        f"{entry.stitch_count},{percent},"
                        f"{with_waste},{cost:.2f},{skip_flag}\n"
                    )

            QMessageBox.information(
                self, t("Export erfolgreich"), f"Statistiken exportiert nach:\n{path}"
            )

        except OSError as e:
            QMessageBox.critical(self, t("Fehler"), f"Export fehlgeschlagen:\n{e}")
