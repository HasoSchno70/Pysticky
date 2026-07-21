"""
Minimap-Widget zur Übersicht für große Muster.
"""

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QImage,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QResizeEvent,
)
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from ...core import Pattern
from ...core.i18n import t
from ...utils import clamp
from ..color_utils import to_qcolor
from ..styles import THEME, Styles


class MinimapWidget(QFrame):
    """Minimap zur Musterübersicht mit Viewport-Anzeige."""

    viewport_changed = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pattern: Pattern | None = None
        self._viewport_x: float = 0.0
        self._viewport_y: float = 0.0
        self._viewport_w: float = 1.0
        self._viewport_h: float = 1.0

        self._cached_image: QImage | None = None
        self._dragging: bool = False

        self.setMinimumSize(120, 100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setStyleSheet(f"""
            MinimapWidget {{
                background: {THEME.bg_dark};
                border: 2px solid {THEME.border_medium};
                border-radius: 8px;
            }}
        """)

    def set_pattern(self, pattern: Pattern) -> None:
        self._pattern = pattern
        self._cached_image = None
        self._rebuild_cache()
        self.update()

    def set_viewport(self, x: float, y: float, w: float, h: float) -> None:
        self._viewport_x = clamp(x, 0.0, 1.0)
        self._viewport_y = clamp(y, 0.0, 1.0)
        self._viewport_w = clamp(w, 0.01, 1.0)
        self._viewport_h = clamp(h, 0.01, 1.0)
        self.update()

    def _get_available_size(self) -> tuple[int, int]:
        margin = 8
        return (max(20, self.width() - margin * 2), max(20, self.height() - margin * 2))

    def _rebuild_cache(self) -> None:
        if not self._pattern:
            self._cached_image = None
            return

        avail_w, avail_h = self._get_available_size()
        pattern_aspect = self._pattern.width / self._pattern.height
        avail_aspect = avail_w / avail_h

        if pattern_aspect > avail_aspect:
            img_w = avail_w
            img_h = int(avail_w / pattern_aspect)
        else:
            img_h = avail_h
            img_w = int(avail_h * pattern_aspect)

        img_w = max(10, img_w)
        img_h = max(10, img_h)

        image = QImage(img_w, img_h, QImage.Format.Format_RGB32)
        image.fill(QColor(250, 250, 245))

        scale_x = img_w / self._pattern.width
        scale_y = img_h / self._pattern.height

        for y in range(self._pattern.height):
            for x in range(self._pattern.width):
                color_idx = self._pattern.get_stitch(x, y)
                if color_idx is not None:
                    entry = self._pattern.get_color_entry(color_idx)
                    if entry:
                        px = int(x * scale_x)
                        py = int(y * scale_y)
                        px_end = max(px + 1, int((x + 1) * scale_x))
                        py_end = max(py + 1, int((y + 1) * scale_y))

                        color = to_qcolor(entry.thread.color).rgb()

                        for py2 in range(py, min(py_end, img_h)):
                            for px2 in range(px, min(px_end, img_w)):
                                image.setPixel(px2, py2, color)

        self._cached_image = image

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._pattern or not self._cached_image:
            painter.setPen(QColor(THEME.text_muted))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, t("Kein Muster"))
            return

        img_rect = self._get_image_rect()
        painter.drawImage(img_rect, self._cached_image)

        painter.setPen(QPen(QColor(THEME.border_medium), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(img_rect)

        vp_rect = self._get_viewport_screen_rect(img_rect)
        overlay_color = QColor(0, 0, 0, 100)

        if vp_rect.top() > img_rect.top():
            painter.fillRect(
                img_rect.left(),
                img_rect.top(),
                img_rect.width(),
                vp_rect.top() - img_rect.top(),
                overlay_color,
            )
        if vp_rect.bottom() < img_rect.bottom():
            painter.fillRect(
                img_rect.left(),
                vp_rect.bottom(),
                img_rect.width(),
                img_rect.bottom() - vp_rect.bottom(),
                overlay_color,
            )
        if vp_rect.left() > img_rect.left():
            painter.fillRect(
                img_rect.left(),
                max(vp_rect.top(), img_rect.top()),
                vp_rect.left() - img_rect.left(),
                min(vp_rect.bottom(), img_rect.bottom()) - max(vp_rect.top(), img_rect.top()),
                overlay_color,
            )
        if vp_rect.right() < img_rect.right():
            painter.fillRect(
                vp_rect.right(),
                max(vp_rect.top(), img_rect.top()),
                img_rect.right() - vp_rect.right(),
                min(vp_rect.bottom(), img_rect.bottom()) - max(vp_rect.top(), img_rect.top()),
                overlay_color,
            )

        painter.setPen(QPen(QColor(THEME.accent_primary), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(vp_rect.adjusted(0, 0, -1, -1))

    def _get_image_rect(self) -> QRect:
        if not self._cached_image:
            return QRect()

        img_w = self._cached_image.width()
        img_h = self._cached_image.height()
        x = (self.width() - img_w) // 2
        y = (self.height() - img_h) // 2
        return QRect(x, y, img_w, img_h)

    def _get_viewport_screen_rect(self, img_rect: QRect) -> QRect:
        x = img_rect.left() + int(self._viewport_x * img_rect.width())
        y = img_rect.top() + int(self._viewport_y * img_rect.height())
        w = max(4, int(self._viewport_w * img_rect.width()))
        h = max(4, int(self._viewport_h * img_rect.height()))

        if x < img_rect.left():
            x = img_rect.left()
        if y < img_rect.top():
            y = img_rect.top()
        if x + w > img_rect.right():
            w = img_rect.right() - x
        if y + h > img_rect.bottom():
            h = img_rect.bottom() - y

        return QRect(x, y, w, h)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._handle_click(event.position().toPoint())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self._handle_click(event.position().toPoint())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

    def _handle_click(self, pos: QPoint) -> None:
        if not self._cached_image:
            return

        img_rect = self._get_image_rect()
        if img_rect.width() <= 0 or img_rect.height() <= 0:
            return

        rel_x = clamp((pos.x() - img_rect.left()) / img_rect.width(), 0.0, 1.0)
        rel_y = clamp((pos.y() - img_rect.top()) / img_rect.height(), 0.0, 1.0)

        self.viewport_changed.emit(rel_x, rel_y)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._rebuild_cache()

    def refresh(self) -> None:
        self._rebuild_cache()
        self.update()

    def _apply_theme(self) -> None:
        self.setStyleSheet(f"""
            MinimapWidget {{
                background: {THEME.bg_dark};
                border: 2px solid {THEME.border_medium};
                border-radius: 8px;
            }}
        """)
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(200, 150)


class MinimapPanel(QWidget):
    """Panel mit Minimap und Titel."""

    viewport_changed = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._title = QLabel("📍 " + t("ÜBERSICHT"))
        self._title.setStyleSheet(Styles.section_header())
        layout.addWidget(self._title)

        self.minimap = MinimapWidget()
        self.minimap.viewport_changed.connect(self.viewport_changed.emit)
        layout.addWidget(self.minimap, 1)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet(f"font-size: 10px; color: {THEME.text_muted};")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)

    def _apply_theme(self) -> None:
        # Titel fehlte hier bisher (Runde 14) -- gleiche Bug-Klasse wie
        # tile_preview_panel.py (Runde 12): Styles.section_header() wurde
        # nur einmalig in _setup_ui() gesetzt und blieb nach einem Live-
        # Theme-Wechsel auf der alten Akzentfarbe haengen.
        self._title.setStyleSheet(Styles.section_header())
        self.minimap._apply_theme()
        self.info_label.setStyleSheet(f"font-size: 10px; color: {THEME.text_muted};")

    def set_pattern(self, pattern: Pattern) -> None:
        self.minimap.set_pattern(pattern)
        if pattern:
            self.info_label.setText(f"{pattern.width} × {pattern.height} Stiche")
        else:
            self.info_label.setText("")

    def set_viewport(self, x: float, y: float, w: float, h: float) -> None:
        self.minimap.set_viewport(x, y, w, h)

    def refresh(self) -> None:
        self.minimap.refresh()
