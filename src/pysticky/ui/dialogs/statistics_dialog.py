"""
Muster-Statistik und Garnverbrauch-Rechner Dialog.

Features:
- Detaillierte Stich-Statistiken pro Farbe
- Zeitschätzung für das Sticken
- Garnverbrauch mit Strangberechnung
- Kostenberechnung
- Export als Text/CSV

Die einzelnen Tabs sind eigenständige Widgets im Package `statistics_tabs`.
"""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import t
from ..styles import THEME, Styles
from .dialog_sizing import auto_size_dialog
from .statistics_tabs import (
    STITCHES_PER_SKEIN,
    ColorsTab,
    OverviewTab,
    ProgressTab,
    ShoppingTab,
    ThreadTab,
    TimeTab,
)

if TYPE_CHECKING:
    from ...core import Pattern


class PatternStatisticsDialog(QDialog):
    """Dialog für Muster-Statistiken und Garnverbrauch."""

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
        self._apply_theme()
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
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # Tabs
        tabs = QTabWidget()
        self._tabs = tabs

        # Tab 1: Übersicht
        self._overview_tab = OverviewTab()
        tabs.addTab(self._overview_tab, t("📊 Übersicht"))

        # Tab 2: Farben-Details
        self._colors_tab = ColorsTab()
        tabs.addTab(self._colors_tab, t("🎨 Farben"))

        # Tab 3: Garnverbrauch-Rechner (nur Kreuzstich — DP kennt keine
        # Strang-/Skein-Einheit, Diamanten werden stückweise verbraucht)
        self._thread_tab = ThreadTab()
        thread_idx = tabs.addTab(self._thread_tab, t("🧵 Garnverbrauch"))

        # Tab 4: Zeitschätzung
        self._time_tab = TimeTab()
        tabs.addTab(self._time_tab, t("⏱️ Zeitschätzung"))

        # Tab 5: Fortschritt
        self._progress_tab = ProgressTab()
        tabs.addTab(self._progress_tab, t("✅ Fortschritt"))

        # Tab 6: Einkaufsliste (aus Garn-Vorrat) — ebenfalls nur Kreuzstich
        self._shopping_tab = ShoppingTab()
        shopping_idx = tabs.addTab(self._shopping_tab, t("🛒 Einkaufsliste"))

        if self._pattern.mode == "diamond":
            tabs.setTabVisible(thread_idx, False)
            tabs.setTabVisible(shopping_idx, False)

        self._tab_widgets: list[QWidget] = [
            self._overview_tab,
            self._colors_tab,
            self._thread_tab,
            self._time_tab,
            self._progress_tab,
            self._shopping_tab,
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
        # Diese Datei setzt in _apply_theme() einen eigenen dialogweiten
        # QPushButton-Stil, der die globale :default-Hervorhebung überschreibt
        # — daher hier explizit den sanktionierten Primary-Button-Stil setzen.
        close_btn.setStyleSheet(Styles.button_primary())
        footer.addWidget(button_box)

        layout.addLayout(footer)

    def _apply_theme(self) -> None:
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
                /* alternate-background-color statt ::item:alternate-Regel:
                   die ::item-QSS-Regel uebermalt per setBackground gesetzte
                   Farb-Swatches in geraden Zeilen — die Palette-Variante
                   laesst Item-Hintergruende gewinnen. */
                alternate-background-color: {THEME.bg_light};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
                gridline-color: {THEME.border_dark};
            }}
            QTableWidget::item {{
                padding: 5px;
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
        """Berechnet die Statistiken einmal und reicht sie an alle Tabs durch."""
        stats = self._pattern.get_statistics()

        self._overview_tab.update_stats(self._pattern, stats)
        self._colors_tab.update_stats(self._pattern, stats)
        self._thread_tab.update_stats(self._pattern, stats)
        self._time_tab.update_stats(self._pattern, stats)
        self._progress_tab.update_stats(self._pattern, stats)
        # Denselben Verschnitt-Zuschlag wie der Garnverbrauch-Tab verwenden
        # (siehe ShoppingTab.update_stats()-Docstring) -- calculator_settings()
        # gibt (fabric_count, waste_percent, price_per_skein) zurueck.
        _, waste_percent, _ = self._thread_tab.calculator_settings()
        self._shopping_tab.update_stats(self._pattern, stats, waste_percent)

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
            import csv
            import math

            # newline="" ist bei csv.writer Pflicht (siehe csv-Modul-Doku) --
            # sonst schreibt Windows zusaetzliche Leerzeilen zwischen jeder
            # Datenzeile. csv.writer quotet/escaped Kommas/Anfuehrungszeichen
            # in Farbnamen automatisch -- die vorige rohe f-String-
            # Verkettung verschob bei einem Komma im Namen/Hersteller
            # stillschweigend alle folgenden Spalten.
            # Diamond-Painting kennt keine Strang-/Skein-Einheit (siehe
            # dp-stitch-parity-2026-07-18.md: Garnverbrauch-/Einkaufsliste-
            # Tabs sind im DP-Modus komplett ausgeblendet). Der CSV-Export
            # las trotzdem calculator_settings() vom versteckten ThreadTab
            # (nie mit pattern.fabric_count synchronisiert, defaultet auf
            # Aida-14) und schrieb bedeutungslose Strang-/Kosten-Werte.
            # Diese Spalten werden im DP-Modus jetzt komplett weggelassen.
            is_diamond = self._pattern.mode == "diamond"

            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                header = ["Symbol", "Name", "Hersteller", "Katalognummer", "Stiche", "Prozent"]
                if not is_diamond:
                    header += ["Stränge", "Kosten"]
                header.append("Nicht sticken")
                writer.writerow(header)

                if not is_diamond:
                    # Daten (Rechner-Einstellungen aus dem Garnverbrauch-Tab)
                    fabric_count, waste_percent, price = self._thread_tab.calculator_settings()
                    stitches_per_skein = STITCHES_PER_SKEIN.get(fabric_count, 500)
                    waste_factor = 1 + (waste_percent / 100)

                # Nur nicht-übersprungene für Prozent
                total = (
                    sum(e.stitch_count for e in self._pattern.color_entries if not e.skip_stitching)
                    or 1
                )

                for entry in self._pattern.color_entries:
                    if entry.skip_stitching:
                        percent = "-"
                        with_waste = 0
                        cost = 0.0
                    else:
                        percent = f"{(entry.stitch_count / total) * 100:.1f}%"
                        if not is_diamond:
                            exact_skeins = entry.stitch_count / stitches_per_skein
                            with_waste = (
                                math.ceil(exact_skeins * waste_factor)
                                if entry.stitch_count > 0
                                else 0
                            )
                            cost = with_waste * price

                    skip_flag = "Ja" if entry.skip_stitching else "Nein"

                    # Tweed-Blends (entry.thread.is_blend) werden in ihre
                    # ECHTEN Komponenten-Garne aufgeloest (siehe
                    # Thread.real_components()) -- pro Komponente eine
                    # eigene Zeile mit der vollen Stichzahl, da jeder Stich
                    # einen vollen Strang JEDER Komponente verbraucht.
                    for real_thread in entry.thread.real_components():
                        row = [
                            entry.symbol,
                            real_thread.name,
                            real_thread.manufacturer or "-",
                            real_thread.catalog_number or "-",
                            entry.stitch_count,
                            percent,
                        ]
                        if not is_diamond:
                            row += [with_waste, f"{cost:.2f}"]
                        row.append(skip_flag)
                        writer.writerow(row)

            QMessageBox.information(
                self, t("Export erfolgreich"), f"Statistiken exportiert nach:\n{path}"
            )

        except OSError as e:
            QMessageBox.critical(self, t("Fehler"), f"Export fehlgeschlagen:\n{e}")
