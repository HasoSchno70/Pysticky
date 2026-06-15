"""
Dialog zum Finden und Zusammenführen ähnlicher Farben.

Berechnet paarweise Farbdistanzen und zeigt Paare unter einem
konfigurierbaren Schwellwert an.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...core.color_math import delta_e
from ..styles import THEME

if TYPE_CHECKING:
    from ...core import Pattern


class _ColorSwatch(QWidget):
    """Kleines Farbfeld."""

    def __init__(self, color: QColor, size: int = 28, parent=None) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(THEME.border_light), 1))
        p.setBrush(QBrush(self._color))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 3, 3)


class _ColorPairRow(QFrame):
    """Zeile für ein Farbpaar mit Merge-Checkbox."""

    def __init__(
        self,
        idx_a: int,
        idx_b: int,
        name_a: str,
        name_b: str,
        color_a: QColor,
        color_b: QColor,
        distance: float,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.idx_a = idx_a
        self.idx_b = idx_b

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self.checkbox = QCheckBox()
        layout.addWidget(self.checkbox)

        layout.addWidget(_ColorSwatch(color_a))
        layout.addWidget(QLabel(f"{name_a}"))
        layout.addWidget(QLabel("  ->  "))
        layout.addWidget(_ColorSwatch(color_b))
        layout.addWidget(QLabel(f"{name_b}"))
        layout.addStretch()
        layout.addWidget(QLabel(f"ΔE: {distance:.1f}"))

        self.setStyleSheet(f"""
            _ColorPairRow {{
                background: {THEME.bg_medium};
                border-radius: 4px;
                margin: 2px 0;
            }}
        """)


class SimilarColorsDialog(QDialog):
    """Dialog zum Zusammenführen ähnlicher Farben."""

    colors_merged = Signal()

    def __init__(self, pattern: "Pattern", parent=None) -> None:
        super().__init__(parent)
        self._pattern = pattern
        self._pair_rows: list[_ColorPairRow] = []

        self.setWindowTitle("Ähnliche Farben zusammenführen")
        self.setMinimumSize(600, 450)
        self._setup_ui()
        self._update_pairs()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Ähnliche Farben finden und zusammenführen")
        title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {THEME.text_primary};")
        layout.addWidget(title)

        # Schwellwert-Slider
        threshold_row = QHBoxLayout()
        threshold_row.addWidget(QLabel("Schwellwert:"))
        self._slider = QSlider(Qt.Orientation.Horizontal)
        # Schwellwert als CIE76 Delta-E: ~5 sehr aehnlich, ~10 Default,
        # ~25 noch zusammenfuehrbar. (Frueher RGB-Euklid 5-150.)
        self._slider.setRange(1, 50)
        self._slider.setValue(10)
        self._slider.valueChanged.connect(self._on_threshold_changed)
        threshold_row.addWidget(self._slider, 1)
        self._threshold_label = QLabel("10")
        self._threshold_label.setMinimumWidth(30)
        threshold_row.addWidget(self._threshold_label)
        layout.addLayout(threshold_row)

        info = QLabel("Niedrigerer Wert = nur sehr ähnliche Farben. Höherer Wert = mehr Paare.")
        info.setStyleSheet(f"color: {THEME.text_muted}; font-size: 10px;")
        layout.addWidget(info)

        # Scrollbereich für Paare
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll_widget = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_widget)
        self._scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._scroll_widget)
        layout.addWidget(self._scroll, 1)

        self._count_label = QLabel()
        self._count_label.setStyleSheet(f"color: {THEME.text_muted};")
        layout.addWidget(self._count_label)

        # Alle auswählen
        select_row = QHBoxLayout()
        select_all = QPushButton("Alle auswählen")
        select_all.clicked.connect(self._select_all)
        select_row.addWidget(select_all)
        select_none = QPushButton("Keine auswählen")
        select_none.clicked.connect(self._select_none)
        select_row.addWidget(select_none)
        select_row.addStretch()
        layout.addLayout(select_row)

        # Buttons
        buttons = QDialogButtonBox()
        self._merge_btn = buttons.addButton(
            "Zusammenführen", QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_merge)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _color_distance(self, idx_a: int, idx_b: int) -> float:
        ca = self._pattern.color_entries[idx_a].thread.color
        cb = self._pattern.color_entries[idx_b].thread.color
        return delta_e((ca.r, ca.g, ca.b), (cb.r, cb.g, cb.b))

    def _on_threshold_changed(self, value: int) -> None:
        self._threshold_label.setText(str(value))
        self._update_pairs()

    def _update_pairs(self) -> None:
        # Alte Rows entfernen
        for row in self._pair_rows:
            self._scroll_layout.removeWidget(row)
            row.deleteLater()
        self._pair_rows.clear()

        threshold = self._slider.value()
        entries = self._pattern.color_entries
        n = len(entries)

        pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                dist = self._color_distance(i, j)
                if dist <= threshold:
                    pairs.append((i, j, dist))

        pairs.sort(key=lambda p: p[2])

        for idx_a, idx_b, dist in pairs:
            ea = entries[idx_a]
            eb = entries[idx_b]
            ca = ea.thread.color
            cb = eb.thread.color
            row = _ColorPairRow(
                idx_a,
                idx_b,
                ea.thread.name,
                eb.thread.name,
                QColor(ca.r, ca.g, ca.b),
                QColor(cb.r, cb.g, cb.b),
                dist,
            )
            self._scroll_layout.addWidget(row)
            self._pair_rows.append(row)

        self._count_label.setText(f"{len(pairs)} Paar(e) gefunden")
        self._merge_btn.setEnabled(len(pairs) > 0)

    def _select_all(self) -> None:
        for row in self._pair_rows:
            row.checkbox.setChecked(True)

    def _select_none(self) -> None:
        for row in self._pair_rows:
            row.checkbox.setChecked(False)

    def _on_merge(self) -> None:
        selected = [r for r in self._pair_rows if r.checkbox.isChecked()]
        if not selected:
            QMessageBox.information(self, "Hinweis", "Keine Paare zum Zusammenführen ausgewählt.")
            return

        count = len(selected)
        reply = QMessageBox.question(
            self,
            "Farben zusammenführen",
            f"{count} Farbpaar(e) zusammenführen?\n\n"
            "Die zweite Farbe jedes Paares wird durch die erste ersetzt.\n"
            "Diese Aktion kann nicht rückgängig gemacht werden.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Sammle Merges: source_index -> target_index
        # Verarbeite in absteigender Reihenfolge des Source-Index
        merges = []
        for row in selected:
            merges.append((row.idx_b, row.idx_a))  # merge B into A

        # Sortiere absteigend nach source_index
        merges.sort(key=lambda m: m[0], reverse=True)

        # Dedupliziere: Jeder Source nur einmal
        seen_sources = set()
        unique_merges = []
        for source, target in merges:
            if source not in seen_sources:
                seen_sources.add(source)
                unique_merges.append((source, target))

        for source_idx, target_idx in unique_merges:
            # Alle Stiche von source nach target verschieben
            for layer in self._pattern.layer_stack:
                layer.replace_color(source_idx, target_idx)
            # Farbe entfernen (verschiebt Indizes)
            self._pattern.remove_color(source_idx)
            # Target-Index anpassen falls nötig
            # (nicht nötig da wir absteigend verarbeiten)

        self.colors_merged.emit()
        self.accept()
