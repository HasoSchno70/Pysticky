"""
Kreuzstich-Canvas für die Musteranzeige und -bearbeitung.

Ein Grid-basiertes Canvas, das Kreuzstich-Muster als Raster darstellt.
Unterstützt mehrere Layer und Undo/Redo.

Performance-Optimierungen:
- QColor-Cache für Farbobjekte
- Font-Cache für Symbol-Rendering
- Viewport-Culling (nur sichtbare Zellen zeichnen)
- Deferred Updates mit Timer (~60 FPS)

Die Funktionalität ist in Mixins aufgeteilt:
- CoordinatesMixin: Koordinaten-Umrechnung
- MirrorMixin: Spiegelmodus-Funktionalität
- RenderingMixin: Zeichnen
- ZoomMixin: Zoom-Funktionen
- MouseEventsMixin: Maus-/Viewport-Events (Pan, Tool-Delegation, Batching, Wheel-Zoom)
- KeyboardEventsMixin: Tastatur-Events
- TabletGestureMixin: Stift-Tablet- und Touch-Gesten-Events
- PropertiesMixin: Properties
"""

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import QWidget

from ...config import CANVAS_CONFIG
from ...core import Pattern
from ..tools.base_tool import ToolContext
from ..tools.tool_enum import Tool
from ..tools.tool_manager import ToolManager
from .cache import CanvasCache
from .enums import MirrorMode
from .mixins import (
    CoordinatesMixin,
    KeyboardEventsMixin,
    MirrorMixin,
    MouseEventsMixin,
    PropertiesMixin,
    RenderingMixin,
    TabletGestureMixin,
    ZoomMixin,
)


