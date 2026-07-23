# -*- coding: utf-8 -*-
"""Regressionstests (HiDPI-Audit 2026-07-23): der Chunk-Cache
(`ui/canvas/performance.py`) und die Aida-Textur-Pixmap (`ui/canvas/canvas.py`)
legten ihre `QPixmap`s immer mit 1 physischem Pixel pro logischem Pixel an,
unabhängig vom tatsächlichen `devicePixelRatioF()` des Bildschirms. Auf einem
HiDPI-Display (125/150/200% Windows-Skalierung) oder nach einem Drag auf
einen anders skalierten Zweitmonitor zeichnet `QPainter.drawPixmap()`/die
Brush-Kachelung diese Pixmaps dann unscharf hochskaliert -- der Direkt-
Render-Pfad (kleine Muster, kein Chunk-Cache) ist davon nicht betroffen, weil
er ohne Zwischen-Pixmap direkt auf den Bildschirm-Painter zeichnet. Das macht
den Chunk-Cache-Pfad (aktiv ab 200x200 Zellen) auf HiDPI-Displays sichtbar
unschärfer als kleine Muster -- ein rein größenabhängiger Qualitätsunterschied,
der nichts mit dem Pattern selbst zu tun hat.

Fix: beide Pixmap-Erzeugungsstellen legen die Pixmap jetzt in physischen
Pixeln an (`round(logische_größe * dpr)`) und markieren sie per
`setDevicePixelRatio(dpr)` -- alle Zeichenoperationen bleiben unverändert in
logischen Koordinaten, weil QPainter das für ein Gerät mit gesetztem DPR
automatisch mitskaliert. Die DPR ist außerdem Teil des Chunk-Cache-Keys, damit
ein bei anderer DPR gerenderter Chunk (z.B. nach einem Monitor-Wechsel) beim
nächsten paintEvent korrekt als Cache-Miss erkannt und neu gerendert wird."""

import pytest
from PySide6.QtGui import QColor, QFont, QPixmap

from pysticky.core import Pattern, Thread
from pysticky.ui.canvas.performance import PerformanceManager, render_chunk_to_pixmap

pytestmark = pytest.mark.usefixtures("qtbot")


def _large_pattern() -> Pattern:
    """Muster über dem Chunk-Cache-Schwellwert (200x200 = 40.000 Zellen)."""
    pattern = Pattern(name="Gross", width=210, height=210)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    return pattern


def test_render_chunk_to_pixmap_is_crisp_at_hidpi_scale_factor():
    """Bei device_pixel_ratio=1.5 (150% Windows-Skalierung) muss die
    zurückgegebene Pixmap mit 1.5 physischen Pixeln pro logischem Pixel
    angelegt sein, sonst skaliert Qt sie beim Zeichnen unscharf hoch."""
    pattern = _large_pattern()
    chunk_size = 8
    cell_size = 20

    pixmap = render_chunk_to_pixmap(
        pattern,
        0,
        0,
        chunk_size,
        cell_size,
        QColor(255, 255, 255),
        True,
        True,
        False,
        False,
        {},
        QFont(),
        device_pixel_ratio=1.5,
    )

    logical_size = chunk_size * cell_size  # 160
    assert pixmap.devicePixelRatio() == 1.5, (
        "Regression: Chunk-Pixmap wurde ohne devicePixelRatio angelegt -- "
        "auf einem HiDPI-Bildschirm rendert Qt sie dadurch unscharf hochskaliert"
    )
    # Physische Pixelgröße muss der logischen Größe * DPR entsprechen.
    assert pixmap.width() == round(logical_size * 1.5)
    assert pixmap.height() == round(logical_size * 1.5)
    # Die logische (deviceIndependent) Größe muss unverändert bleiben, sonst
    # verschiebt sich die Chunk-Position beim Zeichnen (drawPixmap(x, y, pixmap)).
    assert pixmap.size().width() / pixmap.devicePixelRatio() == logical_size
    assert pixmap.size().height() / pixmap.devicePixelRatio() == logical_size


