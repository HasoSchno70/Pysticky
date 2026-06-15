"""
Panels-Modul: Seitenpanels für die Hauptanwendung.
"""

from .backstitch_options_panel import BackstitchOptionsPanel
from .gradient_options_panel import GradientOptionsPanel
from .info_panel import InfoPanel
from .layer_panel import LayerPanel
from .palette_panel import PalettePanel
from .text_options_panel import TextOptionsPanel
from .tile_preview_panel import TilePreviewPanel

__all__ = [
    "PalettePanel",
    "InfoPanel",
    "LayerPanel",
    "TextOptionsPanel",
    "GradientOptionsPanel",
    "TilePreviewPanel",
    "BackstitchOptionsPanel",
]
