"""
Properties-Mixin für Canvas.

Enthält alle Property-Definitionen für Ansichtsoptionen.
"""

from typing import TYPE_CHECKING

from PySide6.QtGui import QColor

from ....core.color_blindness import ColorBlindType
from ..enums import MirrorMode

if TYPE_CHECKING:
    from ..canvas import CrossStitchCanvas


class PropertiesMixin:
    """Mixin für Canvas-Properties."""

    @property
    def show_grid(self: "CrossStitchCanvas") -> bool:
        return self._show_grid

    @show_grid.setter
    def show_grid(self: "CrossStitchCanvas", value: bool) -> None:
        self._show_grid = value
        self.update()

    @property
    def show_symbols(self: "CrossStitchCanvas") -> bool:
        return self._show_symbols

    @show_symbols.setter
    def show_symbols(self: "CrossStitchCanvas", value: bool) -> None:
        self._show_symbols = value
        self.update()

    @property
    def show_colors(self: "CrossStitchCanvas") -> bool:
        return self._show_colors

    @show_colors.setter
    def show_colors(self: "CrossStitchCanvas", value: bool) -> None:
        self._show_colors = value
        self.update()

    @property
    def show_backstitches(self: "CrossStitchCanvas") -> bool:
        return self._show_backstitches

    @show_backstitches.setter
    def show_backstitches(self: "CrossStitchCanvas", value: bool) -> None:
        self._show_backstitches = value
        self.update()

    @property
    def show_fabric_texture(self: "CrossStitchCanvas") -> bool:
        return self._show_fabric_texture

    @show_fabric_texture.setter
    def show_fabric_texture(self: "CrossStitchCanvas", value: bool) -> None:
        self._show_fabric_texture = value
        self.update()

    @property
    def show_only_active_layer(self: "CrossStitchCanvas") -> bool:
        return self._show_only_active_layer

    @show_only_active_layer.setter
    def show_only_active_layer(self: "CrossStitchCanvas", value: bool) -> None:
        self._show_only_active_layer = value
        self.update()

    @property
    def dim_other_layers(self: "CrossStitchCanvas") -> bool:
        return self._dim_other_layers

    @dim_other_layers.setter
    def dim_other_layers(self: "CrossStitchCanvas", value: bool) -> None:
        self._dim_other_layers = value
        self.update()

    @property
    def show_center_crosshair(self: "CrossStitchCanvas") -> bool:
        return self._show_center_crosshair

    @show_center_crosshair.setter
    def show_center_crosshair(self: "CrossStitchCanvas", value: bool) -> None:
        self._show_center_crosshair = value
        self.update()

    @property
    def mirror_mode(self: "CrossStitchCanvas") -> MirrorMode:
        return self._mirror_mode

    @mirror_mode.setter
    def mirror_mode(self: "CrossStitchCanvas", value: MirrorMode) -> None:
        self._mirror_mode = value
        self.update()

    @property
    def mirror_horizontal(self: "CrossStitchCanvas") -> bool:
        return self._mirror_horizontal

    @mirror_horizontal.setter
    def mirror_horizontal(self: "CrossStitchCanvas", value: bool) -> None:
        self._mirror_horizontal = value
        self.update()

    @property
    def mirror_vertical(self: "CrossStitchCanvas") -> bool:
        return self._mirror_vertical

    @mirror_vertical.setter
    def mirror_vertical(self: "CrossStitchCanvas", value: bool) -> None:
        self._mirror_vertical = value
        self.update()

    @property
    def major_grid_interval(self: "CrossStitchCanvas") -> int:
        return self._major_grid_interval

    @major_grid_interval.setter
    def major_grid_interval(self: "CrossStitchCanvas", value: int) -> None:
        self._major_grid_interval = max(1, value)
        self.update()

    @property
    def minor_grid_interval(self: "CrossStitchCanvas") -> int:
        return self._minor_grid_interval

    @minor_grid_interval.setter
    def minor_grid_interval(self: "CrossStitchCanvas", value: int) -> None:
        self._minor_grid_interval = max(1, value)
        self.update()

    @property
    def show_minor_grid(self: "CrossStitchCanvas") -> bool:
        return self._show_minor_grid

    @show_minor_grid.setter
    def show_minor_grid(self: "CrossStitchCanvas", value: bool) -> None:
        self._show_minor_grid = value
        self.update()

    @property
    def grid_color(self: "CrossStitchCanvas") -> QColor:
        return self._grid_color

    @grid_color.setter
    def grid_color(self: "CrossStitchCanvas", value: QColor) -> None:
        self._grid_color = value
        self.update()

    @property
    def grid_minor_color(self: "CrossStitchCanvas") -> QColor:
        return self._grid_minor_color

    @grid_minor_color.setter
    def grid_minor_color(self: "CrossStitchCanvas", value: QColor) -> None:
        self._grid_minor_color = value
        self.update()

    @property
    def grid_major_color(self: "CrossStitchCanvas") -> QColor:
        return self._grid_major_color

    @grid_major_color.setter
    def grid_major_color(self: "CrossStitchCanvas", value: QColor) -> None:
        self._grid_major_color = value
        self.update()

    @property
    def snap_to_grid(self: "CrossStitchCanvas") -> bool:
        return self._snap_to_grid

    @snap_to_grid.setter
    def snap_to_grid(self: "CrossStitchCanvas", value: bool) -> None:
        self._snap_to_grid = value
        self.update()

    @property
    def snap_interval(self: "CrossStitchCanvas") -> int:
        return self._snap_interval

    @snap_interval.setter
    def snap_interval(self: "CrossStitchCanvas", value: int) -> None:
        self._snap_interval = max(1, value)
        self.update()

    @property
    def diamond_view(self: "CrossStitchCanvas") -> bool:
        """True wenn die Diamond-Painting-Ansicht aktiv ist.

        In diesem Modus werden FULL-Stiche als facettierte Drills gerendert
        (statt als einfarbige Quadrate), Symbole werden durch DMC-Nummern
        ersetzt, und die Stoff-Textur wird durch ein DP-Grid abgelöst. Es
        ist ein reines Rendering-Override — die Daten im Pattern bleiben
        unverändert.
        """
        return getattr(self, "_diamond_view", False)

    @diamond_view.setter
    def diamond_view(self: "CrossStitchCanvas", value: bool) -> None:
        self._diamond_view = bool(value)
        self.update()

    @property
    def colorblind_mode(self: "CrossStitchCanvas") -> ColorBlindType:
        return getattr(self, "_colorblind_mode", ColorBlindType.NONE)

    @colorblind_mode.setter
    def colorblind_mode(self: "CrossStitchCanvas", value: ColorBlindType) -> None:
        from ....core.color_blindness import clear_cache

        self._colorblind_mode = value
        clear_cache()
        self.update()
