"""
Anwendungsweite Konfiguration mit Klassen-API.

Numerische Defaults (Cell-Size, Grid-Interval, Fabric-Count, ...) kommen
aus `core/constants.py` — diese Datei wickelt sie nur in `@dataclass`-
Bündel, damit die UI sie als `CANVAS_CONFIG.default_cell_size` statt als
freie Module-Konstanten konsumieren kann.

Wer die rohen Konstanten will: `from .core.constants import ...`.
"""

from dataclasses import dataclass
from typing import Final

from .core.constants import (
    DEFAULT_CELL_SIZE,
    DEFAULT_UNDO_HISTORY,
    MAJOR_GRID_INTERVAL,
    MAX_CELL_SIZE,
    MIN_CELL_SIZE,
)

# === Anwendungs-Metadaten ===
# APP_VERSION ist die EINZIGE Versionsquelle: pyproject.toml liest sie via
# [tool.setuptools.dynamic] aus dieser Konstante. Hier hochzählen genügt.
APP_NAME: Final[str] = "PySticky"
APP_VERSION: Final[str] = "0.9.0"
ORG_NAME: Final[str] = "PySticky"


@dataclass(frozen=True)
class CanvasConfig:
    """Konfiguration für das Canvas."""

    min_cell_size: int = MIN_CELL_SIZE
    max_cell_size: int = MAX_CELL_SIZE
    default_cell_size: int = DEFAULT_CELL_SIZE

    zoom_step: float = 1.2  # Zoom-Faktor pro Schritt
    pan_speed: int = 1  # Pixel pro Pan-Einheit

    # Grid
    major_grid_interval: int = MAJOR_GRID_INTERVAL
    minor_grid_interval: int = 5

    # Snap
    default_snap_interval: int = 5


@dataclass(frozen=True)
class UndoConfig:
    """Konfiguration für Undo/Redo."""

    max_history: int = DEFAULT_UNDO_HISTORY
    batch_timeout_ms: int = 500  # Zeit bis Batch automatisch geschlossen wird


@dataclass(frozen=True)
class FileConfig:
    """Konfiguration für Dateioperationen."""

    pattern_extension: str = ".pxs"
    pattern_filter: str = "PySticky Muster (*.pxs)"

    image_extensions: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
    image_filter: str = "Bilder (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"

    html_extension: str = ".html"
    html_filter: str = "HTML-Dateien (*.html)"

    max_recent_files: int = 10
    autosave_interval_minutes: int = 5


@dataclass(frozen=True)
class UIConfig:
    """
    Konfiguration für die Benutzeroberfläche.

    Hinweis Dialog-Mindestgrößen: Die `dialog_min_*`-Tupel sind nur
    Standardgrößen-Klassen für neue Dialoge. Bestehende Dialoge mit
    individuellen Werten (z.B. Settings 750x820, Stitch Path 1000x700)
    bleiben bewusst individuell — das sind pro-Dialog-Design-Entscheidungen.
    """

    min_window_width: int = 1400
    min_window_height: int = 850
    default_window_width: int = 1920
    default_window_height: int = 1080

    toolbar_icon_size: int = 24
    panel_min_width: int = 200

    status_message_timeout_ms: int = 3000

    # Standard-Mindestgrößen für Dialoge (Breite, Höhe in Pixel)
    dialog_min_small: tuple[int, int] = (400, 300)
    dialog_min_medium: tuple[int, int] = (600, 500)
    dialog_min_large: tuple[int, int] = (800, 600)
    dialog_min_xlarge: tuple[int, int] = (1000, 700)


# === Globale Instanzen ===
CANVAS_CONFIG = CanvasConfig()
UNDO_CONFIG = UndoConfig()
FILE_CONFIG = FileConfig()
UI_CONFIG = UIConfig()
