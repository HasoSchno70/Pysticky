# -*- coding: utf-8 -*-
"""Regressionstest (Runde 25): render_chunk_to_pixmap() (Chunk-Cache-Renderpfad
für grosse Muster, performance.py) kannte Stichtyp 11 (DIAMOND) nicht --
core/stitch_shapes.py::normalized_partial_stitch_shape(11) liefert eine leere
Punkteliste, also fiel _fill_partial_stitch_perf() auf ein flaches
painter.fillRect() zurueck statt den facettierten Drill (RenderingMixin.
_draw_diamond_drill) zu zeichnen. Diamond-Painting-Muster ab 200x200 Zellen
(automatisch Chunk-Cache-Modus) zeigten dadurch flache Quadrate statt Drills;
kleinere Muster (Direkt-Render-Pfad) waren korrekt -- Inkonsistenz je nach
Mustergroesse. Ebenso fehlte die diamond_view-Sonderbehandlung fuer FULL-
Stiche (stype=0), die der Direkt-Render-Pfad in RenderingMixin._draw_layer_cells
korrekt hat."""

import pytest
from PySide6.QtGui import QColor, QImage

pytestmark = pytest.mark.usefixtures("qtbot")


def _corner_and_center_differ(pixmap, cell_size: int) -> bool:
    """Ein facettierter Drill hat am oberen Rand ein helleres Facette als am
    unteren -- eine flache fillRect-Fuellung ist ueberall identisch (bis auf
    Antialiasing an den Raendern, daher Sampling deutlich innerhalb der Zelle)."""
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB32)
    top = image.pixelColor(cell_size // 2, cell_size // 4)
    bottom = image.pixelColor(cell_size // 2, cell_size - cell_size // 4)
    return top != bottom


def test_chunk_cache_renders_diamond_stitch_as_facetted_drill(qtbot):
    from pysticky.core import Pattern, Thread
    from pysticky.core.stitch import StitchType
    from pysticky.ui.canvas.performance import render_chunk_to_pixmap

    pattern = Pattern(name="Test", width=10, height=10, mode="diamond")
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.set_stitch(0, 0, 0, stitch_type=StitchType.DIAMOND.value)

    cell_size = 40
    pixmap = render_chunk_to_pixmap(
        pattern,
        0,
        0,
        chunk_size=10,
        cell_size=cell_size,
        empty_color=QColor("#FFFFFF"),
        show_colors=True,
        show_symbols=False,
        show_only_active=False,
        dim_other_layers=False,
        color_cache={},
        symbol_font=None,
    )

    assert _corner_and_center_differ(pixmap, cell_size), (
        "Diamond-Stich (Typ 11) wurde als flaches Rechteck statt facettierter "
        "Drill gerendert -- is_diamond()-Zweig fehlte in _fill_partial_stitch_perf()"
    )


def test_chunk_cache_renders_full_stitch_as_drill_in_diamond_view(qtbot):
    """diamond_view=True muss auch normale FULL-Stiche (Typ 0) als Drill
    zeichnen, konsistent mit RenderingMixin._draw_layer_cells."""
    from pysticky.core import Pattern, Thread
    from pysticky.ui.canvas.performance import render_chunk_to_pixmap

    pattern = Pattern(name="Test", width=10, height=10)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.set_stitch(0, 0, 0)  # stype=0 (FULL), Standard

    cell_size = 40
    pixmap = render_chunk_to_pixmap(
        pattern,
        0,
        0,
        chunk_size=10,
        cell_size=cell_size,
        empty_color=QColor("#FFFFFF"),
        show_colors=True,
        show_symbols=False,
        show_only_active=False,
        dim_other_layers=False,
        color_cache={},
        symbol_font=None,
        diamond_view=True,
    )

    assert _corner_and_center_differ(pixmap, cell_size), (
        "diamond_view=True zeichnete FULL-Stiche weiterhin als flaches "
        "Rechteck statt als Drill -- Inkonsistenz zum Direkt-Render-Pfad"
    )
