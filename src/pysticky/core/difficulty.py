"""
Schwierigkeits-Heuristik für ein Muster.

Gewichteter Score, der vier Dimensionen zusammenfasst:
- Anzahl verwendeter Farben (mehr Farben = häufigere Fadenwechsel)
- Anteil Spezial-Stiche (Halb-/Viertel-Stiche, French Knots, Beads)
- Anzahl Backstitch-Linien (Konturen brauchen Präzision)
- Gesamt-Stichanzahl (Geduld)

Output ist ein dict mit `level` (Anfänger / Mittel / Fortgeschritten / Profi),
einem numerischen `score` und der `factors`-Aufschlüsselung. Die Funktion ist
pur (keine Side-Effects, keine Qt-Abhängigkeit) und damit gut testbar.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pattern import Pattern


LEVELS = ("Anfänger", "Mittel", "Fortgeschritten", "Profi")


def _color_score(used_colors: int) -> int:
    """0–3 Punkte basierend auf der Anzahl gestickter Farben."""
    if used_colors <= 5:
        return 0
    if used_colors <= 15:
        return 1
    if used_colors <= 30:
        return 2
    return 3


def _size_score(stitches_to_do: int) -> int:
    """0–3 Punkte für Geduld — basiert auf Anzahl zu stickender Stiche."""
    if stitches_to_do <= 1_000:
        return 0
    if stitches_to_do <= 5_000:
        return 1
    if stitches_to_do <= 20_000:
        return 2
    return 3


def _special_stitch_score(special_ratio: float) -> int:
    """0–3 Punkte für Anteil Sonder-Stiche (0.0 - 1.0)."""
    if special_ratio < 0.02:
        return 0
    if special_ratio < 0.10:
        return 1
    if special_ratio < 0.25:
        return 2
    return 3


def _backstitch_score(backstitches: int) -> int:
    """0–3 Punkte für die Anzahl Backstitch-Linien."""
    if backstitches == 0:
        return 0
    if backstitches <= 30:
        return 1
    if backstitches <= 150:
        return 2
    return 3


def _level_for_score(score: int) -> str:
    """Mappt 0–12 auf eines der LEVELS-Strings."""
    if score <= 2:
        return LEVELS[0]
    if score <= 5:
        return LEVELS[1]
    if score <= 8:
        return LEVELS[2]
    return LEVELS[3]


def compute_difficulty(pattern: "Pattern") -> dict:
    """Berechnet den Schwierigkeitsgrad eines Patterns.

    Returns:
        dict mit:
        - `level`: einer von LEVELS
        - `score`: int 0–12 (Summe der Faktor-Scores)
        - `factors`: dict mit `colors`, `size`, `special`, `backstitches` (je 0–3)
        - `details`: dict mit den Roh-Werten (used_colors, stitches_to_do, ...)
    """
    import numpy as np

    # Verwendete Farben (skip_stitching nicht zählen)
    used_colors = sum(
        1 for e in pattern.color_entries if e.stitch_count > 0 and not e.skip_stitching
    )

    # Stiche zum Sticken
    stitches_to_do = sum(e.stitch_count for e in pattern.color_entries if not e.skip_stitching)

    # Spezial-Stich-Anteil über alle sichtbaren Layer.
    #
    # Im Diamond-Painting-Modus stempelt Pattern.set_stitch() JEDEN
    # platzierten Drill automatisch mit StitchType.DIAMOND (11) --
    # das ist die normale Platzierung fuer DP, keine Komplexitaet.
    # Ohne diesen Ausschluss bekam JEDES DP-Muster einen special_ratio
    # nahe 1.0 und wurde dadurch unabhaengig von der tatsaechlichen
    # Komplexitaet (Farbanzahl/Groesse/Backstitches) pauschal um bis zu
    # 3 Punkte zu schwer eingestuft.
    from .stitch import StitchType

    baseline_type = StitchType.DIAMOND.value if pattern.mode == "diamond" else StitchType.FULL.value

    total_stitch_cells = 0
    special_cells = 0
    for layer in pattern.layer_stack:
        if layer.stitch_type_grid is None:
            continue
        # Zellen mit gesetztem Stich (nicht NO_STITCH=-1)
        stitch_mask = layer.grid >= 0
        cnt = int(np.count_nonzero(stitch_mask))
        if cnt == 0:
            continue
        total_stitch_cells += cnt
        # Sondertypen sind alles ausser dem Baseline-Typ des aktuellen Modus
        special_mask = stitch_mask & (layer.stitch_type_grid != baseline_type)
        special_cells += int(np.count_nonzero(special_mask))

    special_ratio = (special_cells / total_stitch_cells) if total_stitch_cells > 0 else 0.0

    backstitches = len(pattern.backstitches)

    factors = {
        "colors": _color_score(used_colors),
        "size": _size_score(stitches_to_do),
        "special": _special_stitch_score(special_ratio),
        "backstitches": _backstitch_score(backstitches),
    }
    score = sum(factors.values())
    level = _level_for_score(score)

    return {
        "level": level,
        "score": score,
        "factors": factors,
        "details": {
            "used_colors": used_colors,
            "stitches_to_do": stitches_to_do,
            "special_ratio": special_ratio,
            "backstitches": backstitches,
        },
    }