class CrossStitchCanvas(
    CoordinatesMixin,
    MirrorMixin,
    RenderingMixin,
    ZoomMixin,
    MouseEventsMixin,
    KeyboardEventsMixin,
    TabletGestureMixin,
    PropertiesMixin,
    QWidget,
):
    """
    Canvas zur Anzeige und Bearbeitung von Kreuzstich-Mustern.

    Performance-Features:
    - Farb- und Font-Caching
    - Inkrementelles Update nur geänderter Zellen
    - Deferred Updates mit Timer
    - Viewport-Culling
    """

    # === Signals ===
    position_changed = Signal(int, int)
    stitch_placed = Signal(int, int, int)
    stitch_removed = Signal(int, int)
    color_picked = Signal(int)
    text_confirmed = Signal()
    zoom_changed = Signal(float)
    offset_changed = Signal(int, int)

    # Auswahl-Signale für Tool-spezifische Tasten (F/R/H/V im keyPressEvent).
    # Copy/Cut/Paste/Delete laufen über QActions im Bearbeiten-Menü —
    # daher hier nicht mehr nötig.
    selection_fill = Signal()
    selection_rotate_cw = Signal()
    selection_rotate_ccw = Signal()
    selection_flip_h = Signal()
    selection_flip_v = Signal()

    # Backstitch-Signale
    backstitch_added = Signal(int, int, int, int, int)
    backstitch_removed = Signal(int, int, int, int, int)

    # Fortschritts-Signale
    stitch_marked_completed = Signal(int, int)  # (x, y)
    stitch_unmarked_completed = Signal(int, int)  # (x, y)

    # Batch-Signale für Undo
    batch_started = Signal(str)
    batch_ended = Signal()

    # === Konstanten (aus config.py) ===
    MIN_CELL_SIZE: int = CANVAS_CONFIG.min_cell_size
    MAX_CELL_SIZE: int = CANVAS_CONFIG.max_cell_size
    DEFAULT_CELL_SIZE: int = CANVAS_CONFIG.default_cell_size

    # Farben als RGB-Tuple (für Cache-Lookup)
    _BG_COLOR_RGB = (26, 26, 46)  # THEME.bg_dark
    _EMPTY_CELL_RGB = (250, 250, 245)
    _CURSOR_COLOR_RGB = (0, 120, 212)
    _GRID_COLOR_RGB = (80, 80, 80)
    _GRID_MINOR_RGB = (120, 120, 120)
    _GRID_MAJOR_RGB = (100, 100, 100)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # Pattern & State
        self._pattern: Pattern | None = None
        self._cell_size: int = self.DEFAULT_CELL_SIZE
        self._offset_x: int = 0
        self._offset_y: int = 0
        self._current_color_index: int = 0

        # Cache-System
        self._cache = CanvasCache()

        # Vorberechnete Farben (einmalig erstellt)
        self._bg_color = QColor(*self._BG_COLOR_RGB)
        self._empty_color = QColor(*self._EMPTY_CELL_RGB)
        self._cursor_color = QColor(*self._CURSOR_COLOR_RGB)

        # Font-Cache
        self._symbol_font: QFont | None = None
        self._last_font_size: int = 0

        # Ansichts-Optionen
        self._show_grid: bool = True
        self._show_symbols: bool = False
        self._show_colors: bool = True
        self._show_backstitches: bool = False
        self._show_only_active_layer: bool = False
        self._dim_other_layers: bool = False
        self._show_center_crosshair: bool = False
        self._show_completion: bool = True
        self._show_fabric_texture: bool = True  # Aida-Optik für leere Zellen
        self._colorblind_mode = None  # ColorBlindType.NONE
        self._active_stitch_type: int = 0  # StitchType.FULL
        # Diamond-Painting-Ansicht: FULL-Stiche werden als facettierte Drills
        # gerendert, Symbole werden zu DMC-Nummern. Daten bleiben unverändert
        # — reines Rendering-Override (analog show_symbols).
        self._diamond_view: bool = False

        # Stoff-Textur-Pixmap (lazy generiert, abhängig von cell_size)
        self._fabric_pixmap: QPixmap | None = None
        self._fabric_pixmap_cell_size: int = 0

        # Spiegelmodus
        self._mirror_mode: MirrorMode = MirrorMode.NONE
        self._mirror_horizontal: bool = False  # Legacy-Kompatibilität
        self._mirror_vertical: bool = False  # Legacy-Kompatibilität

        # Raster-Optionen
        self._major_grid_interval: int = CANVAS_CONFIG.major_grid_interval
        self._minor_grid_interval: int = CANVAS_CONFIG.minor_grid_interval
        self._show_minor_grid: bool = True
        self._grid_color: QColor = QColor(*self._GRID_COLOR_RGB)
        self._grid_minor_color: QColor = QColor(*self._GRID_MINOR_RGB)
        self._grid_major_color: QColor = QColor(*self._GRID_MAJOR_RGB)

        # Snap-to-Grid
        self._snap_to_grid: bool = False
        self._snap_interval: int = CANVAS_CONFIG.default_snap_interval

        # Werkzeug-Manager
        self._tool_manager = ToolManager()

        # Interaktion
        self._panning: bool = False
        self._last_pan_point: QPoint = QPoint()
        self._cursor_pos: QPoint | None = None
        self._batch_active: bool = False

        # Farb-Isolation (None = aus). Andere Farben werden in _draw_layer_cells
        # mit reduzierter Alpha gezeichnet — Cache-Key hängt schon an Alpha,
        # also keine zusätzliche Cache-Invalidierung nötig.
        self._isolate_color_index: int | None = None

        # Sticken-Modus-Cursor: separate Zelle (Grid-Koordinaten), die durch
        # Pfeiltasten-Navigation gesteuert wird. Unabhängig vom Hover-Cursor.
        self._stitch_cursor: tuple[int, int] | None = None

        # Auswahl
        self._selection: QRect | None = None

        # Tablet-Pressure: aktuelle Stiftstärke (0.0-1.0). 0.0 bedeutet
        # entweder kein Stift verwendet oder Pen-Up. Wird vom tabletEvent
        # gesetzt und vom Pencil-Tool gelesen.
        self._tablet_pressure: float = 0.0
        self._tablet_in_use: bool = False  # True während der Stift Kontakt hat

        # Deferred Update Timer (~60 FPS)
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(16)
        self._update_timer.timeout.connect(self._do_deferred_update)
        self._pending_update: bool = False

        self._setup_widget()

    def _setup_widget(self) -> None:
        """Initialisiert Widget-Eigenschaften."""
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(400, 300)
        # Doppelpufferung für bessere Performance
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        # Kein Default-Kontextmenu — sonst flackert beim Rechtsklick-Drag
        # ein leeres Menü auf, weil Qt unconditionally ContextMenuEvent
        # feuert. Wir nutzen Rechtsklick selbst (Löschen).
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        # Touch-Events / Gestures abhängig vom Setting aktivieren
        self._apply_touch_setting()
        # Pinch-Gesture Status für differenz-basiertes Zoomen
        self._gesture_last_scale: float = 1.0

    def _apply_touch_setting(self) -> None:
        """Aktiviert/deaktiviert Touch-Events und Pinch-Gesture.

        Aus den Settings (`touch/gestures_enabled`, Default False).
        Standardmäßig AUS, weil Windows auf manchen Geräten einen
        Tablet/Touch-Indicator-Toast beim langen Drag zeigt, wenn Touch
        akzeptiert wird (auch ohne Touchscreen).
        """
        from PySide6.QtCore import QSettings

        s = QSettings()
        enabled = s.value("touch/gestures_enabled", False, type=bool)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, enabled)
        if enabled:
            self.grabGesture(Qt.GestureType.PinchGesture)
        else:
            self.ungrabGesture(Qt.GestureType.PinchGesture)

    # =========================================================================
    # Stoff-Textur
    # =========================================================================

    def _get_fabric_pixmap(self) -> QPixmap:
        """
        Liefert eine Tile-Pixmap mit Aida-Stoff-Optik.

        Wird beim Render für die leeren Zellen als Brush benutzt. Gecacht
        pro `cell_size`, damit Zoom-Wechsel nicht jeden Frame neu rendert.
        """
        cs = self._cell_size
        if self._fabric_pixmap is not None and self._fabric_pixmap_cell_size == cs:
            return self._fabric_pixmap

        from PySide6.QtGui import QPainter as _QP

        pixmap = QPixmap(cs, cs)
        pixmap.fill(self._empty_color)

        # Subtile Punkt-Textur — nur bei größeren Zellen sichtbar
        if cs >= 8:
            p = _QP(pixmap)
            try:
                p.setRenderHint(_QP.RenderHint.Antialiasing, True)
                # Dot-Farbe: dezenter Schatten, niedrige Alpha
                dot = QColor(180, 170, 150, 70)
                p.setBrush(dot)
                p.setPen(Qt.PenStyle.NoPen)
                # Punkt in der Mitte
                r = max(1, cs // 12)
                center = cs // 2
                p.drawEllipse(center - r, center - r, 2 * r, 2 * r)
            finally:
                p.end()

        self._fabric_pixmap = pixmap
        self._fabric_pixmap_cell_size = cs
        return pixmap

    def _invalidate_fabric_pixmap(self) -> None:
        """Verwirft den Fabric-Pixmap-Cache (z.B. nach Theme-Wechsel)."""
        self._fabric_pixmap = None
        self._fabric_pixmap_cell_size = 0

    # =========================================================================
    # Public API
    # =========================================================================

    def set_pattern(self, pattern: Pattern) -> None:
        """Setzt das anzuzeigende Pattern."""
        self._pattern = pattern
        # Per-Pattern-State zurücksetzen
        self._isolate_color_index = None
        self._stitch_cursor = None
        self._center_pattern()
        self.update()

    def set_current_color(self, index: int) -> None:
        """Setzt die aktuelle Zeichenfarbe."""
        self._current_color_index = index

    @property
    def isolate_color_index(self) -> int | None:
        """Aktuell isolierte Farb-Indizes (None = Isolation aus)."""
        return self._isolate_color_index

    def set_isolate_color(self, index: int | None) -> None:
        """Isoliert eine Farbe — alle anderen werden gedimmt gerendert.

        Args:
            index: Farb-Index, der voll sichtbar bleibt, oder None zum Aufheben.
        """
        if index == self._isolate_color_index:
            return
        self._isolate_color_index = index
        # Stitch-Cursor zurücksetzen, damit er nicht auf einer gedimmten Zelle
        # einer anderen Farbe stehen bleibt (verwirrend).
        if index is not None:
            self._stitch_cursor = None
        self.update()

    @property
    def stitch_cursor(self) -> tuple[int, int] | None:
        return self._stitch_cursor

    def set_stitch_cursor(self, pos: tuple[int, int] | None) -> None:
        """Setzt den Sticken-Modus-Cursor und scrollt die Zelle in den Viewport."""
        self._stitch_cursor = pos
        if pos is not None:
            self._ensure_cell_visible(pos[0], pos[1])
        self.update()

    def jump_to_next_stitch(self, forward: bool = True) -> bool:
        """Springt zum nächsten/vorherigen ungehakten Stich der aktiven Farbe.

        Reading-Order (links-rechts, oben-unten). Wickelt am Ende um.

        Returns:
            True, wenn ein Stich gefunden wurde.
        """
        if not self._pattern:
            return False
        color_idx = self._current_color_index
        if color_idx < 0 or color_idx >= len(self._pattern.color_entries):
            return False

        import numpy as np

        composite = self._pattern.layer_stack.get_composite_grid()
        # Completion-Mask aus dem oberen sichtbaren Layer pro Cell.
        # Vereinfachung: wir nehmen das "irgendein Layer hat completion auf
        # dieser Cell"-Pattern — gleicher Layer-Stack-Composite-Logik wie
        # Rendering. Präzise: composite-Layer mit Match-Color.
        completion = np.zeros_like(composite, dtype=bool)
        for layer in self._pattern.layer_stack:
            if not layer.visible:
                continue
            mask = layer.grid == color_idx
            completion |= mask & layer.completion_grid

        target_mask = (composite == color_idx) & ~completion
        positions = np.argwhere(target_mask)  # [[y, x], ...]
        if len(positions) == 0:
            return False

        # Reading-order-Index (y * W + x)
        W = self._pattern.width
        order = positions[:, 0] * W + positions[:, 1]
        order_sorted = np.sort(order)

        cur_x, cur_y = self._stitch_cursor if self._stitch_cursor else (-1, -1)
        cur_key = cur_y * W + cur_x  # -W-1 wenn None → kleinster Wert

        if forward:
            mask_next = order_sorted > cur_key
            target_key = (
                int(order_sorted[mask_next][0]) if mask_next.any() else int(order_sorted[0])
            )
        else:
            mask_prev = order_sorted < cur_key
            target_key = (
                int(order_sorted[mask_prev][-1]) if mask_prev.any() else int(order_sorted[-1])
            )

        ty, tx = divmod(target_key, W)
        self.set_stitch_cursor((int(tx), int(ty)))
        return True

    def _ensure_cell_visible(self, x: int, y: int) -> None:
        """Pannt das Pattern so, dass die Zelle im sichtbaren Bereich liegt."""
        cs = self._cell_size
        screen_x = x * cs + self._offset_x
        screen_y = y * cs + self._offset_y
        margin = cs * 2

        new_x, new_y = self._offset_x, self._offset_y
        if screen_x < margin:
            new_x = self._offset_x + (margin - screen_x)
        elif screen_x + cs > self.width() - margin:
            new_x = self._offset_x - ((screen_x + cs) - (self.width() - margin))
        if screen_y < margin:
            new_y = self._offset_y + (margin - screen_y)
        elif screen_y + cs > self.height() - margin:
            new_y = self._offset_y - ((screen_y + cs) - (self.height() - margin))

        if new_x != self._offset_x or new_y != self._offset_y:
            self._offset_x = new_x
            self._offset_y = new_y
            self.offset_changed.emit(self._offset_x, self._offset_y)

    def set_tool(self, tool: Tool) -> None:
        """Setzt das aktuelle Werkzeug."""
        self._tool_manager.current_tool = tool
        self.setCursor(self._tool_manager.get_cursor())

    @property
    def current_tool(self) -> Tool:
        """Gibt das aktuelle Werkzeug zurück."""
        return self._tool_manager.current_tool

    @property
    def selection(self) -> QRect | None:
        """Gibt die aktuelle Auswahl zurück."""
        return self._selection

    def clear_selection(self) -> None:
        """Löscht die aktuelle Auswahl."""
        self._selection = None
        self.update()

    def set_offset(self, x: int, y: int) -> None:
        """Setzt den Canvas-Offset (für Minimap-Navigation)."""
        self._offset_x = x
        self._offset_y = y
        self.update()

    # =========================================================================
    # Cache-Management
    # =========================================================================

    def invalidate_cell(self, x: int, y: int) -> None:
        """Markiert eine Zelle für Neuzeichnung."""
        self._request_update()

    def invalidate_region(self, rect: QRect) -> None:
        """Markiert einen Bereich für Neuzeichnung."""
        self._request_update()

    def _request_update(self) -> None:
        """Fordert ein verzögertes Update an (Batching)."""
        if not self._pending_update:
            self._pending_update = True
            self._update_timer.start()

    def _do_deferred_update(self) -> None:
        """Führt das aufgeschobene Update aus."""
        self._pending_update = False
        self.update()

    # =========================================================================
    # Font-Cache
    # =========================================================================

    def _get_symbol_font(self) -> QFont:
        """Gibt den gecachten Symbol-Font zurück."""
        target_size = max(8, self._cell_size - 6)
        if self._symbol_font is None or self._last_font_size != target_size:
            self._symbol_font = QFont("Segoe UI Symbol", target_size)
            self._last_font_size = target_size
        return self._symbol_font

    # =========================================================================
    # Tool-Kontext
    # =========================================================================

    def _create_tool_context(self, screen_x: int, screen_y: int) -> ToolContext | None:
        """Erstellt einen ToolContext für die Werkzeug-Interaktion."""
        if not self._pattern:
            return None

        grid_x, grid_y = self._screen_to_grid(screen_x, screen_y)

        return ToolContext(
            canvas=self,
            pattern=self._pattern,
            current_color_index=self._current_color_index,
            grid_x=grid_x,
            grid_y=grid_y,
            screen_x=screen_x,
            screen_y=screen_y,
            cell_size=self._cell_size,
            offset_x=self._offset_x,
            offset_y=self._offset_y,
        )

    # =========================================================================
    # Change-Handling
    # =========================================================================

    def _apply_changes(self, changes: list[tuple[int, int, int | None]]) -> None:
        """Wendet Änderungen an (ohne Spiegelung)."""
        for x, y, color_index in changes:
            if color_index is None:
                self.stitch_removed.emit(x, y)
            else:
                self.stitch_placed.emit(x, y, color_index)

    def _apply_changes_with_mirror(self, changes: list[tuple[int, int, int | None]]) -> None:
        """Wendet Änderungen mit Spiegelung an."""
        if not self._has_mirror_active():
            self._apply_changes(changes)
            return

        for x, y, color_index in changes:
            for mx, my in self.get_mirrored_positions(x, y):
                if color_index is None:
                    self.stitch_removed.emit(mx, my)
                else:
                    self.stitch_placed.emit(mx, my, color_index)
