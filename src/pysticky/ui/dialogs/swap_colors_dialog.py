"""
Dialog zum Tauschen zweier Farben (A ⇄ B).
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)

from ...core import Pattern
from ...core.i18n import t
from ..color_utils import color_swatch_icon
from ..styles import THEME
from .replace_color_dialog import ColorBox


class SwapColorsDialog(QDialog):
    """Dialog zum Tauschen zweier Farben (A ⇄ B)."""

    def __init__(self, pattern: Pattern, current_color_index: int = 0, parent=None):
        super().__init__(parent)
        self.pattern = pattern
        self._first_index = current_color_index
        self._second_index = 0
        if len(pattern.color_entries) >= 2 and self._second_index == self._first_index:
            self._second_index = 1 if self._first_index == 0 else 0

        self.setWindowTitle(t("Farben tauschen"))
        self.setMinimumWidth(420)

        self._setup_ui()
        self._update_preview()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        desc = QLabel(
            t(
                "Tauscht alle Stiche zweier Farben gegenseitig.\n"
                "Symbole und Listenreihenfolge bleiben erhalten."
            )
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {THEME.text_muted};")
        layout.addWidget(desc)

        first_row = QHBoxLayout()
        first_row.addWidget(QLabel(t("Farbe A:")))
        self.first_combo = QComboBox()
        self._populate_combo(self.first_combo)
        self.first_combo.setCurrentIndex(self._first_index)
        self.first_combo.currentIndexChanged.connect(self._on_first_changed)
        first_row.addWidget(self.first_combo, 1)
        self.first_color_box = ColorBox()
        first_row.addWidget(self.first_color_box)
        layout.addLayout(first_row)

        arrow_label = QLabel("⇅")
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow_label.setStyleSheet(
            f"font-size: 24px; color: {THEME.accent_primary}; font-weight: bold;"
        )
        layout.addWidget(arrow_label)

        second_row = QHBoxLayout()
        second_row.addWidget(QLabel(t("Farbe B:")))
        self.second_combo = QComboBox()
        self._populate_combo(self.second_combo)
        self.second_combo.setCurrentIndex(self._second_index)
        self.second_combo.currentIndexChanged.connect(self._on_second_changed)
        second_row.addWidget(self.second_combo, 1)
        self.second_color_box = ColorBox()
        second_row.addWidget(self.second_color_box)
        layout.addLayout(second_row)

        self.info_label = QLabel()
        self.info_label.setStyleSheet(f"color: {THEME.text_muted}; font-style: italic;")
        layout.addWidget(self.info_label)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _populate_combo(self, combo: QComboBox) -> None:
        combo.setIconSize(QSize(18, 18))
        for i, entry in enumerate(self.pattern.color_entries):
            thread = entry.thread
            text = f"{entry.symbol} - {thread.manufacturer} {thread.catalog_number or ''} ({thread.name})"
            icon = color_swatch_icon(thread.color, 18)
            combo.addItem(icon, text, i)

    def _on_first_changed(self, index: int) -> None:
        self._first_index = index
        self._update_preview()

    def _on_second_changed(self, index: int) -> None:
        self._second_index = index
        self._update_preview()

    def _update_preview(self) -> None:
        first_count = 0
        second_count = 0
        if 0 <= self._first_index < len(self.pattern.color_entries):
            entry = self.pattern.color_entries[self._first_index]
            self.first_color_box.set_color(
                entry.thread.color.r, entry.thread.color.g, entry.thread.color.b
            )
            first_count = entry.stitch_count
        if 0 <= self._second_index < len(self.pattern.color_entries):
            entry = self.pattern.color_entries[self._second_index]
            self.second_color_box.set_color(
                entry.thread.color.r, entry.thread.color.g, entry.thread.color.b
            )
            second_count = entry.stitch_count

        if first_count == 0 and second_count == 0:
            self.info_label.setText(t("Keine Stiche in beiden Farben"))
        else:
            unit = (
                t("Drills") if getattr(self.pattern, "mode", "stitch") == "diamond" else t("Stiche")
            )
            self.info_label.setText(
                t("{first} ↔ {second} {unit} werden getauscht").format(
                    first=first_count, second=second_count, unit=unit
                )
            )

    def _on_accept(self) -> None:
        if self._first_index == self._second_index:
            QMessageBox.warning(self, t("Hinweis"), t("Bitte zwei unterschiedliche Farben wählen."))
            return
        self.accept()

    def get_first_index(self) -> int:
        return self._first_index

    def get_second_index(self) -> int:
        return self._second_index
