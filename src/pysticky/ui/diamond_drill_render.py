"""
Gemeinsame QPainter-Zeichenlogik für Diamond-Painting-Drills.

Diese Datei kapselt die facettierte Drill-Optik (vier dreieckige Facetten:
Glanzlicht oben, Schatten unten, seitlich mittel), die von DREI unabhängigen
Rendering-Pfaden derselben App visuell identisch aussehen MUSS:

- Direkt-Render-Pfad (kleine/mittlere Muster):
  ``ui/canvas/mixins/rendering_mixin.py::RenderingMixin._draw_diamond_drill``
- Chunk-Cache-Pfad (grosse Muster, > 200x200 Zellen):
  ``ui/canvas/performance.py::_draw_diamond_drill_perf``
- Vorschau-Render-Pfad (Stoff-/Pixel-Vorschau, Export-Cover):
  ``ui/rendering/preview_render_engine.py::PreviewRenderEngine._draw_diamond_drill_preview``

Vor 2026-07-23 hielt jeder der drei Pfade eine eigene Kopie der
Facetten-Geometrie UND der Helligkeits-Faktoren (145/110/95/70). Die Kopien
waren zufällig noch byte-für-byte äquivalent, aber ohne gemeinsamen Helfer
oder Synchronisations-Test hätte eine künftige Anpassung (z.B. andere
Schattierungsfaktoren) leicht nur auf einer Kopie landen können, mit
sichtbar inkonsistentem Rendering je nach Mustergrösse/Ansicht als Folge.
Diese Funktion ist jetzt die einzige Quelle dieser Logik -- alle drei Pfade
rufen sie auf.

Bewusst NICHT in ``core/stitch_shapes.py`` verschoben: dieses Modul ist laut
eigenem Docstring renderer-agnostisch (QPainter, reportlab, SVG, ...) und
enthält bewusst kein Qt. Der SVG-Export-Pfad
(``io/export_common.py::svg_drill_shape``) bleibt daher separat -- er
zeichnet auf ein anderes Ziel (SVG-String statt QPainter) und teilt sich
mit den drei QPainter-Pfaden bereits die reinen Geometrie-Helfer aus
``core/stitch_shapes.py`` (``diamond_inset_pixels``/``diamond_should_draw_edge``).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

from ..core.stitch_shapes import diamond_inset_pixels, diamond_should_draw_edge


def draw_diamond_drill(painter: QPainter, x: int, y: int, size: int, color: QColor) -> None:
    """Zeichnet einen Diamond-Painting-Drill: facettiertes Quadrat.

    Echte Drills sind 2.5mm-Quadrate mit pyramidaler Spitze — von oben
    sieht man vier dreieckige Facetten. Die obere Facette ist die hellste
    (Glanzlicht), die untere die dunkelste (Schatten), links/rechts mittel.
    Zusammen ergibt das die typische DP-Optik.

    Inset ist adaptiv: bei kleiner Zelle (<12px) berühren sich die
    Drills nahtlos, damit das Pattern bei rausgezoomter Ansicht nicht
    ausgewaschen weiss wirkt.

    Gemeinsam genutzt von allen drei QPainter-Rendering-Pfaden (Direkt-
    Render, Chunk-Cache, Vorschau) -- siehe Modul-Docstring.
    """
    inset = int(diamond_inset_pixels(size))
    x0 = x + inset
    y0 = y + inset
    x1 = x + size - inset
    y1 = y + size - inset
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0

    # Vier Facetten als Dreiecke (jeweils Mittelpunkt + zwei Kanten-Ecken)
    top = QPainterPath()
    top.moveTo(x0, y0)
    top.lineTo(x1, y0)
    top.lineTo(cx, cy)
    top.closeSubpath()

    right = QPainterPath()
    right.moveTo(x1, y0)
    right.lineTo(x1, y1)
    right.lineTo(cx, cy)
    right.closeSubpath()

    bottom = QPainterPath()
    bottom.moveTo(x1, y1)
    bottom.lineTo(x0, y1)
    bottom.lineTo(cx, cy)
    bottom.closeSubpath()

    left = QPainterPath()
    left.moveTo(x0, y1)
    left.lineTo(x0, y0)
    left.lineTo(cx, cy)
    left.closeSubpath()

    # Helligkeits-Varianten mit Alpha-Erhalt (lighter/darker normieren auf
    # 255 Alpha — wir müssen die Original-Alpha aus `color` zurückschreiben,
    # sonst frisst der Effekt die Layer-Deckkraft).
    alpha = color.alpha()

    def _shift(c: QColor, factor: int) -> QColor:
        shifted = c.lighter(factor) if factor >= 100 else c.darker(200 - factor)
        shifted.setAlpha(alpha)
        return shifted

    c_top = _shift(color, 145)  # Glanzlicht
    c_right = _shift(color, 110)
    c_left = _shift(color, 95)
    c_bottom = _shift(color, 70)  # Schatten

    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.fillPath(top, c_top)
    painter.fillPath(right, c_right)
    painter.fillPath(bottom, c_bottom)
    painter.fillPath(left, c_left)

    # Dünner Kantenrand für Trennschärfe zwischen Nachbar-Drills.
    # Bei kleinem Zoom weglassen, sonst frisst der Rand den Drill auf.
    if diamond_should_draw_edge(size):
        edge = QColor(0, 0, 0, min(120, alpha))
        painter.setPen(QPen(edge, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(x0, y0, x1 - x0, y1 - y0)

    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
