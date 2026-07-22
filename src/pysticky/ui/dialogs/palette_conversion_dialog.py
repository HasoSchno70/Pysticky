"""
Dialog zur Konvertierung der Farbpalette.

Ermöglicht die Konvertierung aller Farben eines Musters
von einem Hersteller zu einem anderen (z.B. DMC → Anchor).
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ...core.color_math import delta_e
from ...core.i18n import t
from ...core.palette import ThreadPalette, get_palette_manager
from ...core.thread import Thread, ThreadColor
from ..color_utils import color_swatch_icon
from ..styles import THEME, Styles

if TYPE_CHECKING:
    from ...core import Pattern


def _color_distance(c1: ThreadColor, c2: ThreadColor) -> float:
    """Perzeptuelle Farbdistanz (CIEDE2000 Delta-E in Lab)."""
    return delta_e((c1.r, c1.g, c1.b), (c2.r, c2.g, c2.b))


class _TargetThreadSelector(QDialog):
    """Sub-Dialog zum manuellen Auswählen eines Ziel-Garns."""

    def __init__(
        self,
        source_thread: Thread,
        target_palette: ThreadPalette,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._source = source_thread
        self._palette = target_palette
        self._selected_thread: Thread | None = None

        self.setWindowTitle(t("Ziel-Garn wählen"))
        self.setMinimumSize(550, 500)
        self._setup_ui()
        self._apply_theme()
        self._populate()

    # -- UI ---------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # Info
        info = QLabel(
            f"Quellfarbe: <b>{self._source.name}</b> "
            f"({self._source.manufacturer or '-'} {self._source.catalog_number or '-'})"
        )
        info.setStyleSheet(f"color: {THEME.text_primary};")
        layout.addWidget(info)

        # Suchfeld
        self._search = QLineEdit()
        self._search.setPlaceholderText(t("🔍 Nach Name oder Nummer suchen..."))
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_search)
        layout.addWidget(self._search)

        # Tabelle
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["", t("Name"), t("Hersteller"), t("Nr."), t("Abstand")]
        )
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.doubleClicked.connect(self._on_double_click)
        self._table.verticalHeader().setDefaultSectionSize(28)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)
        self._select_btn = QPushButton(t("Auswählen"))
        self._select_btn.setEnabled(False)
        self._select_btn.clicked.connect(self._on_select)
        # _apply_theme() setzt einen eigenen dialogweiten QPushButton-Stil,
        # der die globale :default-Hervorhebung überschreibt.
        self._select_btn.setStyleSheet(Styles.button_primary())
        button_box.addButton(self._select_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        btn_layout.addWidget(button_box)
        layout.addLayout(btn_layout)

        self._table.selectionModel().selectionChanged.connect(
            lambda: self._select_btn.setEnabled(bool(self._table.selectedItems()))
        )

    def _apply_theme(self) -> None:
        self.setStyleSheet(f"""
            QDialog {{ background: {THEME.bg_dark}; }}
            QTableWidget {{
                background: {THEME.bg_medium}; color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark}; gridline-color: {THEME.border_dark};
            }}
            QTableWidget::item:selected {{ background: {THEME.accent_primary}; color: white; }}
            QTableWidget::item:alternate {{ background: {THEME.bg_light}; }}
            QHeaderView::section {{
                background: {THEME.bg_dark}; color: {THEME.text_secondary};
                border: 1px solid {THEME.border_dark}; padding: 4px;
            }}
            QLineEdit {{
                background: {THEME.bg_medium}; color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark}; border-radius: 4px;
                padding: 6px 10px;
            }}
            QLineEdit:focus {{ border-color: {THEME.accent_primary}; }}
            QPushButton {{
                background: {THEME.bg_medium}; color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark}; border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{ background: {THEME.bg_light}; }}
        """)

    def _populate(self) -> None:
        """Befüllt die Tabelle, sortiert nach Farbabstand."""
        src_color = self._source.color
        # Alle Garne mit Distanz berechnen
        self._thread_data: list[tuple[Thread, float]] = []
        for thread in self._palette.threads:
            dist = _color_distance(src_color, thread.color)
            self._thread_data.append((thread, dist))
        self._thread_data.sort(key=lambda x: x[1])

        self._fill_table(self._thread_data)

    def _fill_table(self, data: list[tuple[Thread, float]]) -> None:
        self._table.setRowCount(len(data))
        for row, (thread, dist) in enumerate(data):
            # Farb-Icon
            icon_item = QTableWidgetItem()
            icon_item.setIcon(color_swatch_icon(thread.color, 20, rounded=True))
            icon_item.setData(Qt.ItemDataRole.UserRole, row)
            self._table.setItem(row, 0, icon_item)

            self._table.setItem(row, 1, QTableWidgetItem(thread.name))
            self._table.setItem(row, 2, QTableWidgetItem(thread.manufacturer or "-"))
            self._table.setItem(row, 3, QTableWidgetItem(thread.catalog_number or "-"))

            dist_item = QTableWidgetItem(f"{dist:.1f}")
            dist_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Farb-Indikator
            if dist <= 30:
                dist_item.setForeground(QBrush(QColor("#4CAF50")))
            elif dist <= 60:
                dist_item.setForeground(QBrush(QColor("#FF9800")))
            else:
                dist_item.setForeground(QBrush(QColor("#F44336")))
            self._table.setItem(row, 4, dist_item)

        self._table.resizeColumnToContents(0)
        self._table.resizeColumnToContents(3)
        self._table.resizeColumnToContents(4)

    def _on_search(self, text: str) -> None:
        search = text.strip().lower()
        if not search:
            self._fill_table(self._thread_data)
            return
        filtered = [
            (t, d)
            for t, d in self._thread_data
            if search in t.name.lower()
            or search in (t.catalog_number or "").lower()
            or search in (t.manufacturer or "").lower()
        ]
        self._fill_table(filtered)

    def _on_select(self) -> None:
        row = self._table.currentRow()
        if row >= 0:
            index = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self._selected_thread = self._thread_data[index][0]
            self.accept()

    def _on_double_click(self) -> None:
        self._on_select()

    @property
    def selected_thread(self) -> Thread | None:
        return self._selected_thread


class PaletteConversionDialog(QDialog):
    """Dialog zur Konvertierung einer Farbpalette zu einem anderen Hersteller."""

    def __init__(self, pattern: "Pattern", parent=None) -> None:
        super().__init__(parent)
        self._pattern = pattern
        self._pm = get_palette_manager()
        self._mapping: list[dict] = []  # [{source_entry, target_thread, distance}, ...]

        self.setWindowTitle(t("Palette konvertieren"))
        self.setMinimumSize(800, 550)
        self._setup_ui()
        self._apply_theme()

        # Initial-Palette laden
        if self._palette_combo.count() > 0:
            self._on_palette_changed(0)

    # -- UI ---------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # Ziel-Palette auswählen
        palette_row = QHBoxLayout()
        palette_row.addWidget(QLabel(t("Ziel-Palette:")))
        self._palette_combo = QComboBox()
        palette_names = sorted(self._pm.available_palettes)
        self._palette_combo.addItems(palette_names)
        self._palette_combo.currentIndexChanged.connect(self._on_palette_changed)
        palette_row.addWidget(self._palette_combo)

        self._palette_info = QLabel()
        self._palette_info.setStyleSheet(f"color: {THEME.text_muted};")
        palette_row.addWidget(self._palette_info)
        palette_row.addStretch()
        layout.addLayout(palette_row)

        # Zuordnungstabelle
        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels(
            [
                "",
                t("Quellfarbe"),
                t("Hersteller/Nr."),
                "",
                t("Zielfarbe"),
                t("Hersteller/Nr."),
                t("Abstand"),
                "",
            ]
        )
        h = self._table.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setDefaultSectionSize(32)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table, 1)

        # Zusammenfassung
        self._summary_label = QLabel()
        self._summary_label.setStyleSheet(
            f"color: {THEME.text_secondary}; font-size: 12px; padding: 4px;"
        )
        layout.addWidget(self._summary_label)

        # Footer
        footer = QHBoxLayout()
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)
        self._apply_btn = QPushButton(t("Alle konvertieren"))
        self._apply_btn.clicked.connect(self._on_apply)
        # _apply_theme() setzt einen eigenen dialogweiten QPushButton-Stil,
        # der die globale :default-Hervorhebung überschreibt.
        self._apply_btn.setStyleSheet(Styles.button_primary())
        button_box.addButton(self._apply_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        footer.addStretch()
        footer.addWidget(button_box)
        layout.addLayout(footer)

    def _apply_theme(self) -> None:
        self.setStyleSheet(f"""
            QDialog {{ background: {THEME.bg_dark}; }}
            QLabel {{ color: {THEME.text_primary}; }}
            QTableWidget {{
                background: {THEME.bg_medium}; color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark}; gridline-color: {THEME.border_dark};
            }}
            QTableWidget::item:selected {{ background: {THEME.accent_primary}; color: white; }}
            QTableWidget::item:alternate {{ background: {THEME.bg_light}; }}
            QHeaderView::section {{
                background: {THEME.bg_dark}; color: {THEME.text_secondary};
                border: 1px solid {THEME.border_dark}; padding: 4px;
            }}
            QComboBox {{
                background: {THEME.bg_medium}; color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark}; border-radius: 4px;
                padding: 5px 10px; min-width: 180px;
            }}
            QPushButton {{
                background: {THEME.bg_medium}; color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark}; border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{ background: {THEME.bg_light}; }}
        """)

    # -- Logik ------------------------------------------------------------

    def _on_palette_changed(self, index: int) -> None:
        """Neue Zielpalette ausgewählt → Auto-Matching durchführen."""
        palette_name = self._palette_combo.currentText()
        palette = self._pm.get_palette(palette_name)
        if not palette:
            return

        self._target_palette = palette
        self._palette_info.setText(f"({len(palette)} Farben)")

        # Auto-Matching
        self._mapping.clear()
        for entry in self._pattern.color_entries:
            src_color = entry.thread.color
            matches = palette.find_similar_color(src_color, max_results=1)
            target = matches[0] if matches else None
            dist = _color_distance(src_color, target.color) if target else 999.0
            self._mapping.append(
                {
                    "entry": entry,
                    "target_thread": target,
                    "distance": dist,
                }
            )

        self._refresh_table()

    def _refresh_table(self) -> None:
        """Aktualisiert die Zuordnungstabelle."""
        self._table.setRowCount(len(self._mapping))

        good = acceptable = poor = 0

        for row, m in enumerate(self._mapping):
            entry = m["entry"]
            target: Thread | None = m["target_thread"]
            dist: float = m["distance"]

            # Quell-Icon
            src_icon_item = QTableWidgetItem()
            src_icon_item.setIcon(color_swatch_icon(entry.thread.color, 20, rounded=True))
            self._table.setItem(row, 0, src_icon_item)

            # Quellfarbe Name
            self._table.setItem(row, 1, QTableWidgetItem(entry.thread.name))

            # Quell-Hersteller/Nr
            src_info = f"{entry.thread.manufacturer or '-'} {entry.thread.catalog_number or '-'}"
            self._table.setItem(row, 2, QTableWidgetItem(src_info))

            if target:
                # Ziel-Icon
                tgt_icon_item = QTableWidgetItem()
                tgt_icon_item.setIcon(color_swatch_icon(target.color, 20, rounded=True))
                self._table.setItem(row, 3, tgt_icon_item)

                # Zielfarbe Name
                self._table.setItem(row, 4, QTableWidgetItem(target.name))

                # Ziel-Hersteller/Nr
                tgt_info = f"{target.manufacturer or '-'} {target.catalog_number or '-'}"
                self._table.setItem(row, 5, QTableWidgetItem(tgt_info))

                # Abstand (CIEDE2000 Delta-E: <=10 gut, <=25 akzeptabel)
                dist_item = QTableWidgetItem(f"{dist:.1f}")
                dist_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if dist <= 10:
                    dist_item.setForeground(QBrush(QColor("#4CAF50")))
                    good += 1
                elif dist <= 25:
                    dist_item.setForeground(QBrush(QColor("#FF9800")))
                    acceptable += 1
                else:
                    dist_item.setForeground(QBrush(QColor("#F44336")))
                    poor += 1
                self._table.setItem(row, 6, dist_item)
            else:
                for col in (3, 4, 5):
                    self._table.setItem(row, col, QTableWidgetItem("-"))
                self._table.setItem(row, 6, QTableWidgetItem("?"))
                poor += 1

            # Ändern-Button
            change_btn = QPushButton(t("Ändern"))
            change_btn.setFixedSize(70, 26)
            change_btn.clicked.connect(lambda checked, r=row: self._on_change_target(r))
            self._table.setCellWidget(row, 7, change_btn)

        # Spaltenbreiten
        self._table.resizeColumnToContents(0)
        self._table.resizeColumnToContents(3)
        self._table.resizeColumnToContents(6)
        self._table.setColumnWidth(7, 80)

        # Zusammenfassung
        self._summary_label.setText(
            f"Zusammenfassung: "
            f"<span style='color:#4CAF50;'>🟢 {good} gut</span>, "
            f"<span style='color:#FF9800;'>🟡 {acceptable} akzeptabel</span>, "
            f"<span style='color:#F44336;'>🔴 {poor} schlecht</span>"
        )

    def _on_change_target(self, row: int) -> None:
        """Öffnet den Sub-Dialog zum manuellen Ändern eines Ziel-Garns."""
        m = self._mapping[row]
        source_thread = m["entry"].thread

        dialog = _TargetThreadSelector(source_thread, self._target_palette, self)
        if dialog.exec() and dialog.selected_thread:
            new_target = dialog.selected_thread
            new_dist = _color_distance(source_thread.color, new_target.color)
            m["target_thread"] = new_target
            m["distance"] = new_dist
            self._refresh_table()

    def _on_apply(self) -> None:
        """Konvertiert alle Farben."""
        # Prüfung: alle Ziele vorhanden?
        missing = sum(1 for m in self._mapping if m["target_thread"] is None)
        if missing:
            QMessageBox.warning(
                self,
                t("Fehlende Zuordnungen"),
                f"{missing} Farbe(n) haben keine Zuordnung.\n"
                "Bitte weisen Sie allen Farben ein Ziel-Garn zu.",
            )
            return

        # Mehrfachzuordnung warnen: mehrere Quellfarben auf dasselbe Zielgarn
        # gemappt ergibt zwei nicht mehr unterscheidbare Farbeintraege im
        # Muster -- gleiche Lehre wie similar_colors_dialog.py's Merge-
        # Konflikt-Check (dort schon gefixt, hier nie ergaenzt worden).
        targets_seen: dict[tuple, list[str]] = {}
        for m in self._mapping:
            target = m["target_thread"]
            if target is None:
                continue
            key = (target.manufacturer, target.catalog_number, target.name)
            targets_seen.setdefault(key, []).append(m["entry"].thread.name)

        collisions = [names for names in targets_seen.values() if len(names) > 1]
        if collisions:
            details = "\n".join(f"- {', '.join(names)}" for names in collisions)
            reply = QMessageBox.question(
                self,
                t("Mehrfachzuordnung"),
                t(
                    "Mehrere Quellfarben werden auf dieselbe Zielfarbe abgebildet:\n\n"
                    "{details}\n\n"
                    "Das Muster enthält danach nicht mehr unterscheidbare "
                    "Farbeinträge. Trotzdem fortfahren?"
                ).format(details=details),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Schlechte Zuordnungen warnen -- Schwelle (25) muss mit der
        # "poor"/rot-Einfaerbung der Tabelle (Zeile ~403) uebereinstimmen,
        # sonst klickt der Nutzer an sichtbar rot markierten Zeilen vorbei,
        # ohne je eine Warnung zu sehen.
        poor = sum(1 for m in self._mapping if m["distance"] > 25)
        if poor:
            reply = QMessageBox.question(
                self,
                t("Schlechte Zuordnungen"),
                f"{poor} Farbe(n) haben einen hohen Farbabstand (>25).\nTrotzdem konvertieren?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Konvertierung durchführen
        for m in self._mapping:
            m["entry"].thread = m["target_thread"]

        self.accept()
