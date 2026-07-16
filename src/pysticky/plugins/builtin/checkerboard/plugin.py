"""
Plugin: Schachbrett füllen.

Füllt das gesamte Pattern mit einem zweifarbigen Schachbrettmuster.
Die ersten beiden Farben der Pattern-Palette werden verwendet.
"""

from __future__ import annotations


def run(pattern, ctx) -> None:
    if len(pattern.color_entries) < 2:
        ctx.show_error("Schachbrett braucht mindestens zwei Farben in der Palette.")
        return

    cell_size = ctx.prompt_int(
        "Feldgroesse (in Stichen)?",
        default=2,
        minimum=1,
        maximum=min(pattern.width, pattern.height) // 2 or 1,
    )
    if cell_size is None:
        return

    placed = 0
    for y in range(pattern.height):
        for x in range(pattern.width):
            # Schachbrett-Muster: (x // size + y // size) % 2
            cell_x = x // cell_size
            cell_y = y // cell_size
            color_index = (cell_x + cell_y) % 2
            if pattern.set_stitch(x, y, color_index):
                placed += 1

    ctx.show_message(f"Schachbrett mit Feldgroesse {cell_size} erzeugt ({placed} Stiche).")
