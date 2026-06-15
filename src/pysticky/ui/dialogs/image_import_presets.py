"""
Preset-Verwaltung für den Bildimport-Dialog.
"""

import json
from pathlib import Path

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
    # Diamond-Painting-Presets: Groessen passen bei 2.5mm-Drill-Pitch
    # 1:1 auf das jeweilige DIN-Format. "palette" springt automatisch auf
    # DMC Diamond Painting, "dp_mode" markiert das Pattern als DP.
    {
        "name": "💎 DP A4 quadratisch (60×60)",
        "width": 60,
        "height": 60,
        "max_colors": 30,
        "dithering_mode": "floyd_steinberg",
        "quantization_method": "median_cut",
        "auto_backstitches": False,
        "palette": "DMC Diamond Painting",
        "dp_mode": True,
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
        "dp_mode": True,
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
        "dp_mode": True,
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
        "dp_mode": True,
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
        "dp_mode": True,
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
                return json.load(f)
        except (OSError, json.JSONDecodeError, ValueError):
            pass
    return []


def save_user_presets(presets: list[dict]) -> None:
    """Speichert benutzerdefinierte Import-Presets."""
    path = get_user_presets_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)
