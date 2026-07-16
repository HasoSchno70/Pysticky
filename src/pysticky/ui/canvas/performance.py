"""
Performance-Erweiterungen für den CrossStitchCanvas.

Dieses Modul enthält Mixins und Utilities für verbesserte Performance
bei großen Mustern (500x500+).

Verwendung:
    1. Im MainWindow: canvas.enable_performance_mode() aufrufen
    2. Oder: Automatisch aktiviert wenn Muster > LARGE_PATTERN_THRESHOLD
"""

from typing import TYPE_CHECKING

from ...utils.logging import get_logger

logger = get_logger(__name__)

from PySide6.QtCore import QPointF, QRect
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap, Qt

from ...core.stitch_shapes import (
    bead_radius_factor,
    french_knot_radius_factor,
    is_bead,
    is_french_knot,
    normalized_partial_stitch_shape,
)
from ..color_utils import to_qcolor

if TYPE_CHECKING:
    from ...core import Pattern
    from .canvas import CrossStitchCanvas


# Schwellwert ab dem Performance-Modus automatisch aktiviert wird
LARGE_PATTERN_THRESHOLD = 200 * 200  # 40.000 Zellen


def _fill_partial_stitch_perf(
    painter: "QPainter", x: int, y: int, size: int, stype: int, color: "QColor"
) -> None:
    """Füllt einen halben/Viertel-Stich oder French-Knot im Chunk-Cache-Pfad."""
    if is_french_knot(stype):
        radius = max(1, int(size * french_knot_radius_factor()))
        cx = x + size // 2
        cy = y + size // 2
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(cx - radius, cy - radius, 2 * radius, 2 * radius)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        return

    if is_bead(stype):
        radius = max(2, int(size * bead_radius_factor()))
        cx = x + size // 2
        cy = y + size // 2
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(cx - radius, cy - radius, 2 * radius, 2 * radius)
        # Glanzpunkt
        highlight = color.lighter(150)
        highlight.setAlphaF(0.85)
        painter.setBrush(highlight)
        h_r = max(1, radius // 3)
        painter.drawEllipse(cx - radius // 2, cy - radius // 2, 2 * h_r, 2 * h_r)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        return

    pts = normalized_partial_stitch_shape(stype)
    if not pts:
        painter.fillRect(x, y, size, size, color)
        return
    path = QPainterPath()
    first = True
    for nx, ny in pts:
        px = x + nx * size
        py = y + ny * size
        if first:
            path.moveTo(QPointF(px, py))
            first = False
        else:
            path.lineTo(QPointF(px, py))
    path.closeSubpath()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.fillPath(path, color)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)


class PerformanceManager:
    """
    Verwaltet Performance-Optimierungen für den Canvas.

    Features:
    - Automatische Aktivierung bei großen Mustern
    - Chunk-basiertes Rendering
    - Level-of-Detail
    - Statistiken für Debugging
    """

    def __init__(self, canvas: "CrossStitchCanvas") -> None:
        self._canvas = canvas
        self._enabled = False
        self._chunk_cache: dict[tuple[int, int], QPixmap] = {}
        self._dirty_chunks: set[tuple[int, int]] = set()
        self._chunk_size = 64  # Zellen pro Chunk
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "chunks_rendered": 0,
            "last_frame_time_ms": 0,
        }

    @property
    def enabled(self) -> bool:
        """Gibt zurück ob Performance-Modus aktiv ist."""
        return self._enabled

    def check_auto_enable(self, pattern: "Pattern") -> bool:
        """
        Prüft ob Performance-Modus automatisch aktiviert werden soll.

        Aktiviert wenn: Muster > LARGE_PATTERN_THRESHOLD Zellen
        """
        if pattern is None:
            return False

        cell_count = pattern.width * pattern.height
        should_enable = cell_count > LARGE_PATTERN_THRESHOLD

        if should_enable and not self._enabled:
            self.enable()
            return True
        elif not should_enable and self._enabled:
            self.disable()
            return False

        return self._enabled

    def enable(self) -> None:
        """Aktiviert den Performance-Modus."""
        self._enabled = True
        self._invalidate_all()
        logger.info(
            "Chunk-Caching aktiviert (Chunk-Größe: %dx%d)", self._chunk_size, self._chunk_size
        )

    def disable(self) -> None:
        """Deaktiviert den Performance-Modus."""
        self._enabled = False
        self._chunk_cache.clear()
        self._dirty_chunks.clear()
        logger.info("Chunk-Caching deaktiviert")

    def invalidate_cell(self, x: int, y: int) -> None:
        """Markiert den Chunk mit dieser Zelle als dirty."""
        if not self._enabled:
            return

        chunk_x = x // self._chunk_size
        chunk_y = y // self._chunk_size
        self._dirty_chunks.add((chunk_x, chunk_y))

    def invalidate_region(self, rect: QRect) -> None:
        """Markiert alle Chunks im Bereich als dirty."""
        if not self._enabled:
            return

        start_cx = rect.left() // self._chunk_size
        start_cy = rect.top() // self._chunk_size
        end_cx = (rect.right() + self._chunk_size) // self._chunk_size
        end_cy = (rect.bottom() + self._chunk_size) // self._chunk_size

        for cy in range(start_cy, end_cy + 1):
            for cx in range(start_cx, end_cx + 1):
                self._dirty_chunks.add((cx, cy))

    def _invalidate_all(self) -> None:
        """Invalidiert alle Chunks."""
        self._chunk_cache.clear()
        self._dirty_chunks.clear()

    def invalidate_all(self) -> None:
        """Öffentliche Methode zum Invalidieren aller Chunks."""
        self._invalidate_all()

    def get_cached_chunk(
        self,
        chunk_x: int,
        chunk_y: int,
        pattern: "Pattern",
        cell_size: int,
        show_colors: bool,
        show_symbols: bool,
        show_only_active: bool,
        dim_other_layers: bool,
    ) -> QPixmap | None:
        """
        Gibt den gecachten Chunk zurück, oder None wenn er neu gerendert werden muss.
        """
        if not self._enabled:
            return None

        key = (chunk_x, chunk_y)

        # Dirty?
        if key in self._dirty_chunks:
            self._dirty_chunks.discard(key)
            if key in self._chunk_cache:
                del self._chunk_cache[key]
            self._stats["cache_misses"] += 1
            return None

        # Im Cache?
        if key in self._chunk_cache:
            self._stats["cache_hits"] += 1
            return self._chunk_cache[key]

        self._stats["cache_misses"] += 1
        return None

    def cache_chunk(self, chunk_x: int, chunk_y: int, pixmap: QPixmap) -> None:
        """Speichert einen Chunk im Cache."""
        if not self._enabled:
            return

        self._chunk_cache[(chunk_x, chunk_y)] = pixmap
        self._stats["chunks_rendered"] += 1

    def get_stats(self) -> dict:
        """Gibt Performance-Statistiken zurück."""
        total = self._stats["cache_hits"] + self._stats["cache_misses"]
        hit_rate = (self._stats["cache_hits"] / total * 100) if total > 0 else 0

        return {
            **self._stats,
            "cached_chunks": len(self._chunk_cache),
            "dirty_chunks": len(self._dirty_chunks),
            "hit_rate_percent": round(hit_rate, 1),
            "chunk_size": self._chunk_size,
        }

    def reset_stats(self) -> None:
        """Setzt die Statistiken zurück."""
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "chunks_rendered": 0,
            "last_frame_time_ms": 0,
        }


