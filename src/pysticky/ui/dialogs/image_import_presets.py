"""
Preset-Verwaltung für den Bildimport-Dialog.
"""

import json
from pathlib import Path

from ...utils.logging import get_logger

logger = get_logger(__name__)

BUILTIN_PRESETS = [
    # Kreuzstich-Presets
    {
        "name": "Klein (Lesezeichen)",
        "width": 40,
        "height": 60,
        "max_colors": 10,
        "dithering_mode": "none",
        "quantization_method": "nearest",
        "auto_backstitches": False,
    },
    {
        "name": "Mittel (Bild)",
        "width": 100,
        "height": 100,
        "max_colors": 25,
        "dithering_mode": "floyd_steinberg",
        "quantization_method": "nearest",
        "auto_backstitches": False,
    },
    {
        "name": "Gross (Wandbild)",
        "width": 200,
        "height": 250,
        "max_colors": 40,
        "dithering_mode": "floyd_steinberg",
        "quantization_method": "median_cut",
        "auto_backstitches": False,
    },
    {
        "name": "Foto (Detailreich)",
        "width": 150,
        "height": 150,
        "max_colors": 50,
        "dithering_mode": "ordered",
        "quantization_method": "median_cut",
        "auto_backstitches": True,
    },
    # Diamond-Painting-Presets: Größen passen bei 2.5mm-Drill-Pitch
    # 1:1 auf das jeweilige DIN-Format. "palette" springt automatisch auf
    # DMC Diamond Painting — deren is_diamond-Flag markiert das Pattern
    # beim Import als DP (image_import.py), ein separates dp_mode-Flag
    # auf dem Preset ist dafür nicht nötig.
    {
        "name": "💎 DP A4 quadratisch (60×60)",
        "width": 60,
        "height": 60,
        "max_colors": 30,
        "dithering_mode": "floyd_steinberg",
        "quantization_method": "median_cut",
        "auto_backstitches": False,
        "palette": "DMC Diamond Painting",
    },
    {
        "name": "💎 DP A3 (100×100)",
        "width": 100,
        "height": 100,
        "max_colors": 35,
        "dithering_mode": "floyd_steinberg",
        "quantization_method": "median_cut",
        "auto_backstitches": False,
        "palette": "DMC Diamond Painting",
    },
    {
        "name": "💎 DP A2 (150×150)",
        "width": 150,
        "height": 150,
        "max_colors": 40,
        "dithering_mode": "floyd_steinberg",
        "quantization_method": "median_cut",
        "auto_backstitches": False,
        "palette": "DMC Diamond Painting",
    },
    {
        "name": "💎 DP A1 (200×200)",
        "width": 200,
        "height": 200,
        "max_colors": 45,
        "dithering_mode": "floyd_steinberg",
        "quantization_method": "median_cut",
        "auto_backstitches": False,
        "palette": "DMC Diamond Painting",
    },
    {
        "name": "💎 DP A0 (300×300)",
        "width": 300,
        "height": 300,
        "max_colors": 50,
        "dithering_mode": "floyd_steinberg",
        "quantization_method": "median_cut",
        "auto_backstitches": False,
        "palette": "DMC Diamond Painting",
    },
]


def get_user_presets_path() -> Path:
    """Gibt den Pfad zur User-Presets-Datei zurück."""
    presets_dir = Path.home() / ".pysticky"
    presets_dir.mkdir(exist_ok=True)
    return presets_dir / "import_presets.json"


def load_user_presets() -> list[dict]:
    """Lädt benutzerdefinierte Import-Presets."""
    path = get_user_presets_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError, ValueError):
            logger.warning("User-Presets konnten nicht geladen werden: %s", path)
            return []

        # Struktur validieren -- _populate_presets() (presets_mixin.py)
        # greift auf p["name"] fuer jeden Eintrag zu. Ohne diese Pruefung
        # liess eine strukturell falsche Datei (kaputtbearbeitet, aus einer
        # aelteren/anderen Version) den kompletten Bildimport-Dialog schon
        # beim Oeffnen mit TypeError/KeyError abstuerzen (gleiche
        # Fehlerklasse wie die laengst gefixten PaletteManager-/Inventory-/
        # LibraryData-Loader). Strukturell falsche Eintraege werden
        # uebersprungen statt alles mitzureissen.
        if not isinstance(raw, list):
            logger.warning("User-Presets-Datei hat unerwartetes Format: %s", path)
            return []

        valid: list[dict] = []
        for entry in raw:
            if isinstance(entry, dict) and isinstance(entry.get("name"), str):
                valid.append(entry)
            else:
                logger.warning("Ungueltiger User-Preset-Eintrag uebersprungen: %r", entry)
        return valid
    return []


def save_user_presets(presets: list[dict]) -> None:
    """Speichert benutzerdefinierte Import-Presets."""
    path = get_user_presets_path()
    # Atomar schreiben (Temp-Datei + os.replace()) -- wie save_pattern()
    # seit Runde 6. Ein Crash/Stromausfall mitten in json.dump() haette
    # sonst genau die strukturell kaputte Datei zurueckgelassen, die
    # load_user_presets() oben jetzt zwar abfaengt, aber die den
    # Dialog vorher komplett lahmgelegt hat.
    temp_path = path.with_suffix(".json.tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)
    temp_path.replace(path)
