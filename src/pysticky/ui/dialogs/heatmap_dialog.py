"""
Pattern-Heatmap-Dialog.

Visualisiert das Muster als Heatmap, d.h. jede Rasterzelle (block_size x
block_size Stiche) bekommt eine Farbe zwischen blau (wenig) und rot (viel).

Achsen:
- Stichdichte: Anzahl gesetzter Stiche im Block
- Farbenvielfalt: Anzahl verschiedener Farben im Block
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import t
from ...core.layer import NO_STITCH
from ...utils import clamp
from ..styles import THEME

if TYPE_CHECKING:
    from ...core import Pattern


def _composite_color_grid(pattern: "Pattern") -> np.ndarray:
    """Komposit-Farb-Index pro Zelle (numpy int32, -1 = leer)."""
    H, W = pattern.height, pattern.width
    out = np.full((H, W), NO_STITCH, dtype=np.int32)
    for layer in reversed(pattern.layer_stack.layers):
        if not layer.visible or layer.grid is None:
            continue
        lh, lw = layer.grid.shape
        vh = min(lh, H)
        vw = min(lw, W)
        slot = out[:vh, :vw]
        lg = layer.grid[:vh, :vw]
        mask = (slot == NO_STITCH) & (lg != NO_STITCH)
        if mask.any():
            slot[mask] = lg[mask]
    return out


def _density_heatmap(composite: np.ndarray, block_size: int) -> np.ndarray:
    """Stichdichte pro Block: 2D-Array von floats in [0,1]."""
    H, W = composite.shape
    bs = max(1, block_size)
    bh = (H + bs - 1) // bs
    bw = (W + bs - 1) // bs
    counts = np.zeros((bh, bw), dtype=np.int32)
    occupied = (composite != NO_STITCH).astype(np.int32)
    for by in range(bh):
        y0 = by * bs
        y1 = min(y0 + bs, H)
        for bx in range(bw):
            x0 = bx * bs
            x1 = min(x0 + bs, W)
            counts[by, bx] = occupied[y0:y1, x0:x1].sum()
    max_count = counts.max() if counts.size else 0
    if max_count == 0:
        return counts.astype(np.float32)
    return counts.astype(np.float32) / float(max_count)


def _color_variety_heatmap(composite: np.ndarray, block_size: int) -> np.ndarray:
    """Anzahl unterschiedlicher Farben pro Block: 2D-floats in [0,1]."""
    H, W = composite.shape
    bs = max(1, block_size)
    bh = (H + bs - 1) // bs
    bw = (W + bs - 1) // bs
    variety = np.zeros((bh, bw), dtype=np.int32)
    for by in range(bh):
        y0 = by * bs
        y1 = min(y0 + bs, H)
        for bx in range(bw):
            x0 = bx * bs
            x1 = min(x0 + bs, W)
            block = composite[y0:y1, x0:x1]
            non_empty = block[block != NO_STITCH]
            variety[by, bx] = len(np.unique(non_empty)) if non_empty.size else 0
    max_var = variety.max() if variety.size else 0
    if max_var == 0:
        return variety.astype(np.float32)
    return variety.astype(np.float32) / float(max_var)


def _intensity_to_rgb(intensity: float) -> tuple[int, int, int]:
    """Mapped intensity in [0,1] auf blau -> cyan -> grün -> gelb -> rot."""
    if intensity <= 0.0:
        return (20, 20, 60)  # fast schwarz für leere Blöcke
    intensity = clamp(intensity, 0.0, 1.0)
    # 4 Segmente
    if intensity < 0.25:
        u = intensity / 0.25
        r, g, b = 0, int(255 * u), 255
    elif intensity < 0.5:
        u = (intensity - 0.25) / 0.25
        r, g, b = 0, 255, int(255 * (1 - u))
    elif intensity < 0.75:
        u = (intensity - 0.5) / 0.25
        r, g, b = int(255 * u), 255, 0
    else:
        u = (intensity - 0.75) / 0.25
        r, g, b = 255, int(255 * (1 - u)), 0
    return (r, g, b)


def _heatmap_to_qimage(values: np.ndarray, cell_px: int) -> QImage:
    """Rendert ein normalisiertes 2D-Float-Array als QImage."""
    bh, bw = values.shape
    img_w = max(1, bw * cell_px)
    img_h = max(1, bh * cell_px)
    img = QImage(img_w, img_h, QImage.Format.Format_RGB32)
    img.fill(QColor(20, 20, 30))
    rgb_cache: dict[int, int] = {}
    for by in range(bh):
        for bx in range(bw):
            intensity = float(values[by, bx])
            bucket = int(intensity * 1000)
            if bucket not in rgb_cache:
                r, g, b = _intensity_to_rgb(intensity)
                rgb_cache[bucket] = (0xFF << 24) | (r << 16) | (g << 8) | b
            color = rgb_cache[bucket]
            x0 = bx * cell_px
            y0 = by * cell_px
            for yy in range(y0, min(y0 + cell_px, img_h)):
                for xx in range(x0, min(x0 + cell_px, img_w)):
                    img.setPixel(xx, yy, color)
    return img


class HeatmapDialog(QDialog):
    """Dialog zur Anzeige der Pattern-Heatmap."""

    AXIS_DENSITY = "density"
    AXIS_COLORS = "colors"

    def __init__(self, pattern: "Pattern", parent=None) -> None:
        super().__init__(parent)
        self._pattern = pattern
        self._composite = _composite_color_grid(pattern)
        self._block_size = 8
        self._axis = self.AXIS_COLORS

        self.setWindowTitle(t("Pattern-Heatmap"))
        self.setMinimumSize(700, 600)

        # Debounce fuer resizeEvent -- _refresh_heatmap() rendert per-Pixel
        # (siehe _heatmap_to_qimage()), ein Aufruf pro einzelnem Resize-Event
        # waehrend eines Fenster-Zieh-Vorgangs waere unnoetig teuer.
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(150)
        self._resize_timer.timeout.connect(self._refresh_heatmap)

        self._setup_ui()
        self._refresh_heatmap()

    def resizeEvent(self, event) -> None:
        """Rendert die Heatmap bei Groessenaenderung neu.

        Ohne diesen Override blieb die Heatmap dauerhaft bei der Groesse
        haengen, die der Scroll-Viewport beim Konstruktor-Aufruf hatte --
        Vergroessern/Maximieren des Dialogs aenderte am Bild nichts, bis
        zufaellig Achsen-Combo oder Block-Slider angefasst wurden (beide
        rufen _refresh_heatmap() ohnehin schon auf).
        """
        super().resizeEvent(event)
        self._resize_timer.start()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        controls = QFormLayout()
        controls.setSpacing(8)

        self._axis_combo = QComboBox()
        # Farbenvielfalt zuerst: zeigt beim ersten Blick eine bunte, aussagekräftige
        # Heatmap. Stichdichte ist bei vollflächig gestickten Mustern meist
        # durchgehend rot (ein einziger roter Kasten) und damit als Default weniger
        # anschaulich.
        self._axis_combo.addItem(
            t("Farbenvielfalt (verschiedene Farben pro Block)"), self.AXIS_COLORS
        )
        self._axis_combo.addItem(t("Stichdichte (Anzahl Stiche pro Block)"), self.AXIS_DENSITY)
        self._axis_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        # Popup-Breite explizit an den längsten Item-Text anpassen — sonst kann
        # das Dropdown schmaler als der Text sein und diesen abschneiden.
        self._axis_combo.view().setMinimumWidth(self._axis_combo.minimumSizeHint().width())
        # Popup-Höhe explizit setzen: Qt's automatische Popup-Größe basiert
        # auf sizeHintForRow(), das den globalen QSS-Padding auf
        # "QComboBox QAbstractItemView" nicht mit einrechnet — das Ergebnis
        # ist ein Dropdown, das knapp zu niedrig ist und die letzte Zeile
        # abschneidet. Großzügiger Puffer pro Zeile umgeht das zuverläßig.
        row_height = self._axis_combo.fontMetrics().height() + 14
        self._axis_combo.view().setMinimumHeight(row_height * self._axis_combo.count() + 8)
        self._axis_combo.currentIndexChanged.connect(self._on_axis_changed)
        controls.addRow(t("Achse:"), self._axis_combo)

        slider_row = QHBoxLayout()
        self._block_slider = QSlider(Qt.Orientation.Horizontal)
        self._block_slider.setMinimum(1)
        self._block_slider.setMaximum(32)
        self._block_slider.setValue(self._block_size)
        self._block_slider.setTickInterval(4)
        self._block_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._block_slider.valueChanged.connect(self._on_block_changed)
        slider_row.addWidget(self._block_slider, 1)
        self._block_label = QLabel(f"{self._block_size} px")
        self._block_label.setMinimumWidth(48)
        slider_row.addWidget(self._block_label)
        controls.addRow(t("Block-Größe:"), slider_row)

        layout.addLayout(controls)

        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        layout.addWidget(self._summary_label)

        # Heatmap-Anzeige in ScrollArea, damit grosse Patterns rollbar bleiben.
        # Container-Widget mit eigener V/H-Layout zentriert das Bild im Viewport.
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._image_container = QWidget()
        # Sehr dunkler Hintergrund — die Heatmap-Farben (hell) sollen pop'pen.
        # In beiden Themes konstant dunkel, weil die Heatmap-Skala dunkelblau startet.
        self._image_container.setStyleSheet("background: #0a0a18;")
        container_layout = QHBoxLayout(self._image_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self._image_label)

        self._scroll.setWidget(self._image_container)
        layout.addWidget(self._scroll, 1)

        # Legende: Farbverlauf — voll Dialog-Breite
        self._legend_label = QLabel()
        self._legend_label.setFixedHeight(22)
        self._legend_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._legend_label)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self._render_legend()

    def _on_axis_changed(self, _index: int) -> None:
        self._axis = self._axis_combo.currentData() or self.AXIS_DENSITY
        self._refresh_heatmap()

    def _on_block_changed(self, value: int) -> None:
        self._block_size = max(1, value)
        self._block_label.setText(f"{self._block_size} px")
        self._refresh_heatmap()

    def _refresh_heatmap(self) -> None:
        if self._axis == self.AXIS_COLORS:
            values = _color_variety_heatmap(self._composite, self._block_size)
            label = t("Farbenvielfalt")
        else:
            values = _density_heatmap(self._composite, self._block_size)
            label = t("Stichdichte")

        # Cell-Pixel berechnen: heatmap soll im Scroll-Bereich nicht winzig sein.
        # Kein harter Cap — bei wenigen, grossen Blöcken darf die Heatmap auch
        # gross werden, damit der Dialog ausgefüllt wirkt.
        bh, bw = values.shape
        target_w = max(400, self._scroll.viewport().width() - 20)
        target_h = max(400, self._scroll.viewport().height() - 20)
        cell_px = max(2, min(target_w // max(1, bw), target_h // max(1, bh)))

        img = _heatmap_to_qimage(values, cell_px)
        self._image_label.setPixmap(QPixmap.fromImage(img))
        self._image_label.setFixedSize(img.size())

        bh, bw = values.shape
        nz = int((values > 0).sum())
        self._summary_label.setText(
            f"{label}: {bw}×{bh} Blöcke à {self._block_size} Stich(e), {nz} aktive Blöcke"
        )

    def _render_legend(self) -> None:
        # Legende skaliert mit Dialog-Breite — wir rendern intern in 480px
        # Auflösung und lassen Qt auf die finale Label-Breite skalieren.
        w = 480
        h = 14
        img = QImage(w, h, QImage.Format.Format_RGB32)
        for x in range(w):
            intensity = x / float(w - 1)
            r, g, b = _intensity_to_rgb(intensity)
            color = (0xFF << 24) | (r << 16) | (g << 8) | b
            for y in range(h):
                img.setPixel(x, y, color)
        pixmap = QPixmap.fromImage(img)
        self._legend_label.setPixmap(pixmap)
        self._legend_label.setScaledContents(True)
        self._legend_label.setToolTip(
            t("Links: niedrig — Rechts: hoch (maximaler Wert im Pattern)")
        )
