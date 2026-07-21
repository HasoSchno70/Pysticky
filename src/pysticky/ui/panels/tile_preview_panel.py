"""
Panel zur Vorschau von Muster-Kacheln (Wiederholungsmuster).
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core import Pattern
from ...core.i18n import t
from ...utils import clamp_int
from ..color_utils import to_qcolor
from ..styles import THEME, Styles


class TilePreviewWidget(QFrame):
    """Widget das das Muster als Kacheln anzeigt."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pattern: Pattern | None = None
        self._tiles_x: int = 3
        self._tiles_y: int = 3
        self._show_borders: bool = True
        self._cell_size: int = 4

        self.setMinimumSize(250, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)

    def set_pattern(self, pattern: Pattern) -> None:
        self._pattern = pattern
        self._calculate_cell_size()
        self.update()

    def set_tiles(self, x: int, y: int) -> None:
        self._tiles_x = clamp_int(x, 1, 5)
        self._tiles_y = clamp_int(y, 1, 5)
        self._calculate_cell_size()
        self.update()

    def set_show_borders(self, show: bool) -> None:
        self._show_borders = show
        self.update()

    def _calculate_cell_size(self) -> None:
        if not self._pattern:
            return

        available_w = self.width() - 20
        available_h = self.height() - 30

        total_w = self._pattern.width * self._tiles_x
        total_h = self._pattern.height * self._tiles_y

        if total_w > 0 and total_h > 0:
            cell_w = available_w // total_w
            cell_h = available_h // total_h
            self._cell_size = max(1, min(cell_w, cell_h, 12))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._calculate_cell_size()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Hintergrund
        painter.fillRect(self.rect(), QColor(THEME.bg_dark))

        if not self._pattern:
            painter.setPen(QColor(THEME.text_muted))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Kein Muster geladen")
            return

        pw = self._pattern.width
        ph = self._pattern.height
        cs = self._cell_size

        if pw == 0 or ph == 0:
            painter.setPen(QColor(THEME.text_muted))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Leeres Muster")
            return

        # Zentrierung
        total_w = pw * self._tiles_x * cs
        total_h = ph * self._tiles_y * cs
        start_x = (self.width() - total_w) // 2
        start_y = (self.height() - total_h) // 2

        # Kacheln zeichnen
        empty_cell_color = QColor(250, 250, 245)  # Cremeweiß
        grid_color = QColor(200, 200, 200, 80)

        for ty in range(self._tiles_y):
            for tx in range(self._tiles_x):
                tile_x = start_x + tx * pw * cs
                tile_y = start_y + ty * ph * cs

                painter.fillRect(tile_x, tile_y, pw * cs, ph * cs, empty_cell_color)
                self._draw_pattern_tile(painter, tile_x, tile_y, cs)

                if cs >= 4:
                    painter.setPen(QPen(grid_color, 1))
                    for x in range(pw + 1):
                        px = tile_x + x * cs
                        painter.drawLine(px, tile_y, px, tile_y + ph * cs)
                    for y in range(ph + 1):
                        py = tile_y + y * cs
                        painter.drawLine(tile_x, py, tile_x + pw * cs, py)

                if self._show_borders:
                    pen = QPen(QColor(THEME.accent_primary + "99"), 1, Qt.PenStyle.DashLine)
                    painter.setPen(pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(tile_x, tile_y, pw * cs, ph * cs)

        # Hauptkachel hervorheben
        if self._tiles_x >= 3 and self._tiles_y >= 3:
            center_tx = self._tiles_x // 2
            center_ty = self._tiles_y // 2
        else:
            center_tx = 0
            center_ty = 0

        cx = start_x + center_tx * pw * cs
        cy = start_y + center_ty * ph * cs

        pen = QPen(QColor(THEME.accent_primary), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(cx - 1, cy - 1, pw * cs + 2, ph * cs + 2)

        # Info-Text
        painter.setPen(QColor(THEME.text_muted))
        info = f"{pw}×{ph} Stiche | {self._tiles_x}×{self._tiles_y} Kacheln"
        painter.drawText(10, self.height() - 10, info)

    def _draw_pattern_tile(
        self, painter: QPainter, offset_x: int, offset_y: int, cell_size: int
    ) -> None:
        if not self._pattern:
            return

        for layer in self._pattern.layer_stack.layers:
            if not layer.visible:
                continue

            for y in range(layer.height):
                for x in range(layer.width):
                    color_idx = layer.get_stitch(x, y)
                    if color_idx is not None:
                        entry = self._pattern.get_color_entry(color_idx)
                        if entry:
                            color = to_qcolor(entry.thread.color)
                            px = offset_x + x * cell_size
                            py = offset_y + y * cell_size
                            painter.fillRect(px, py, cell_size, cell_size, color)


class TilePreviewPanel(QWidget):
    """Panel für Muster-Kachel-Vorschau."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pattern: Pattern | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Titel
        self._title = QLabel("🔲 " + t("MUSTER-KACHELN"))
        layout.addWidget(self._title)

        # Info
        self._info = QLabel(t("Vorschau für Wiederholungsmuster und Bordüren."))
        self._info.setWordWrap(True)
        layout.addWidget(self._info)

        # Kachel-Anzahl
        tiles_layout = QHBoxLayout()
        tiles_layout.setSpacing(8)

        self._lbl_tiles = QLabel(t("Kacheln:"))
        tiles_layout.addWidget(self._lbl_tiles)

        self._spin_x = QSpinBox()
        self._spin_x.setRange(1, 5)
        self._spin_x.setValue(3)
        self._spin_x.setPrefix("X: ")
        self._spin_x.setFixedWidth(70)
        self._spin_x.valueChanged.connect(self._on_tiles_changed)
        tiles_layout.addWidget(self._spin_x)

        self._spin_y = QSpinBox()
        self._spin_y.setRange(1, 5)
        self._spin_y.setValue(3)
        self._spin_y.setPrefix("Y: ")
        self._spin_y.setFixedWidth(70)
        self._spin_y.valueChanged.connect(self._on_tiles_changed)
        tiles_layout.addWidget(self._spin_y)

        tiles_layout.addStretch()
        layout.addLayout(tiles_layout)

        # Optionen
        self._chk_borders = QCheckBox(t("Kachelgrenzen anzeigen"))
        self._chk_borders.setChecked(True)
        self._chk_borders.toggled.connect(self._on_borders_changed)
        layout.addWidget(self._chk_borders)

        # Vorschau-Widget
        self._preview = TilePreviewWidget()
        layout.addWidget(self._preview, 1)

        self._apply_theme()

    def _apply_theme(self) -> None:
        """Setzt alle THEME-abhaengigen Stylesheets neu -- wird sowohl beim
        initialen Aufbau als auch bei einem Live-Theme-Wechsel aufgerufen.
        Vorher wurden diese Styles nur einmalig in _setup_ui() gesetzt und
        blieben nach einem Theme-Wechsel auf den alten Farben stehen."""
        self.setStyleSheet(f"TilePreviewPanel {{ background: {THEME.bg_medium}; }}")
        self._title.setStyleSheet(Styles.section_header())
        self._info.setStyleSheet(f"color: {THEME.text_muted}; font-size: 10px;")
        self._lbl_tiles.setStyleSheet(f"color: {THEME.text_secondary};")

        spin_style = f"""
            QSpinBox {{
                padding: 4px;
                border: 1px solid {THEME.border_medium};
                border-radius: 4px;
                background: {THEME.bg_dark};
                color: {THEME.text_primary};
            }}
            QSpinBox:hover {{
                border-color: {THEME.accent_primary};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 16px;
                background: {THEME.bg_light};
            }}
        """
        self._spin_x.setStyleSheet(spin_style)
        self._spin_y.setStyleSheet(spin_style)

        self._chk_borders.setStyleSheet(f"""
            QCheckBox {{
                color: {THEME.text_secondary};
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background: {THEME.accent_primary};
            }}
            QCheckBox::indicator:unchecked {{
                background: {THEME.bg_lighter};
                border: 1px solid {THEME.border_medium};
            }}
        """)

        self._preview.update()

    def set_pattern(self, pattern: Pattern) -> None:
        self._pattern = pattern
        self._preview.set_pattern(pattern)

    def refresh(self) -> None:
        if self._pattern:
            self._preview.update()

    def _on_tiles_changed(self) -> None:
        self._preview.set_tiles(self._spin_x.value(), self._spin_y.value())

    def _on_borders_changed(self, checked: bool) -> None:
        self._preview.set_show_borders(checked)
