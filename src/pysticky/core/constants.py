# -*- coding: utf-8 -*-
"""
Zentrale Konstanten für PySticky (Core-Modul).

HINWEIS: Für neue Konstanten bitte pysticky.config verwenden!
Diese Datei enthält Core-spezifische Konstanten, die keine UI-Abhängigkeit haben.
UI-Konfiguration (Fenstergrößen, Autosave, etc.) ist in pysticky.config definiert.
"""

# === Muster-Größen ===
MIN_PATTERN_SIZE = 1
MAX_PATTERN_SIZE = 1000
DEFAULT_PATTERN_WIDTH = 50
DEFAULT_PATTERN_HEIGHT = 50

# === Stoffzählung (Stiche pro Inch) ===
DEFAULT_FABRIC_COUNT = 14
MIN_FABRIC_COUNT = 6
MAX_FABRIC_COUNT = 32
COMMON_FABRIC_COUNTS = [11, 14, 16, 18, 22, 28, 32]

# === Farben ===
MIN_COLORS = 1
MAX_COLORS = 100
DEFAULT_MAX_IMPORT_COLORS = 20

# === Canvas ===
MIN_CELL_SIZE = 4
MAX_CELL_SIZE = 60
DEFAULT_CELL_SIZE = 20
MAJOR_GRID_INTERVAL = 10

# === Zoom ===
MIN_ZOOM_PERCENT = 20
MAX_ZOOM_PERCENT = 300
DEFAULT_ZOOM_PERCENT = 100
ZOOM_STEP = 10

# === Undo/Redo ===
DEFAULT_UNDO_HISTORY = 100
MAX_UNDO_HISTORY = 500

# === Dateiformat ===
FILE_EXTENSION = ".pxs"
FILE_FORMAT_NAME = "pysticky"
# Die aktuelle Formatversion lebt als FORMAT_VERSION in core.file_io
# (zusammen mit der Versionshistorie) — hier nicht duplizieren.

# UI- und Autosave-Defaults wohnen in pysticky.config (UI_CONFIG, FILE_CONFIG).
# Wer hier Fenstergroessen erwartet hat: nutze UI_CONFIG.default_window_*.

# === Bildimport ===
SUPPORTED_IMAGE_FORMATS = [
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.bmp",
    "*.gif",
    "*.webp",
    "*.tiff",
    "*.tif",
]
MAX_IMPORT_DIMENSION = 500


# === Farben (UI) ===
class CanvasColors:
    """Farben für den Canvas."""

    BACKGROUND = (45, 45, 45)
    GRID = (80, 80, 80)
    GRID_MAJOR = (100, 100, 100)
    EMPTY_CELL = (250, 250, 245)  # Cremeweiß wie Aida-Stoff
    SELECTION = (0, 120, 212, 100)
    CURSOR = (0, 120, 212)


# === Keyboard Shortcuts ===
class Shortcuts:
    """Standard-Tastenkürzel."""

    NEW = "Ctrl+N"
    OPEN = "Ctrl+O"
    SAVE = "Ctrl+S"
    SAVE_AS = "Ctrl+Shift+S"
    UNDO = "Ctrl+Z"
    REDO = "Ctrl+Y"
    ZOOM_IN = "Ctrl++"
    ZOOM_OUT = "Ctrl+-"
    ZOOM_FIT = "Ctrl+0"
    ZOOM_100 = "Ctrl+1"
    NEW_LAYER = "Ctrl+Shift+N"
    IMPORT_IMAGE = "Ctrl+I"
