"""
Farbblindheits-Simulation für die Canvas-Anzeige.

Verwendet Brettel/Vienot-Simulationsmatrizen zur Darstellung von
Protanopie, Deuteranopie und Tritanopie.

Die Transformation wird nur auf die Anzeige angewandt,
die gespeicherten Farben bleiben unverändert.
"""

from enum import Enum


class ColorBlindType(Enum):
    """Farbblindheits-Typen."""

    NONE = "none"
    PROTANOPIA = "protanopia"
    DEUTERANOPIA = "deuteranopia"
    TRITANOPIA = "tritanopia"


# Vienot 1999 Simulationsmatrizen (sRGB Farbraum)
# Jede Matrix ist ein 3x3 Array: [[r->r, g->r, b->r], [r->g, g->g, b->g], [r->b, g->b, b->b]]
_MATRICES = {
    ColorBlindType.PROTANOPIA: [
        [0.56667, 0.43333, 0.00000],
        [0.55833, 0.44167, 0.00000],
        [0.00000, 0.24167, 0.75833],
    ],
    ColorBlindType.DEUTERANOPIA: [
        [0.62500, 0.37500, 0.00000],
        [0.70000, 0.30000, 0.00000],
        [0.00000, 0.30000, 0.70000],
    ],
    ColorBlindType.TRITANOPIA: [
        [0.95000, 0.05000, 0.00000],
        [0.00000, 0.43333, 0.56667],
        [0.00000, 0.47500, 0.52500],
    ],
}

# Cache für transformierte Farben (wird bei Type-Wechsel geleert)
_cache: dict[tuple[int, int, int, str], tuple[int, int, int]] = {}


def simulate_color(r: int, g: int, b: int, cb_type: ColorBlindType) -> tuple[int, int, int]:
    """
    Simuliert eine Farbe wie sie bei der gegebenen Farbblindheit wahrgenommen wird.

    Args:
        r, g, b: RGB-Werte (0-255)
        cb_type: Farbblindheits-Typ

    Returns:
        Transformierte (r, g, b) Werte (0-255)
    """
    if cb_type == ColorBlindType.NONE:
        return (r, g, b)

    key = (r, g, b, cb_type.value)
    cached = _cache.get(key)
    if cached is not None:
        return cached

    matrix = _MATRICES[cb_type]
    nr = matrix[0][0] * r + matrix[0][1] * g + matrix[0][2] * b
    ng = matrix[1][0] * r + matrix[1][1] * g + matrix[1][2] * b
    nb = matrix[2][0] * r + matrix[2][1] * g + matrix[2][2] * b

    result = (
        max(0, min(255, int(round(nr)))),
        max(0, min(255, int(round(ng)))),
        max(0, min(255, int(round(nb)))),
    )
    _cache[key] = result
    return result


def clear_cache() -> None:
    """Leert den Simulationscache (bei Type-Wechsel aufrufen)."""
    _cache.clear()
