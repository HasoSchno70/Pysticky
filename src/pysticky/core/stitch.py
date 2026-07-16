"""
Stich-Typen für Kreuzstich-Muster.

Bei Kreuzstich ist ein "Stich" einfach eine gefüllte Zelle im Raster.
Diese Datei enthält Hilfsklassen für erweiterte Stichtypen.
"""

from enum import Enum


class StitchType(Enum):
    """
    Verschiedene Stichtypen im Kreuzstich.

    Standard ist FULL (kompletter Kreuzstich).
    Werte sind fixiert für stabile Serialisierung.
    """

    FULL = 0  # Kompletter Kreuzstich (X)
    HALF_TL_BR = 1  # Halber Stich: oben-links nach unten-rechts (/)
    HALF_TR_BL = 2  # Halber Stich: oben-rechts nach unten-links (\)
    QUARTER_TL = 3  # Viertelstich oben-links
    QUARTER_TR = 4  # Viertelstich oben-rechts
    QUARTER_BL = 5  # Viertelstich unten-links
    QUARTER_BR = 6  # Viertelstich unten-rechts
    THREE_QUARTER = 7  # Dreiviertelstich
    BACKSTITCH = 8  # Rückstich (Kontur)
    FRENCH_KNOT = 9  # Französischer Knoten
    BEAD = 10  # Perle (Bead) — glänzende Kugel in der Zellmitte
    DIAMOND = 11  # Diamond-Painting-Drill — facettiertes Quadrat


# Lookup-Tabellen für Transformation von Stichtypen.
# Backstitch (8), French Knot (9), Bead (10) und Diamond (11) sind
# rotations-/spiegel-invariant.
FLIP_H_MAP = {
    0: 0,
    1: 2,
    2: 1,
    3: 4,
    4: 3,
    5: 6,
    6: 5,
    7: 7,
    8: 8,
    9: 9,
    10: 10,
    11: 11,
}
FLIP_V_MAP = {
    0: 0,
    1: 2,
    2: 1,
    3: 5,
    4: 6,
    5: 3,
    6: 4,
    7: 7,
    8: 8,
    9: 9,
    10: 10,
    11: 11,
}
ROTATE_CW_MAP = {
    0: 0,
    1: 2,
    2: 1,
    3: 4,
    4: 6,
    5: 3,
    6: 5,
    7: 7,
    8: 8,
    9: 9,
    10: 10,
    11: 11,
}
ROTATE_CCW_MAP = {
    0: 0,
    1: 2,
    2: 1,
    3: 5,
    4: 3,
    5: 6,
    6: 4,
    7: 7,
    8: 8,
    9: 9,
    10: 10,
    11: 11,
}
