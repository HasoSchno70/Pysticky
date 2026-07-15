"""
Horizontale Icon-Werkzeugleiste (oberer Rand des Hauptfensters).

Ersetzt eine native ``QToolBar`` durch ein eigenes Widget, damit bei
schmalen Fenstern das gleiche Hover-Auto-Scroll-Verhalten wie bei der
linken Werkzeugleiste (``widgets/tool_bar.py``) greift, statt Qt's
Standard-Ueberlauf-Pfeil (">>"-Menue).
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QWidget


class IconToolBar(QWidget):
    """Horizontal scrollbare Icon-Leiste mit Hover-Auto-Scroll.

    Analog zur vertikalen ``ToolBar``: statt eines klassischen Scrollbalkens
    scrollt der Inhalt automatisch, sobald die Maus links/rechts in eine
    schmale Hover-Zone kommt. Kleine ◀/▶-Hinweise am Rand zeigen an, wenn
    in dieser Richtung noch mehr Icons folgen.
    """

    HOVER_ZONE_PX = 28
    SCROLL_STEP_PX = 6
    SCROLL_INTERVAL_MS = 16

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer_layout.addWidget(self._scroll_area)

        content = QWidget()
        self._scroll_area.setWidget(content)
        self._content_layout = QHBoxLayout(content)
        self._content_layout.setContentsMargins(6, 2, 6, 2)
        self._content_layout.setSpacing(2)

        # ◀/▶-Scroll-Hinweise: eigene Overlay-Labels, transparent fuer
        # Maus-Events, damit die Hover-Auto-Scroll-Zone darunter weiter
        # funktioniert (gleiches Prinzip wie bei der vertikalen ToolBar).
        self._scroll_hint_left = self._create_scroll_hint("◀")
        self._scroll_hint_right = self._create_scroll_hint("▶")
        bar = self._scroll_area.horizontalScrollBar()
        bar.valueChanged.connect(self._update_scroll_hints)
        bar.rangeChanged.connect(self._update_scroll_hints)

        # Pollt die Cursor-Position statt auf Mouse-Move-Events zu warten
        # (Begruendung siehe ``ToolBar._poll_auto_scroll``: die Buttons
        # fuellen fast den ganzen Viewport aus, Move-Events landen also
        # auf den Buttons, nicht auf dem Viewport dahinter).
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setInterval(self.SCROLL_INTERVAL_MS)
        self._scroll_timer.timeout.connect(self._poll_auto_scroll)
        self._scroll_timer.start()

    def addWidget(self, widget: QWidget) -> None:
        """Fuegt ein Widget rechts an die Leiste an (API-kompatibel zu QToolBar.addWidget)."""
        self._content_layout.addWidget(widget)

    def finalize(self) -> None:
        """Nach dem letzten ``addWidget``-Aufruf: Stretch + Hoehe fixieren."""
        self._content_layout.addStretch()
        content_height = self._scroll_area.widget().sizeHint().height()
        self.setFixedHeight(content_height)
        self._position_scroll_hints()
        QTimer.singleShot(0, self._update_scroll_hints)

    def _create_scroll_hint(self, arrow: str) -> QLabel:
        label = QLabel(arrow, self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedWidth(16)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        label.hide()
        return label

    def _position_scroll_hints(self) -> None:
        h = self.height()
        self._scroll_hint_left.setGeometry(0, 0, 16, h)
        self._scroll_hint_right.setGeometry(self.width() - 16, 0, 16, h)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_scroll_hints()

    def _update_scroll_hints(self) -> None:
        bar = self._scroll_area.horizontalScrollBar()
        self._scroll_hint_left.setVisible(bar.value() > bar.minimum())
        self._scroll_hint_right.setVisible(bar.value() < bar.maximum())

    def _poll_auto_scroll(self) -> None:
        bar = self._scroll_area.horizontalScrollBar()
        if bar.maximum() == bar.minimum():
            return

        viewport = self._scroll_area.viewport()
        local_pos = viewport.mapFromGlobal(QCursor.pos())
        if not viewport.rect().contains(local_pos):
            return

        x = local_pos.x()
        if x < self.HOVER_ZONE_PX:
            bar.setValue(bar.value() - self.SCROLL_STEP_PX)
        elif x > viewport.width() - self.HOVER_ZONE_PX:
            bar.setValue(bar.value() + self.SCROLL_STEP_PX)

    def reapply_hint_style(self, accent_color: str, bg_color: str) -> None:
        """Aktualisiert das Styling der Scroll-Hinweise (Theme-Wechsel)."""
        hint_style = f"""
            color: {accent_color};
            background: {bg_color};
            font-size: 11px;
            font-weight: bold;
        """
        self._scroll_hint_left.setStyleSheet(hint_style)
        self._scroll_hint_right.setStyleSheet(hint_style)
