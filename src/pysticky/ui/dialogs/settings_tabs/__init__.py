"""
Settings-Tab-Widgets für den Einstellungs-Dialog.
"""

from .canvas_tab import CanvasTab
from .color_button import ColorButton
from .colors_tab import ColorsTab
from .files_tab import FilesTab
from .general_tab import GeneralTab
from .shortcuts_tab import ShortcutsTab
from .tools_tab import ToolsTab

__all__ = [
    "ColorButton",
    "GeneralTab",
    "CanvasTab",
    "ToolsTab",
    "ColorsTab",
    "FilesTab",
    "ShortcutsTab",
]
