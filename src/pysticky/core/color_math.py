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

Metrik: CIEDE2000 (Sharma et al. 2005) — Nachfolger von CIE76 (simple
euklidische Lab-Distanz), korrigiert dessen bekannte Schwäche bei
gesättigten/chromatischen Farben (Lightness/Chroma/Hue-Gewichtung +
Rotationsterm für den Blau-Violett-Bereich). Skalar-Implementierung
gegen den offiziellen 34-Paar-Referenzdatensatz von Sharmas Webseite
validiert (max. Abweichung < 0.0001), die vektorisierte Variante gegen
die Skalar-Variante (Abweichung im Bereich der Fließkomma-Präzision).
"""

from __future__ import annotations

import math
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


def delta_e2000(
    lab1: tuple[float, float, float],
    lab2: tuple[float, float, float],
    kL: float = 1.0,
    kC: float = 1.0,
    kH: float = 1.0,
) -> float:
    """CIEDE2000 Delta-E zwischen zwei CIE-Lab-Farben. Skalar, numpy-frei.

    Referenzimplementierung nach Sharma, Wu & Dalal (2005) — gegen deren
    veröffentlichten 34-Paar-Testdatensatz validiert (max. Abweichung
    < 0.0001). kL/kC/kH sind die Standard-Gewichtungsfaktoren (1.0 für
    Referenzbedingungen, siehe Paper).
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    c1 = math.hypot(a1, b1)
    c2 = math.hypot(a2, b2)
    c_bar = (c1 + c2) / 2.0

    c_bar7 = c_bar**7
    g = 0.5 * (1 - math.sqrt(c_bar7 / (c_bar7 + 25.0**7)))

    a1p = (1 + g) * a1
    a2p = (1 + g) * a2

    c1p = math.hypot(a1p, b1)
    c2p = math.hypot(a2p, b2)

    def _hue(ap: float, b: float) -> float:
        if ap == 0 and b == 0:
            return 0.0
        h = math.degrees(math.atan2(b, ap))
        return h + 360.0 if h < 0 else h

    h1p = _hue(a1p, b1)
    h2p = _hue(a2p, b2)

    dl_p = L2 - L1
    dc_p = c2p - c1p

    prod = c1p * c2p
    if prod == 0:
        dh_p_deg = 0.0
    else:
        dh = h2p - h1p
        if dh > 180:
            dh -= 360
        elif dh < -180:
            dh += 360
        dh_p_deg = dh

    dh_p = 2 * math.sqrt(prod) * math.sin(math.radians(dh_p_deg) / 2)

    l_bar_p = (L1 + L2) / 2.0
    c_bar_p = (c1p + c2p) / 2.0

    if prod == 0:
        h_bar_p = h1p + h2p
    elif abs(h1p - h2p) > 180:
        h_bar_p = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    else:
        h_bar_p = (h1p + h2p) / 2

    t = (
        1
        - 0.17 * math.cos(math.radians(h_bar_p - 30))
        + 0.24 * math.cos(math.radians(2 * h_bar_p))
        + 0.32 * math.cos(math.radians(3 * h_bar_p + 6))
        - 0.20 * math.cos(math.radians(4 * h_bar_p - 63))
    )

    delta_theta = 30 * math.exp(-(((h_bar_p - 275) / 25) ** 2))
    c_bar_p7 = c_bar_p**7
    rc = 2 * math.sqrt(c_bar_p7 / (c_bar_p7 + 25.0**7))
    sl = 1 + (0.015 * (l_bar_p - 50) ** 2) / math.sqrt(20 + (l_bar_p - 50) ** 2)
    sc = 1 + 0.045 * c_bar_p
    sh = 1 + 0.015 * c_bar_p * t
    rt = -math.sin(math.radians(2 * delta_theta)) * rc

    dl = dl_p / (kL * sl)
    dc = dc_p / (kC * sc)
    dh = dh_p / (kH * sh)

    return math.sqrt(dl * dl + dc * dc + dh * dh + rt * dc * dh)


