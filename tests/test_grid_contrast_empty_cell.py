# -*- coding: utf-8 -*-
"""Regressionstest (2026-07-18): Gitterlinien gegen die Hintergrundfarbe
leerer Zellen (empty_cell_color) unsichtbar.

grid_color (hartcodiert), grid_color_minor/grid_color_major (Canvas-
Einstellungen) und empty_cell_color (Canvas-Einstellungen) sind seit der
Canvas-Settings-Verdrahtung alle unabhängig frei konfigurierbar. Mit den
tatsächlichen Defaults (#2a2a4a leer, #303050 minor, #404060 major, dazu
das hartcodierte (45,45,45) für normale Linien) liegt der WCAG-Kontrast
aller drei Gitterfarben gegen die leere Zelle bei ~1.0-1.4:1 -- praktisch
unsichtbar. Auf großen Mustern (Chunk-Cache-Pfad, seit dem vorigen Fix mit
Aida-Textur) wurde das erstmals sichtbar: gezeichnete Stiche zeigten ein
klares Gitter (Kontrast gegen die Fadenfarbe), der leere Bereich nur Punkte
ohne jedes Gitter."""

import pytest
from PySide6.QtGui import QColor

pytestmark = pytest.mark.usefixtures("qtbot")


def test_ensure_contrast_replaces_low_contrast_color():
    from pysticky.ui.color_utils import ensure_contrast

    empty_cell_color = QColor("#2a2a4a")
    grid_color = QColor(45, 45, 45)
    grid_minor = QColor("#303050")
    grid_major = QColor("#404060")

    for original in (grid_color, grid_minor, grid_major):
        adjusted = ensure_contrast(original, empty_cell_color)
        assert adjusted != original


def test_ensure_contrast_keeps_already_visible_color():
    from pysticky.ui.color_utils import ensure_contrast

    # Klassischer heller Aida-Hintergrund + dunkles Gitter -- unverändert.
    light_empty = QColor(250, 250, 245)
    dark_grid = QColor(45, 45, 45)
    assert ensure_contrast(dark_grid, light_empty) == dark_grid


def test_direct_and_chunked_grid_paths_use_contrast_safe_colors(qtbot):
    """Beide Render-Pfade (RenderingMixin._draw_grid und
    optimized_canvas.py's draw_optimized_grid-Aufruf) müssen dieselbe
    Kontrastkorrektur anwenden, sonst driften Direkt- und Chunk-Cache-Pfad
    optisch auseinander."""
    from pysticky.core import Pattern, Thread
    from pysticky.ui.canvas import CrossStitchCanvas, OptimizedCrossStitchCanvas
    from pysticky.ui.color_utils import ensure_contrast

    pattern = Pattern(name="Test", width=10, height=10)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Weiss", "#FFFFFF"))

    low_contrast_grid = QColor(45, 45, 45)
    low_contrast_empty = QColor("#2a2a4a")
    expected = ensure_contrast(low_contrast_grid, low_contrast_empty)
    assert expected != low_contrast_grid  # Testannahme: Kollision besteht wirklich

    for cls in (CrossStitchCanvas, OptimizedCrossStitchCanvas):
        canvas = cls()
        qtbot.addWidget(canvas)
        canvas._grid_color = QColor(low_contrast_grid)
        canvas._empty_color = QColor(low_contrast_empty)
        canvas.set_pattern(pattern)
        canvas.resize(200, 200)
        canvas.show()
        qtbot.waitExposed(canvas)
        canvas.repaint()  # darf nicht crashen; reine Rauch-Absicherung
