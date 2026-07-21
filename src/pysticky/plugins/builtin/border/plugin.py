"""
Plugin: Rahmen generieren.

Fragt nach Abstand vom Rand und Linienstärke und zeichnet einen rechteckigen
Rahmen in der aktuell aktiven Farbe (color_index 0 wenn keine aktive Farbe).
"""

from __future__ import annotations


def run(pattern, ctx) -> None:
    margin = ctx.prompt_int(
        "Abstand vom Rand (in Stichen)?",
        default=2,
        minimum=0,
        maximum=min(pattern.width, pattern.height) // 2,
    )
    if margin is None:
        return

    thickness = ctx.prompt_int(
        "Linienstärke (in Stichen)?",
        default=1,
        minimum=1,
        maximum=10,
    )
    if thickness is None:
        return

    if not pattern.color_entries:
        ctx.show_error("Pattern hat keine Farben — bitte erst eine Farbe hinzufügen.")
        return

    color_index = 0  # Erste Farbe — Plugins haben keinen Zugriff auf
    # MainWindow.current_color, also nehmen wir die erste.

    width = pattern.width
    height = pattern.height
    placed = 0

    for t_offset in range(thickness):
        m = margin + t_offset
        if m >= min(width, height) / 2:
            break
        # Oben + Unten -- bei ungerader Höhe/Breite kann die mittlere
        # Zeile/Spalte oberer UND unterer (bzw. linker UND rechter) Rand
        # zugleich sein. Dieselbe Zelle dann nicht ein zweites Mal zählen
        # (set_stitch() auf dieselbe Zelle ändert das Ergebnis nicht, aber
        # "placed" wurde vorher trotzdem doppelt hochgezählt).
        top_row, bottom_row = m, height - 1 - m
        for x in range(m, width - m):
            if pattern.set_stitch(x, top_row, color_index):
                placed += 1
            if bottom_row != top_row and pattern.set_stitch(x, bottom_row, color_index):
                placed += 1
        # Links + Rechts (ohne Ecken doppelt)
        left_col, right_col = m, width - 1 - m
        for y in range(m + 1, height - 1 - m):
            if pattern.set_stitch(left_col, y, color_index):
                placed += 1
            if right_col != left_col and pattern.set_stitch(right_col, y, color_index):
                placed += 1

    ctx.show_message(f"Rahmen erstellt: {placed} Stiche.")
