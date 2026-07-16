"""
Farbmathematik: sRGB <-> CIE-Lab und perzeptuelle Nächste-Farbe-Suche.

EINE Quelle für alle Lab-Konvertierungen im Projekt. Früher war die
D65-Matrix mehrfach kopiert (thread.py scalar, thread_cross_ref.py numpy,
vom Eyedropper mitbenutzt) — klassische Copy-Paste-Drift mit Bug-Risiko,
weil eine Korrektur an mehreren Stellen hätte erfolgen müssen.

Zwei Pfade, dieselbe Mathematik:

- **Skalar** (`rgb_to_lab` / `lab_to_rgb`): pure Python, KEIN numpy-Import
  auf Modulebene — damit "core lite"-Module wie `thread.py` numpy-frei
  importierbar bleiben. Schnell genug für Einzelfarben.
- **Vektorisiert** (`rgb_to_lab_array` / `nearest_index_by_lab`): numpy,
  lokal in der Funktion importiert. Für Massen-Konvertierung beim
  Paletten-Matching (~500 Garne pro Palette).

Metrik: CIE76 Delta-E (euklidische Distanz im Lab-Raum). Für Garn-Matching
ausreichend, deterministisch und wahrnehmungsbasiert besser als plain RGB.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    import numpy as np

# --- Konstanten (D65-Referenzweiss) ---
_D65 = (0.95047, 1.0, 1.08883)
_EPS = 0.008856
_KAPPA = 903.3

# linear sRGB -> XYZ (D65). Zeilen ergeben X, Y, Z.
_M_RGB_TO_XYZ = (
    (0.4124564, 0.3575761, 0.1804375),
    (0.2126729, 0.7151522, 0.0721750),
    (0.0193339, 0.1191920, 0.9503041),
)
# XYZ -> linear sRGB (Inverse von _M_RGB_TO_XYZ).
_M_XYZ_TO_RGB = (
    (3.2404542, -1.5371385, -0.4985314),
    (-0.9692660, 1.8760108, 0.0415560),
    (0.0556434, -0.2040259, 1.0572252),
)


def _srgb_to_linear(c: float) -> float:
    """Gamma-Korrektur sRGB (0-255) -> linear (0-1)."""
    c /= 255.0
    if c > 0.04045:
        return ((c + 0.055) / 1.055) ** 2.4
    return c / 12.92


def _linear_to_srgb(c: float) -> int:
    """Inverse Gamma-Korrektur linear (0-1) -> sRGB (0-255), geklemmt."""
    c = max(0.0, min(1.0, c))
    if c > 0.0031308:
        v = 1.055 * (c ** (1.0 / 2.4)) - 0.055
    else:
        v = 12.92 * c
    return max(0, min(255, int(round(v * 255))))


def _f(t: float) -> float:
    """Lab-Hilfsfunktion: t^(1/3) bzw. linearer Ast unterhalb eps."""
    if t > _EPS:
        return t ** (1.0 / 3.0)
    return (_KAPPA * t + 16) / 116


def _inv_f(t: float) -> float:
    """Inverse zu _f."""
    t3 = t**3
    if t3 > _EPS:
        return t3
    return (116 * t - 16) / _KAPPA


def rgb_to_lab(r: int, g: int, b: int) -> tuple[float, float, float]:
    """sRGB (0-255) -> CIE-Lab (D65). Skalar, numpy-frei."""
    rl, gl, bl = _srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b)
    mx, my, mz = _M_RGB_TO_XYZ
    X = mx[0] * rl + mx[1] * gl + mx[2] * bl
    Y = my[0] * rl + my[1] * gl + my[2] * bl
    Z = mz[0] * rl + mz[1] * gl + mz[2] * bl
    xn, yn, zn = _D65
    fx, fy, fz = _f(X / xn), _f(Y / yn), _f(Z / zn)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def lab_to_rgb(L: float, a: float, b: float) -> tuple[int, int, int]:
    """CIE-Lab (D65) -> sRGB (0-255). Inverse von rgb_to_lab."""
    xn, yn, zn = _D65
    fy = (L + 16) / 116
    fx = a / 500 + fy
    fz = fy - b / 200
    X = _inv_f(fx) * xn
    Y = _inv_f(fy) * yn
    Z = _inv_f(fz) * zn
    mr, mg, mb = _M_XYZ_TO_RGB
    rl = mr[0] * X + mr[1] * Y + mr[2] * Z
    gl = mg[0] * X + mg[1] * Y + mg[2] * Z
    bl = mb[0] * X + mb[1] * Y + mb[2] * Z
    return (_linear_to_srgb(rl), _linear_to_srgb(gl), _linear_to_srgb(bl))


def delta_e_sq(
    lab1: tuple[float, float, float],
    lab2: tuple[float, float, float],
) -> float:
    """Quadriertes CIE76 Delta-E. Wurzel beim reinen Vergleichen unnötig."""
    dl = lab1[0] - lab2[0]
    da = lab1[1] - lab2[1]
    db = lab1[2] - lab2[2]
    return dl * dl + da * da + db * db


def delta_e(
    rgb1: tuple[int, int, int],
    rgb2: tuple[int, int, int],
) -> float:
    """CIE76 Delta-E zwischen zwei sRGB-Farben (0-255). Skalar, numpy-frei.

    Liefert die echte (nicht quadrierte) perzeptuelle Distanz — praktisch
    für Anzeige-Indikatoren. Faustwerte: ΔE < 1 nicht wahrnehmbar, ~2-3
    sehr guter Garn-Treffer, ~10 deutlich sichtbar, > 25 schlechter Match.
    """
    return delta_e_sq(rgb_to_lab(*rgb1), rgb_to_lab(*rgb2)) ** 0.5


def rgb_to_lab_array(rgb: "np.ndarray") -> "np.ndarray":
    """RGB (0-255), Shape (N, 3) -> CIE-Lab (D65), Shape (N, 3). Vektorisiert."""
    import numpy as np

    rgb_norm = np.asarray(rgb, dtype=np.float64) / 255.0

    # sRGB -> linear RGB (Gamma-Korrektur)
    linear = np.where(
        rgb_norm > 0.04045,
        np.power((rgb_norm + 0.055) / 1.055, 2.4),
        rgb_norm / 12.92,
    )

    # linear RGB -> XYZ (D65)
    xyz = linear @ np.array(_M_RGB_TO_XYZ).T

    # XYZ -> Lab
    xyz_norm = xyz / np.array(_D65)
    f = np.where(
        xyz_norm > _EPS,
        np.cbrt(xyz_norm),
        (_KAPPA * xyz_norm + 16) / 116,
    )
    L = 116 * f[:, 1] - 16
    a = 500 * (f[:, 0] - f[:, 1])
    b = 200 * (f[:, 1] - f[:, 2])
    return np.stack([L, a, b], axis=1)


def nearest_index_by_lab(
    target_rgb: tuple[int, int, int],
    candidates_rgb: Sequence[tuple[int, int, int]],
) -> int:
    """Index des perzeptuell nächsten Kandidaten (CIE76 Delta-E in Lab).

    Args:
        target_rgb: Zielfarbe (r, g, b), 0-255.
        candidates_rgb: Kandidaten-Farben, mindestens eine.

    Returns:
        Index in `candidates_rgb` mit kleinstem Delta-E zur Zielfarbe.

    Nutzt numpy für die Massen-Konvertierung (typisch ~500 Garne).
    """
    import numpy as np

    target_lab = rgb_to_lab_array(np.array([target_rgb], dtype=np.float64))[0]
    cand_lab = rgb_to_lab_array(np.asarray(candidates_rgb, dtype=np.float64))
    diff = cand_lab - target_lab
    return int(np.argmin(np.sum(diff * diff, axis=1)))