def render_chunk_to_pixmap(
    pattern: "Pattern",
    chunk_x: int,
    chunk_y: int,
    chunk_size: int,
    cell_size: int,
    empty_color: QColor,
    show_colors: bool,
    show_symbols: bool,
    show_only_active: bool,
    dim_other_layers: bool,
    color_cache: dict[int, QColor],
    symbol_font,
) -> QPixmap:
    """
    Rendert einen Chunk als QPixmap.

    Args:
        pattern: Das Pattern
        chunk_x, chunk_y: Chunk-Indizes
        chunk_size: Zellen pro Chunk
        cell_size: Pixel pro Zelle
        empty_color: Hintergrundfarbe
        show_colors: Farben anzeigen
        show_symbols: Symbole anzeigen
        show_only_active: Nur aktiven Layer anzeigen
        dim_other_layers: Andere Layer abdunkeln
        color_cache: QColor-Cache
        symbol_font: Font für Symbole

    Returns:
        QPixmap mit dem gerenderten Chunk
    """
    # Chunk-Grenzen berechnen
    grid_x = chunk_x * chunk_size
    grid_y = chunk_y * chunk_size
    width = min(chunk_size, pattern.width - grid_x)
    height = min(chunk_size, pattern.height - grid_y)

    if width <= 0 or height <= 0:
        return QPixmap()

    # Pixmap erstellen
    pixel_width = width * cell_size
    pixel_height = height * cell_size
    pixmap = QPixmap(pixel_width, pixel_height)
    pixmap.fill(empty_color)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    if show_symbols and cell_size >= 12:
        painter.setFont(symbol_font)

    # Layer bestimmen
    if show_only_active:
        layers = [pattern.active_layer] if pattern.active_layer else []
    else:
        layers = [l for l in pattern.layer_stack if l.visible]

    active_layer = pattern.active_layer

    # Zellen zeichnen
    for local_y in range(height):
        gy = grid_y + local_y
        py = local_y * cell_size

        for local_x in range(width):
            gx = grid_x + local_x
            px = local_x * cell_size

            for layer in layers:
                color_index = layer.get_stitch(gx, gy)
                if color_index is None:
                    continue

                entry = pattern.get_color_entry(color_index)
                if not entry:
                    continue

                # Deckkraft
                opacity = layer.opacity
                if dim_other_layers and layer != active_layer:
                    opacity *= 0.5

                # Farbe
                thread_color = entry.thread.color
                alpha = int(opacity * 255)
                color_key = (
                    (thread_color.r << 24) | (thread_color.g << 16) | (thread_color.b << 8) | alpha
                )

                if color_key not in color_cache:
                    color_cache[color_key] = to_qcolor(thread_color, alpha)

                fill_color = color_cache[color_key]

                # Zelle füllen — voll (Rect) oder Polygon für halbe/Viertel
                if show_colors:
                    stype = layer.get_stitch_type(gx, gy)
                    if stype == 0:
                        painter.fillRect(px, py, cell_size, cell_size, fill_color)
                    else:
                        _fill_partial_stitch_perf(painter, px, py, cell_size, stype, fill_color)

                # Symbol
                if show_symbols and cell_size >= 12 and opacity >= 0.5:
                    is_light = thread_color.luminance > 0.5
                    painter.setPen(QColor(0, 0, 0) if is_light else QColor(255, 255, 255))
                    painter.drawText(
                        QRect(px, py, cell_size, cell_size),
                        0x84,  # AlignCenter
                        entry.symbol,
                    )

    painter.end()
    return pixmap


