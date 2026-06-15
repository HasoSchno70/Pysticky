"""
Handler-Module für MainWindow.

Diese Module enthalten die Event-Handler und Logik,
die aus MainWindow ausgelagert wurden für bessere Übersichtlichkeit.
"""

from .autosave_handlers import AutosaveHandlersMixin
from .edit_handlers import EditHandlersMixin
from .export_handlers import ExportHandlersMixin
from .file_handlers import FileHandlersMixin
from .misc_handlers import MiscHandlersMixin
from .panel_handlers import PanelHandlersMixin
from .selection_handlers import SelectionHandlersMixin
from .tool_handlers import ToolHandlersMixin
from .undo_handlers import UndoHandlersMixin
from .view_handlers import ViewHandlersMixin

__all__ = [
    "FileHandlersMixin",
    "ExportHandlersMixin",
    "AutosaveHandlersMixin",
    "EditHandlersMixin",
    "ViewHandlersMixin",
    "SelectionHandlersMixin",
    "UndoHandlersMixin",
    "PanelHandlersMixin",
    "ToolHandlersMixin",
    "MiscHandlersMixin",
]
