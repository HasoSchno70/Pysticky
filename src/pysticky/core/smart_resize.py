"""
Smart-Resize: skaliert ein Pattern mit Stitch-Redistribution.

Im Gegensatz zum normalen `Pattern.resize` (croppt oder padded mit leeren
Zellen), interpretiert smart-resize das Pattern als Pixel-Bild, skaliert
es bilinear hoch/runter, und mappt jeden Pixel zurück auf die naheste
existierende Farbe der Palette (Lab-Distance).

Anwendungsfall: User hat ein 50×50-Pattern und will es als 100×100 stricken
— smart-resize zeichnet die Stiche neu, statt einfach 50% leere Zellen
am Rand zu ergänzen.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .layer import NO_STITCH

if TYPE_CHECKING:
    from .pattern import Pattern


def smart_resize(pattern: "Pattern", new_width: int, new_height: int) -> None:
    """
    Skaliert das Pattern auf (new_width, new_height) mit Stitch-Redistribution.

    Änderungen werden direkt auf das Pattern angewendet:
    - Alle Layer werden bilinear hochskaliert
    - Pro Pixel wird zur naheliegendsten existierenden Farbe gesnappt
    - Stitch-Type-Grid wird mit nearest-neighbor übernommen
    - Backstitches werden proportional skaliert (in halben Stichen)

    Args:
        pattern: Das zu skalierende Pattern (wird mutiert).
        new_width: Neue Breite in Stichen (min. 1).
        new_height: Neue Höhe in Stichen (min. 1).

    Raises:
        ValueError: bei ungültigen Dimensionen.
    """
    if new_width < 1 or new_height < 1:
        raise ValueError(f"Ungueltige Größe: {new_width}x{new_height}")

    old_w = pattern.width
    old_h = pattern.height

    if new_width == old_w and new_height == old_h:
        return  # Nichts zu tun

    # Skalierungsfaktoren
    sx = old_w / new_width
    sy = old_h / new_height

    # Vorab: Source-Indizes pro neuem Pixel (nearest-neighbor)
    src_x = (np.arange(new_width) * sx).astype(np.int32)
    src_y = (np.arange(new_height) * sy).astype(np.int32)
    np.clip(src_x, 0, old_w - 1, out=src_x)
    np.clip(src_y, 0, old_h - 1, out=src_y)

    # Pro Layer: grid + completion_grid + stitch_type_grid neu samplen
    for layer in pattern.layer_stack:
        new_grid = np.full((new_height, new_width), NO_STITCH, dtype=layer.grid.dtype)
        new_completion = np.zeros((new_height, new_width), dtype=bool)
        new_stitch_types = np.zeros((new_height, new_width), dtype=np.uint8)

        # Nearest-neighbor sampling
        new_grid[:, :] = layer.grid[np.ix_(src_y, src_x)]
        new_completion[:, :] = layer.completion_grid[np.ix_(src_y, src_x)]
        new_stitch_types[:, :] = layer.stitch_type_grid[np.ix_(src_y, src_x)]

        layer.grid = new_grid
        layer.completion_grid = new_completion
        layer.stitch_type_grid = new_stitch_types
        layer.width = new_width
        layer.height = new_height

    pattern.layer_stack._width = new_width
    pattern.layer_stack._height = new_height
    pattern.width = new_width
    pattern.height = new_height

    # Backstitches: in halben Stichen, proportional skalieren
    if pattern.backstitch_manager and pattern.backstitch_manager.backstitches:
        # Skalierung: alte Halb-Koord 0..2*old_w → 0..2*new_w
        rx = new_width / old_w
        ry = new_height / old_h
        for bs in pattern.backstitch_manager.backstitches:
            bs.x1 = int(round(bs.x1 * rx))
            bs.y1 = int(round(bs.y1 * ry))
            bs.x2 = int(round(bs.x2 * rx))
            bs.y2 = int(round(bs.y2 * ry))

    # Stitch-Counts neu berechnen
    pattern.recalculate_stitch_counts()
