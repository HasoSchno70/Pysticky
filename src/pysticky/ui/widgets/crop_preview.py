"""
Widget für Bildausschnitt-Auswahl.
"""

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QMouseEvent, QPainter, QPaintEvent, QPen, QPixmap
from PySide6.QtWidgets import QLabel

from ...utils import clamp


class CropPreviewWidget(QLabel):
    """
    Vorschau-Widget mit Ausschnitt-Auswahl.

    Ermöglicht das Ziehen eines Rechtecks um einen Bildausschnitt zu wählen.
    """

    crop_changed = Signal(float, float, float, float)  # x1, y1, x2, y2 (normalisiert 0-1)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._pixmap: QPixmap | None = None
        self._scaled_pixmap: QPixmap | None = None
        self._image_rect: QRect = QRect()  # Bereich wo das Bild gezeichnet wird

        # Crop-Auswahl (normalisiert 0-1)
        self._crop_x1: float = 0.0
        self._crop_y1: float = 0.0
        self._crop_x2: float = 1.0
        self._crop_y2: float = 1.0

        # Interaktion
        self._dragging: bool = False
        self._drag_start: QPoint = QPoint()
        self._drag_mode: str = ""  # "new", "move", "resize_tl", "resize_br", etc.
        self._crop_rect: QRect = QRect()  # Pixel-Koordinaten im Widget

        # Resize-Handles
        self._handle_size: int = 10

        self.setMinimumSize(300, 300)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_image(self, pixmap: QPixmap) -> None:
        """Setzt das anzuzeigende Bild."""
        self._pixmap = pixmap
        self._reset_crop()
        self._update_scaled_pixmap()
        self.update()

    def _reset_crop(self) -> None:
        """Setzt den Ausschnitt auf das gesamte Bild zurück."""
        self._crop_x1 = 0.0
        self._crop_y1 = 0.0
        self._crop_x2 = 1.0
        self._crop_y2 = 1.0
        self._emit_crop_changed()

    def _update_scaled_pixmap(self) -> None:
        """Aktualisiert das skalierte Bild."""
        if not self._pixmap:
            return

        # Bild in Widget einpassen
        available = self.size()
        scaled = self._pixmap.scaled(
            available,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._scaled_pixmap = scaled

        # Zentrieren
        x = (available.width() - scaled.width()) // 2
        y = (available.height() - scaled.height()) // 2
        self._image_rect = QRect(x, y, scaled.width(), scaled.height())

        # Crop-Rect aktualisieren
        self._update_crop_rect()

    def _update_crop_rect(self) -> None:
        """Berechnet das Crop-Rechteck in Pixel-Koordinaten."""
        if not self._image_rect.isValid():
            return

        x1 = self._image_rect.x() + int(self._crop_x1 * self._image_rect.width())
        y1 = self._image_rect.y() + int(self._crop_y1 * self._image_rect.height())
        x2 = self._image_rect.x() + int(self._crop_x2 * self._image_rect.width())
        y2 = self._image_rect.y() + int(self._crop_y2 * self._image_rect.height())

        self._crop_rect = QRect(QPoint(x1, y1), QPoint(x2, y2))

    def _pixel_to_normalized(self, x: int, y: int) -> tuple[float, float]:
        """Konvertiert Pixel-Koordinaten zu normalisierten Werten."""
        if not self._image_rect.isValid() or self._image_rect.width() == 0:
            return (0.0, 0.0)

        nx = (x - self._image_rect.x()) / self._image_rect.width()
        ny = (y - self._image_rect.y()) / self._image_rect.height()

        return (clamp(nx, 0.0, 1.0), clamp(ny, 0.0, 1.0))

    def _emit_crop_changed(self) -> None:
        """Sendet das crop_changed Signal."""
        self.crop_changed.emit(self._crop_x1, self._crop_y1, self._crop_x2, self._crop_y2)

    def get_crop(self) -> tuple[float, float, float, float]:
        """Gibt den aktuellen Ausschnitt zurück (normalisiert)."""
        return (self._crop_x1, self._crop_y1, self._crop_x2, self._crop_y2)

    def has_crop(self) -> bool:
        """Prüft ob ein Ausschnitt gewählt wurde (nicht das ganze Bild)."""
        return not (
            self._crop_x1 <= 0.01
            and self._crop_y1 <= 0.01
            and self._crop_x2 >= 0.99
            and self._crop_y2 >= 0.99
        )

    def reset_crop(self) -> None:
        """Setzt den Ausschnitt zurück."""
        self._reset_crop()
        self._update_crop_rect()
        self.update()

    def set_crop(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """Setzt den Ausschnitt programmatisch (normalisiert 0-1), z.B. beim
        Vorbefüllen des Import-Dialogs aus einem bereits importierten Muster."""
        x1, y1, x2, y2 = (
            clamp(x1, 0.0, 1.0),
            clamp(y1, 0.0, 1.0),
            clamp(x2, 0.0, 1.0),
            clamp(y2, 0.0, 1.0),
        )
        # x1<=x2/y1<=y2 erzwingen (der Maus-Drag-Pfad haelt das immer ein,
        # dieser programmatische Pfad bisher nicht) -- eine invertierte
        # source_image_crop aus einer beschaedigten/handbearbeiteten .pxs-
        # Datei (file_io.py laedt das ohne Validierung) wuerde sonst
        # unbemerkt bis zu core/image_import.py durchgereicht, wo ein
        # max(right, left+1)-Fallback das nur noch stillschweigend auf
        # einen 1px-Streifen zusammenstaucht statt einen Fehler zu zeigen.
        self._crop_x1, self._crop_x2 = min(x1, x2), max(x1, x2)
        self._crop_y1, self._crop_y2 = min(y1, y2), max(y1, y2)
        self._update_crop_rect()
        self._emit_crop_changed()
        self.update()

    def resizeEvent(self, event) -> None:
        """Widget-Größe geändert."""
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Zeichnet das Widget."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Hintergrund
        painter.fillRect(self.rect(), QColor(26, 26, 46))

        if not self._scaled_pixmap:
            # Kein Bild
            painter.setPen(QColor(96, 96, 128))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Kein Bild geladen")
            return

        # Bild zeichnen (abgedunkelt außerhalb des Ausschnitts)
        painter.drawPixmap(self._image_rect, self._scaled_pixmap)

        # Abdunkelung außerhalb des Crop-Bereichs
        overlay = QColor(0, 0, 0, 150)

        # Oben
        painter.fillRect(
            self._image_rect.x(),
            self._image_rect.y(),
            self._image_rect.width(),
            self._crop_rect.y() - self._image_rect.y(),
            overlay,
        )
        # Unten
        painter.fillRect(
            self._image_rect.x(),
            self._crop_rect.bottom(),
            self._image_rect.width(),
            self._image_rect.bottom() - self._crop_rect.bottom(),
            overlay,
        )
        # Links
        painter.fillRect(
            self._image_rect.x(),
            self._crop_rect.y(),
            self._crop_rect.x() - self._image_rect.x(),
            self._crop_rect.height(),
            overlay,
        )
        # Rechts
        painter.fillRect(
            self._crop_rect.right(),
            self._crop_rect.y(),
            self._image_rect.right() - self._crop_rect.right(),
            self._crop_rect.height(),
            overlay,
        )

        # Crop-Rahmen
        pen = QPen(QColor(110, 198, 160), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self._crop_rect)

        # Drittel-Linien (Regel der Drittel)
        pen.setWidth(1)
        pen.setColor(QColor(110, 198, 160, 100))
        painter.setPen(pen)

        w = self._crop_rect.width()
        h = self._crop_rect.height()
        x = self._crop_rect.x()
        y = self._crop_rect.y()

        # Vertikale Linien
        painter.drawLine(x + w // 3, y, x + w // 3, y + h)
        painter.drawLine(x + 2 * w // 3, y, x + 2 * w // 3, y + h)
        # Horizontale Linien
        painter.drawLine(x, y + h // 3, x + w, y + h // 3)
        painter.drawLine(x, y + 2 * h // 3, x + w, y + 2 * h // 3)

        # Resize-Handles
        handle_color = QColor(110, 198, 160)
        painter.setBrush(QBrush(handle_color))
        painter.setPen(QPen(QColor(255, 255, 255), 1))

        handles = self._get_handles()
        for handle_rect in handles.values():
            painter.drawRect(handle_rect)

    def _get_handles(self) -> dict[str, QRect]:
        """Gibt die Positionen der Resize-Handles zurück."""
        hs = self._handle_size
        r = self._crop_rect

        return {
            "tl": QRect(r.left() - hs // 2, r.top() - hs // 2, hs, hs),
            "tr": QRect(r.right() - hs // 2, r.top() - hs // 2, hs, hs),
            "bl": QRect(r.left() - hs // 2, r.bottom() - hs // 2, hs, hs),
            "br": QRect(r.right() - hs // 2, r.bottom() - hs // 2, hs, hs),
            "t": QRect(r.center().x() - hs // 2, r.top() - hs // 2, hs, hs),
            "b": QRect(r.center().x() - hs // 2, r.bottom() - hs // 2, hs, hs),
            "l": QRect(r.left() - hs // 2, r.center().y() - hs // 2, hs, hs),
            "r": QRect(r.right() - hs // 2, r.center().y() - hs // 2, hs, hs),
        }

    def _get_handle_at(self, pos: QPoint) -> str:
        """Ermittelt welcher Handle sich an der Position befindet."""
        handles = self._get_handles()
        for name, rect in handles.items():
            if rect.contains(pos):
                return name
        return ""

    def _update_cursor(self, pos: QPoint) -> None:
        """Aktualisiert den Cursor basierend auf der Position."""
        handle = self._get_handle_at(pos)

        if handle in ("tl", "br"):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif handle in ("tr", "bl"):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif handle in ("t", "b"):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif handle in ("l", "r"):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif self._crop_rect.contains(pos):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Maus gedrückt."""
        # WICHTIG: event.accept() bei Mittel-/Rechtsklick verhindert Windows
        # AutoScroll-Modus (das flackernde "Scrollen deaktiviert"-Toast),
        # siehe MouseEventsMixin.mousePressEvent für den gleichen Fix.
        event.accept()
        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.position().toPoint()
        self._drag_start = pos
        self._dragging = True

        # Handle?
        handle = self._get_handle_at(pos)
        if handle:
            self._drag_mode = f"resize_{handle}"
        elif self._crop_rect.contains(pos):
            self._drag_mode = "move"
        else:
            # Neues Rechteck beginnen
            self._drag_mode = "new"
            nx, ny = self._pixel_to_normalized(pos.x(), pos.y())
            self._crop_x1 = nx
            self._crop_y1 = ny
            self._crop_x2 = nx
            self._crop_y2 = ny

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Maus bewegt."""
        pos = event.position().toPoint()

        if not self._dragging:
            self._update_cursor(pos)
            return

        nx, ny = self._pixel_to_normalized(pos.x(), pos.y())

        if self._drag_mode == "new":
            # Neues Rechteck ziehen
            start_nx, start_ny = self._pixel_to_normalized(
                self._drag_start.x(), self._drag_start.y()
            )
            self._crop_x1 = min(start_nx, nx)
            self._crop_y1 = min(start_ny, ny)
            self._crop_x2 = max(start_nx, nx)
            self._crop_y2 = max(start_ny, ny)

        elif self._drag_mode == "move":
            # Rechteck verschieben
            dx = nx - self._pixel_to_normalized(self._drag_start.x(), 0)[0]
            dy = ny - self._pixel_to_normalized(0, self._drag_start.y())[1]

            w = self._crop_x2 - self._crop_x1
            h = self._crop_y2 - self._crop_y1

            new_x1 = self._crop_x1 + dx
            new_y1 = self._crop_y1 + dy

            # Grenzen prüfen
            if new_x1 < 0:
                new_x1 = 0
            if new_y1 < 0:
                new_y1 = 0
            if new_x1 + w > 1:
                new_x1 = 1 - w
            if new_y1 + h > 1:
                new_y1 = 1 - h

            self._crop_x1 = new_x1
            self._crop_y1 = new_y1
            self._crop_x2 = new_x1 + w
            self._crop_y2 = new_y1 + h

            self._drag_start = pos

        elif self._drag_mode.startswith("resize_"):
            # Größe ändern
            handle = self._drag_mode[7:]  # "resize_tl" -> "tl"

            if "l" in handle:
                self._crop_x1 = min(nx, self._crop_x2 - 0.05)
            if "r" in handle:
                self._crop_x2 = max(nx, self._crop_x1 + 0.05)
            if "t" in handle:
                self._crop_y1 = min(ny, self._crop_y2 - 0.05)
            if "b" in handle:
                self._crop_y2 = max(ny, self._crop_y1 + 0.05)

        self._update_crop_rect()
        self._emit_crop_changed()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Maus losgelassen."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._drag_mode = ""

            # Zu kleinen Ausschnitt auf Vollbild zurücksetzen
            w = self._crop_x2 - self._crop_x1
            h = self._crop_y2 - self._crop_y1
            if w < 0.05 or h < 0.05:
                self._reset_crop()
                self._update_crop_rect()
                self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Doppelklick - Ausschnitt zurücksetzen."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.reset_crop()
