"""
Panel für Farbverlauf-Optionen.
"""

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...core import Pattern
from ...core.i18n import t
from ..styles import THEME, Styles


class ColorPreview(QFrame):
    """Zeigt eine Farbvorschau."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._color = QColor(128, 128, 128)
        self.setFixedSize(40, 40)
        self.setStyleSheet(f"border: 2px solid {THEME.border_medium}; border-radius: 6px;")

    def _apply_theme(self) -> None:
        self.setStyleSheet(f"border: 2px solid {THEME.border_medium}; border-radius: 6px;")
        self.update()

    def set_color(self, color: QColor) -> None:
        self._color = color
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        painter.fillRect(self.contentsRect().adjusted(2, 2, -2, -2), self._color)


class GradientOptionsPanel(QWidget):
    """Panel für Farbverlauf-Einstellungen."""

    start_color_changed = Signal(int)
    end_color_changed = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pattern: Pattern | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Titel
        title = QLabel(t("FARBVERLAUF"))
        title.setStyleSheet(Styles.section_header())
        layout.addWidget(title)

        # Info
        info = QLabel(
            t(
                "Ziehe eine Linie zwischen zwei Punkten.\n"
                "Die Farben werden automatisch interpoliert."
            )
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {THEME.text_muted}; font-size: 10px;")
        layout.addWidget(info)

        # Startfarbe
        start_layout = QHBoxLayout()
        start_label = QLabel(t("Startfarbe:"))
        start_label.setFixedWidth(70)
        start_label.setStyleSheet(f"color: {THEME.text_secondary};")
        start_layout.addWidget(start_label)

        self._start_preview = ColorPreview()
        start_layout.addWidget(self._start_preview)

        self._start_combo = QComboBox()
        self._start_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._start_combo.setStyleSheet(Styles.combo_box())
        self._start_combo.currentIndexChanged.connect(self._on_start_changed)
        start_layout.addWidget(self._start_combo)

        layout.addLayout(start_layout)

        # Endfarbe
        end_layout = QHBoxLayout()
        end_label = QLabel(t("Endfarbe:"))
        end_label.setFixedWidth(70)
        end_label.setStyleSheet(f"color: {THEME.text_secondary};")
        end_layout.addWidget(end_label)

        self._end_preview = ColorPreview()
        end_layout.addWidget(self._end_preview)

        self._end_combo = QComboBox()
        self._end_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._end_combo.setStyleSheet(Styles.combo_box())
        self._end_combo.currentIndexChanged.connect(self._on_end_changed)
        end_layout.addWidget(self._end_combo)

        layout.addLayout(end_layout)

        # Tauschen-Button
        swap_btn = QPushButton("↔ " + t("Farben tauschen"))
        swap_btn.setStyleSheet(Styles.button_secondary())
        swap_btn.clicked.connect(self._on_swap)
        layout.addWidget(swap_btn)

        layout.addStretch()

        self.setStyleSheet(f"GradientOptionsPanel {{ background: {THEME.bg_medium}; }}")

    def _apply_theme(self) -> None:
        self.setStyleSheet(f"GradientOptionsPanel {{ background: {THEME.bg_medium}; }}")
        self._start_combo.setStyleSheet(Styles.combo_box())
        self._end_combo.setStyleSheet(Styles.combo_box())
        self._start_preview._apply_theme()
        self._end_preview._apply_theme()

    def set_pattern(self, pattern: Pattern) -> None:
        self._pattern = pattern
        self._update_combos()

    def _update_combos(self) -> None:
        self._start_combo.blockSignals(True)
        self._end_combo.blockSignals(True)

        self._start_combo.clear()
        self._end_combo.clear()

        if self._pattern:
            for i, entry in enumerate(self._pattern.color_entries):
                name = f"{entry.symbol} {entry.thread.name}"
                self._start_combo.addItem(name, i)
                self._end_combo.addItem(name, i)

            if len(self._pattern.color_entries) >= 2:
                self._start_combo.setCurrentIndex(0)
                self._end_combo.setCurrentIndex(1)
                self._update_previews()

        self._start_combo.blockSignals(False)
        self._end_combo.blockSignals(False)

    def _update_previews(self) -> None:
        if not self._pattern:
            return

        start_idx = self._start_combo.currentData()
        if start_idx is not None and start_idx < len(self._pattern.color_entries):
            entry = self._pattern.color_entries[start_idx]
            self._start_preview.set_color(
                QColor(entry.thread.color.r, entry.thread.color.g, entry.thread.color.b)
            )

        end_idx = self._end_combo.currentData()
        if end_idx is not None and end_idx < len(self._pattern.color_entries):
            entry = self._pattern.color_entries[end_idx]
            self._end_preview.set_color(
                QColor(entry.thread.color.r, entry.thread.color.g, entry.thread.color.b)
            )

    def _on_start_changed(self, index: int) -> None:
        self._update_previews()
        color_idx = self._start_combo.currentData()
        if color_idx is not None:
            self.start_color_changed.emit(color_idx)

    def _on_end_changed(self, index: int) -> None:
        self._update_previews()
        color_idx = self._end_combo.currentData()
        if color_idx is not None:
            self.end_color_changed.emit(color_idx)

    def _on_swap(self) -> None:
        start_idx = self._start_combo.currentIndex()
        end_idx = self._end_combo.currentIndex()
        self._start_combo.setCurrentIndex(end_idx)
        self._end_combo.setCurrentIndex(start_idx)

    @property
    def start_color_index(self) -> int:
        idx = self._start_combo.currentData()
        return idx if idx is not None else 0

    @property
    def end_color_index(self) -> int:
        idx = self._end_combo.currentData()
        return idx if idx is not None else 0

    def set_start_color(self, index: int) -> None:
        if 0 <= index < self._start_combo.count():
            self._start_combo.setCurrentIndex(index)

    def set_end_color(self, index: int) -> None:
        if 0 <= index < self._end_combo.count():
            self._end_combo.setCurrentIndex(index)
