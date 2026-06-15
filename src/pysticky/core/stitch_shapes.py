"""
Geometrie-Helfer fuer Teil-Stiche (halbe + Viertel).

Liefert pro `StitchType` die Eckpunkte des Dreiecks/Polygons als
normalisierte Koordinaten (Werte in [0, 1] bezogen auf die Zelle).
Damit kann jeder Renderer (QPainter, reportlab, SVG, ...) den gleichen
Punkt-Satz nutzen, ohne dass die Form-Logik dupliziert wird.

Konvention pro Zelle:
    (0,0) ----- (0.5,0) ----- (1,0)
       |                          |
   (0,0.5)      (0.5,0.5)    (1,0.5)
       |                          |
    (0,1) ----- (0.5,1) ----- (1,1)

Y waechst nach unten (Bildschirm-Koordinaten).
"""

from __future__ import annotations

# Punkt-Liste pro Stitch-Type, normalisiert auf [0, 1].
# 0 (FULL) und 8/9 (BACKSTITCH/FRENCH_KNOT) sind keine Polygone — der
# Aufrufer muss sie speziell behandeln.
_PARTIAL_SHAPES: dict[int, tuple[tuple[float, float], ...]] = {
    # HALF_TL_BR (/): oberes-linkes Dreieck
    1: ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)),
    # HALF_TR_BL (\): oberes-rechtes Dreieck
    2: ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0)),
    # QUARTER_TL
    3: ((0.0, 0.0), (0.5, 0.0), (0.0, 0.5)),
    # QUARTER_TR
    4: ((0.5, 0.0), (1.0, 0.0), (1.0, 0.5)),
    # QUARTER_BL
    5: ((0.0, 0.5), (0.0, 1.0), (0.5, 1.0)),
    # QUARTER_BR
    6: ((1.0, 0.5), (0.5, 1.0), (1.0, 1.0)),
    # THREE_QUARTER: alles ausser unten-links
    7: ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
}


def partial_stitch_points(
    stitch_type: int,
    x: float,
    y: float,
    size: float,
) -> tuple[tuple[float, float], ...]:
    """
    Liefert die Polygon-Eckpunkte in Pixel-Koordinaten fuer einen
    halben/Viertel-Stich.

    Args:
        stitch_type: 1..7 (Halbe/Viertel/Dreiviertel). 0 wird als leeres
            Tupel zurueckgegeben — der Aufrufer rendert dann den vollen
            Stich auf seine eigene Art.
        x, y: linke obere Ecke der Zelle in Pixel
        size: Zellgroesse in Pixel

    Returns:
        Liste von (px, py)-Tupeln, oder leeres Tupel fuer FULL/Backstitch/Knot.
    """
    shape = _PARTIAL_SHAPES.get(stitch_type)
    if not shape:
        return ()
    return tuple((x + nx * size, y + ny * size) for nx, ny in shape)


def is_partial_stitch(stitch_type: int) -> bool:
    """True wenn der Type ein Polygon erzeugt (nicht voll und kein Backstitch)."""
    return stitch_type in _PARTIAL_SHAPES


# French Knot (9) ist kein Polygon — er wird als kleiner Kreis in der
# Zellmitte gezeichnet. Renderer pruefen `is_french_knot()` separat und
# nutzen `french_knot_radius_factor()` fuer eine konsistente Punktgroesse.

_FRENCH_KNOT_TYPE = 9
_BEAD_TYPE = 10
_DIAMOND_TYPE = 11


def is_french_knot(stitch_type: int) -> bool:
    """True wenn der Type ein Franzoesischer Knoten ist."""
    return stitch_type == _FRENCH_KNOT_TYPE


def french_knot_radius_factor() -> float:
    """
    Relative Radius des French-Knot-Punkts bezogen auf cell_size.

    cell_size * factor = Radius in Pixeln. 0.18 sieht in der Vorschau
    natuerlich aus — klein genug um nicht wie ein voller Stitch zu wirken,
    gross genug um auf typischen Zoom-Stufen sichtbar zu sein.
    """
    return 0.18


def is_bead(stitch_type: int) -> bool:
    """True wenn der Type eine Perle (Bead) ist."""
    return stitch_type == _BEAD_TYPE


def bead_radius_factor() -> float:
    """
    Relativer Radius einer Perle bezogen auf cell_size.

    Perlen sind merklich groesser als French Knots (0.18) — eine echte Perle
    fuellt fast die ganze Zelle. 0.38 = 76% Zell-Durchmesser, mit Stoff-Rand
    drumherum sichtbar damit Nachbarperlen sich nicht beruehren.
    """
    return 0.38


def is_diamond(stitch_type: int) -> bool:
    """True wenn der Type ein Diamond-Painting-Drill ist."""
    return stitch_type == _DIAMOND_TYPE


def diamond_inset_factor() -> float:
    """
    Relativer Innenabstand des Drill-Quadrats bezogen auf cell_size.

    Echte Diamond-Painting-Drills sind 2.5mm-Quadrate, die auf einem
    Klebegrund liegen und einen sichtbaren Rand zur Nachbarzelle haben.
    0.08 = 8% Inset pro Seite -> 84% Zell-Kantenlaenge fuer den Drill.
    """
    return 0.08


def diamond_inset_pixels(cell_size: float) -> float:
    """Liefert den absoluten Inset in Pixeln, adaptiv an die Zellgroesse.

    Bei kleinen Cells (Vorschau, Cover-Mini) wuerde ein konstanter 1px-
    Inset einen sichtbaren weissen Spalt zwischen den Drills erzeugen, der
    die ganze Vorlage hell und ausgewaschen wirken laesst.

    Strategie:
    - cell_size < 12 → Inset = 0 (Drills beruehren sich, Spalt nicht sichtbar)
    - cell_size >= 12 → Inset = round(cell_size * 0.08), max begrenzt damit der
      Drill bei sehr grosser Zelle nicht zu winzig wird.

    Der Rueckgabewert ist float — Renderer casten selbst zu int falls noetig.
    """
    if cell_size < 12:
        return 0.0
    return min(cell_size * 0.08, cell_size * 0.15)


def diamond_should_draw_edge(cell_size: float) -> bool:
    """True, wenn der dunkle Kantenrand um den Drill gezeichnet werden soll.

    Bei kleinen Cells frisst ein 1px-Edge die Hauptfarbe weitgehend auf —
    der Rand wirkt dominant statt subtil. Erst ab moderater Zellgroesse
    sinnvoll.
    """
    return cell_size >= 14


def normalized_partial_stitch_shape(
    stitch_type: int,
) -> tuple[tuple[float, float], ...]:
    """
    Liefert die normalisierten Eckpunkte (Koordinaten in [0, 1]) fuer den
    Stichtyp. Y waechst nach unten (Screen-Koordinaten).

    Leeres Tupel fuer FULL/Backstitch/French-Knot — kein Polygon.
    """
    return _PARTIAL_SHAPES.get(stitch_type, ())
