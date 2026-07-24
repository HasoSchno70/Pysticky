# -*- coding: utf-8 -*-
"""Regressionstest: MinimapWidget._rebuild_cache() darf bei einem grossen,
vollstaendig gefuellten Muster keinen spuerbaren UI-Freeze mehr verursachen.

_rebuild_cache() baute das Minimap-Bild frueher ueber einen verschachtelten
reinen Python-Loop ueber JEDEN Stich des Musters (pattern.get_stitch(x, y) +
get_color_entry() + QImage.setPixel() pro Zielpixel). Fuer ein nahezu maximal
grosses, komplett gefuelltes Muster (MAX_PATTERN_SIZE, siehe core/constants.py)
dauerte ein einzelner Rebuild empirisch ~1.5s -- bei jedem Undo/Redo, Farbe-
Ersetzen, Fuellen oder Datei-Laden (ausgeloest ueber den in Runde 63
eingefuehrten Debounce in undo_handlers.py::_schedule_minimap_refresh, der nur
verhindert, dass mehrere Rebuilds hintereinander laufen -- der einzelne Rebuild
selbst blieb langsam).

Der Fix ersetzt den Pro-Stich-Loop durch numpy-Vektorisierung: composite-Grid
als Array holen, per Nearest-Neighbor-Indexing direkt auf Zielaufloesung
downsamplen (statt jeden Stich einzeln zu besuchen) und ueber eine Farb-LUT in
einen zusammenhaengenden RGB888-Puffer schreiben.
"""

import time

import pytest

from pysticky.core import Pattern, Thread
from pysticky.core.constants import MAX_PATTERN_SIZE


@pytest.fixture
def full_max_pattern():
    """Erzeugt ein MAX_PATTERN_SIZE x MAX_PATTERN_SIZE-Muster, komplett mit
    einer Farbe gefuellt (numpy-Bulk-Fill statt einer set_stitch()-Schleife
    pro Zelle, damit das Fixture selbst schnell bleibt)."""
    p = Pattern(name="Perf", width=MAX_PATTERN_SIZE, height=MAX_PATTERN_SIZE)
    p.color_entries.clear()
    p.add_color(Thread.from_hex("Rot", "#FF0000"))
    p.layer_stack[0].grid[:, :] = 0
    return p


def test_minimap_rebuild_cache_is_fast_for_full_max_pattern(full_max_pattern, qtbot):
    from pysticky.ui.widgets.minimap import MinimapWidget

    widget = MinimapWidget()
    qtbot.addWidget(widget)
    widget.resize(220, 180)

    start = time.perf_counter()
    widget.set_pattern(full_max_pattern)
    elapsed = time.perf_counter() - start

    # Vor dem Fix lag ein einzelner Rebuild bei ~1.5s. Grosszuegige Schranke
    # gegen CI-Schwankungen, aber weit unter der alten Groessenordnung.
    assert elapsed < 0.5, f"Minimap-Rebuild zu langsam: {elapsed:.2f}s"

    assert widget._cached_image is not None
    assert not widget._cached_image.isNull()


def test_minimap_rebuild_cache_renders_correct_colors(qtbot):
    """Vektorisierter Pfad muss weiterhin die richtigen Farben an den
    richtigen Stellen zeichnen (nicht nur schnell sein)."""
    from pysticky.ui.widgets.minimap import MinimapWidget

    pattern = Pattern(name="Colors", width=4, height=4)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.add_color(Thread.from_hex("Blau", "#0000FF"))
    # Linke Haelfte rot, rechte Haelfte blau, unterste Zeile leer.
    for y in range(3):
        for x in range(4):
            pattern.set_stitch(x, y, 0 if x < 2 else 1)

    widget = MinimapWidget()
    qtbot.addWidget(widget)
    widget.resize(220, 180)
    widget.set_pattern(pattern)

    image = widget._cached_image
    assert image is not None

    # Linke obere Ecke muss rot, rechte obere Ecke muss blau sein.
    top_left = image.pixelColor(2, 2)
    top_right = image.pixelColor(image.width() - 3, 2)
    assert top_left.red() > top_left.blue()
    assert top_right.blue() > top_right.red()

    # Unterste Zeile (keine Stiche) muss der Hintergrundfarbe entsprechen.
    bottom = image.pixelColor(image.width() // 2, image.height() - 1)
    assert (bottom.red(), bottom.green(), bottom.blue()) == (250, 250, 245)
