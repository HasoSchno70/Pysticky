"""
Dialog zum Ersetzen einer Farbe durch eine andere.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)

from ...core import Pattern
from ..styles import THEME


class ColorBox(QFrame):
    """Farbbox zur Vorschau."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor(200, 200, 200)
        self.setFixedSize(40, 40)
        self.setFrameStyle(QFrame.Shape.Box)

    def set_color(self, r: int, g: int, b: int) -> None:
        self._color = QColor(r, g, b)
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(2, 2, self.width() - 4, self.height() - 4, self._color)


class ReplaceColorDialog(QDialog):
    """Dialog zum Ersetzen einer Farbe."""

    def __init__(self, pattern: Pattern, current_color_index: int = 0, parent=None):
        super().__init__(parent)
        self.pattern = pattern
        self._source_index = current_color_index
        self._target_index = 0

        self.setWindowTitle("Farbe ersetzen")
        self.setMinimumWidth(400)

        self._setup_ui()
        self._update_preview()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Beschreibung
        desc = QLabel("Ersetzt alle Stiche einer Farbe durch eine andere Farbe.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {THEME.text_muted};")
        layout.addWidget(desc)

        # Quellfarbe
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Ersetze:"))

        self.source_combo = QComboBox()
        self._populate_combo(self.source_combo)
        self.source_combo.setCurrentIndex(self._source_index)
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        source_layout.addWidget(self.source_combo, 1)

        self.source_color_box = ColorBox()
        source_layout.addWidget(self.source_color_box)

        layout.addLayout(source_layout)

        # Pfeil
        arrow_label = QLabel("⬇")
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow_label.setStyleSheet(
            f"font-size: 24px; color: {THEME.accent_primary}; font-weight: bold;"
        )
        layout.addWidget(arrow_label)

        # Zielfarbe
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("Durch:"))

        self.target_combo = QComboBox()
        self._populate_combo(self.target_combo)
        self.target_combo.currentIndexChanged.connect(self._on_target_changed)
        target_layout.addWidget(self.target_combo, 1)

        self.target_color_box = ColorBox()
        target_layout.addWidget(self.target_color_box)

        layout.addLayout(target_layout)

        # Info
        self.info_label = QLabel()
        self.info_label.setStyleSheet(f"color: {THEME.text_muted}; font-style: italic;")
        layout.addWidget(self.info_label)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _populate_combo(self, combo: QComboBox) -> None:
        """Füllt eine ComboBox mit den Farben (inkl. Farbquadrat als Icon)."""
        from PySide6.QtCore import QSize

        from .swap_colors_dialog import _color_icon

        combo.setIconSize(QSize(18, 18))
        for i, entry in enumerate(self.pattern.color_entries):
            thread = entry.thread
            text = f"{entry.symbol} - {thread.manufacturer} {thread.catalog_number or ''} ({thread.name})"
            icon = _color_icon(thread.color.r, thread.color.g, thread.color.b)
            combo.addItem(icon, text, i)

    def _on_source_changed(self, index: int) -> None:
        self._source_index = index
        self._update_preview()

    def _on_target_changed(self, index: int) -> None:
        self._target_index = index
        self._update_preview()

    def _update_preview(self) -> None:
        # Quellfarbe
        if 0 <= self._source_index < len(self.pattern.color_entries):
            entry = self.pattern.color_entries[self._source_index]
            self.source_color_box.set_color(
                entry.thread.color.r, entry.thread.color.g, entry.thread.color.b
            )
            source_count = entry.stitch_count
        else:
            source_count = 0

        # Zielfarbe
        if 0 <= self._target_index < len(self.pattern.color_entries):
            entry = self.pattern.color_entries[self._target_index]
            self.target_color_box.set_color(
                entry.thread.color.r, entry.thread.color.g, entry.thread.color.b
            )

        # Info
        if source_count > 0:
            self.info_label.setText(f"{source_count} Stiche werden ersetzt")
        else:
            self.info_label.setText("Keine Stiche mit dieser Farbe vorhanden")

    def _on_accept(self) -> None:
        if self._source_index == self._target_index:
            QMessageBox.warning(self, "Hinweis", "Quell- und Zielfarbe sind identisch.")
            return

        self.accept()

    def get_source_index(self) -> int:
        """Gibt den Index der Quellfarbe zurück."""
        return self._source_index

    def get_target_index(self) -> int:
        """Gibt den Index der Zielfarbe zurück."""
        return self._target_index