def draw_optimized_grid(
    painter: QPainter,
    visible_rect: QRect,
    cell_size: int,
    offset_x: int,
    offset_y: int,
    grid_color: QColor,
    minor_color: QColor,
    major_color: QColor,
    major_interval: int = 10,
    minor_interval: int = 5,
    show_minor: bool = True,
) -> None:
    """
    Zeichnet das Grid optimiert mit Batch-Rendering.

    Gruppiert Linien nach Typ und minimiert Pen-Wechsel.
    """
    from PySide6.QtGui import QPen

    # Bereichsgrenzen
    left = visible_rect.left() * cell_size + offset_x
    right = (visible_rect.left() + visible_rect.width()) * cell_size + offset_x
    top = visible_rect.top() * cell_size + offset_y
    bottom = (visible_rect.top() + visible_rect.height()) * cell_size + offset_y

    # Linien sammeln
    normal_v, normal_h = [], []
    minor_v, minor_h = [], []
    major_v, major_h = [], []

    for x in range(visible_rect.left(), visible_rect.left() + visible_rect.width() + 1):
        sx = x * cell_size + offset_x
        if x % major_interval == 0:
            major_v.append((sx, top, sx, bottom))
        elif show_minor and x % minor_interval == 0:
            minor_v.append((sx, top, sx, bottom))
        else:
            normal_v.append((sx, top, sx, bottom))

    for y in range(visible_rect.top(), visible_rect.top() + visible_rect.height() + 1):
        sy = y * cell_size + offset_y
        if y % major_interval == 0:
            major_h.append((left, sy, right, sy))
        elif show_minor and y % minor_interval == 0:
            minor_h.append((left, sy, right, sy))
        else:
            normal_h.append((left, sy, right, sy))

    # Batch-Zeichnen (minimiert Pen-Wechsel)
    if normal_v or normal_h:
        painter.setPen(QPen(grid_color, 1))
        for line in normal_v + normal_h:
            painter.drawLine(*line)

    if minor_v or minor_h:
        painter.setPen(QPen(minor_color, 1))
        for line in minor_v + minor_h:
            painter.drawLine(*line)

    if major_v or major_h:
        painter.setPen(QPen(major_color, 2))
        for line in major_v + major_h:
            painter.drawLine(*line)


def should_skip_details(cell_size: int) -> tuple[bool, bool, bool]:
    """
    Bestimmt welche Details bei der aktuellen Zellgröße übersprungen werden.

    Returns:
        (skip_symbols, skip_grid, use_simplified)
    """
    skip_symbols = cell_size < 12
    skip_grid = cell_size < 8
    use_simplified = cell_size < 6

    return skip_symbols, skip_grid, use_simplified
