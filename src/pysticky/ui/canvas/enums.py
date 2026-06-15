"""
Enumerationen für das Canvas-Modul.
"""

from enum import IntEnum


class MirrorMode(IntEnum):
    """Spiegelmodus für Live-Spiegelung beim Zeichnen."""

    NONE = 0  # Keine Spiegelung
    HORIZONTAL = 1  # 2-fach: Horizontale Achse
    VERTICAL = 2  # 2-fach: Vertikale Achse
    QUAD = 3  # 4-fach: Beide Achsen
    OCTAL = 4  # 8-fach: Beide Achsen + Diagonalen
