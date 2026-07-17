"""
Statistik-Tab-Widgets für den Muster-Statistik-Dialog.
"""

from ._constants import STITCHES_PER_SKEIN
from .colors_tab import ColorsTab
from .overview_tab import OverviewTab
from .progress_tab import ProgressTab
from .shopping_tab import ShoppingTab
from .thread_tab import ThreadTab
from .time_tab import TimeTab

__all__ = [
    "STITCHES_PER_SKEIN",
    "OverviewTab",
    "ColorsTab",
    "ThreadTab",
    "TimeTab",
    "ProgressTab",
    "ShoppingTab",
]
