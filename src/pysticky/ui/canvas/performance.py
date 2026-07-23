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
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, Qt

from ...core.stitch_shapes import (
    bead_radius_factor,
    diamond_inset_pixels,
    diamond_should_draw_edge,
    french_knot_radius_factor,
    is_bead,
    is_diamond,
    is_french_knot,
    normalized_partial_stitch_shape,
)

if TYPE_CHECKING:
    from ...core import Pattern
    from ...core.color_blindness import ColorBlindType
    from .canvas import CrossStitchCanvas


# Schwellwert ab dem Performance-Modus automatisch aktiviert wird
LARGE_PATTERN_THRESHOLD = 200 * 200  # 40.000 Zellen


def _draw_diamond_drill_perf(
    painter: "QPainter", x: int, y: int, size: int, color: "QColor"
) -> None:
    """Zeichnet einen Diamond-Painting-Drill im Chunk-Cache-Pfad.

    Duplikat von RenderingMixin._draw_diamond_drill (Direkt-Render-Pfad) --
    facettiertes Quadrat statt flachem Rechteck.
    """
    inset = int(diamond_inset_pixels(size))
    x0 = x + inset
    y0 = y + inset
    x1 = x + size - inset
    y1 = y + size - inset
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0

    top = QPainterPath()
    top.moveTo(x0, y0)
    top.lineTo(x1, y0)
    top.lineTo(cx, cy)
    top.closeSubpath()

    right = QPainterPath()
    right.moveTo(x1, y0)
    right.lineTo(x1, y1)
    right.lineTo(cx, cy)
    right.closeSubpath()

    bottom = QPainterPath()
    bottom.moveTo(x1, y1)
    bottom.lineTo(x0, y1)
    bottom.lineTo(cx, cy)
    bottom.closeSubpath()

    left = QPainterPath()
    left.moveTo(x0, y1)
    left.lineTo(x0, y0)
    left.lineTo(cx, cy)
    left.closeSubpath()

    alpha = color.alpha()

    def _shift(c: "QColor", factor: int) -> "QColor":
        shifted = c.lighter(factor) if factor >= 100 else c.darker(200 - factor)
        shifted.setAlpha(alpha)
        return shifted

    c_top = _shift(color, 145)
    c_right = _shift(color, 110)
    c_left = _shift(color, 95)
    c_bottom = _shift(color, 70)

    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.fillPath(top, c_top)
    painter.fillPath(right, c_right)
    painter.fillPath(bottom, c_bottom)
    painter.fillPath(left, c_left)

    if diamond_should_draw_edge(size):
        edge = QColor(0, 0, 0, min(120, alpha))
        painter.setPen(QPen(edge, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(x0, y0, x1 - x0, y1 - y0)

    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)


def _fill_partial_stitch_perf(
    painter: "QPainter", x: int, y: int, size: int, stype: int, color: "QColor"
) -> None:
    """Füllt einen halben/Viertel-Stich oder French-Knot im Chunk-Cache-Pfad."""
    if is_diamond(stype):
        _draw_diamond_drill_perf(painter, x, y, size, color)
        return

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
        # Wert ist (Pixmap, Render-Parameter) -- die Parameter werden bei
        # jedem Zugriff mit den aktuellen verglichen, damit z.B. ein
        # Zoom-Wechsel (cell_size) oder "Nur aktive Ebene"/"Andere Ebenen
        # abdunkeln" nicht einen bei anderen Einstellungen gerenderten,
        # falsch skalierten oder inhaltlich falschen Pixmap wiederverwendet.
        self._chunk_cache: dict[tuple[int, int], tuple[QPixmap, tuple]] = {}
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

        # rect.right()/bottom() sind inklusiv (Qt-Konvention) -- eine simple
        # Ganzzahl-Division liefert bereits den korrekten letzten
        # Chunk-Index. Das vorherige "+ self._chunk_size" vor der Division
        # markierte dadurch systematisch eine Chunk-Reihe/Spalte zu viel als
        # dirty.
        start_cx = rect.left() // self._chunk_size
        start_cy = rect.top() // self._chunk_size
        end_cx = rect.right() // self._chunk_size
        end_cy = rect.bottom() // self._chunk_size

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
        fabric_texture: bool = False,
        diamond_view: bool = False,
        empty_color: QColor | None = None,
        colorblind_mode: "ColorBlindType | None" = None,
        symbol_font_family: str | None = None,
        symbol_size_offset: int = 0,
        device_pixel_ratio: float = 1.0,
    ) -> QPixmap | None:
        """
        Gibt den gecachten Chunk zurück, oder None wenn er neu gerendert werden muss.
        """
        if not self._enabled:
            return None

        key = (chunk_x, chunk_y)
        params = (
            cell_size,
            show_colors,
            show_symbols,
            show_only_active,
            dim_other_layers,
            fabric_texture,
            diamond_view,
            empty_color.name() if empty_color is not None else None,
            colorblind_mode,
            symbol_font_family,
            symbol_size_offset,
            device_pixel_ratio,
        )

        # Dirty?
        if key in self._dirty_chunks:
            self._dirty_chunks.discard(key)
            if key in self._chunk_cache:
                del self._chunk_cache[key]
            self._stats["cache_misses"] += 1
            return None

        # Im Cache -- aber nur gültig, wenn mit denselben Render-Parametern
        # erzeugt (siehe Kommentar an _chunk_cache oben).
        if key in self._chunk_cache:
            cached_pixmap, cached_params = self._chunk_cache[key]
            if cached_params == params:
                self._stats["cache_hits"] += 1
                return cached_pixmap
            del self._chunk_cache[key]

        self._stats["cache_misses"] += 1
        return None

    def cache_chunk(
        self,
        chunk_x: int,
        chunk_y: int,
        pixmap: QPixmap,
        cell_size: int = 0,
        show_colors: bool = True,
        show_symbols: bool = True,
        show_only_active: bool = False,
        dim_other_layers: bool = False,
        fabric_texture: bool = False,
        diamond_view: bool = False,
        empty_color: QColor | None = None,
        colorblind_mode: "ColorBlindType | None" = None,
        symbol_font_family: str | None = None,
        symbol_size_offset: int = 0,
        device_pixel_ratio: float = 1.0,
    ) -> None:
        """Speichert einen Chunk im Cache, zusammen mit den Render-Parametern
        gegen die spätere get_cached_chunk()-Aufrufe validieren."""
        if not self._enabled:
            return

        params = (
            cell_size,
            show_colors,
            show_symbols,
            show_only_active,
            dim_other_layers,
            fabric_texture,
            diamond_view,
            empty_color.name() if empty_color is not None else None,
            colorblind_mode,
            symbol_font_family,
            symbol_size_offset,
            device_pixel_ratio,
        )
        self._chunk_cache[(chunk_x, chunk_y)] = (pixmap, params)
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
    fabric_pixmap: QPixmap | None = None,
    diamond_view: bool = False,
    colorblind_mode: "ColorBlindType | None" = None,
    device_pixel_ratio: float = 1.0,
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
        fabric_pixmap: Aida-Textur-Tile (canvas._get_fabric_pixmap()), oder
            None für eine flache Farbfüllung. Chunk-Grenzen liegen immer
            auf Zellgrenzen, daher kachelt die Textur ohne Transform-Offset.
        diamond_view: DP-Klebegrund-Hintergrund statt Aida-Textur.
        colorblind_mode: Farbblindheits-Simulation (wie im Direkt-Render-
            Pfad, `RenderingMixin`) -- ohne das blieb die Simulation auf
            großen (Performance-Mode-)Mustern wirkungslos.
        device_pixel_ratio: `canvas.devicePixelRatioF()` zum Aufnahmezeitpunkt.
            Ohne dies wurde die Pixmap immer mit 1 physischem Pixel pro
            logischem Pixel angelegt -- auf einem HiDPI-Bildschirm (125/150/
            200% Windows-Skalierung) zeichnet `QPainter.drawPixmap()` sie dann
            unscharf hochskaliert, weil ihr die physische Auflösung fehlt, die
            der direkte (Nicht-Chunk-)Renderpfad automatisch bekommt. Die
            Pixmap wird deshalb in physischen Pixeln angelegt und per
            `setDevicePixelRatio()` markiert; alle Zeichenoperationen unten
            bleiben unverändert in logischen Koordinaten, da QPainter das
            Skalieren für ein Gerät mit gesetztem DPR selbst übernimmt.

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

    # Pixmap erstellen -- physische Pixel-Größe, damit die Zellen auf einem
    # HiDPI-Bildschirm scharf statt hochskaliert-unscharf gezeichnet werden
    # (siehe device_pixel_ratio-Docstring oben).
    pixel_width = width * cell_size
    pixel_height = height * cell_size
    pixmap = QPixmap(
        max(1, round(pixel_width * device_pixel_ratio)),
        max(1, round(pixel_height * device_pixel_ratio)),
    )
    pixmap.setDevicePixelRatio(device_pixel_ratio)

    if diamond_view:
        pixmap.fill(QColor(235, 232, 220))
    else:
        pixmap.fill(empty_color)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    if not diamond_view and fabric_pixmap is not None and not fabric_pixmap.isNull():
        from PySide6.QtGui import QBrush

        painter.fillRect(pixmap.rect(), QBrush(fabric_pixmap))

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
                tr, tg, tb = thread_color.r, thread_color.g, thread_color.b

                # Farbblindheits-Simulation (wie RenderingMixin._draw_all_cells)
                if colorblind_mode is not None and colorblind_mode.value != "none":
                    from ...core.color_blindness import simulate_color

                    tr, tg, tb = simulate_color(tr, tg, tb, colorblind_mode)

                alpha = int(opacity * 255)
                color_key = (tr << 24) | (tg << 16) | (tb << 8) | alpha

                if color_key not in color_cache:
                    color_cache[color_key] = QColor(tr, tg, tb, alpha)

                fill_color = color_cache[color_key]

                # Zelle füllen — voll (Rect), Drill (Diamond-View) oder
                # Polygon für halbe/Viertel. Im Diamond-View werden FULL-
                # Stiche als Drill gerendert, konsistent mit dem
                # Direkt-Render-Pfad (RenderingMixin._draw_layer_cells).
                if show_colors:
                    stype = layer.get_stitch_type(gx, gy)
                    if is_diamond(stype) or (diamond_view and stype == 0):
                        _draw_diamond_drill_perf(painter, px, py, cell_size, fill_color)
                    elif stype == 0:
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
