# -*- coding: utf-8 -*-
"""Regressionstest (Clean-Code-Audit, Nachfolge-Runde auf Runde 26): stellt
sicher, dass die drei unabhaengigen QPainter-Rendering-Pfade fuer
Diamond-Painting-Drills (Direkt-Render, Chunk-Cache, Vorschau) tatsaechlich
EIN gemeinsames Stueck Code nutzen (``ui/diamond_drill_render.py::
draw_diamond_drill``) statt drei separater Kopien der Facetten-/
Schattierungs-Mathematik (145/110/95/70-Faktoren etc.).

Runde 26 hatte den Fund dokumentiert, aber zurueckgestellt: die drei Pfade
waren zufaellig noch byte-fuer-byte aequivalent, aber ohne gemeinsamen
Helfer oder Test haette eine kuenftige Anpassung nur auf einer Kopie landen
koennen -- Diamond-Drills haetten dann je nach Mustergroesse/Ansicht
unterschiedlich ausgesehen. Dieser Test macht ein Auseinanderdriften
technisch unmoeglich (nur noch eine Implementierung) UND beweist es
zusaetzlich per Pixel-Vergleich.
"""

import pytest
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap

pytestmark = pytest.mark.usefixtures("qtbot")


def _render_via(draw_fn, size: int, color: QColor) -> QImage:
    """Rendert einen Drill ueber die gegebene Zeichenfunktion auf ein
    isoliertes QPixmap und liefert das Ergebnis als QImage zum Vergleich."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("white"))
    painter = QPainter(pixmap)
    try:
        draw_fn(painter, 0, 0, size, color)
    finally:
        painter.end()
    return pixmap.toImage().convertToFormat(QImage.Format.Format_RGB32)


def _images_equal(a: QImage, b: QImage) -> bool:
    if a.size() != b.size():
        return False
    for y in range(a.height()):
        for x in range(a.width()):
            if a.pixelColor(x, y) != b.pixelColor(x, y):
                return False
    return True


def test_all_three_diamond_drill_paths_share_one_implementation():
    """Direkt-Render-, Chunk-Cache- und Vorschau-Pfad muessen alle auf
    dieselbe Funktion aus ``ui/diamond_drill_render.py`` verweisen -- keine
    drei separaten Kopien mehr."""
    from pysticky.ui.canvas.mixins.rendering_mixin import RenderingMixin
    from pysticky.ui.canvas.performance import _draw_diamond_drill_perf
    from pysticky.ui.rendering.preview_render_engine import PreviewRenderEngine

    # Alle drei Wrapper muessen intern draw_diamond_drill aufrufen. Wir
    # pruefen das ueber Monkeypatching: wenn wir die geteilte Funktion durch
    # einen Spy ersetzen, muss JEDER der drei Aufrufer ihn treffen.
    calls = []

    def _spy(painter, x, y, size, color):
        calls.append((x, y, size, color.name()))

    import pysticky.ui.diamond_drill_render as shared_module

    original = shared_module.draw_diamond_drill
    try:
        shared_module.draw_diamond_drill = _spy

        pixmap = QPixmap(10, 10)
        painter = QPainter(pixmap)
        try:
            RenderingMixin._draw_diamond_drill(painter, 1, 2, 10, QColor("#FF0000"))
            _draw_diamond_drill_perf(painter, 3, 4, 10, QColor("#00FF00"))
            PreviewRenderEngine._draw_diamond_drill_preview(painter, 5, 6, 10, QColor("#0000FF"))
        finally:
            painter.end()
    finally:
        shared_module.draw_diamond_drill = original

    assert calls == [
        (1, 2, 10, "#ff0000"),
        (3, 4, 10, "#00ff00"),
        (5, 6, 10, "#0000ff"),
    ], (
        "Mindestens einer der drei Diamond-Drill-Aufrufer ruft nicht mehr "
        "die geteilte draw_diamond_drill()-Funktion auf -- Konsolidierung "
        "wurde umgangen oder rueckgaengig gemacht."
    )


def test_all_three_diamond_drill_paths_render_pixel_identical():
    """Unabhaengig von der Implementierungs-Frage: die drei Aufrufer muessen
    auch tatsaechlich pixelidentisch rendern (beweist, dass die
    Konsolidierung keine sichtbare Regression eingefuehrt hat)."""
    from pysticky.ui.canvas.mixins.rendering_mixin import RenderingMixin
    from pysticky.ui.canvas.performance import _draw_diamond_drill_perf
    from pysticky.ui.rendering.preview_render_engine import PreviewRenderEngine

    size = 40
    color = QColor(200, 80, 120, 255)

    img_direct = _render_via(RenderingMixin._draw_diamond_drill, size, color)
    img_chunk = _render_via(_draw_diamond_drill_perf, size, color)
    img_preview = _render_via(PreviewRenderEngine._draw_diamond_drill_preview, size, color)

    assert _images_equal(img_direct, img_chunk), (
        "Direkt-Render-Pfad und Chunk-Cache-Pfad rendern Diamond-Drills nicht mehr pixelidentisch."
    )
    assert _images_equal(img_direct, img_preview), (
        "Direkt-Render-Pfad und Vorschau-Pfad rendern Diamond-Drills nicht mehr pixelidentisch."
    )


def test_diamond_drill_has_facetted_shading_not_flat_fill():
    """Sanity-Check: der gemeinsame Drill ist tatsaechlich facettiert (oben
    hell, unten dunkel) und keine flache Fuellung -- sonst waere der
    Pixel-Vergleich oben trivial erfuellt (drei identische, aber falsche
    flache Rechtecke)."""
    from pysticky.ui.diamond_drill_render import draw_diamond_drill

    size = 40
    color = QColor(200, 80, 120, 255)
    image = _render_via(draw_diamond_drill, size, color)

    top = image.pixelColor(size // 2, size // 4)
    bottom = image.pixelColor(size // 2, size - size // 4)
    assert top != bottom, (
        "Oberer und unterer Facetten-Sample-Punkt sind identisch -- der "
        "Drill wird flach statt facettiert gerendert."
    )
