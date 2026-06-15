"""
Canvas-Mixins für modulare Funktionalität.
"""

from .coordinates_mixin import CoordinatesMixin
from .events_mixin import EventsMixin
from .mirror_mixin import MirrorMixin
from .properties_mixin import PropertiesMixin
from .rendering_mixin import RenderingMixin
from .zoom_mixin import ZoomMixin

__all__ = [
    "CoordinatesMixin",
    "MirrorMixin",
    "RenderingMixin",
    "ZoomMixin",
    "EventsMixin",
    "PropertiesMixin",
]
