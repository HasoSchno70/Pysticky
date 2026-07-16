"""
Farb-Ersetzungs- und Reduzierungs-Logik.

Reine Berechnungen für den "Farbe ersetzen"-Dialog: Vorschläge ähnlicher
Farben (perzeptuell via CIE-Lab Delta-E) und die automatische Reduzierung
selten verwendeter Farben ("Konfetti") auf die jeweils ähnlichste häufige
Farbe. Qt-frei und headless testbar.
"""

from typing import TYPE_CHECKING

from .color_math import delta_e

if TYPE_CHECKING:
    from .pattern import Pattern


def rank_similar_colors(pattern: "Pattern", source_index: int) -> list[tuple[int, float]]:
    """
    Sortiert alle anderen Palette-Farben nach perzeptueller Nähe zur Quellfarbe.

    Args:
        pattern: Das Muster.
        source_index: Index der Quellfarbe in pattern.color_entries.

    Returns:
        Liste von (index, delta_e), aufsteigend nach Distanz — die
        ähnlichste Farbe zuerst. Die Quellfarbe selbst ist nicht enthalten.
    """
    entries = pattern.color_entries
    if not (0 <= source_index < len(entries)):
        return []

    src = entries[source_index].thread.color
    ranked = [
        (i, delta_e(src.to_tuple(), entry.thread.color.to_tuple()))
        for i, entry in enumerate(entries)
        if i != source_index
    ]
    ranked.sort(key=lambda item: item[1])
    return ranked


def compute_rare_color_replacements(
    pattern: "Pattern", max_stitch_count: int
) -> list[tuple[int, int]]:
    """
    Berechnet die Auto-Reduzierung: jede selten verwendete Farbe wird der
    perzeptuell ähnlichsten häufigen Farbe zugeordnet.

    "Selten" heißt: 1 bis max_stitch_count Stiche. Unbenutzte Farben
    (0 Stiche) bleiben unangetastet — sie kosten nichts im Stickbild.
    Ziel-Farben sind ausschließlich häufige Farben (> max_stitch_count),
    damit Konfetti nicht in anderes Konfetti umgefärbt wird.

    Args:
        pattern: Das Muster.
        max_stitch_count: Obergrenze, bis zu der eine Farbe als selten gilt.

    Returns:
        Liste von (quell_index, ziel_index). Leer, wenn es keine seltenen
        oder keine häufigen Farben gibt.
    """
    entries = pattern.color_entries
    rare = [i for i, e in enumerate(entries) if 0 < e.stitch_count <= max_stitch_count]
    frequent = [i for i, e in enumerate(entries) if e.stitch_count > max_stitch_count]
    if not rare or not frequent:
        return []

    replacements = []
    for i in rare:
        src = entries[i].thread.color.to_tuple()
        best = min(
            frequent,
            key=lambda j: delta_e(src, entries[j].thread.color.to_tuple()),
        )
        replacements.append((i, best))
    return replacements
