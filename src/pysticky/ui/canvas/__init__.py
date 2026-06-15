"""Canvas-Modul für PySticky.

Enthält:
- CrossStitchCanvas: Standard-Canvas mit Basis-Optimierungen (Mixin-basiert)
- OptimizedCrossStitchCanvas: Erweiterte Canvas mit Chunk-Caching (empfohlen)
- MirrorMode: Spiegelmodus-Enum
- CanvasCache: Farb-Cache für Performance
- Performance-Utilities für große Muster

Die Canvas-Funktionalität ist modular in Mixins aufgeteilt:
- CoordinatesMixin: Koordinaten-Umrechnung
- MirrorMixin: Spiegelmodus-Funktionalität
- RenderingMixin: Zeichnen
- ZoomMixin: Zoom-Funktionen
- MouseEventsMixin / KeyboardEventsMixin / TabletGestureMixin: Event-Handler
- PropertiesMixin: Properties
"""

from .cache import CanvasCache
from .canvas import CrossStitchCanvas
from .enums import MirrorMode
from .optimized_canvas import OptimizedCrossStitchCanvas
from .performance import (
    LARGE_PATTERN_THRESHOLD,
    PerformanceManager,
    draw_optimized_grid,
    render_chunk_to_pixmap,
    should_skip_details,
)

__all__ = [
    # Canvas-Klassen
    "CrossStitchCanvas",
    "OptimizedCrossStitchCanvas",
    # Enums & Cache
    "MirrorMode",
    "CanvasCache",
    # Performance-Module
    "PerformanceManager",
    # Utility-Funktionen
    "render_chunk_to_pixmap",
    "draw_optimized_grid",
    "should_skip_details",
    "LARGE_PATTERN_THRESHOLD",
]
