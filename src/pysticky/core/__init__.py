"""
Core-Modul: Enthält die Kernlogik für Kreuzstich-Verarbeitung.
"""

from .backstitch_manager import Backstitch, BackstitchManager
from .constants import (
    DEFAULT_FABRIC_COUNT,
    DEFAULT_PATTERN_HEIGHT,
    DEFAULT_PATTERN_WIDTH,
    DEFAULT_UNDO_HISTORY,
    MAX_PATTERN_SIZE,
    MIN_PATTERN_SIZE,
    CanvasColors,
    Shortcuts,
)
from .file_io import load_pattern, save_pattern
from .image_import import (
    ImportSettings,
    can_change_palette,
    change_palette,
    check_pillow_available,
    create_preview,
    get_image_info,
    import_image,
)
from .layer import NO_STITCH, Layer, LayerStack
from .palette import PaletteManager, ThreadPalette, get_palette_manager, reset_palette_manager
from .pattern import SYMBOLS, ColorEntry, Pattern
from .stitch import StitchType
from .stitch_path_optimizer import (
    ColorPath,
    OptimizationResult,
    OptimizationStrategy,
    StitchPathOptimizer,
    StitchStep,
    compare_strategies,
)
from .thread import DEFAULT_THREAD_COLORS, Thread, ThreadColor
from .undo import (
    AddBackstitchCommand,
    BatchStitchCommand,
    ClearLayerCommand,
    Command,
    LayerSnapshotCommand,
    MarkColorCompletedCommand,
    MarkStitchCompletedCommand,
    PlaceStitchCommand,
    RemoveBackstitchCommand,
    RemoveStitchCommand,
    UndoManager,
    UnmarkStitchCompletedCommand,
)

__all__ = [
    # Constants
    "MIN_PATTERN_SIZE",
    "MAX_PATTERN_SIZE",
    "DEFAULT_PATTERN_WIDTH",
    "DEFAULT_PATTERN_HEIGHT",
    "DEFAULT_FABRIC_COUNT",
    "DEFAULT_UNDO_HISTORY",
    "CanvasColors",
    "Shortcuts",
    # Stitch
    "StitchType",
    # Thread
    "Thread",
    "ThreadColor",
    "DEFAULT_THREAD_COLORS",
    # Pattern
    "Pattern",
    "ColorEntry",
    "SYMBOLS",
    # Backstitch
    "Backstitch",
    "BackstitchManager",
    # Layer
    "Layer",
    "LayerStack",
    "NO_STITCH",
    # Palette
    "ThreadPalette",
    "PaletteManager",
    "get_palette_manager",
    "reset_palette_manager",
    # Undo
    "Command",
    "PlaceStitchCommand",
    "RemoveStitchCommand",
    "BatchStitchCommand",
    "AddBackstitchCommand",
    "RemoveBackstitchCommand",
    "ClearLayerCommand",
    "LayerSnapshotCommand",
    "MarkStitchCompletedCommand",
    "UnmarkStitchCompletedCommand",
    "MarkColorCompletedCommand",
    "UndoManager",
    # File I/O
    "save_pattern",
    "load_pattern",
    # Image Import
    "ImportSettings",
    "import_image",
    "get_image_info",
    "create_preview",
    "check_pillow_available",
    "change_palette",
    "can_change_palette",
    # Stitch Path Optimizer
    "OptimizationStrategy",
    "StitchStep",
    "ColorPath",
    "OptimizationResult",
    "StitchPathOptimizer",
    "compare_strategies",
]
