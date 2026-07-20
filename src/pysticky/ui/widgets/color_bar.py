"""
Farbleiste für schnellen Farbzugriff - mit Drag & Drop Unterstützung.
"""

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QMimeData,
    QPoint,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QDrag,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QFont,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QPolygon,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

SWAP_MIME = "application/x-pysticky-color-swap"

from ...core import ColorEntry, Pattern, Thread, ThreadColor
from ...core.i18n import t
from ..color_utils import to_qcolor
from ..styles import THEME


class ColorSwatch(QWidget):
    """Einzelnes Farbfeld in der Farbleiste."""

    clicked = Signal(int)
    double_clicked = Signal(int)
    context_menu_requested = Signal(int, object)  # index, QPoint
    swap_dropped = Signal(int, int)  # source_index, target_index

    # Referenzgroesse (Breite, Hoehe), auf die alle relativen paintEvent-
    # Positionen abgestimmt sind -- size_wh skaliert proportional dazu.
    BASE_SIZE = (48, 62)

    def __init__(
        self, index: int, entry: ColorEntry, parent=None, size_wh: tuple[int, int] | None = None
    ) -> None:
        super().__init__(parent)
        self._index = index
        self._entry = entry
        self._selected = False
        self._hovered = False
        self._glow_intensity = 0.0
        self._press_pos: QPoint | None = None
        self._drop_hover = False
        self._isolated = False  # True wenn diese Farbe gerade hervorgehoben ist
        # Im Diamond-Modus zeigt das Swatch die Drill-Nummer statt des Symbols.
        self._mode: str = "stitch"

        self.setFixedSize(*(size_wh or self.BASE_SIZE))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(self._create_tooltip())
        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        self._glow_animation = QPropertyAnimation(self, b"glow_intensity")
        self._glow_animation.setDuration(300)
        self._glow_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _create_tooltip(self) -> str:
        thread = self._entry.thread
        skip_text = (
            "<br><b style='color: #ff9800;'>⊘ Wird nicht gestickt</b>"
            if self._entry.skip_stitching
            else ""
        )
        return (
            f"<b style='color: {THEME.accent_primary};'>{self._entry.symbol}</b> <b>{thread.name}</b><br>"
            f"<span style='color: {THEME.text_muted};'>{thread.manufacturer or ''}</span><br>"
            f"Nr: {thread.catalog_number or '-'}<br>"
            f"<span style='color: {THEME.accent_primary};'>{self._entry.stitch_count} Stiche</span>{skip_text}"
        )

    def get_glow_intensity(self) -> float:
        return self._glow_intensity

    def set_glow_intensity(self, value: float) -> None:
        self._glow_intensity = value
        self.update()

    glow_intensity = Property(float, get_glow_intensity, set_glow_intensity)

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool) -> None:
        if self._selected != value:
            self._selected = value
            self._glow_animation.stop()
            self._glow_animation.setStartValue(self._glow_intensity)
            self._glow_animation.setEndValue(1.0 if value else 0.0)
            self._glow_animation.start()
            self.update()

    @property
    def isolated(self) -> bool:
        return self._isolated

    @isolated.setter
    def isolated(self, value: bool) -> None:
        if self._isolated != value:
            self._isolated = value
            self.update()

    def set_mode(self, mode: str) -> None:
        """Modus-Wechsel: stitch zeigt Symbol, diamond zeigt Drill-Nummer."""
        if mode == self._mode:
            return
        self._mode = mode
        self.update()

    def update_entry(self, entry: ColorEntry) -> None:
        self._entry = entry
        self.setToolTip(self._create_tooltip())
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(4, 4, -4, -18)
        color = to_qcolor(self._entry.thread.color)
        accent = QColor(THEME.accent_primary)

        # Glow-Effekt
        if self._glow_intensity > 0:
            glow_color = QColor(accent)
            glow_color.setAlphaF(0.3 * self._glow_intensity)

            for i in range(3):
                glow_rect = rect.adjusted(-3 - i * 2, -3 - i * 2, 3 + i * 2, 3 + i * 2)
                glow_color.setAlphaF((0.2 - i * 0.05) * self._glow_intensity)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(glow_color)
                painter.drawRoundedRect(glow_rect, 8 + i, 8 + i)

        # Dreieck-Marker oben
        if self._selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(accent)
            cx = self.width() // 2
            triangle = QPolygon([QPoint(cx - 5, 0), QPoint(cx + 5, 0), QPoint(cx, 5)])
            painter.drawPolygon(triangle)

        # Schatten
        if self._selected or self._hovered:
            shadow = rect.adjusted(2, 2, 2, 2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 60 if self._selected else 40))
            painter.drawRoundedRect(shadow, 6, 6)

        # Farbe mit Gradient
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, color.lighter(115))
        gradient.setColorAt(0.5, color)
        gradient.setColorAt(1, color.darker(110))

        painter.setBrush(QBrush(gradient))

        if self._drop_hover:
            painter.setPen(QPen(QColor(THEME.accent_primary), 3, Qt.PenStyle.DashLine))
        elif self._selected:
            painter.setPen(QPen(accent, 3))
        elif self._hovered:
            painter.setPen(QPen(QColor(THEME.success), 2))
        else:
            painter.setPen(QPen(QColor(THEME.border_light), 1))

        painter.drawRoundedRect(rect, 6, 6)

        # Glanz-Effekt
        gloss = rect.adjusted(3, 3, -3, -rect.height() // 2)
        gloss_grad = QLinearGradient(gloss.topLeft(), gloss.bottomLeft())
        gloss_grad.setColorAt(0, QColor(255, 255, 255, 45))
        gloss_grad.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gloss_grad))
        painter.drawRoundedRect(gloss, 4, 4)

        # Checkmark bei Auswahl
        if self._selected:
            check_size = 14
            check_x = rect.right() - check_size + 2
            check_y = rect.bottom() - check_size + 2

            painter.setBrush(accent)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(check_x, check_y, check_size, check_size)

            painter.setPen(
                QPen(
                    QColor(THEME.text_primary),
                    2,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
            )
            painter.drawLine(check_x + 3, check_y + 7, check_x + 6, check_y + 10)
            painter.drawLine(check_x + 6, check_y + 10, check_x + 11, check_y + 4)

        # Isolations-Markierung: oranger Auflage-Rahmen + 🔍-Badge
        if self._isolated:
            warning = QColor(THEME.warning)
            ring = rect.adjusted(-3, -3, 3, 3)
            painter.setPen(QPen(warning, 2, Qt.PenStyle.SolidLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(ring, 8, 8)
            # Lupen-Badge oben links
            badge_size = 14
            badge_x = rect.left() - 4
            badge_y = rect.top() - 4
            painter.setBrush(warning)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(badge_x, badge_y, badge_size, badge_size)
            painter.setPen(QPen(QColor(THEME.text_primary), 1.5))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(
                badge_x, badge_y, badge_size, badge_size, Qt.AlignmentFlag.AlignCenter, "🔍"
            )

        # "Nicht sticken"-Markierung (diagonale Linie)
        if self._entry.skip_stitching:
            skip_color = QColor(255, 152, 0, 200)  # Orange
            painter.setPen(QPen(skip_color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            # Diagonale Linie von links oben nach rechts unten
            painter.drawLine(rect.left() + 4, rect.top() + 4, rect.right() - 4, rect.bottom() - 4)
            # Kleines "⊘" Symbol oben links
            painter.setBrush(skip_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(rect.left() - 2, rect.top() - 2, 12, 12)
            painter.setPen(QPen(QColor(255, 255, 255), 1.5))
            painter.drawLine(rect.left() + 1, rect.top() + 1, rect.left() + 7, rect.top() + 7)

        # Beschriftung unter dem Swatch: Symbol, wie auf der Zeichenfläche
        # (Diamant-Farben bekommen dasselbe Symbol wie Garnfarben, siehe
        # Pattern.add_color) — sonst lässt sich ein Canvas-Symbol nicht auf
        # das passende Swatch zurückführen.
        symbol_y = rect.bottom() + 2

        label_text = self._entry.symbol
        size = 10 if self._selected else 9

        if self._selected:
            painter.setPen(accent)
            font = QFont("Segoe UI", size, QFont.Weight.Bold)
        else:
            painter.setPen(QColor(THEME.text_muted))
            font = QFont("Segoe UI", size)

        painter.setFont(font)
        painter.drawText(0, symbol_y, self.width(), 14, Qt.AlignmentFlag.AlignCenter, label_text)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
            self.clicked.emit(self._index)
        elif event.button() == Qt.MouseButton.RightButton:
            self.context_menu_requested.emit(self._index, event.globalPosition().toPoint())

    # Schwelle, ab der ein Drag für Color-Swap startet. Default-Qt sind ~10
    # px — viel zu wenig: jede minimale Mausbewegung beim Klick startet
    # einen Drag, dabei wollte der User nur die Farbe selektieren. Mit 25 px
    # muss der Drag bewusst sein.
    _SWAP_DRAG_THRESHOLD = 25

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._press_pos is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        # Wenn die Maus die ColorBar verlassen hat, abbrechen — der User
        # zieht in den Canvas oder woanders hin und will keinen Swap. Ohne
        # diesen Check startet ein Drag-Pixmap-Window mitten im Canvas.
        color_bar = self._find_colorbar_parent()
        if color_bar is not None:
            bar_local = color_bar.mapFromGlobal(event.globalPosition().toPoint())
            if not color_bar.rect().contains(bar_local):
                self._press_pos = None
                return

        distance = (event.position().toPoint() - self._press_pos).manhattanLength()
        threshold = max(self._SWAP_DRAG_THRESHOLD, QApplication.startDragDistance() * 2)
        if distance < threshold:
            return
        self._press_pos = None  # Drag läuft — keine weiteren Triggers

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(SWAP_MIME, str(self._index).encode("utf-8"))
        drag.setMimeData(mime)
        # Drag-Vorschau: kleines Farbquadrat
        preview = QPixmap(36, 36)
        preview.fill(Qt.GlobalColor.transparent)
        p = QPainter(preview)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = to_qcolor(self._entry.thread.color)
        p.setBrush(c)
        p.setPen(QPen(QColor(0, 0, 0, 180), 2))
        p.drawRoundedRect(2, 2, 32, 32, 6, 6)
        p.end()
        drag.setPixmap(preview)
        drag.setHotSpot(QPoint(18, 18))
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._press_pos = None
        super().mouseReleaseEvent(event)

    def _find_colorbar_parent(self) -> "ColorBar | None":
        """Sucht das ColorBar-Parent-Widget in der Hierarchie."""
        w = self.parent()
        while w is not None:
            if isinstance(w, ColorBar):
                return w
            w = w.parent()
        return None

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self._index)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat(SWAP_MIME):
            try:
                src = int(bytes(event.mimeData().data(SWAP_MIME)).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                event.ignore()
                return
            if src == self._index:
                event.ignore()
                return
            event.acceptProposedAction()
            self._drop_hover = True
            self.update()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._drop_hover = False
        self.update()

    def dropEvent(self, event: QDropEvent) -> None:
        self._drop_hover = False
        self.update()
        if not event.mimeData().hasFormat(SWAP_MIME):
            event.ignore()
            return
        try:
            src = int(bytes(event.mimeData().data(SWAP_MIME)).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            event.ignore()
            return
        if src == self._index:
            event.ignore()
            return
        event.acceptProposedAction()
        self.swap_dropped.emit(src, self._index)


class DropIndicator(QWidget):
    """Visueller Indikator für Drop-Zone."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(50, 62)
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        self._active = value
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self._active:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        accent = QColor(THEME.accent_primary)
        pen = QPen(accent, 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 30))

        rect = self.rect().adjusted(5, 5, -5, -18)
        painter.drawRoundedRect(rect, 6, 6)

        painter.setPen(QPen(accent, 2))
        cx, cy = self.width() // 2, (self.height() - 18) // 2 + 5
        painter.drawLine(cx - 8, cy, cx + 8, cy)
        painter.drawLine(cx, cy - 8, cx, cy + 8)


class ColorBar(QWidget):
    """Farbleiste für schnellen Farbzugriff mit Drag & Drop."""

    color_selected = Signal(int)
    color_double_clicked = Signal(int)  # For symbol editing
    color_right_clicked = Signal(int, object)  # For context menu (index, global_pos)
    color_dropped = Signal(object)
    color_swap_requested = Signal(int, int)  # source_index, target_index — Drag&Drop Swap

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pattern: Pattern | None = None
        self._swatches: list[ColorSwatch] = []
        self._current_index: int = 0
        # Merkt sich die ausgewaehlte Farbe zusaetzlich per Objekt-Identitaet
        # (nicht nur per Index) -- Pattern.remove_color() verschiebt hoehere
        # Indizes nach unten, behaelt aber dieselben ColorEntry-Objekte fuer
        # die ueberlebenden Farben. Ohne das wuerde refresh()/_rebuild_swatches()
        # nach dem Loeschen einer Farbe VOR der aktuell ausgewaehlten den
        # gleichen Zahlen-Index weiter als "ausgewaehlt" markieren -- der
        # jetzt aber auf eine ANDERE Farbe zeigt (Canvas' current_color_index
        # bleibt dabei auf der urspruenglich gemeinten Farbe stehen).
        self._current_entry: ColorEntry | None = None
        self._isolated_index: int | None = None
        # Modus beeinflusst die Beschriftung unter den Swatches: Sticken
        # zeigt das Unicode-Symbol, Diamond Painting die DMC-Drill-Nummer.
        self._mode: str = "stitch"
        # Breite der Swatches; Hoehe wird proportional zu ColorSwatch.BASE_SIZE
        # mitskaliert, damit paintEvent's relative Positionierung stimmig bleibt.
        self._swatch_width: int = ColorSwatch.BASE_SIZE[0]

        self.setObjectName("colorBarWidget")
        self.setAcceptDrops(True)
        self._setup_ui()

    @property
    def swatch_size(self) -> int:
        return self._swatch_width

    @swatch_size.setter
    def swatch_size(self, value: int) -> None:
        if value == self._swatch_width:
            return
        self._swatch_width = value
        self._rebuild_swatches()

    def set_mode(self, mode: str) -> None:
        """Wechselt zwischen Stitch- und Diamond-Beschriftung der Swatches."""
        if mode not in ("stitch", "diamond") or mode == self._mode:
            return
        self._mode = mode
        for swatch in self._swatches:
            swatch.set_mode(mode)

    def set_isolated_index(self, index: int | None) -> None:
        """Setzt den Index der isolierten Farbe (None = keine).

        Aktualisiert die Swatch-Marker, ohne die Selektion zu verändern.
        """
        self._isolated_index = index
        for i, swatch in enumerate(self._swatches):
            swatch.isolated = index is not None and i == index

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(0)

        # Header — alle Labels mit parent=self konstruieren, sonst kurzes
        # Top-Level-Phantom beim ersten Show.
        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel("● " + t("MUSTERFARBEN"), self)
        title.setStyleSheet(
            f"font-size: 10px; font-weight: 700; color: {THEME.text_muted}; letter-spacing: 1px;"
        )
        header.addWidget(title)

        self._count_label = QLabel("0", self)
        self._count_label.setStyleSheet(f"font-size: 10px; color: {THEME.text_disabled};")
        header.addWidget(self._count_label)

        self._current_color_label = QLabel("", self)
        self._current_color_label.setStyleSheet(
            f"font-size: 10px; color: {THEME.accent_primary}; font-weight: bold; padding-left: 10px;"
        )
        header.addWidget(self._current_color_label)

        self._drop_hint = QLabel("⬇ " + t("Farbe hierher ziehen"), self)
        self._drop_hint.setStyleSheet(
            f"font-size: 10px; color: {THEME.accent_primary}; font-style: italic;"
        )
        self._drop_hint.setVisible(False)
        header.addWidget(self._drop_hint)

        header.addStretch()
        layout.addLayout(header)
        layout.addSpacing(4)

        # Scroll-Bereich
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFixedHeight(70)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")
        self._scroll.installEventFilter(self)
        self._scroll.viewport().installEventFilter(self)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._container.setFixedHeight(68)
        self._container_layout = QHBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(4)
        self._container_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._drop_indicator = DropIndicator(self._container)
        self._drop_indicator.setVisible(False)

        self._container_layout.addStretch()

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

        self.setFixedHeight(96)

    def set_pattern(self, pattern: Pattern) -> None:
        self._pattern = pattern
        self._current_index = 0
        self._current_entry = pattern.color_entries[0] if pattern.color_entries else None
        self._isolated_index = None  # Isolation gilt pro Pattern
        self._rebuild_swatches()
        self._update_current_color_label()

    @property
    def current_index(self) -> int:
        return self._current_index

    def refresh(self) -> None:
        self._rebuild_swatches()
        if 0 <= self._current_index < len(self._swatches):
            self._swatches[self._current_index].selected = True
        self._update_current_color_label()

    def _update_current_color_label(self) -> None:
        if self._pattern and 0 <= self._current_index < len(self._pattern.color_entries):
            entry = self._pattern.color_entries[self._current_index]
            self._current_color_label.setText(f"✎ {entry.symbol} {entry.thread.name}")
        else:
            self._current_color_label.setText("")

    def _rebuild_swatches(self) -> None:
        # Bulk-Update: Repaint während des Rebuilds aussetzen, damit beim
        # Pattern-Laden kein leeres Phantom-Fenster aufflackert. Qt rendert
        # frisch-konstruierte Widgets sonst kurz top-level bevor sie ins
        # Layout einsortiert sind.
        self.setUpdatesEnabled(False)
        try:
            for swatch in self._swatches:
                swatch.hide()
                swatch.setParent(None)
                swatch.deleteLater()
            self._swatches.clear()

            while self._container_layout.count() > 0:
                item = self._container_layout.takeAt(0)
                if item.widget() and item.widget() != self._drop_indicator:
                    item.widget().hide()
                    item.widget().deleteLater()

            if not self._pattern:
                self._count_label.setText("0")
                self._container_layout.addWidget(self._drop_indicator)
                self._container_layout.addStretch()
                return

            # Ausgewaehlte Farbe per Objekt-Identitaet wiederfinden, statt
            # den alten Zahlen-Index einfach weiterzuverwenden -- wurde eine
            # Farbe VOR der ausgewaehlten geloescht, verschieben sich alle
            # nachfolgenden Indizes um 1, der alte Index zeigt dann auf eine
            # ANDERE Farbe. Nur falls die ausgewaehlte Farbe selbst geloescht
            # wurde (nicht mehr auffindbar), faellt das auf den alten Index
            # zurueck (weiter unten geklemmt).
            if self._current_entry is not None:
                for i, entry in enumerate(self._pattern.color_entries):
                    if entry is self._current_entry:
                        self._current_index = i
                        break

            base_w, base_h = ColorSwatch.BASE_SIZE
            size_wh = (self._swatch_width, round(base_h * self._swatch_width / base_w))
            for i, entry in enumerate(self._pattern.color_entries):
                swatch = ColorSwatch(i, entry, self._container, size_wh=size_wh)
                swatch.set_mode(self._mode)
                swatch.clicked.connect(self._on_swatch_clicked)
                swatch.double_clicked.connect(self._on_swatch_double_clicked)
                swatch.context_menu_requested.connect(self._on_swatch_context_menu)
                swatch.swap_dropped.connect(self.color_swap_requested.emit)
                swatch.selected = i == self._current_index
                swatch.isolated = self._isolated_index is not None and i == self._isolated_index
                self._swatches.append(swatch)
                self._container_layout.addWidget(swatch)

            self._container_layout.addWidget(self._drop_indicator)
            self._container_layout.addStretch()
            self._count_label.setText(f"{len(self._pattern.color_entries)}")
        finally:
            self.setUpdatesEnabled(True)

        if self._swatches and self._current_index >= len(self._swatches):
            self._current_index = 0
        if self._swatches:
            self._swatches[self._current_index].selected = True
            self._current_entry = self._pattern.color_entries[self._current_index]

    def update_swatches(self) -> None:
        if not self._pattern:
            return
        for i, swatch in enumerate(self._swatches):
            if i < len(self._pattern.color_entries):
                swatch.update_entry(self._pattern.color_entries[i])

    def select_color(self, index: int) -> None:
        if 0 <= index < len(self._swatches):
            if 0 <= self._current_index < len(self._swatches):
                self._swatches[self._current_index].selected = False
            self._current_index = index
            self._current_entry = (
                self._pattern.color_entries[index]
                if self._pattern and index < len(self._pattern.color_entries)
                else None
            )
            self._swatches[index].selected = True
            self._scroll.ensureWidgetVisible(self._swatches[index])
            self._update_current_color_label()

    def _on_swatch_clicked(self, index: int) -> None:
        self.select_color(index)
        self.color_selected.emit(index)

    def _on_swatch_double_clicked(self, index: int) -> None:
        self.color_double_clicked.emit(index)

    def _on_swatch_context_menu(self, index: int, global_pos) -> None:
        self.color_right_clicked.emit(index, global_pos)

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.accept()
        scrollbar = self._scroll.horizontalScrollBar()
        delta = event.angleDelta().y()

        if delta != 0:
            step = 50 if abs(delta) > 100 else 30
            if delta > 0:
                scrollbar.setValue(scrollbar.value() - step)
            else:
                scrollbar.setValue(scrollbar.value() + step)

    def eventFilter(self, obj, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Wheel:
            if obj == self._scroll or obj == self._scroll.viewport():
                scrollbar = self._scroll.horizontalScrollBar()
                wheel_event = event
                delta = wheel_event.angleDelta().y()

                if delta != 0:
                    step = 50 if abs(delta) > 100 else 30
                    if delta > 0:
                        scrollbar.setValue(scrollbar.value() - step)
                    else:
                        scrollbar.setValue(scrollbar.value() + step)

                return True
        return super().eventFilter(obj, event)

    def _apply_theme(self) -> None:
        """Re-applies styles for live theme switching."""
        from ..styles import THEME

        # Header-Labels aktualisieren
        for child in self.findChildren(QLabel):
            name = child.text()
            if "MUSTERFARBEN" in name:
                child.setStyleSheet(
                    f"font-size: 10px; font-weight: 700; color: {THEME.text_muted}; letter-spacing: 1px;"
                )
            elif child is self._count_label:
                child.setStyleSheet(f"font-size: 10px; color: {THEME.text_disabled};")
            elif child is self._current_color_label:
                child.setStyleSheet(
                    f"font-size: 10px; color: {THEME.accent_primary}; font-weight: bold; padding-left: 10px;"
                )
            elif child is self._drop_hint:
                child.setStyleSheet(
                    f"font-size: 10px; color: {THEME.accent_primary}; font-style: italic;"
                )
        # Swatch-Tooltips aktualisieren
        for swatch in self._swatches:
            swatch.setToolTip(swatch._create_tooltip())
            swatch.update()

    # Drag & Drop

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat("application/x-pysticky-thread"):
            event.acceptProposedAction()
            self._drop_indicator.active = True
            self._drop_indicator.setVisible(True)
            self._drop_hint.setVisible(True)
            accent = QColor(THEME.accent_primary)
            self.setStyleSheet(
                f"ColorBar {{ background: rgba({accent.red()}, {accent.green()}, {accent.blue()}, 0.1); }}"
            )
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasFormat("application/x-pysticky-thread"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._drop_indicator.active = False
        self._drop_indicator.setVisible(False)
        self._drop_hint.setVisible(False)
        self.setStyleSheet("")

    def dropEvent(self, event: QDropEvent) -> None:
        self._drop_indicator.active = False
        self._drop_indicator.setVisible(False)
        self._drop_hint.setVisible(False)
        self.setStyleSheet("")

        if not event.mimeData().hasFormat("application/x-pysticky-thread"):
            event.ignore()
            return

        data = event.mimeData().data("application/x-pysticky-thread").data().decode()
        parts = data.split("|")

        if len(parts) >= 4:
            manufacturer, catalog_number, name, hex_color = parts[:4]
            color = ThreadColor.from_hex(hex_color)
            thread = Thread(
                name=name,
                color=color,
                manufacturer=manufacturer,
                catalog_number=catalog_number if catalog_number else None,
            )
            event.acceptProposedAction()
            self.color_dropped.emit(thread)
        else:
            event.ignore()
