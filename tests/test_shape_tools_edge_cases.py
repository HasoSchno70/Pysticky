# -*- coding: utf-8 -*-
"""
Grenzfall-Tests fuer die Zeichenwerkzeuge Linie, Rechteck, Ellipse.

Deckt konkrete Grenzfaelle ab: 1-Pixel-Klick (kein Drag), umgekehrte
Zugrichtung, sowie einen echten Bug im Ellipsen-Werkzeug bei sehr kleinen
gezogenen Flaechen (Runde 52 des Clean-Code-Audits).
"""

from pysticky.ui.tools.ellipse_tool import EllipseTool
from pysticky.ui.tools.line_tool import LineTool
from pysticky.ui.tools.rect_tool import RectTool

# === Ellipse: Bugfix-Regression ===
#
# Vorher: rx und ry wurden per Integer-Division berechnet (`abs(dx) // 2`).
# Bei einem gezogenen Bereich von nur 2 Zellen in beiden Achsen (z.B.
# Diagonale von (0,0) nach (1,1)) rundeten BEIDE Radien auf 0, was denselben
# Code-Pfad wie ein echter 1-Pixel-Klick (Start==Ende) ausloeste. Das
# Werkzeug lieferte dann nur den EINEN Startpunkt zurueck, obwohl der
# Nutzer ueber eine 2x2- (bzw. 1x2-/2x1-)Flaeche gezogen hat.


def test_ellipse_tiny_diagonal_drag_covers_full_area_not_single_point():
    """2x2-Diagonalzug darf nicht auf einen einzelnen Punkt kollabieren."""
    tool = EllipseTool(filled=False)
    points = set(tool._get_ellipse_points(0, 0, 1, 1))
    assert points == {(0, 0), (0, 1), (1, 0), (1, 1)}


def test_ellipse_tiny_diagonal_drag_filled_matches_unfilled():
    """Bei einer so kleinen Flaeche gibt es keinen Rahmen/Fuellung-Unterschied
    (wie beim Rechteck-Werkzeug) -- aber beide muessen die volle Flaeche
    liefern, nicht nur einen Punkt."""
    unfilled = EllipseTool(filled=False)
    filled = EllipseTool(filled=True)
    pts_unfilled = set(unfilled._get_ellipse_points(0, 0, 1, 1))
    pts_filled = set(filled._get_ellipse_points(0, 0, 1, 1))
    assert pts_unfilled == pts_filled == {(0, 0), (0, 1), (1, 0), (1, 1)}


def test_ellipse_two_cell_vertical_drag_produces_both_points():
    """dx=0, dy=1 (2 Zellen hoch) rundete ry ebenfalls auf 0 -> selber Bug."""
    tool = EllipseTool(filled=False)
    points = set(tool._get_ellipse_points(0, 0, 0, 1))
    assert points == {(0, 0), (0, 1)}


def test_ellipse_two_cell_horizontal_drag_produces_both_points():
    """dx=1, dy=0 (2 Zellen breit) rundete rx ebenfalls auf 0 -> selber Bug."""
    tool = EllipseTool(filled=False)
    points = set(tool._get_ellipse_points(0, 0, 1, 0))
    assert points == {(0, 0), (1, 0)}


def test_ellipse_true_click_without_drag_still_single_point():
    """Start==Ende (echter Klick ohne Drag) muss weiterhin genau EINEN
    Punkt liefern -- der Fix darf diesen Fall nicht veraendern."""
    tool = EllipseTool(filled=False)
    assert tool._get_ellipse_points(5, 5, 5, 5) == [(5, 5)]


def test_ellipse_tiny_diagonal_drag_direction_independent():
    """Zugrichtung darf das Ergebnis nicht beeinflussen (umgekehrter Zug von
    unten-rechts nach oben-links liefert dieselbe Flaeche, nur verschoben)."""
    tool = EllipseTool(filled=False)
    forward = set(tool._get_ellipse_points(0, 0, 1, 1))
    backward = set(tool._get_ellipse_points(1, 1, 0, 0))
    assert forward == backward == {(0, 0), (0, 1), (1, 0), (1, 1)}


def test_ellipse_3x3_filled_vs_unfilled_still_differ():
    """Regression: die schon vor dem Fix korrekte Unterscheidung fuer eine
    3x3-Flaeche (Rahmen vs. Fuellung inkl. Mittelpunkt) darf nicht kaputt
    gehen."""
    unfilled = EllipseTool(filled=False)
    filled = EllipseTool(filled=True)
    pts_unfilled = set(unfilled._get_ellipse_points(0, 0, 2, 2))
    pts_filled = set(filled._get_ellipse_points(0, 0, 2, 2))
    assert (1, 1) not in pts_unfilled
    assert (1, 1) in pts_filled
    assert pts_filled == pts_unfilled | {(1, 1)}


# === Rechteck: Grenzfaelle (bereits korrekt, als Regression abgesichert) ===


def test_rect_tiny_2x2_filled_equals_unfilled():
    """Bei 2x2 gibt es keine Innenflaeche -- Rahmen und Fuellung sind
    identisch (kein Bug, aber dokumentiertes/erwartetes Verhalten)."""
    unfilled = RectTool(filled=False)
    filled = RectTool(filled=True)
    pts_unfilled = set(unfilled._get_rect_points(0, 0, 1, 1))
    pts_filled = set(filled._get_rect_points(0, 0, 1, 1))
    assert pts_unfilled == pts_filled == {(0, 0), (0, 1), (1, 0), (1, 1)}


