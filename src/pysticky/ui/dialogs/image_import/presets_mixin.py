"""
Preset-Mixin für den Bildimport-Dialog.

Befüllen der Preset-ComboBox, Laden einer Voreinstellung in die
Widgets und Speichern der aktuellen Einstellungen als User-Preset.
"""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QInputDialog

from ....core.i18n import t
from ..image_import_presets import (
    BUILTIN_PRESETS,
    load_user_presets,
    save_user_presets,
)

if TYPE_CHECKING:
    from .dialog import ImageImportDialog


class PresetsMixin:
    """Mixin für die Import-Voreinstellungen."""

    def _populate_presets(self: "ImageImportDialog") -> None:
        """Füllt die Preset-ComboBox mit Built-in und User-Presets."""
        self.combo_preset.blockSignals(True)
        self.combo_preset.clear()
        self.combo_preset.addItem(t("— Keine Voreinstellung —"))

        for p in BUILTIN_PRESETS:
            self.combo_preset.addItem(f"📦 {p['name']}")

        user_presets = load_user_presets()
        for p in user_presets:
            self.combo_preset.addItem(f"👤 {p['name']}")

        self.combo_preset.blockSignals(False)

    def _on_preset_changed(self: "ImageImportDialog", index: int) -> None:
        """Lädt die ausgewählte Voreinstellung."""
        if index <= 0:
            return  # "Keine Voreinstellung"

        # Built-in Presets: Index 1..len(BUILTIN_PRESETS)
        builtin_count = len(BUILTIN_PRESETS)
        if index <= builtin_count:
            preset = BUILTIN_PRESETS[index - 1]
        else:
            # User Preset
            user_index = index - builtin_count - 1
            user_presets = load_user_presets()
            if user_index < len(user_presets):
                preset = user_presets[user_index]
            else:
                return

        # Einstellungen anwenden (ohne Debounce-Trigger)
        self._updating_size = True
        self.spin_width.setValue(preset.get("width", 80))
        self.spin_height.setValue(preset.get("height", 80))
        self._updating_size = False
        self.spin_colors.setValue(preset.get("max_colors", 20))

        # Dithering
        mode = preset.get("dithering_mode", "none")
        mode_map = {"none": 0, "floyd_steinberg": 1, "ordered": 2}
        self.combo_dithering.setCurrentIndex(mode_map.get(mode, 0))

        # Quantisierung
        quant = preset.get("quantization_method", "nearest")
        quant_map = {"nearest": 0, "median_cut": 1}
        self.combo_quantization.setCurrentIndex(quant_map.get(quant, 0))

        # Backstitches
        self.chk_backstitches.setChecked(preset.get("auto_backstitches", False))

        # Confetti-Reduktion (1 = aus)
        self.spin_confetti.setValue(preset.get("confetti_min_run_size", 1))

        # Palette — DP-Presets springen automatisch auf "DMC Diamond Painting".
        preset_palette = preset.get("palette")
        if preset_palette:
            palette_index = self.combo_palette.findText(preset_palette)
            if palette_index >= 0:
                self.combo_palette.setCurrentIndex(palette_index)

    def _on_save_preset(self: "ImageImportDialog") -> None:
        """Speichert die aktuellen Einstellungen als User-Preset."""
        name, ok = QInputDialog.getText(
            self,
            t("Preset speichern"),
            t("Name für die Voreinstellung:"),
        )
        if not ok or not name.strip():
            return

        preset = {
            "name": name.strip(),
            "width": self.spin_width.value(),
            "height": self.spin_height.value(),
            "max_colors": self.spin_colors.value(),
            "dithering_mode": {0: "none", 1: "floyd_steinberg", 2: "ordered"}.get(
                self.combo_dithering.currentIndex(), "none"
            ),
            "quantization_method": {0: "nearest", 1: "median_cut"}.get(
                self.combo_quantization.currentIndex(), "nearest"
            ),
            "auto_backstitches": self.chk_backstitches.isChecked(),
            "confetti_min_run_size": self.spin_confetti.value(),
        }

        user_presets = load_user_presets()
        # Ersetze bei gleichem Namen
        user_presets = [p for p in user_presets if p.get("name") != preset["name"]]
        user_presets.append(preset)
        save_user_presets(user_presets)

        self._populate_presets()
        # Zum neuen Preset wechseln
        for i in range(self.combo_preset.count()):
            if self.combo_preset.itemText(i) == f"👤 {preset['name']}":
                self.combo_preset.setCurrentIndex(i)
                break
