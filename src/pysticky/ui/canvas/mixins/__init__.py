"""
Canvas-Mixins für modulare Funktionalität.
"""

from .coordinates_mixin import CoordinatesMixin
from .keyboard_events_mixin import KeyboardEventsMixin
from .mirror_mixin import MirrorMixin
from .mouse_events_mixin import MouseEventsMixin
from .properties_mixin import PropertiesMixin
from .rendering_mixin import RenderingMixin
from .tablet_gesture_mixin import TabletGestureMixin
from .zoom_mixin import ZoomMixin

__all__ = [
    "CoordinatesMixin",
    "MirrorMixin",
    "RenderingMixin",
    "ZoomMixin",
    "MouseEventsMixin",
    "KeyboardEventsMixin",
    "TabletGestureMixin",
    "PropertiesMixin",
]