def delta_e(
    rgb1: tuple[int, int, int],
    rgb2: tuple[int, int, int],
) -> float:
    """CIEDE2000 Delta-E zwischen zwei sRGB-Farben (0-255). Skalar, numpy-frei.

    Faustwerte (gelten näherungsweise auch für CIEDE2000, die Skala wurde
    bewusst nahe an CIE76 gehalten): ΔE < 1 nicht wahrnehmbar, ~2-3 sehr
    guter Garn-Treffer, ~10 deutlich sichtbar, > 25 schlechter Match.
    """
    return delta_e2000(rgb_to_lab(*rgb1), rgb_to_lab(*rgb2))


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


def _delta_e2000_array(target_lab: "np.ndarray", cand_lab: "np.ndarray") -> "np.ndarray":
    """CIEDE2000 zwischen einer Ziel-Lab-Farbe (Shape (3,)) und N Kandidaten
    (Shape (N, 3)). Vektorisierte Variante von `delta_e2000` — Ergebnisse
    stimmen mit der Skalar-Funktion bis auf Fließkomma-Rundung überein.
    """
    import numpy as np

    L1, a1, b1 = target_lab[0], target_lab[1], target_lab[2]
    L2, a2, b2 = cand_lab[:, 0], cand_lab[:, 1], cand_lab[:, 2]

    c1 = math.hypot(a1, b1)
    c2 = np.hypot(a2, b2)
    c_bar = (c1 + c2) / 2.0

    c_bar7 = c_bar**7
    g = 0.5 * (1 - np.sqrt(c_bar7 / (c_bar7 + 25.0**7)))

    a1p = (1 + g) * a1
    a2p = (1 + g) * a2

    c1p = np.hypot(a1p, b1)
    c2p = np.hypot(a2p, b2)

    def _hue(ap: "np.ndarray", b: "np.ndarray") -> "np.ndarray":
        h = np.degrees(np.arctan2(b, ap))
        h = np.where(h < 0, h + 360.0, h)
        return np.where((ap == 0) & (b == 0), 0.0, h)

    h1p = _hue(a1p, np.full_like(a2p, b1))
    h2p = _hue(a2p, b2)

    dl_p = L2 - L1
    dc_p = c2p - c1p

    prod = c1p * c2p
    dh = h2p - h1p
    dh = np.where(dh > 180, dh - 360, dh)
    dh = np.where(dh < -180, dh + 360, dh)
    dh_p_deg = np.where(prod == 0, 0.0, dh)

    dh_p = 2 * np.sqrt(np.clip(prod, 0, None)) * np.sin(np.radians(dh_p_deg) / 2)

    l_bar_p = (L1 + L2) / 2.0
    c_bar_p = (c1p + c2p) / 2.0

    hsum = h1p + h2p
    h_bar_p_far = np.where(hsum < 360, (hsum + 360) / 2, (hsum - 360) / 2)
    h_bar_p = np.where(prod == 0, hsum, np.where(np.abs(h1p - h2p) > 180, h_bar_p_far, hsum / 2))

    t = (
        1
        - 0.17 * np.cos(np.radians(h_bar_p - 30))
        + 0.24 * np.cos(np.radians(2 * h_bar_p))
        + 0.32 * np.cos(np.radians(3 * h_bar_p + 6))
        - 0.20 * np.cos(np.radians(4 * h_bar_p - 63))
    )

    delta_theta = 30 * np.exp(-(((h_bar_p - 275) / 25) ** 2))
    c_bar_p7 = c_bar_p**7
    rc = 2 * np.sqrt(c_bar_p7 / (c_bar_p7 + 25.0**7))
    sl = 1 + (0.015 * (l_bar_p - 50) ** 2) / np.sqrt(20 + (l_bar_p - 50) ** 2)
    sc = 1 + 0.045 * c_bar_p
    sh = 1 + 0.015 * c_bar_p * t
    rt = -np.sin(np.radians(2 * delta_theta)) * rc

    dl = dl_p / sl
    dc = dc_p / sc
    dh_final = dh_p / sh

    return np.sqrt(dl * dl + dc * dc + dh_final * dh_final + rt * dc * dh_final)


def nearest_index_by_lab(
    target_rgb: tuple[int, int, int],
    candidates_rgb: Sequence[tuple[int, int, int]],
) -> int:
    """Index des perzeptuell nächsten Kandidaten (CIEDE2000 in Lab).

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
    distances = _delta_e2000_array(target_lab, cand_lab)
    return int(np.argmin(distances))
