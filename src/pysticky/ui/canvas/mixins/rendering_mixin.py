"""
Rendering-Mixin für Canvas.

Enthält alle Zeichenmethoden für Zellen, Grid, Overlays und Backstitches.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPaintEvent, QPen

from ...styles import THEME
from ..enums import MirrorMode

if TYPE_CHECKING:
    from ....core.layer import Layer
    from ..canvas import CrossStitchCanvas


class RenderingMixin:
    """Mixin für Canvas-Rendering."""

    # =========================================================================
    # Main Paint
    # =========================================================================

    def paintEvent(self: "CrossStitchCanvas", event: QPaintEvent) -> None:
        painter = QPainter(self)
        try:
            self._paint(painter)
        finally:
            painter.end()

    def _paint(self: "CrossStitchCanvas", painter: QPainter) -> None:
        # Hintergrund
        painter.fillRect(self.rect(), self._bg_color)

        if not self._pattern:
            self._draw_empty_message(painter)
            return

        visible_rect = self._get_visible_grid_rect()

        # Zellen zeichnen (immer alle sichtbaren - Viewport-Culling reicht)
        self._draw_all_cells(painter, visible_rect)

        # Fortschritts-Overlay (erledigte Stiche)
        if self._show_completion:
            self._draw_completion_overlay(painter, visible_rect)

        # Backstitches
        if self._show_backstitches:
            self._draw_backstitches(painter)

        # Grid
        if self._show_grid:
            self._draw_grid(painter, visible_rect)

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
        if self._stitch_cursor is not None:
            self._draw_stitch_cursor(painter)

    def _draw_empty_message(self: "CrossStitchCanvas", painter: QPainter) -> None:
        """Zeichnet eine Nachricht wenn kein Pattern geladen ist."""
        painter.setPen(QColor(THEME.text_muted))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Kein Muster geladen")

    # =========================================================================
    # Zellen zeichnen
    # =========================================================================

    def _draw_all_cells(self: "CrossStitchCanvas", painter: QPainter, visible_rect: QRect) -> None:
        """Zeichnet alle sichtbaren Zellen (optimiert)."""
        if not self._pattern:
            return

        cell_size = self._cell_size
        offset_x = self._offset_x
        offset_y = self._offset_y

        # Font nur einmal setzen
        if self._show_symbols and cell_size >= 12:
            painter.setFont(self._get_symbol_font())

        # Anti-Aliasing aus für Rechtecke (schneller)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Erst: Alle leeren Zellen als ein großes Rechteck
        pattern_rect = QRect(
            visible_rect.left() * cell_size + offset_x,
            visible_rect.top() * cell_size + offset_y,
            visible_rect.width() * cell_size,
            visible_rect.height() * cell_size,
        )
        diamond_view = getattr(self, "_diamond_view", False)
        if diamond_view:
            # DP-Klebegrund: leicht abgedunkelter Untergrund mit dezenten
            # Drill-Slots-Andeutungen — keine Aida-Punkte (DP hat Klebefolie).
            painter.fillRect(pattern_rect, QColor(235, 232, 220))
        elif self._show_fabric_texture and cell_size >= 6:
            # Aida-Stoff-Optik als Tile-Brush (cached pro cell_size).
            # Die Brush startet per Default an Widget-Koordinaten (0, 0) —
            # bei Pan / Zoom wandern dann die Punkte relativ zur Zelle.
            # Per Transform am Pattern-Anfang verankern -> Punkt bleibt
            # zellzentriert, egal wo der Pattern-Origin liegt.
            from PySide6.QtGui import QBrush, QTransform

            brush = QBrush(self._get_fabric_pixmap())
            brush.setTransform(QTransform.fromTranslate(offset_x, offset_y))
            painter.fillRect(pattern_rect, brush)
        else:
            painter.fillRect(pattern_rect, self._empty_color)

        # Nur aktive Ebene anzeigen?
        if self._show_only_active_layer:
            layer = self._pattern.active_layer
            if layer and layer.visible:
                self._draw_layer_cells(painter, layer, visible_rect, layer.opacity)
        else:
            # Alle Layer von unten nach oben zeichnen (mit individueller Deckkraft)
            active_layer = self._pattern.active_layer
            for layer in self._pattern.layer_stack:
                if not layer.visible:
                    continue

                # Deckkraft berechnen
                opacity = layer.opacity

                # Optional: Andere Ebenen abdunkeln
                if self._dim_other_layers and layer != active_layer:
                    opacity = opacity * 0.5  # Zusätzlich gedimmt

                self._draw_layer_cells(painter, layer, visible_rect, opacity)

    def _draw_layer_cells(
        self: "CrossStitchCanvas",
        painter: QPainter,
        layer: "Layer",
        visible_rect: QRect,
        opacity: float,
    ) -> None:
        """Zeichnet alle Zellen eines Layers mit gegebener Deckkraft."""
        cell_size = self._cell_size
        offset_x = self._offset_x
        offset_y = self._offset_y

        # Deckkraft in Alpha umrechnen (0.0-1.0 -> 0-255)
        alpha = int(opacity * 255)

        # Farb-Isolation: andere Farben werden stark gedimmt. Cache-Key
        # `(r,g,b,a)` ist alpha-aware, also kein Cache-Refresh nötig.
        isolate_idx = self._isolate_color_index
        dim_alpha = max(20, alpha // 5)

        for y in range(visible_rect.top(), visible_rect.top() + visible_rect.height()):
            row_y = y * cell_size + offset_y

            for x in range(visible_rect.left(), visible_rect.left() + visible_rect.width()):
                if not self._is_valid_grid_pos(x, y):
                    continue

                color_index = layer.get_stitch(x, y)
                if color_index is None:
                    continue

                entry = self._pattern.get_color_entry(color_index)
                if not entry:
                    continue

                screen_x = x * cell_size + offset_x
                thread_color = entry.thread.color
                tr, tg, tb = thread_color.r, thread_color.g, thread_color.b

                # Farbblindheits-Simulation anwenden
                cb_mode = getattr(self, "_colorblind_mode", None)
                if cb_mode is not None and cb_mode.value != "none":
                    from ....core.color_blindness import simulate_color

                    tr, tg, tb = simulate_color(tr, tg, tb, cb_mode)

                # Per-Cell-Alpha: bei Isolation andere Farben stark senken
                cell_alpha = (
                    alpha if (isolate_idx is None or color_index == isolate_idx) else dim_alpha
                )

                # Farbe mit Deckkraft aus Cache
                fill_color = self._cache.get_color(tr, tg, tb, cell_alpha)

                # Stichtyp prüfen und zeichnen
                stype = layer.get_stitch_type(x, y)
                diamond_view = getattr(self, "_diamond_view", False)
                # Im Diamond-View werden FULL-Stiche als Drill gerendert —
                # Konsistente Optik, egal ob die Farbe aus einer DP-Palette
                # oder einer Garn-Palette stammt.
                if stype == 11 or (diamond_view and stype == 0):
                    self._draw_diamond_drill(painter, screen_x, row_y, cell_size, fill_color)
                elif stype == 0:
                    # FULL: ganzes Rechteck
                    painter.fillRect(screen_x, row_y, cell_size, cell_size, fill_color)
                elif stype == 9:
                    # FRENCH_KNOT: Kreis in der Zellmitte
                    self._draw_french_knot(painter, screen_x, row_y, cell_size, fill_color)
                elif stype == 10:
                    # BEAD: größere Kugel mit Glanzpunkt
                    self._draw_bead(painter, screen_x, row_y, cell_size, fill_color)
                else:
                    self._draw_partial_stitch(
                        painter, screen_x, row_y, cell_size, stype, fill_color
                    )

                # Symbol zeichnen — hängt am show_symbols-Toggle, damit der
                # User es ein/aus knipsen kann ohne Mode-Wechsel. Diamant-
                # Farben bekommen dasselbe Symbol wie Garn-Farben (siehe
                # Pattern.add_color), keine Sonderbehandlung mehr nötig.
                show_label = (
                    self._show_symbols
                    and opacity >= 0.5
                    and cell_size >= 12
                    and (isolate_idx is None or color_index == isolate_idx)
                )
                if show_label:
                    symbol_color = self._cache.get_symbol_color(thread_color.luminance > 0.5)
                    painter.setPen(symbol_color)
                    painter.drawText(
                        QRect(screen_x, row_y, cell_size, cell_size),
                        Qt.AlignmentFlag.AlignCenter,
                        entry.symbol,
                    )

    @staticmethod
    def _draw_partial_stitch(
        painter: QPainter, x: int, y: int, size: int, stype: int, color: QColor
    ) -> None:
        """Zeichnet einen Teil-Stich (halb/viertel) als Dreieck."""
        path = QPainterPath()
        tl = QPointF(x, y)
        tr = QPointF(x + size, y)
        bl = QPointF(x, y + size)
        br = QPointF(x + size, y + size)

        if stype == 1:  # HALF_TL_BR: oberes-linkes Dreieck (/)
            path.moveTo(tl)
            path.lineTo(tr)
            path.lineTo(bl)
            path.closeSubpath()
        elif stype == 2:  # HALF_TR_BL: oberes-rechtes Dreieck (\)
            path.moveTo(tl)
            path.lineTo(tr)
            path.lineTo(br)
            path.closeSubpath()
        elif stype == 3:  # QUARTER_TL
            path.moveTo(tl)
            path.lineTo(QPointF(x + size / 2, y))
            path.lineTo(QPointF(x, y + size / 2))
            path.closeSubpath()
        elif stype == 4:  # QUARTER_TR
            path.moveTo(QPointF(x + size / 2, y))
            path.lineTo(tr)
            path.lineTo(QPointF(x + size, y + size / 2))
            path.closeSubpath()
        elif stype == 5:  # QUARTER_BL
            path.moveTo(QPointF(x, y + size / 2))
            path.lineTo(bl)
            path.lineTo(QPointF(x + size / 2, y + size))
            path.closeSubpath()
        elif stype == 6:  # QUARTER_BR
            path.moveTo(QPointF(x + size, y + size / 2))
            path.lineTo(QPointF(x + size / 2, y + size))
            path.lineTo(br)
            path.closeSubpath()
        elif stype == 7:  # THREE_QUARTER (3/4 = full minus one corner)
            path.moveTo(tl)
            path.lineTo(tr)
            path.lineTo(br)
            path.lineTo(bl)
            path.closeSubpath()
        else:
            # Fallback: ganzes Rechteck
            painter.fillRect(x, y, size, size, color)
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillPath(path, color)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    @staticmethod
    def _draw_french_knot(painter: QPainter, x: int, y: int, size: int, color: QColor) -> None:
        """Zeichnet einen Französischen Knoten als gefüllten Kreis."""
        from ....core.stitch_shapes import french_knot_radius_factor

        radius = max(1, int(size * french_knot_radius_factor()))
        cx = x + size // 2
        cy = y + size // 2
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - radius, cy - radius, 2 * radius, 2 * radius)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    @staticmethod
    def _draw_diamond_drill(painter: QPainter, x: int, y: int, size: int, color: QColor) -> None:
        """Zeichnet einen Diamond-Painting-Drill: facettiertes Quadrat.

        Echte Drills sind 2.5mm-Quadrate mit pyramidaler Spitze — von oben
        sieht man vier dreieckige Facetten. Die obere Facette ist die hellste
        (Glanzlicht), die untere die dunkelste (Schatten), links/rechts mittel.
        Zusammen ergibt das die typische DP-Optik.

        Inset ist adaptiv: bei kleiner Zelle (<12px) berühren sich die
        Drills nahtlos, damit das Pattern bei rausgezoomter Ansicht nicht
        ausgewaschen weiss wirkt.
        """
        from ....core.stitch_shapes import diamond_inset_pixels

        inset = int(diamond_inset_pixels(size))
        x0 = x + inset
        y0 = y + inset
        x1 = x + size - inset
        y1 = y + size - inset
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0

        # Vier Facetten als Dreiecke (jeweils Mittelpunkt + zwei Kanten-Ecken)
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

        # Helligkeits-Varianten mit Alpha-Erhalt (lighter/darker normieren auf
        # 255 Alpha — wir müssen die Original-Alpha aus `color` zurückschreiben,
        # sonst frisst der Effekt die Layer-Deckkraft).
        alpha = color.alpha()

        def _shift(c: QColor, factor: int) -> QColor:
            shifted = c.lighter(factor) if factor >= 100 else c.darker(200 - factor)
            shifted.setAlpha(alpha)
            return shifted

        c_top = _shift(color, 145)  # Glanzlicht
        c_right = _shift(color, 110)
        c_left = _shift(color, 95)
        c_bottom = _shift(color, 70)  # Schatten

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.fillPath(top, c_top)
        painter.fillPath(right, c_right)
        painter.fillPath(bottom, c_bottom)
        painter.fillPath(left, c_left)

        # Dünner Kantenrand für Trennschärfe zwischen Nachbar-Drills.
        # Bei kleinem Zoom weglassen, sonst frisst der Rand den Drill auf.
        from ....core.stitch_shapes import diamond_should_draw_edge

        if diamond_should_draw_edge(size):
            edge = QColor(0, 0, 0, min(120, alpha))
            painter.setPen(QPen(edge, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(x0, y0, x1 - x0, y1 - y0)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    @staticmethod
    def _draw_bead(painter: QPainter, x: int, y: int, size: int, color: QColor) -> None:
        """Zeichnet eine Perle: größerer Kreis mit Glanzpunkt."""
        from ....core.stitch_shapes import bead_radius_factor

        radius = max(2, int(size * bead_radius_factor()))
        cx = x + size // 2
        cy = y + size // 2
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # Schatten unter der Perle
        shadow = QColor(0, 0, 0, 60)
        painter.setBrush(shadow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - radius + 1, cy - radius + 2, 2 * radius, 2 * radius)
        # Perle in Farbe
        painter.setBrush(color)
        painter.drawEllipse(cx - radius, cy - radius, 2 * radius, 2 * radius)
        # Glanzpunkt für Plastizität
        highlight = color.lighter(150)
        highlight.setAlphaF(0.85)
        painter.setBrush(highlight)
        h_r = max(1, radius // 3)
        painter.drawEllipse(cx - radius // 2, cy - radius // 2, 2 * h_r, 2 * h_r)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    def _draw_dirty_cells(
        self: "CrossStitchCanvas",
        painter: QPainter,
        dirty_cells: set[tuple[int, int]],
        visible_rect: QRect,
    ) -> None:
        """Zeichnet nur die geänderten Zellen neu."""
        if not self._pattern:
            return

        cell_size = self._cell_size
        offset_x = self._offset_x
        offset_y = self._offset_y

        if self._show_symbols and cell_size >= 12:
            painter.setFont(self._get_symbol_font())

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        active_layer = self._pattern.active_layer

        for x, y in dirty_cells:
            # Nur sichtbare Zellen
            if not visible_rect.contains(x, y):
                continue

            if not self._is_valid_grid_pos(x, y):
                continue

            screen_x = x * cell_size + offset_x
            screen_y = y * cell_size + offset_y
            cell_rect = QRect(screen_x, screen_y, cell_size, cell_size)

            # Erst leeren
            painter.fillRect(cell_rect, self._empty_color)

            # Dann alle Layer von unten nach oben zeichnen
            if self._show_only_active_layer:
                layers_to_draw = [active_layer] if active_layer and active_layer.visible else []
            else:
                layers_to_draw = [l for l in self._pattern.layer_stack if l.visible]

            for layer in layers_to_draw:
                color_index = layer.get_stitch(x, y)
                if color_index is None:
                    continue

                entry = self._pattern.get_color_entry(color_index)
                if not entry:
                    continue

                thread_color = entry.thread.color
                tr, tg, tb = thread_color.r, thread_color.g, thread_color.b

                cb_mode = getattr(self, "_colorblind_mode", None)
                if cb_mode is not None and cb_mode.value != "none":
                    from ....core.color_blindness import simulate_color

                    tr, tg, tb = simulate_color(tr, tg, tb, cb_mode)

                # Deckkraft berechnen
                opacity = layer.opacity
                if self._dim_other_layers and layer != active_layer:
                    opacity = opacity * 0.5

                alpha = int(opacity * 255)
                fill_color = self._cache.get_color(tr, tg, tb, alpha)

                stype = layer.get_stitch_type(x, y)
                diamond_view = getattr(self, "_diamond_view", False)
                if stype == 11 or (diamond_view and stype == 0):
                    self._draw_diamond_drill(painter, screen_x, screen_y, cell_size, fill_color)
                else:
                    painter.fillRect(cell_rect, fill_color)

                if self._show_symbols and cell_size >= 12 and opacity >= 0.5:
                    symbol_color = self._cache.get_symbol_color(thread_color.luminance > 0.5)
                    painter.setPen(symbol_color)
                    painter.drawText(cell_rect, Qt.AlignmentFlag.AlignCenter, entry.symbol)

    def _get_visible_stitch(self: "CrossStitchCanvas", x: int, y: int) -> int | None:
        """Gibt den sichtbaren Farbindex an Position (x, y) zurück."""
        if self._show_only_active_layer:
            layer = self._pattern.active_layer
            return layer.get_stitch(x, y) if layer else None
        else:
            return self._pattern.get_stitch(x, y)

    def _is_on_active_layer(self: "CrossStitchCanvas", x: int, y: int) -> bool:
        """Prüft ob der Stich auf dem aktiven Layer ist."""
        active = self._pattern.active_layer
        return active is not None and active.get_stitch(x, y) is not None

    # =========================================================================
    # Grid zeichnen
    # =========================================================================

    def _draw_grid(self: "CrossStitchCanvas", painter: QPainter, visible_rect: QRect) -> None:
        """Zeichnet das Grid (optimiert)."""
        if not self._pattern:
            return

        cell_size = self._cell_size
        offset_x = self._offset_x
        offset_y = self._offset_y

        # Pens einmal vorbereiten
        normal_pen = QPen(self._grid_color, 1)
        minor_pen = QPen(self._grid_minor_color, 1)
        major_pen = QPen(self._grid_major_color, 2)

        # Bereichsgrenzen
        left = visible_rect.left() * cell_size + offset_x
        right = (visible_rect.left() + visible_rect.width()) * cell_size + offset_x
        top = visible_rect.top() * cell_size + offset_y
        bottom = (visible_rect.top() + visible_rect.height()) * cell_size + offset_y

        # Vertikale Linien
        for x in range(visible_rect.left(), visible_rect.left() + visible_rect.width() + 1):
            screen_x = x * cell_size + offset_x

            if x % self._major_grid_interval == 0:
                painter.setPen(major_pen)
            elif self._show_minor_grid and x % self._minor_grid_interval == 0:
                painter.setPen(minor_pen)
            else:
                painter.setPen(normal_pen)

            painter.drawLine(screen_x, top, screen_x, bottom)

        # Horizontale Linien
        for y in range(visible_rect.top(), visible_rect.top() + visible_rect.height() + 1):
            screen_y = y * cell_size + offset_y

            if y % self._major_grid_interval == 0:
                painter.setPen(major_pen)
            elif self._show_minor_grid and y % self._minor_grid_interval == 0:
                painter.setPen(minor_pen)
            else:
                painter.setPen(normal_pen)

            painter.drawLine(left, screen_y, right, screen_y)

    # =========================================================================
    # Overlays zeichnen
    # =========================================================================

    def _draw_cursor(self: "CrossStitchCanvas", painter: QPainter) -> None:
        """Zeichnet den Cursor und gespiegelte Cursor."""
        if not self._cursor_pos or not self._pattern:
            return

        grid_x, grid_y = self._screen_to_grid(self._cursor_pos.x(), self._cursor_pos.y())

        if not self._is_valid_grid_pos(grid_x, grid_y):
            return

        screen_x, screen_y = self._grid_to_screen(grid_x, grid_y)

        # Haupt-Cursor
        painter.setPen(QPen(self._cursor_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(screen_x, screen_y, self._cell_size, self._cell_size)

        # Gespiegelte Cursor
        if self._has_mirror_active():
            mirror_color = self._cache.get_color(
                self._cursor_color.red(), self._cursor_color.green(), self._cursor_color.blue(), 100
            )
            painter.setPen(QPen(mirror_color, 2))
            for mx, my in self.get_mirrored_positions(grid_x, grid_y)[1:]:
                sx, sy = self._grid_to_screen(mx, my)
                painter.drawRect(sx, sy, self._cell_size, self._cell_size)

    def _draw_stitch_cursor(self: "CrossStitchCanvas", painter: QPainter) -> None:
        """Markiert die durch Pfeiltasten gewählte Ziel-Zelle im Sticken-Modus."""
        if not self._stitch_cursor or not self._pattern:
            return
        x, y = self._stitch_cursor
        if not self._is_valid_grid_pos(x, y):
            return
        sx, sy = self._grid_to_screen(x, y)
        cs = self._cell_size
        # Auffälliger oranger Rahmen, doppelt — sticht auch auf bunten Cells raus.
        outer = QColor(THEME.warning)
        inner = QColor(THEME.warning)
        outer.setAlpha(220)
        inner.setAlpha(255)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(outer, 4))
        painter.drawRect(sx - 2, sy - 2, cs + 4, cs + 4)
        painter.setPen(QPen(inner, 2))
        painter.drawRect(sx, sy, cs, cs)

    def _draw_center_crosshair(self: "CrossStitchCanvas", painter: QPainter) -> None:
        """Zeichnet das Zentrierkreuz."""
        if not self._pattern:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        center_x = (self._pattern.width * self._cell_size) // 2 + self._offset_x
        center_y = (self._pattern.height * self._cell_size) // 2 + self._offset_y

        left = self._offset_x
        right = self._offset_x + self._pattern.width * self._cell_size
        top = self._offset_y
        bottom = self._offset_y + self._pattern.height * self._cell_size

        pen = QPen(QColor(255, 100, 100, 180), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)

        painter.drawLine(left, center_y, right, center_y)
        painter.drawLine(center_x, top, center_x, bottom)

        painter.setPen(QPen(QColor(255, 100, 100), 2))
        painter.setBrush(QColor(255, 100, 100, 100))
        painter.drawEllipse(center_x - 6, center_y - 6, 12, 12)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    def _draw_mirror_axes(self: "CrossStitchCanvas", painter: QPainter) -> None:
        """Zeichnet die Spiegelachsen basierend auf dem aktuellen Modus."""
        if not self._pattern:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        center_x = (self._pattern.width * self._cell_size) // 2 + self._offset_x
        center_y = (self._pattern.height * self._cell_size) // 2 + self._offset_y

        left = self._offset_x
        right = self._offset_x + self._pattern.width * self._cell_size
        top = self._offset_y
        bottom = self._offset_y + self._pattern.height * self._cell_size

        mode = self._mirror_mode

        # Vertikale Achse (für horizontale Spiegelung) - Blau
        show_v = (
            mode in (MirrorMode.HORIZONTAL, MirrorMode.QUAD, MirrorMode.OCTAL)
            or self._mirror_horizontal
        )
        if show_v:
            painter.setPen(QPen(QColor(100, 200, 255, 200), 3))
            painter.drawLine(center_x, top, center_x, bottom)
            painter.setPen(QColor(100, 200, 255))
            painter.drawText(center_x + 5, top - 5, "↔")

        # Horizontale Achse (für vertikale Spiegelung) - Orange
        show_h = (
            mode in (MirrorMode.VERTICAL, MirrorMode.QUAD, MirrorMode.OCTAL)
            or self._mirror_vertical
        )
        if show_h:
            painter.setPen(QPen(QColor(255, 180, 100, 200), 3))
            painter.drawLine(left, center_y, right, center_y)
            painter.setPen(QColor(255, 180, 100))
            painter.drawText(right + 5, center_y + 5, "↕")

        # Diagonale Achsen (nur bei 8-fach)
        if mode == MirrorMode.OCTAL:
            # Hauptdiagonale (Lila, gestrichelt)
            painter.setPen(QPen(QColor(180, 100, 255, 150), 2, Qt.PenStyle.DashLine))
            painter.drawLine(left, top, right, bottom)

            # Anti-Diagonale (Türkis, gestrichelt)
            painter.setPen(QPen(QColor(100, 255, 200, 150), 2, Qt.PenStyle.DashLine))
            painter.drawLine(right, top, left, bottom)

        # Modus-Anzeige im Zentrum
        mode_labels = {
            MirrorMode.HORIZONTAL: "2x↔",
            MirrorMode.VERTICAL: "2x↕",
            MirrorMode.QUAD: "4x",
            MirrorMode.OCTAL: "8x",
        }

        label = mode_labels.get(mode, "")
        if label:
            painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
            painter.setBrush(QColor(50, 50, 80, 200))
            painter.drawEllipse(center_x - 18, center_y - 18, 36, 36)

            painter.setPen(QColor(255, 255, 255))
            font = painter.font()
            font.setPixelSize(14)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                QRect(center_x - 18, center_y - 18, 36, 36), Qt.AlignmentFlag.AlignCenter, label
            )

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    def _draw_tool_preview(self: "CrossStitchCanvas", painter: QPainter) -> None:
        """Zeichnet die Werkzeug-Vorschau."""
        from ...tools.tool_enum import Tool

        if self._tool_manager.current_tool == Tool.SELECT:
            ctx = self._create_tool_context(
                self._cursor_pos.x() if self._cursor_pos else 0,
                self._cursor_pos.y() if self._cursor_pos else 0,
            )
            if ctx:
                self._tool_manager.draw_preview(ctx, painter)
        elif self._cursor_pos:
            ctx = self._create_tool_context(self._cursor_pos.x(), self._cursor_pos.y())
            if ctx:
                self._tool_manager.draw_preview(ctx, painter)

    # =========================================================================
    # Fortschritts-Overlay (Completion)
    # =========================================================================

    def _draw_completion_overlay(
        self: "CrossStitchCanvas", painter: QPainter, visible_rect: QRect
    ) -> None:
        """Zeichnet ein visuelles Overlay auf erledigten Stichen."""
        if not self._pattern:
            return

        import numpy as np

        from ....core.layer import NO_STITCH

        cell_size = self._cell_size
        offset_x = self._offset_x
        offset_y = self._offset_y

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Farben vorbereiten
        overlay_color = QColor(0, 200, 80, 50)
        check_color = QColor(0, 180, 60, 200)

        # Sichtbaren Bereich ermitteln
        vx1 = max(0, visible_rect.left())
        vy1 = max(0, visible_rect.top())
        vx2 = min(self._pattern.width, visible_rect.left() + visible_rect.width())
        vy2 = min(self._pattern.height, visible_rect.top() + visible_rect.height())

        if vx2 <= vx1 or vy2 <= vy1:
            return

        layers_to_check = (
            [self._pattern.active_layer]
            if self._show_only_active_layer and self._pattern.active_layer
            else [l for l in self._pattern.layer_stack if l.visible]
        )

        # Pass 1: Grünes Overlay pro Layer. Positions werden gecached für
        # den optionalen Häkchen-Pass — früher zweimal np.argwhere pro Layer.
        cached_positions: list = []
        for layer in layers_to_check:
            sub_completion = layer.completion_grid[vy1:vy2, vx1:vx2]
            sub_grid = layer.grid[vy1:vy2, vx1:vx2]
            mask = sub_completion & (sub_grid != NO_STITCH)

            if not np.any(mask):
                continue

            positions = np.argwhere(mask)
            cached_positions.append(positions)

            for rel_y, rel_x in positions:
                sx = (rel_x + vx1) * cell_size + offset_x
                sy = (rel_y + vy1) * cell_size + offset_y
                painter.fillRect(sx, sy, cell_size, cell_size, overlay_color)

        # Pass 2: Häkchen nur bei größerem Zoom — wiederverwenden der gecachten Positions
        if cached_positions and cell_size >= 16:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            pen_width = max(1, cell_size // 8)
            painter.setPen(
                QPen(check_color, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            )

            half_cell = cell_size // 2
            s = cell_size // 4
            half_s = s // 2

            for positions in cached_positions:
                for rel_y, rel_x in positions:
                    cx = (rel_x + vx1) * cell_size + offset_x + half_cell
                    cy = (rel_y + vy1) * cell_size + offset_y + half_cell
                    painter.drawLine(cx - s, cy, cx - half_s, cy + s)
                    painter.drawLine(cx - half_s, cy + s, cx + s, cy - s)

            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    # =========================================================================
    # Backstitches zeichnen
    # =========================================================================

    def _draw_backstitches(self: "CrossStitchCanvas", painter: QPainter) -> None:
        """Zeichnet alle Backstitches und die Vorschau."""
        if not self._pattern:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        half_cell = self._cell_size // 2

        # Existierende Backstitches
        for bs in self._pattern.backstitches:
            entry = self._pattern.get_color_entry(bs.color_index)
            if entry:
                color = self._cache.get_color(
                    entry.thread.color.r, entry.thread.color.g, entry.thread.color.b
                )
            else:
                color = QColor(0, 0, 0)

            x1 = bs.x1 * half_cell + self._offset_x
            y1 = bs.y1 * half_cell + self._offset_y
            x2 = bs.x2 * half_cell + self._offset_x
            y2 = bs.y2 * half_cell + self._offset_y

            # Schatten
            line_width = max(2, self._cell_size // 6) + self._backstitch_width_offset
            painter.setPen(
                QPen(
                    QColor(0, 0, 0, 100),
                    max(3, self._cell_size // 5 + 2) + self._backstitch_width_offset,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                )
            )
            painter.drawLine(x1, y1, x2, y2)

            # Linie
            painter.setPen(
                QPen(
                    color,
                    line_width,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                )
            )
            painter.drawLine(x1, y1, x2, y2)

        # Backstitch-Tool Vorschau
        backstitch_tool = self._tool_manager.get_backstitch_tool()
        if backstitch_tool:
            start = backstitch_tool.start_point
            if start:
                sx = start[0] * half_cell + self._offset_x
                sy = start[1] * half_cell + self._offset_y

                painter.setPen(QPen(QColor(THEME.accent_primary), 2))
                painter.setBrush(QColor(THEME.accent_primary + "99"))
                painter.drawEllipse(sx - 5, sy - 5, 10, 10)

            preview = backstitch_tool.preview
            if preview:
                entry = self._pattern.get_color_entry(preview.color_index)
                if entry:
                    color = self._cache.get_color(
                        entry.thread.color.r, entry.thread.color.g, entry.thread.color.b
                    )
                else:
                    color = QColor(THEME.accent_primary)

                x1 = preview.x1 * half_cell + self._offset_x
                y1 = preview.y1 * half_cell + self._offset_y
                x2 = preview.x2 * half_cell + self._offset_x
                y2 = preview.y2 * half_cell + self._offset_y

                pen = QPen(color, max(2, self._cell_size // 6), Qt.PenStyle.DashLine)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawLine(x1, y1, x2, y2)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