def test_rect_direction_independent():
    """Umgekehrte Zugrichtung liefert dieselbe Flaeche wie die normale."""
    tool = RectTool(filled=True)
    forward = set(tool._get_rect_points(0, 0, 2, 2))
    backward = set(tool._get_rect_points(2, 2, 0, 0))
    assert forward == backward


def test_rect_single_click_no_drag_yields_one_point():
    """Klick ohne Drag (Start==Ende) zeichnet genau eine Zelle -- ohne
    Duplikat in der Changes-Liste (siehe Bugfix-Regression unten)."""
    tool = RectTool(filled=False)
    assert tool._get_rect_points(4, 4, 4, 4) == [(4, 4)]


# === Rechteck: Bugfix-Regression (doppelte Punkte bei entarteter Groesse) ===
#
# Vorher: der Umriss-Zweig von _get_rect_points() haengte Punkte an eine
# Liste an, ohne auf Duplikate zu pruefen. Bei einem Rechteck mit Breite
# oder Hoehe genau 1 Zelle (min_x==max_x bzw. min_y==max_y) wurde dieselbe
# Zelle zweimal angehaengt -- jede Wiederholung erzeugt in
# mouse_events_mixin.py einen eigenen Undo-Command/eine eigene
# invalidate_cell()+stitch_placed-Emission fuer dieselbe Zelle.


def test_rect_unfilled_single_row_has_no_duplicate_points():
    """Breite > 1, Hoehe == 1 (waagerechte 'Linie' per Rechteck-Werkzeug)
    darf jede Zelle nur einmal liefern."""
    tool = RectTool(filled=False)
    points = tool._get_rect_points(0, 5, 4, 5)
    assert len(points) == len(set(points))
    assert set(points) == {(0, 5), (1, 5), (2, 5), (3, 5), (4, 5)}


def test_rect_unfilled_single_column_has_no_duplicate_points():
    """Breite == 1, Hoehe > 1 (senkrechte 'Linie' per Rechteck-Werkzeug)
    darf jede Zelle nur einmal liefern."""
    tool = RectTool(filled=False)
    points = tool._get_rect_points(5, 0, 5, 4)
    assert len(points) == len(set(points))
    assert set(points) == {(5, 0), (5, 1), (5, 2), (5, 3), (5, 4)}


def test_rect_unfilled_single_click_has_no_duplicate_points():
    """1x1-Klick darf die Zelle nicht doppelt liefern."""
    tool = RectTool(filled=False)
    points = tool._get_rect_points(4, 4, 4, 4)
    assert len(points) == len(set(points)) == 1


def test_rect_unfilled_normal_size_still_correct():
    """Regression: eine normale (nicht entartete) 5x4-Rechteck-Kontur bleibt
    unveraendert korrekt (Rahmen ohne Innenpunkte)."""
    tool = RectTool(filled=False)
    points = set(tool._get_rect_points(0, 0, 4, 3))
    filled_tool = RectTool(filled=True)
    filled_points = set(filled_tool._get_rect_points(0, 0, 4, 3))
    assert points < filled_points  # echte Teilmenge -- Rahmen hat Innenloch
    assert (2, 1) not in points  # innere Zelle fehlt im Umriss
    assert (2, 1) in filled_points


# === Linie: Bugfix-Regression (Richtungs-Asymmetrie bei bestimmten Steigungen) ===
#
# Vorher: der klassische Bresenham-Algorithmus in _get_line_points() lief
# IMMER vom uebergebenen Start- zum Endpunkt. Bei bestimmten Steigungen
# (z.B. exakt 2:1, dx=4/dy=2) entscheiden die Fehlerterm-Tiebreaks
# (e2 > -dy / e2 < dx) je nach Zugrichtung unterschiedlich, welche Zelle bei
# einem diagonalen Schritt gewaehlt wird -- eine Linie von (0,0) nach (4,2)
# ergab dadurch eine SICHTBAR ANDERE Treppenstufen-Form als dieselbe Linie
# von (4,2) nach (0,0), obwohl beide dieselben zwei Endpunkte verbinden.


def test_line_direction_independent_at_asymmetric_slope():
    """2:1-Steigung war der konkrete Fall, bei dem Vor-/Rueckwaerts-Zug vor
    dem Fix unterschiedliche Punktmengen ergab."""
    tool = LineTool()
    forward = tool._get_line_points(0, 0, 4, 2)
    backward = tool._get_line_points(4, 2, 0, 0)
    assert set(forward) == set(backward)


def test_line_direction_independent_various_slopes():
    """Mehrere Steigungen gegen Richtungs-Asymmetrie absichern."""
    tool = LineTool()
    cases = [(0, 0, 4, 2), (0, 0, 6, 3), (0, 0, 8, 4), (2, 2, 10, 6), (0, 0, 5, 3)]
    for x1, y1, x2, y2 in cases:
        forward = set(tool._get_line_points(x1, y1, x2, y2))
        backward = set(tool._get_line_points(x2, y2, x1, y1))
        assert forward == backward, f"Asymmetrie bei ({x1},{y1})->({x2},{y2})"


def test_line_single_click_no_drag_yields_one_point():
    """Klick ohne Drag (Start==Ende) zeichnet genau eine Zelle."""
    tool = LineTool()
    assert tool._get_line_points(7, 7, 7, 7) == [(7, 7)]