def test_render_chunk_to_pixmap_defaults_to_dpr_one():
    """Ohne expliziten Parameter (Alt-Aufrufer, z.B. bestehende Tests) muss
    sich am bisherigen Verhalten (dpr=1.0, physische == logische Pixelgröße)
    nichts ändern."""
    pattern = _large_pattern()
    pixmap = render_chunk_to_pixmap(
        pattern,
        0,
        0,
        8,
        20,
        QColor(255, 255, 255),
        True,
        True,
        False,
        False,
        {},
        QFont(),
    )
    assert pixmap.devicePixelRatio() == 1.0
    assert pixmap.width() == 160
    assert pixmap.height() == 160


def test_chunk_cache_treats_different_dpr_as_cache_miss():
    """Ein Chunk, der bei dpr=1.0 gecacht wurde, darf nicht für eine Anfrage
    mit dpr=1.5 wiederverwendet werden -- sonst bliebe eine nach einem Drag
    auf einen HiDPI-Zweitmonitor unscharfe Alt-Pixmap im Cache stecken, bis
    ein unabhängiger Trigger (Zoom, Farbwechsel, ...) sie zufällig mit
    invalidiert."""
    pattern = _large_pattern()
    mgr = PerformanceManager(canvas=None)  # type: ignore[arg-type]
    mgr.enable()

    mgr.cache_chunk(0, 0, QPixmap(1, 1), 20, True, True, False, False, device_pixel_ratio=1.0)

    # Gleiche Parameter, gleiche DPR -- Cache-Hit.
    assert (
        mgr.get_cached_chunk(0, 0, pattern, 20, True, True, False, False, device_pixel_ratio=1.0)
        is not None
    )

    # Gleiche Parameter, andere DPR (z.B. nach Monitor-Wechsel) -- Cache-Miss.
    assert (
        mgr.get_cached_chunk(0, 0, pattern, 20, True, True, False, False, device_pixel_ratio=1.5)
        is None
    )


def test_fabric_pixmap_is_crisp_at_hidpi_scale_factor(qtbot):
    """`CrossStitchCanvas._get_fabric_pixmap()` muss die Aida-Textur-Kachel
    bei devicePixelRatioF() > 1 ebenfalls in physischen Pixeln anlegen,
    sonst bleibt die als QBrush-Textur verwendete Kachel auf HiDPI-Displays
    unscharf, während der Rest des Direkt-Render-Pfads scharf bleibt."""
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas._cell_size = 20

    # devicePixelRatioF() auf dem Test-System ist praktisch immer 1.0 --
    # simuliert einen 150%-skalierten Bildschirm durch Überschreiben der
    # Instanzmethode (dieselbe Technik, mit der Qt/PySide-Code ohne echte
    # HiDPI-Hardware getestet wird).
    canvas.devicePixelRatioF = lambda: 1.5  # type: ignore[method-assign]
    canvas._invalidate_fabric_pixmap()

    pixmap = canvas._get_fabric_pixmap()

    assert pixmap.devicePixelRatio() == 1.5, (
        "Regression: Fabric-Textur-Pixmap ignoriert devicePixelRatioF() -- "
        "wird auf HiDPI-Bildschirmen unscharf hochskaliert"
    )
    assert pixmap.width() == round(20 * 1.5)
    assert pixmap.height() == round(20 * 1.5)


def test_fabric_pixmap_cache_invalidates_on_dpr_change(qtbot):
    """Ein bereits bei dpr=1.0 gecachter Fabric-Pixmap darf nach einem
    (simulierten) Wechsel auf einen HiDPI-Monitor nicht weiterverwendet
    werden -- sonst bleibt die Stoff-Textur nach einem Monitor-Drag unscharf,
    bis cell_size sich zufällig auch ändert (siehe Docstring/Cache-Key in
    `_get_fabric_pixmap`)."""
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas._cell_size = 20

    first = canvas._get_fabric_pixmap()
    assert first.devicePixelRatio() == 1.0

    canvas.devicePixelRatioF = lambda: 1.5  # type: ignore[method-assign]
    second = canvas._get_fabric_pixmap()

    assert second.devicePixelRatio() == 1.5
    assert second is not first
