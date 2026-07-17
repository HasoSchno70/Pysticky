"""
PatternDiffDialog: zeigt zwei Patterns nebeneinander mit Diff-Overlay.

Layout (3 Spalten):
  +----------------+----------------+----------------+
  |  Alt           |  Neu           |  Diff (Maske)  |
  +----------------+----------------+----------------+
  |  Stats: X added, Y removed, Z changed            |
  +--------------------------------------------------+
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
)

from ...core.i18n import t
from ...core.pattern import Pattern
from ...core.pattern_diff import (
    DIFF_ADDED,
    DIFF_CHANGED,
    DIFF_REMOVED,
    DiffResult,
)
from ..styles import THEME

# Farben für die Diff-Visualisierung
COLOR_ADDED = QColor(60, 200, 60, 220)  # grün
COLOR_REMOVED = QColor(220, 70, 70, 220)  # rot
COLOR_CHANGED = QColor(240, 180, 50, 220)  # gelb


class PatternDiffDialog(QDialog):
    """Visueller Diff zwischen zwei Patterns."""

    # Pixel pro Stich
    CELL_SIZE = 6

    def __init__(
        self,
        old_pattern: Pattern,
        new_pattern: Pattern,
        diff: DiffResult,
        snapshot_name: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._old = old_pattern
        self._new = new_pattern
        self._diff = diff

        title = t("Pattern-Vergleich")
        if snapshot_name:
            title += f" — {snapshot_name}"
        self.setWindowTitle(title)
        self.setMinimumSize(900, 560)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Stats-Zeile oben
        s = self._diff.stats
        stats_text = (
            f"<b>Vergleich:</b> "
            f"<span style='color:#3c8;'>+{s.added} hinzugefuegt</span> &middot; "
            f"<span style='color:#d44;'>-{s.removed} entfernt</span> &middot; "
            f"<span style='color:#dba;'>~{s.changed} geändert</span> &middot; "
            f"{s.same} unverändert"
        )
        if s.size_changed:
            stats_text += (
                f" &middot; <span style='color:#888;'>Größe: alt "
                f"{self._old.width}×{self._old.height} → neu "
                f"{self._new.width}×{self._new.height}</span>"
            )
        stats = QLabel(stats_text)
        stats.setTextFormat(Qt.TextFormat.RichText)
        stats.setStyleSheet(
            f"padding: 8px; background: {THEME.bg_light}; "
            f"color: {THEME.text_primary}; border-radius: 4px;"
        )
        layout.addWidget(stats)

        # Drei Spalten
        cols = QHBoxLayout()
        cols.addWidget(self._make_column(t("Alt"), self._render_pattern(self._old)))
        cols.addWidget(self._make_column(t("Neu"), self._render_pattern(self._new)))
        cols.addWidget(self._make_column(t("Diff"), self._render_diff()))
        layout.addLayout(cols, 1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton(t("Schließen"))
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _make_column(self, title: str, pixmap: QPixmap) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        column_layout = QVBoxLayout(frame)

        header = QLabel(f"<b>{title}</b>")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        column_layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel()
        label.setPixmap(pixmap)
        label.setStyleSheet("background: white;")
        scroll.setWidget(label)
        column_layout.addWidget(scroll, 1)
        return frame

    def _render_pattern(self, pattern: Pattern) -> QPixmap:
        """Rendert ein Pattern als Pixmap (nearest-neighbor, CELL_SIZE pro Stich)."""
        w = pattern.width
        h = pattern.height
        grid = pattern.layer_stack.get_composite_grid()

        # numpy-Array mit Hintergrund (Stoff-weiss)
        img_array = np.full((h, w, 3), 250, dtype=np.uint8)
        for i, entry in enumerate(pattern.color_entries):
            mask = grid == i
            if np.any(mask):
                c = entry.thread.color
                img_array[mask] = [c.r, c.g, c.b]

        img = QImage(img_array.data, w, h, w * 3, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(img.copy())
        return pixmap.scaled(
            w * self.CELL_SIZE,
            h * self.CELL_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

    def _render_diff(self) -> QPixmap:
        """Rendert die Diff-Maske als farbiges Overlay über dem neuen Pattern."""
        # Basis: Neues Pattern hell ausgrauen, dann Diff-Farben dramurber
        new = self._new
        w = self._diff.stats.width
        h = self._diff.stats.height

        # Hintergrund: ausgegrautes neues Pattern
        img_array = np.full((h, w, 3), 235, dtype=np.uint8)
        new_grid = new.layer_stack.get_composite_grid()
        for i, entry in enumerate(new.color_entries):
            if i >= len(new.color_entries):
                break
            mask = (new_grid == i) if (i < new.width and h >= new.height) else None
            # vorsichtige Bounds
            if mask is None or mask.shape != new_grid.shape:
                continue
            if new.height <= h and new.width <= w:
                # Im Bounding-Bereich einfärben (etwas heller)
                c = entry.thread.color
                # Mischung: 50% color + 50% hellgrau, damit Diff drüber besser sichtbar wird
                gray_mix = np.array(
                    [
                        (c.r + 235) // 2,
                        (c.g + 235) // 2,
                        (c.b + 235) // 2,
                    ],
                    dtype=np.uint8,
                )
                sub_mask = np.zeros((h, w), dtype=bool)
                sub_mask[: new.height, : new.width] = mask
                img_array[sub_mask] = gray_mix

        # Diff-Overlay
        mask = self._diff.mask
        img_array[mask == DIFF_ADDED] = [COLOR_ADDED.red(), COLOR_ADDED.green(), COLOR_ADDED.blue()]
        img_array[mask == DIFF_REMOVED] = [
            COLOR_REMOVED.red(),
            COLOR_REMOVED.green(),
            COLOR_REMOVED.blue(),
        ]
        img_array[mask == DIFF_CHANGED] = [
            COLOR_CHANGED.red(),
            COLOR_CHANGED.green(),
            COLOR_CHANGED.blue(),
        ]

        img = QImage(img_array.data, w, h, w * 3, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(img.copy())
        return pixmap.scaled(
            w * self.CELL_SIZE,
            h * self.CELL_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
