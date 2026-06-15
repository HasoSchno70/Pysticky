"""
Composite-Grid-Cache fuer HTML- und PDF-Export.

Die Per-Zelle-Funktionen `get_pixel_color` / `get_pixel_stitch_type` /
`get_pixel_symbol` in `export_common.py` iterieren bei jedem Aufruf den
Layer-Stack. Bei grossen Vorschaubildern (Deckblatt, Preview) wird das
ganze Pattern abgegrast — das skaliert mit `breite * hoehe * layers`.

Dieses Modul bildet einmal pro Export die Layer-Komposition als
numpy-Arrays ab und liefert die O(1)-Lookup-API, die HTML- und
PDF-Exporter teilen koennen.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from ..core.layer import NO_STITCH

if TYPE_CHECKING:
    from ..core.pattern import ColorEntry, Pattern


class CompositeGridCache:
    """Vorberechnete Komposition aller sichtbaren Layer in numpy-Arrays."""

    __slots__ = (
        "pattern",
        "width",
        "height",
        "color_index",
        "stitch_type",
        "_color_entries",
        "_color_rgb",
        "_color_symbols",
    )

    def __init__(self, pattern: "Pattern") -> None:
        self.pattern = pattern
        self.width = pattern.width
        self.height = pattern.height

        H, W = self.height, self.width
        self.color_index = np.full((H, W), NO_STITCH, dtype=np.int32)
        self.stitch_type = np.zeros((H, W), dtype=np.uint8)

        for layer in reversed(pattern.layer_stack.layers):
            if not layer.visible:
                continue
            if layer.grid is None:
                continue
            lh, lw = layer.grid.shape
            view_h = min(lh, H)
            view_w = min(lw, W)
            layer_grid = layer.grid[:view_h, :view_w]
            target = self.color_index[:view_h, :view_w]
            mask = (target == NO_STITCH) & (layer_grid != NO_STITCH)
            if not mask.any():
                continue
            target[mask] = layer_grid[mask]
            if layer.stitch_type_grid is not None:
                stype = layer.stitch_type_grid[:view_h, :view_w]
                self.stitch_type[:view_h, :view_w][mask] = stype[mask]

        self._color_entries: list["ColorEntry"] = list(pattern.color_entries)
        self._color_rgb: list[tuple[int, int, int]] = [
            (e.thread.color.r, e.thread.color.g, e.thread.color.b) for e in self._color_entries
        ]
        self._color_symbols: list[str] = [e.symbol for e in self._color_entries]

    def get_color(self, x: int, y: int) -> tuple[int, int, int] | None:
        """RGB des obersten sichtbaren Stiches, oder None."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return None
        idx = int(self.color_index[y, x])
        if idx == NO_STITCH:
            return None
        if 0 <= idx < len(self._color_rgb):
            return self._color_rgb[idx]
        return None

    def get_stitch_type(self, x: int, y: int) -> int:
        """Stitch-Type des obersten sichtbaren Stiches (0 = voll / leer)."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return 0
        idx = int(self.color_index[y, x])
        if idx == NO_STITCH:
            return 0
        return int(self.stitch_type[y, x])

    def get_symbol(self, x: int, y: int) -> str:
        """Symbol des obersten sichtbaren Stiches, oder Leerstring."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return ""
        idx = int(self.color_index[y, x])
        if idx == NO_STITCH:
            return ""
        if 0 <= idx < len(self._color_symbols):
            return self._color_symbols[idx]
        return ""

    def count_page_colors(
        self, start_x: int, start_y: int, end_x: int, end_y: int
    ) -> dict[int, int]:
        """Zaehlt Farb-Indizes auf einem rechteckigen Seitenausschnitt."""
        x0 = max(0, start_x)
        y0 = max(0, start_y)
        x1 = min(self.width - 1, end_x)
        y1 = min(self.height - 1, end_y)
        if x0 > x1 or y0 > y1:
            return {}
        region = self.color_index[y0 : y1 + 1, x0 : x1 + 1]
        non_empty = region[region != NO_STITCH]
        if non_empty.size == 0:
            return {}
        values, counts = np.unique(non_empty, return_counts=True)
        return {int(v): int(c) for v, c in zip(values, counts)}
