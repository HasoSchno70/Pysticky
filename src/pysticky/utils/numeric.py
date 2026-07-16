"""Kleine numerische Helfer."""


def clamp(value: float, lo: float, hi: float) -> float:
    """Begrenzt value auf den Bereich [lo, hi]."""
    return max(lo, min(hi, value))


def clamp_int(value: int, lo: int, hi: int) -> int:
    """Begrenzt einen int auf den Bereich [lo, hi] (typerhaltend)."""
    return max(lo, min(hi, value))
