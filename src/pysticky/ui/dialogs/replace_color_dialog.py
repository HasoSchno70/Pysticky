"""
Dialog zum Ersetzen einer Farbe durch eine andere.

Zeigt zur gewählten Quellfarbe die perzeptuell ähnlichsten Farben als
klickbare Vorschlags-Kacheln (mit Verwendungszahl) und eine große
Original/Neu-Vorschau. Zusätzlich: automatische Reduzierung selten
verwendeter Farben ("Konfetti") auf die jeweils ähnlichste häufige Farbe.
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ...core import Pattern
from ...core.color_reduce import compute_rare_color_replacements, rank_similar_colors
from ...core.i18n import t
from ..color_utils import color_swatch_icon
from ..styles import THEME

# Anzahl der Vorschlags-Kacheln (2 Spalten x 4 Zeilen)
_SUGGESTION_COUNT = 8
_SUGGESTION_COLUMNS = 2


def _stitch_count_text(count: int) -> str:
    """'1 Stich' / 'n Stiche' — korrekt dekliniert."""
    return f"{count} {t('Stich') if count == 1 else t('Stiche')}"


class ColorBox(QFrame):
    """Farbbox zur Vorschau."""

    def __init__(self, parent=None, size: int = 40):
        super().__init__(parent)
        self._color = QColor(200, 200, 200)
        self.setFixedSize(size, size)
        self.setFrameStyle(QFrame.Shape.Box)

    def set_color(self, r: int, g: int, b: int) -> None:
        self._color = QColor(r, g, b)
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(2, 2, self.width() - 4, self.height() - 4, self._color)


class ReplaceColorDialog(QDialog):
    """Dialog zum Ersetzen einer Farbe (mit Vorschlägen und Auto-Reduzierung)."""

    def __init__(self, pattern: Pattern, current_color_index: int = 0, parent=None):
        super().__init__(parent)
        self.pattern = pattern
        self._source_index = current_color_index
        self._target_index = 0
        # Ergebnis: Liste (quell_index, ziel_index). Beim manuellen Ersetzen
        # genau ein Eintrag, beim Auto-Reduzieren mehrere.
        self._replacements: list[tuple[int, int]] = []

        self.setWindowTitle(t("Farbe ersetzen"))
        self.setMinimumWidth(480)

        self._setup_ui()
        self._apply_theme()
        self._rebuild_suggestions()
        self._update_preview()
        self._update_reduce_preview()

    # === UI-Aufbau ===

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        desc = QLabel(
            t(
                "Ersetzt alle Stiche einer Farbe durch eine andere Farbe. "
                "Die ersetzte Farbe bleibt in der Palette erhalten."
            )
        )
        desc.setWordWrap(True)
        desc.setObjectName("descLabel")
        layout.addWidget(desc)

        # --- Quellfarbe ---
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel(t("Ersetze:")))

        self.source_combo = QComboBox()
        self._populate_combo(self.source_combo)
        self.source_combo.setCurrentIndex(self._source_index)
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        source_layout.addWidget(self.source_combo, 1)
        layout.addLayout(source_layout)

        # --- Vorschläge ---
        self._suggestion_group = QGroupBox(t("Vorschläge (ähnlichste Farben)"))
        self._suggestion_grid = QGridLayout(self._suggestion_group)
        self._suggestion_grid.setSpacing(6)
        self._suggestion_buttons = QButtonGroup(self)
        self._suggestion_buttons.setExclusive(True)
        self._suggestion_buttons.idClicked.connect(self._on_suggestion_clicked)
        layout.addWidget(self._suggestion_group)

        # --- Zielfarbe + große Vorschau ---
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel(t("Durch:")))
        self.target_combo = QComboBox()
        self._populate_combo(self.target_combo)
        self.target_combo.currentIndexChanged.connect(self._on_target_changed)
        target_layout.addWidget(self.target_combo, 1)
        layout.addLayout(target_layout)

        preview_layout = QHBoxLayout()
        preview_layout.addStretch()

        original_col = QVBoxLayout()
        original_caption = QLabel(t("Original"))
        original_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        original_col.addWidget(original_caption)
        self.source_color_box = ColorBox(size=56)
        original_col.addWidget(self.source_color_box, alignment=Qt.AlignmentFlag.AlignCenter)
        self.source_count_label = QLabel()
        self.source_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.source_count_label.setObjectName("mutedLabel")
        original_col.addWidget(self.source_count_label)
        preview_layout.addLayout(original_col)

        arrow_label = QLabel("➜")
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow_label.setObjectName("arrowLabel")
        preview_layout.addWidget(arrow_label)

        new_col = QVBoxLayout()
        new_caption = QLabel(t("Neu"))
        new_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        new_col.addWidget(new_caption)
        self.target_color_box = ColorBox(size=56)
        new_col.addWidget(self.target_color_box, alignment=Qt.AlignmentFlag.AlignCenter)
        self.target_count_label = QLabel()
        self.target_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.target_count_label.setObjectName("mutedLabel")
        new_col.addWidget(self.target_count_label)
        preview_layout.addLayout(new_col)

        preview_layout.addStretch()
        layout.addLayout(preview_layout)

        self.info_label = QLabel()
        self.info_label.setObjectName("infoLabel")
        layout.addWidget(self.info_label)

        # --- Auto-Reduzieren ---
        reduce_group = QGroupBox(t("Automatisch reduzieren"))
        reduce_layout = QVBoxLayout(reduce_group)

        reduce_row = QHBoxLayout()
        reduce_row.addWidget(QLabel(t("Alle Farben mit höchstens")))
        self.reduce_spin = QSpinBox()
        self.reduce_spin.setRange(1, 999)
        self.reduce_spin.setValue(10)
        self.reduce_spin.valueChanged.connect(self._update_reduce_preview)
        reduce_row.addWidget(self.reduce_spin)
        reduce_row.addWidget(QLabel(t("Stichen ersetzen")))
        reduce_row.addStretch()
        self.reduce_btn = QPushButton(t("Auto-Reduzieren"))
        self.reduce_btn.clicked.connect(self._on_auto_reduce)
        reduce_row.addWidget(self.reduce_btn)
        reduce_layout.addLayout(reduce_row)

        self.reduce_preview_label = QLabel()
        self.reduce_preview_label.setObjectName("mutedLabel")
        self.reduce_preview_label.setWordWrap(True)
        reduce_layout.addWidget(self.reduce_preview_label)

        layout.addWidget(reduce_group)

        # --- Buttons ---
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _apply_theme(self) -> None:
        self.setStyleSheet(f"""
            QLabel#descLabel {{ color: {THEME.text_muted}; }}
            QLabel#mutedLabel {{ color: {THEME.text_muted}; font-size: 10px; }}
            QLabel#infoLabel {{ color: {THEME.text_muted}; font-style: italic; }}
            QLabel#arrowLabel {{
                font-size: 24px; color: {THEME.accent_primary};
                font-weight: bold; padding: 0 12px;
            }}
            QPushButton[suggestion="true"] {{
                text-align: left;
                padding: 4px 8px;
                background: {THEME.bg_medium};
                border: 1px solid {THEME.border_medium};
                border-radius: 4px;
            }}
            QPushButton[suggestion="true"]:hover {{
                border-color: {THEME.accent_primary};
            }}
            QPushButton[suggestion="true"]:checked {{
                border: 2px solid {THEME.accent_primary};
                background: {THEME.bg_light};
            }}
        """)

    def _populate_combo(self, combo: QComboBox) -> None:
        """Füllt eine ComboBox mit den Farben (inkl. Farbquadrat als Icon)."""
        combo.setIconSize(QSize(18, 18))
        for i, entry in enumerate(self.pattern.color_entries):
            thread = entry.thread
            text = f"{entry.symbol} - {thread.manufacturer} {thread.catalog_number or ''} ({thread.name})"
            icon = color_swatch_icon(thread.color, 18)
            combo.addItem(icon, text, i)

    # === Vorschläge ===

    def _rebuild_suggestions(self) -> None:
        """Baut die Vorschlags-Kacheln für die aktuelle Quellfarbe neu."""
        for btn in self._suggestion_buttons.buttons():
            self._suggestion_buttons.removeButton(btn)
            self._suggestion_grid.removeWidget(btn)
            btn.deleteLater()

        ranked = rank_similar_colors(self.pattern, self._source_index)
        for pos, (idx, _dist) in enumerate(ranked[:_SUGGESTION_COUNT]):
            entry = self.pattern.color_entries[idx]
            thread = entry.thread
            label = f"{thread.catalog_number or thread.name}"
            btn = QPushButton(f"{label}\n{_stitch_count_text(entry.stitch_count)}")
            btn.setIcon(color_swatch_icon(thread.color, 24, rounded=True))
            btn.setIconSize(QSize(24, 24))
            btn.setCheckable(True)
            btn.setProperty("suggestion", "true")
            btn.setToolTip(f"{thread.manufacturer} {thread.catalog_number or ''} — {thread.name}")
            self._suggestion_buttons.addButton(btn, idx)
            self._suggestion_grid.addWidget(
                btn, pos // _SUGGESTION_COLUMNS, pos % _SUGGESTION_COLUMNS
            )

        self._suggestion_group.setVisible(bool(ranked))

        # Beste Empfehlung direkt als Ziel vorwählen, solange der Nutzer
        # noch kein eigenes Ziel gewählt hat (Ziel == Quelle wäre nutzlos).
        if ranked and self._target_index == self._source_index:
            self.target_combo.setCurrentIndex(ranked[0][0])

    def _on_suggestion_clicked(self, color_index: int) -> None:
        """Vorschlag angeklickt: als Zielfarbe übernehmen."""
        self.target_combo.setCurrentIndex(color_index)

    # === Änderungs-Handler ===

    def _on_source_changed(self, index: int) -> None:
        self._source_index = index
        self._rebuild_suggestions()
        self._update_preview()

    def _on_target_changed(self, index: int) -> None:
        self._target_index = index
        # Passenden Vorschlag markieren (falls vorhanden), sonst abwählen
        button = self._suggestion_buttons.button(index)
        if button is not None:
            button.setChecked(True)
        else:
            checked = self._suggestion_buttons.checkedButton()
            if checked is not None:
                self._suggestion_buttons.setExclusive(False)
                checked.setChecked(False)
                self._suggestion_buttons.setExclusive(True)
        self._update_preview()

    def _update_preview(self) -> None:
        entries = self.pattern.color_entries
        source_count = 0
        if 0 <= self._source_index < len(entries):
            entry = entries[self._source_index]
            color = entry.thread.color
            self.source_color_box.set_color(color.r, color.g, color.b)
            source_count = entry.stitch_count
            self.source_count_label.setText(_stitch_count_text(source_count))

        if 0 <= self._target_index < len(entries):
            entry = entries[self._target_index]
            color = entry.thread.color
            self.target_color_box.set_color(color.r, color.g, color.b)
            self.target_count_label.setText(_stitch_count_text(entry.stitch_count))

        if source_count > 0:
            self.info_label.setText(t("{n} Stiche werden ersetzt").format(n=source_count))
        else:
            self.info_label.setText(t("Keine Stiche mit dieser Farbe vorhanden"))

    # === Auto-Reduzieren ===

    def _update_reduce_preview(self) -> None:
        """Zeigt live, was die Auto-Reduzierung bewirken würde."""
        replacements = compute_rare_color_replacements(self.pattern, self.reduce_spin.value())
        if not replacements:
            self.reduce_preview_label.setText(t("Keine seltenen Farben unter dieser Schwelle."))
            self.reduce_btn.setEnabled(False)
            return

        entries = self.pattern.color_entries
        stitches = sum(entries[src].stitch_count for src, _ in replacements)
        targets = len({dst for _, dst in replacements})
        self.reduce_preview_label.setText(
            t(
                "{colors} seltene Farbe(n) mit zusammen {stitches} Stichen würden auf {targets} häufige Farbe(n) verteilt."
            ).format(colors=len(replacements), stitches=stitches, targets=targets)
        )
        self.reduce_btn.setEnabled(True)

    def _on_auto_reduce(self) -> None:
        replacements = compute_rare_color_replacements(self.pattern, self.reduce_spin.value())
        if not replacements:
            return

        entries = self.pattern.color_entries
        lines = []
        for src, dst in replacements[:12]:
            src_t = entries[src].thread
            dst_t = entries[dst].thread
            lines.append(
                f"{src_t.catalog_number or src_t.name} ({entries[src].stitch_count}) ➜ "
                f"{dst_t.catalog_number or dst_t.name}"
            )
        if len(replacements) > 12:
            lines.append("…")

        reply = QMessageBox.question(
            self,
            t("Auto-Reduzieren"),
            t("{n} Farbe(n) werden ersetzt:").format(n=len(replacements))
            + "\n\n"
            + "\n".join(lines),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._replacements = replacements
        self.accept()

    # === Ergebnis ===

    def _on_accept(self) -> None:
        if self._source_index == self._target_index:
            QMessageBox.warning(self, t("Hinweis"), t("Quell- und Zielfarbe sind identisch."))
            return
        self._replacements = [(self._source_index, self._target_index)]
        self.accept()

    def get_replacements(self) -> list[tuple[int, int]]:
        """Liste der beschlossenen Ersetzungen als (quell_index, ziel_index)."""
        return list(self._replacements)
