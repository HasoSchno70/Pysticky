"""
Plugin: Linke Hälfte horizontal spiegeln.

Kopiert die linke Hälfte des Patterns (Spalten 0 .. width/2 - 1) gespiegelt
auf die rechte Hälfte (Spalten width/2 .. width - 1). Stitch-Type wird
mitgespiegelt (HALF_TL_BR -> HALF_TR_BL etc., entsprechend `stitch.FLIP_H_MAP`).
"""

from __future__ import annotations

from pysticky.core.layer import NO_STITCH
from pysticky.core.stitch import FLIP_H_MAP


def run(pattern, ctx) -> None:
    layer = pattern.layer_stack.active_layer
    if layer is None:
        ctx.show_error("Kein aktiver Layer.")
        return

    width = pattern.width
    height = pattern.height
    if width < 2:
        ctx.show_error("Pattern zu schmal (mindestens 2 Spalten nötig).")
        return

    half = width // 2
    placed = 0
    for y in range(height):
        for src_x in range(half):
            dst_x = width - 1 - src_x
            color = int(layer.grid[y, src_x])
            if color == NO_STITCH:
                # Auch die Ziel-Zelle leeren, damit das Pattern wirklich
                # symmetrisch wird (nicht: "linke leer, rechte aus Vorlauf")
                if layer.grid[y, dst_x] != NO_STITCH:
                    pattern.set_stitch(dst_x, y, None)
                continue
            stitch_type = int(layer.stitch_type_grid[y, src_x])
            flipped_type = FLIP_H_MAP.get(stitch_type, stitch_type)
            if pattern.set_stitch(dst_x, y, color, stitch_type=flipped_type):
                placed += 1

    ctx.show_message(f"Horizontale Spiegelung: {placed} Stiche kopiert.")
