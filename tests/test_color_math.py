# -*- coding: utf-8 -*-
"""
Tests für core/color_math.py — insbesondere die CIEDE2000-Implementierung.

Referenzwerte stammen aus dem offiziellen 34-Paar-Testdatensatz von
Sharma, Wu & Dalal (2005), veröffentlicht auf der Autoren-Webseite
(ece.rochester.edu/~gsharma/ciede2000/dataNprograms/ciede2000testdata.txt).
Das ist der de-facto Standard-Referenzdatensatz zur Validierung von
CIEDE2000-Implementierungen — deckt bewusst kniffelige Sonderfälle ab
(a*=b*=0, Hue-Wraparound um 360°, nahe beieinanderliegende Chroma-Werte).
"""

import pytest

from pysticky.core.color_math import delta_e2000, lab_to_rgb, rgb_to_lab

# (lab1, lab2, erwartetes CIEDE2000) — Auszug aus dem Sharma-Referenzdatensatz.
_SHARMA_REFERENCE_PAIRS = [
    ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
    ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
    ((50.0000, -1.3802, -84.2814), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, 0.0000, 0.0000), (50.0000, -1.0000, 2.0000), 2.3669),
    # a*=b*=0-Sonderfall (Hue undefiniert) auf einer Seite.
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0009), 7.1792),
    # Große Helligkeits-/Chroma-/Hue-Sprünge.
    ((50.0000, 2.5000, 0.0000), (73.0000, 25.0000, -18.0000), 27.1492),
    ((50.0000, 2.5000, 0.0000), (56.0000, -27.0000, -3.0000), 31.9030),
    # Reale Garnfarben-Nachbarschaft (kleine Differenzen).
    ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
    ((22.7233, 20.0904, -46.6940), (23.0331, 14.9730, -42.5619), 2.0373),
    ((2.0776, 0.0795, -1.1350), (0.9033, -0.0636, -0.5514), 0.9082),
]


@pytest.mark.parametrize("lab1,lab2,expected", _SHARMA_REFERENCE_PAIRS)
def test_delta_e2000_matches_sharma_reference(lab1, lab2, expected):
    """CIEDE2000 muss dem offiziellen Referenzdatensatz auf 0.001 genau folgen."""
    assert delta_e2000(lab1, lab2) == pytest.approx(expected, abs=0.001)


def test_delta_e2000_is_symmetric():
    """ΔE00(A, B) == ΔE00(B, A) — die Formel ist per Definition symmetrisch."""
    lab1 = (60.2574, -34.0099, 36.2677)
    lab2 = (22.7233, 20.0904, -46.6940)
    assert delta_e2000(lab1, lab2) == pytest.approx(delta_e2000(lab2, lab1), abs=1e-9)


def test_delta_e2000_identical_colors_is_zero():
    lab = (50.0, 12.3, -45.6)
    assert delta_e2000(lab, lab) == pytest.approx(0.0, abs=1e-9)


def test_rgb_to_lab_roundtrip():
    """rgb_to_lab -> lab_to_rgb muss (bis auf Rundung) die Ausgangsfarbe ergeben."""
    for rgb in [(255, 0, 0), (0, 255, 0), (0, 0, 255), (128, 128, 128), (12, 200, 77)]:
        lab = rgb_to_lab(*rgb)
        back = lab_to_rgb(*lab)
        assert back == rgb


def test_delta_e_rgb_matches_delta_e2000_via_lab():
    """delta_e() (RGB-Fassade) muss exakt delta_e2000(rgb_to_lab(...)) entsprechen."""
    from pysticky.core.color_math import delta_e

    rgb1, rgb2 = (255, 0, 0), (200, 20, 20)
    expected = delta_e2000(rgb_to_lab(*rgb1), rgb_to_lab(*rgb2))
    assert delta_e(rgb1, rgb2) == pytest.approx(expected, abs=1e-9)


def test_nearest_index_by_lab_picks_perceptually_closest():
    """Vektorisierte Nächste-Farbe-Suche muss mit der Skalar-Formel übereinstimmen."""
    from pysticky.core.color_math import nearest_index_by_lab

    target = (255, 0, 0)  # Rot
    candidates = [
        (0, 255, 0),  # Gruen -- weit weg
        (250, 10, 10),  # Nahrot -- am naechsten
        (0, 0, 255),  # Blau -- weit weg
    ]
    assert nearest_index_by_lab(target, candidates) == 1
