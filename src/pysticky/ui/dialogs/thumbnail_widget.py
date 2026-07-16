"""
Thumbnail-Widget für die Muster-Bibliothek.

Stellt ein einzelnes Muster als anklickbares Vorschaubild
mit Name und Favoriten-Markierung dar.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QContextMenuEvent, QImage, QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from ...core.file_io import load_pattern
from ..color_utils import to_qcolor
from ..styles import THEME
from .pattern_library_data import LibraryEntry


class ThumbnailWidget(QFrame):
    """Widget für ein einzelnes Muster-Thumbnail."""

    clicked = Signal(object)  # Sendet LibraryEntry
    double_clicked = Signal(object)
    context_menu_requested = Signal(object, object)  # Entry, QPoint
    thumbnail_saved = Signal()  # Thumbnail wurde im Cache gespeichert

    def __init__(
        self,
        entry: LibraryEntry,
        thumbnails_dir: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.entry = entry
        self._thumbnails_dir = thumbnails_dir
        self._selected = False

        self.setFixedSize(140, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Thumbnail
        self._thumb_label = QLabel()
        self._thumb_label.setFixedSize(120, 100)
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_label.setStyleSheet(f"""
            background: {THEME.bg_dark};
            border: 1px solid {THEME.border_dark};
            border-radius: 4px;
        """)
        layout.addWidget(self._thumb_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Name
        name_label = QLabel(entry.name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet(f"""
            color: {THEME.text_primary};
            font-size: 11px;
        """)
        name_label.setWordWrap(True)
        name_label.setFixedHeight(36)
        layout.addWidget(name_label)

        # Favoriten-Indikator
        if entry.favorite:
            fav = QLabel("\u2605")
            fav.setStyleSheet(f"color: {THEME.warning}; font-size: 14px;")
            fav.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            fav.move(self.width() - 20, 4)
            fav.setParent(self)

        # Thumbnail laden oder generieren
        self._load_thumbnail()

    def _update_style(self) -> None:
        """Aktualisiert den Style basierend auf Selektion."""
        if self._selected:
            self.setStyleSheet(f"""
                ThumbnailWidget {{
                    background: {THEME.bg_lighter};
                    border: 2px solid {THEME.accent_primary};
                    border-radius: 8px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                ThumbnailWidget {{
                    background: {THEME.bg_medium};
                    border: 1px solid {THEME.border_dark};
                    border-radius: 8px;
                }}
                ThumbnailWidget:hover {{
                    border-color: {THEME.border_light};
                    background: {THEME.bg_light};
                }}
            """)

    def set_selected(self, selected: bool) -> None:
        """Setzt den Selektionszustand."""
        self._selected = selected
        self._update_style()

    def _load_thumbnail(self) -> None:
        """Lädt oder generiert das Thumbnail."""
        # Versuche gespeichertes Thumbnail zu laden
        if self.entry.thumbnail_path:
            thumb_path = Path(self.entry.thumbnail_path)
            if thumb_path.exists():
                pixmap = QPixmap(str(thumb_path))
                if not pixmap.isNull():
                    self._thumb_label.setPixmap(
                        pixmap.scaled(
                            110,
                            90,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                    return

        # Versuche aus Pattern zu generieren
        pattern_path = Path(self.entry.filepath)
        if pattern_path.exists():
            try:
                # Verzögert laden um UI nicht zu blockieren
                QTimer.singleShot(50, self._generate_thumbnail)
            except (OSError, ValueError):
                pass

        # Placeholder
        self._thumb_label.setText(f"{self.entry.width}\u00d7{self.entry.height}")
        self._thumb_label.setStyleSheet(f"""
            background: {THEME.bg_dark};
            border: 1px solid {THEME.border_dark};
            border-radius: 4px;
            color: {THEME.text_muted};
            font-size: 10px;
        """)

    def _generate_thumbnail(self) -> None:
        """Generiert ein Thumbnail aus dem Pattern und speichert es im Cache."""
        try:
            pattern = load_pattern(self.entry.filepath)

            # Skalierung berechnen
            max_size = 100
            scale = min(max_size / pattern.width, max_size / pattern.height, 2)

            img_width = max(1, int(pattern.width * scale))
            img_height = max(1, int(pattern.height * scale))

            image = QImage(img_width, img_height, QImage.Format.Format_RGB32)
            image.fill(QColor(255, 255, 255))

            painter = QPainter(image)

            for y in range(pattern.height):
                for x in range(pattern.width):
                    color_idx = pattern.get_stitch(x, y)
                    if color_idx is not None and 0 <= color_idx < len(pattern.color_entries):
                        color = pattern.color_entries[color_idx].thread.color
                        qcolor = to_qcolor(color)

                        px = int(x * scale)
                        py = int(y * scale)
                        pw = max(1, int(scale))
                        ph = max(1, int(scale))

                        painter.fillRect(px, py, pw, ph, qcolor)

            painter.end()

            pixmap = QPixmap.fromImage(image)
            self._thumb_label.setPixmap(pixmap)

            # Im Cache speichern
            if self._thumbnails_dir and self._thumbnails_dir.exists():
                file_hash = hashlib.md5(self.entry.filepath.encode()).hexdigest()[:16]
                cache_path = self._thumbnails_dir / f"{file_hash}.png"
                image.save(str(cache_path), "PNG")
                self.entry.thumbnail_path = str(cache_path)
                self.thumbnail_saved.emit()

        except (OSError, ValueError):
            pass

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Mausklick-Handler."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.entry)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Doppelklick-Handler."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.entry)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Kontextmenü-Handler."""
        self.context_menu_requested.emit(self.entry, event.globalPos())
