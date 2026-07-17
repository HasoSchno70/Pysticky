"""
Größen- und Ausschnitt-Logik-Mixin für den Bildimport-Dialog.

Breite/Höhe-Kopplung über das Seitenverhältnis, Crop-Änderungen und
die daraus abgeleitete Standard-Mustergröße.
"""

from typing import TYPE_CHECKING

from ....core.i18n import t
from ....utils import clamp_int

if TYPE_CHECKING:
    from .dialog import ImageImportDialog


class SizeMixin:
    """Mixin für Größen- und Ausschnitt-Berechnungen."""

    def _on_crop_changed(
        self: "ImageImportDialog", x1: float, y1: float, x2: float, y2: float
    ) -> None:
        """Ausschnitt wurde geändert."""
        self._crop = (x1, y1, x2, y2)

        # Info aktualisieren
        if self._image_width > 0 and self._image_height > 0:
            crop_w = int((x2 - x1) * self._image_width)
            crop_h = int((y2 - y1) * self._image_height)

            if self.crop_preview.has_crop():
                self.lbl_crop_info.setText(f"Ausschnitt: {crop_w} × {crop_h} px")
                self.btn_reset_crop.setEnabled(True)
            else:
                self.lbl_crop_info.setText(t("Ausschnitt: Gesamtes Bild"))
                self.btn_reset_crop.setEnabled(False)

            # Größe neu berechnen basierend auf Ausschnitt
            self._recalculate_size_for_crop()

        self._on_settings_changed()

    def _recalculate_size_for_crop(self: "ImageImportDialog") -> None:
        """Berechnet die Mustergröße neu basierend auf dem Ausschnitt."""
        if not self.crop_preview.has_crop():
            return

        x1, y1, x2, y2 = self._crop
        crop_w = int((x2 - x1) * self._image_width)
        crop_h = int((y2 - y1) * self._image_height)

        if crop_w <= 0 or crop_h <= 0:
            return

        # Neue Standardgröße berechnen
        self._updating_size = True
        default_w, default_h = self._calculate_size_for_dimensions(crop_w, crop_h)
        self.spin_width.setValue(default_w)
        self.spin_height.setValue(default_h)
        self._updating_size = False

        self._update_size_info()

    def _on_reset_crop(self: "ImageImportDialog") -> None:
        """Ausschnitt zurücksetzen."""
        self.crop_preview.reset_crop()

    def _on_width_changed(self: "ImageImportDialog", value: int) -> None:
        """Breite wurde geändert."""
        if self._updating_size or not self.chk_aspect.isChecked():
            self._update_size_info()
            self._on_settings_changed()
            return

        # Seitenverhältnis des Ausschnitts verwenden
        crop_w, crop_h = self._get_crop_dimensions()
        if crop_w > 0 and crop_h > 0:
            self._updating_size = True
            aspect = crop_h / crop_w
            new_height = max(10, int(value * aspect))
            self.spin_height.setValue(new_height)
            self._updating_size = False

        self._update_size_info()
        self._on_settings_changed()

    def _on_height_changed(self: "ImageImportDialog", value: int) -> None:
        """Höhe wurde geändert."""
        if self._updating_size or not self.chk_aspect.isChecked():
            self._update_size_info()
            self._on_settings_changed()
            return

        crop_w, crop_h = self._get_crop_dimensions()
        if crop_w > 0 and crop_h > 0:
            self._updating_size = True
            aspect = crop_w / crop_h
            new_width = max(10, int(value * aspect))
            self.spin_width.setValue(new_width)
            self._updating_size = False

        self._update_size_info()
        self._on_settings_changed()

    def _get_crop_dimensions(self: "ImageImportDialog") -> tuple[int, int]:
        """Gibt die Dimensionen des aktuellen Ausschnitts zurück."""
        x1, y1, x2, y2 = self._crop
        crop_w = int((x2 - x1) * self._image_width)
        crop_h = int((y2 - y1) * self._image_height)
        return (crop_w, crop_h)

    def _on_aspect_toggled(self: "ImageImportDialog", checked: bool) -> None:
        """Seitenverhältnis-Checkbox wurde geändert."""
        if checked:
            self._on_width_changed(self.spin_width.value())

    def _update_size_info(self: "ImageImportDialog") -> None:
        """Aktualisiert die Größen-Info."""
        w = self.spin_width.value()
        h = self.spin_height.value()
        w_cm = w / 14 * 2.54
        h_cm = h / 14 * 2.54
        self.lbl_size_info.setText(f"≈ {w_cm:.1f} × {h_cm:.1f} cm bei 14ct Aida")

    def _calculate_size_for_dimensions(
        self: "ImageImportDialog", img_w: int, img_h: int
    ) -> tuple[int, int]:
        """Berechnet eine sinnvolle Standardgröße."""
        if img_w <= 0 or img_h <= 0:
            return (80, 80)

        max_stitches = 100

        if img_w >= img_h:
            width = clamp_int(img_w // 10, 20, max_stitches)
            height = int(width * img_h / img_w)
        else:
            height = clamp_int(img_h // 10, 20, max_stitches)
            width = int(height * img_w / img_h)

        return (max(10, width), max(10, height))

    def _calculate_default_size(self: "ImageImportDialog") -> tuple[int, int]:
        """Berechnet die Standardgröße basierend auf Bild/Ausschnitt."""
        crop_w, crop_h = self._get_crop_dimensions()
        if crop_w > 0 and crop_h > 0:
            return self._calculate_size_for_dimensions(crop_w, crop_h)
        return self._calculate_size_for_dimensions(self._image_width, self._image_height)
