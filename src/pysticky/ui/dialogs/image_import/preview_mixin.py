"""
Vorschau-Mixin für den Bildimport-Dialog.

Debounce-gesteuerte Live-Vorschau, Pattern→Bild-Konvertierung,
Pixmap-Laden (inkl. Pillow-Fallback) und die Bild-Anpassungs-Slider.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap

from ....core import Pattern, check_pillow_available, import_image
from ....core.i18n import t
from ...styles import THEME

if TYPE_CHECKING:
    from .dialog import ImageImportDialog


class PreviewMixin:
    """Mixin für die Muster-Vorschau und Bild-Anpassung."""

    def _on_brightness_changed(self: "ImageImportDialog", value: int) -> None:
        self.lbl_brightness.setText(f"{value}%")
        self._on_settings_changed()

    def _on_contrast_changed(self: "ImageImportDialog", value: int) -> None:
        self.lbl_contrast.setText(f"{value}%")
        self._on_settings_changed()

    def _on_saturation_changed(self: "ImageImportDialog", value: int) -> None:
        self.lbl_saturation.setText(f"{value}%")
        self._on_settings_changed()

    def _on_reset_adjust(self: "ImageImportDialog") -> None:
        """Setzt alle drei Slider auf 100 % zurück."""
        for slider in (self.slider_brightness, self.slider_contrast, self.slider_saturation):
            slider.setValue(100)

    @staticmethod
    def _load_pixmap(image_path: Path) -> QPixmap:
        """
        Lädt ein Bild als QPixmap — auch Formate die Qt nicht nativ unterstützt (AVIF, etc.).

        Qt kann nur PNG/JPG/BMP/GIF nativ laden. Für alle anderen Formate
        wird Pillow als Fallback verwendet: Bild → RGB → QImage → QPixmap.
        """
        # Erst Qt probieren (schneller für native Formate)
        pixmap = QPixmap(str(image_path))
        if not pixmap.isNull():
            return pixmap

        # Fallback: über Pillow laden (AVIF, TIFF-Varianten, etc.)
        try:
            from PIL import Image

            pil_img = Image.open(str(image_path))
            # In RGB konvertieren (AVIF kann RGBA sein)
            if pil_img.mode in ("RGBA", "LA", "P", "PA"):
                background = Image.new("RGB", pil_img.size, (255, 255, 255))
                if pil_img.mode == "P":
                    pil_img = pil_img.convert("RGBA")
                if pil_img.mode in ("RGBA", "LA", "PA"):
                    background.paste(pil_img, mask=pil_img.split()[-1])
                    pil_img = background
                else:
                    pil_img = pil_img.convert("RGB")
            elif pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")

            data = pil_img.tobytes("raw", "RGB")
            qimage = QImage(
                data,
                pil_img.width,
                pil_img.height,
                pil_img.width * 3,
                QImage.Format.Format_RGB888,
            )
            # QImage kopieren, da 'data' sonst aus dem Scope fällt
            return QPixmap.fromImage(qimage.copy())
        except (OSError, ValueError, RuntimeError):
            return QPixmap()  # Leeres Pixmap als letzter Fallback

    def _on_settings_changed(self: "ImageImportDialog") -> None:
        """Einstellungen wurden geändert — startet Debounce-Timer für Live-Vorschau."""
        # Vorschau-Pattern ungültig machen
        self._preview_pattern = None

        if self._image_path:
            self.lbl_preview_info.setText(t("⏳ Vorschau wird aktualisiert..."))
            self.lbl_preview_info.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
            # Debounce: Timer (re-)starten
            self._preview_timer.start()

    def _on_auto_preview(self: "ImageImportDialog") -> None:
        """Automatische Live-Vorschau nach Debounce-Timer."""
        self._on_preview()

    def _on_preview(self: "ImageImportDialog") -> None:
        """Vorschau generieren."""
        if not self._image_path or not check_pillow_available():
            return

        self.lbl_preview_info.setText(t("⏳ Generiere Vorschau..."))
        self.lbl_preview_info.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        self.repaint()

        try:
            settings = self._get_settings()
            self._preview_pattern = import_image(self._image_path, settings, self._crop)

            preview_img = self._pattern_to_image(self._preview_pattern)

            qimage = QImage(
                preview_img.tobytes(),
                preview_img.width,
                preview_img.height,
                preview_img.width * 3,
                QImage.Format.Format_RGB888,
            )
            pixmap = QPixmap.fromImage(qimage)

            # Muster-Vorschau im Label anzeigen (max 250px)
            max_preview = 250
            if pixmap.width() > max_preview or pixmap.height() > max_preview:
                pixmap = pixmap.scaled(
                    max_preview,
                    max_preview,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                )
            self._preview_image_label.setPixmap(pixmap)

            stats = self._preview_pattern.get_statistics()
            self.lbl_preview_info.setText(
                f"✓ {stats['width']} × {stats['height']} Stiche | "
                f"{stats['used_colors']} Farben | {stats['total_stitches']} Stiche"
            )
            self.lbl_preview_info.setStyleSheet(f"color: {THEME.accent_primary}; font-size: 11px;")

        except (OSError, ValueError) as e:
            self.lbl_preview_info.setText(f"❌ Fehler: {e}")
            self.lbl_preview_info.setStyleSheet(f"color: {THEME.error}; font-size: 11px;")

    def _pattern_to_image(self: "ImageImportDialog", pattern: Pattern):
        """
        Konvertiert ein Pattern zu einem PIL Image.

        Verwendet numpy-LUT statt putpixel() für drastisch bessere Performance.
        """
        import numpy as np
        from PIL import Image

        from ....core.layer import NO_STITCH

        cell_size = max(1, 300 // max(pattern.width, pattern.height))

        # Farb-LUT erstellen
        bg_color = np.array([250, 250, 245], dtype=np.uint8)
        color_lut = np.zeros((len(pattern.color_entries) + 1, 3), dtype=np.uint8)
        for i, entry in enumerate(pattern.color_entries):
            color_lut[i] = [entry.thread.color.r, entry.thread.color.g, entry.thread.color.b]

        # Grid als numpy-Array
        layer = pattern.active_layer
        grid = layer.grid.copy()

        # Pixel-Array: 1 Pixel pro Stich
        pixel_array = np.full((pattern.height, pattern.width, 3), bg_color, dtype=np.uint8)
        filled_mask = grid != NO_STITCH
        if np.any(filled_mask):
            pixel_array[filled_mask] = color_lut[grid[filled_mask]]

        # Als Image erstellen und auf cell_size hochskalieren (Nearest Neighbor)
        small_img = Image.fromarray(pixel_array, "RGB")
        img_width = pattern.width * cell_size
        img_height = pattern.height * cell_size
        img = small_img.resize((img_width, img_height), Image.Resampling.NEAREST)

        return img
