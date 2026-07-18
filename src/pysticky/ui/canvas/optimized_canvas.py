"""
OptimizedCrossStitchCanvas - Erweiterung von CrossStitchCanvas mit
automatischen Performance-Optimierungen für große Muster.

Verwendung:
    from pysticky.ui.canvas import OptimizedCrossStitchCanvas
    canvas = OptimizedCrossStitchCanvas()
"""

import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QFont, QPainter

from ...utils import clamp_int
from .canvas import CrossStitchCanvas
from .performance import (
    PerformanceManager,
    draw_optimized_grid,
    render_chunk_to_pixmap,
    should_skip_details,
)

if TYPE_CHECKING:
    from ...core import Pattern


class OptimizedCrossStitchCanvas(CrossStitchCanvas):
    """
    Erweiterte Canvas-Klasse mit automatischen Performance-Optimierungen.

    Features:
    - Automatisches Chunk-Caching bei großen Mustern (>200x200)
    - Level-of-Detail basierend auf Zoom-Stufe
    - Optimiertes Grid-Rendering mit Batch-Drawing
    - Performance-Statistiken für Debugging

    Die Klasse ist API-kompatibel zu CrossStitchCanvas und kann
    als Drop-in-Ersatz verwendet werden.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # Performance-Manager
        self._perf_manager = PerformanceManager(self)

        # Debug-Modus für Performance-Anzeige
        self._show_performance_stats = False

        # Frame-Timing
        self._last_frame_time = 0.0

    def set_pattern(self, pattern: "Pattern") -> None:
        """Setzt das Pattern und aktiviert ggf. Performance-Modus."""
        # Performance-Manager prüfen
        self._perf_manager.check_auto_enable(pattern)
        self._perf_manager.invalidate_all()

        # Original-Methode aufrufen
        super().set_pattern(pattern)

    def invalidate_cell(self, x: int, y: int) -> None:
        """Markiert Zelle und zugehörigen Chunk für Neuzeichnung."""
        self._perf_manager.invalidate_cell(x, y)
        super().invalidate_cell(x, y)

    def invalidate_region(self, rect: QRect) -> None:
        """Markiert Region und zugehörige Chunks für Neuzeichnung."""
        self._perf_manager.invalidate_region(rect)
        super().invalidate_region(rect)

    def invalidate_all(self) -> None:
        """Verwirft den gesamten Chunk-Cache."""
        self._perf_manager.invalidate_all()
        super().invalidate_all()

    def paintEvent(self, event) -> None:
        """Überschriebenes paintEvent mit Performance-Optimierungen."""
        start_time = time.perf_counter()

        painter = QPainter(self)
        try:
            self._paint(painter)
        finally:
            painter.end()

        self._last_frame_time = (time.perf_counter() - start_time) * 1000
        self._perf_manager._stats["last_frame_time_ms"] = self._last_frame_time

    def _paint(self, painter: QPainter) -> None:
        # Hintergrund
        painter.fillRect(self.rect(), self._bg_color)

        if not self._pattern:
            self._draw_empty_message(painter)
            return

        visible_rect = self._get_visible_grid_rect()

        # Level-of-Detail prüfen
        skip_symbols, skip_grid, use_simplified = should_skip_details(self._cell_size)

        # Zellen zeichnen
        # Bei aktiver Farb-Isolation den Chunk-Cache umgehen — der gecachte
        # Pfad in render_chunk_to_pixmap kennt die Per-Cell-Alpha-Logik nicht.
        # Bei grossen Mustern verlieren wir dann den Caching-Vorteil; das ist
        # akzeptabel weil Isolation ein temporärer View-Modus ist.
        use_chunk_cache = (
            self._perf_manager.enabled and not use_simplified and self._isolate_color_index is None
        )
        if use_chunk_cache:
            self._draw_cells_chunked(painter, visible_rect, skip_symbols)
        else:
            self._draw_all_cells(painter, visible_rect)

        # Fortschritts-Overlay (erledigte Stiche) — wird OBEN auf die
        # Stich-Schicht gezeichnet, daher zwischen Zellen und Backstitches.
        # Bug-Fix: vorher fehlte das im Optimized-Pfad komplett — der
        # Sticken-Modus zeigte keine Häkchen.
        if self._show_completion:
            self._draw_completion_overlay(painter, visible_rect)

        # Backstitches
        if self._show_backstitches:
            self._draw_backstitches(painter)

        # Grid mit LOD
        if self._show_grid and not skip_grid:
            draw_optimized_grid(
                painter,
                visible_rect,
                self._cell_size,
                self._offset_x,
                self._offset_y,
                self._grid_color,
                self._grid_minor_color,
                self._grid_major_color,
                self._major_grid_interval,
                self._minor_grid_interval,
                self._show_minor_grid,
            )

        # Overlays
        if self._show_center_crosshair:
            self._draw_center_crosshair(painter)

        if self._has_mirror_active():
            self._draw_mirror_axes(painter)

        # Werkzeug-Vorschau
        self._draw_tool_preview(painter)

        # Cursor
        if self._cursor_pos and not self._tool_manager.is_tool_active():
            self._draw_cursor(painter)

        # Sticken-Cursor (Pfeiltasten-Navigation, über dem normalen Cursor)
        # Wichtig: muss hier mitgepflegt werden, weil OptimizedCanvas seine
        # eigene _paint-Implementation hat und nicht über RenderingMixin._paint
        # läuft. Synchron halten mit RenderingMixin._paint.
        if self._stitch_cursor is not None:
            self._draw_stitch_cursor(painter)

        # Performance-Stats anzeigen (optional)
        if self._show_performance_stats:
            self._draw_performance_overlay(painter)

    def _draw_cells_chunked(
        self, painter: QPainter, visible_rect: QRect, skip_symbols: bool
    ) -> None:
        """Zeichnet Zellen chunk-basiert mit Caching."""
        chunk_size = self._perf_manager._chunk_size

        # Sichtbare Chunks berechnen
        start_cx = max(0, visible_rect.left() // chunk_size)
        start_cy = max(0, visible_rect.top() // chunk_size)
        end_cx = (visible_rect.right() + chunk_size) // chunk_size
        end_cy = (visible_rect.bottom() + chunk_size) // chunk_size

        # Max. Chunk-Indizes
        if self._pattern:
            max_cx = (self._pattern.width + chunk_size - 1) // chunk_size
            max_cy = (self._pattern.height + chunk_size - 1) // chunk_size
            end_cx = min(end_cx, max_cx)
            end_cy = min(end_cy, max_cy)

        # Symbole basierend auf LOD
        show_symbols = self._show_symbols and not skip_symbols

        for cy in range(start_cy, end_cy):
            for cx in range(start_cx, end_cx):
                # Cache prüfen
                pixmap = self._perf_manager.get_cached_chunk(
                    cx,
                    cy,
                    self._pattern,
                    self._cell_size,
                    self._show_colors,
                    show_symbols,
                    self._show_only_active_layer,
                    self._dim_other_layers,
                )

                if pixmap is None:
                    # Chunk rendern
                    pixmap = render_chunk_to_pixmap(
                        self._pattern,
                        cx,
                        cy,
                        chunk_size,
                        self._cell_size,
                        self._empty_color,
                        self._show_colors,
                        show_symbols,
                        self._show_only_active_layer,
                        self._dim_other_layers,
                        self._cache._color_cache if hasattr(self._cache, "_color_cache") else {},
                        self._get_symbol_font(),
                    )
                    self._perf_manager.cache_chunk(cx, cy, pixmap)

                # Chunk zeichnen
                if pixmap and not pixmap.isNull():
                    screen_x = cx * chunk_size * self._cell_size + self._offset_x
                    screen_y = cy * chunk_size * self._cell_size + self._offset_y
                    painter.drawPixmap(screen_x, screen_y, pixmap)

    def _draw_performance_overlay(self, painter: QPainter) -> None:
        """Zeichnet Performance-Statistiken als Overlay."""
        stats = self._perf_manager.get_stats()

        # Hintergrund
        painter.fillRect(10, 10, 220, 120, QColor(0, 0, 0, 180))

        # Text
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Consolas", 10)
        painter.setFont(font)

        lines = [
            f"Frame: {stats['last_frame_time_ms']:.1f}ms",
            f"Cached: {stats['cached_chunks']} chunks",
            f"Dirty: {stats['dirty_chunks']} chunks",
            f"Hit Rate: {stats['hit_rate_percent']:.1f}%",
            f"Mode: {'Chunked' if self._perf_manager.enabled else 'Direct'}",
        ]

        for i, line in enumerate(lines):
            painter.drawText(20, 30 + i * 20, line)

    # =========================================================================
    # Zusätzliche API
    # =========================================================================

    def enable_performance_mode(self, enable: bool = True) -> None:
        """Aktiviert/Deaktiviert den Performance-Modus manuell."""
        if enable:
            self._perf_manager.enable()
        else:
            self._perf_manager.disable()
        self.update()

    def get_performance_stats(self) -> dict:
        """Gibt Performance-Statistiken zurück."""
        return self._perf_manager.get_stats()

    def reset_performance_stats(self) -> None:
        """Setzt Performance-Statistiken zurück."""
        self._perf_manager.reset_stats()

    @property
    def performance_mode_enabled(self) -> bool:
        """Gibt zurück ob Performance-Modus aktiv ist."""
        return self._perf_manager.enabled

    @property
    def show_performance_stats(self) -> bool:
        """Gibt zurück ob Performance-Overlay angezeigt wird."""
        return self._show_performance_stats

    @show_performance_stats.setter
    def show_performance_stats(self, value: bool) -> None:
        """Aktiviert/Deaktiviert Performance-Overlay."""
        self._show_performance_stats = value
        self.update()

    def set_chunk_size(self, size: int) -> None:
        """
        Setzt die Chunk-Größe (Standard: 64).

        Größere Werte (128) für sehr große Muster,
        kleinere Werte (32) für häufige lokale Änderungen.
        """
        self._perf_manager._chunk_size = clamp_int(size, 16, 256)
        self._perf_manager.invalidate_all()
        self.update()
