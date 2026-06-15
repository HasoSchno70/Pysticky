"""
Builder-Mixins für MainWindow.

Diese Mixins enthalten die UI-Erstellungslogik, um main_window.py übersichtlicher zu halten.
"""

from .mw_actions_mixin import ActionsBuilderMixin
from .mw_docks_mixin import DockBuilderMixin
from .mw_menus_mixin import MenuBuilderMixin
from .mw_signals_mixin import SignalsConnectorMixin
from .mw_toolbar_mixin import ToolbarBuilderMixin

__all__ = [
    "ActionsBuilderMixin",
    "MenuBuilderMixin",
    "ToolbarBuilderMixin",
    "DockBuilderMixin",
    "SignalsConnectorMixin",
]
