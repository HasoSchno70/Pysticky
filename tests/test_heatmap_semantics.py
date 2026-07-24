# -*- coding: utf-8 -*-
"""
Regressionstests (Runde 63): Fachliche Korrektheit der Heatmap-Berechnung.

Diese Tests pruefen ECHTES End-to-End-Verhalten des HeatmapDialog (nicht nur
die reinen Helferfunktionen wie in test_heatmap.py) fuer die klassischen
Heatmap-Grenzfaelle: leeres Muster, 1x1-Muster, mehrschichtige Muster
(Composite ueber ALLE sichtbaren Layer, nicht nur den aktiven Layer) und
Diamond-Painting-Modus. Ausserdem eine Pixel-genaue Kontrolle, dass die
gerenderte Farbe an einer Position exakt dem berechneten Intensitaetswert
entspricht (gleiche Fehlerklasse wie der bereits gefixte
Schleifenvariablen-Bug in _intensity_to_rgb()/_heatmap_to_qimage()).

Ergebnis der Runde-63-Untersuchung: Alle hier geprueften Faelle verhalten
sich bereits korrekt (kein Bug gefunden) -- diese Tests fixieren das
korrekte Verhalten als Regressionsschutz.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

from pysticky.core import Pattern, Thread

pytestmark = pytest.mark.usefixtures("qtbot")


def test_empty_pattern_renders_without_crash_and_zero_active_blocks(qtbot):
    """0 Stiche: keine Division durch Null bei der Normalisierung, Summary
    zeigt 0 aktive Bloecke."""
    from pysticky.ui.dialogs.heatmap_dialog import HeatmapDialog

    p = Pattern(name="Leer", width=20, height=20)
    dlg = HeatmapDialog(p)
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.waitExposed(dlg)

    assert "0 aktive Blöcke" in dlg._summary_label.text()
    pm = dlg._image_label.pixmap()
    assert pm is not None and not pm.isNull()


def test_1x1_pattern_renders_without_crash(qtbot):
    """Ein einziges Pixel/Block darf nicht zu einem Crash bei der
    Block-Aufteilung oder dem QImage-Rendering fuehren."""
    from pysticky.ui.dialogs.heatmap_dialog import HeatmapDialog

    p = Pattern(name="Winzig", width=1, height=1)
    p.color_entries.clear()
    p.add_color(Thread.from_hex("Rot", "#FF0000"))
    p.set_stitch(0, 0, 0)

    dlg = HeatmapDialog(p)
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.waitExposed(dlg)

    assert "1×1" in dlg._summary_label.text() or "1x1" in dlg._summary_label.text()
    assert "1 aktive Blöcke" in dlg._summary_label.text()


def test_multilayer_composite_aggregates_all_visible_layers(qtbot):
    """Die Heatmap muss ueber ALLE sichtbaren Layer aggregieren, nicht nur
    ueber den aktiven/ersten Layer -- sonst waere das Bild bei einem
    mehrschichtigen Muster irrefuehrend unvollstaendig."""
    from pysticky.ui.dialogs.heatmap_dialog import _composite_color_grid

    p = Pattern(name="MultiLayer", width=10, height=10)
    p.color_entries.clear()
    p.add_color(Thread.from_hex("Rot", "#FF0000"))
    p.add_color(Thread.from_hex("Blau", "#0000FF"))

    base_layer = p.layer_stack.layers[0]
    for x in range(5):
        base_layer.set_stitch(x, 0, 0)

    top_layer = p.layer_stack.add_layer("Oben")
    for x in range(5, 10):
        top_layer.set_stitch(x, 0, 1)

    comp = _composite_color_grid(p)
    # Beide Haelften der Zeile 0 muessen im Composite auftauchen, obwohl die
    # Stiche auf zwei verschiedenen Layern liegen.
    assert (comp[0] != -1).sum() == 10

    # Wird der obere Layer unsichtbar geschaltet, darf er nicht mehr
    # mitgezaehlt werden.
    top_layer.visible = False
    comp_hidden = _composite_color_grid(p)
    assert (comp_hidden[0] != -1).sum() == 5


def test_diamond_mode_pattern_renders_without_crash(qtbot):
    """Diamond-Painting-Muster nutzen dieselbe Farbindex-Grid-Struktur wie
    Kreuzstich-Muster -- die Heatmap-Berechnung muss auch hier ohne Crash
    ein sinnvolles Ergebnis liefern."""
    from pysticky.ui.dialogs.heatmap_dialog import HeatmapDialog

    p = Pattern(name="DP", width=12, height=12, mode="diamond")
    p.color_entries.clear()
    p.add_color(Thread.from_hex("Rot", "#FF0000"), is_diamond=True)
    p.add_color(Thread.from_hex("Blau", "#0000FF"), is_diamond=True)
    for x in range(12):
        for y in range(12):
            p.set_stitch(x, y, (x + y) % 2)

    dlg = HeatmapDialog(p)
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.waitExposed(dlg)

    # Default-Blockgroesse 8 -> ceil(12/8) = 2 Bloecke pro Achse, alle 4
    # Bloecke sind belegt (Muster ist vollstaendig gefuellt).
    assert "2×2" in dlg._summary_label.text()
    assert "4 aktive Blöcke" in dlg._summary_label.text()
    pm = dlg._image_label.pixmap()
    assert pm is not None and not pm.isNull()


def test_rendered_pixel_matches_computed_intensity_color(qtbot):
    """Pixel-genauer Vergleich: die tatsaechlich im QImage gerenderte Farbe
    an einer Blockposition muss exakt der von _intensity_to_rgb() fuer den
    zugehoerigen normalisierten Wert berechneten Farbe entsprechen (gleiche
    Fehlerklasse wie der frueher gefixte Schleifenvariablen-Bug an dieser
    Stelle -- ein Off-by-One bei Segment- oder Bucket-Grenzen wuerde hier
    auffallen)."""
    from pysticky.ui.dialogs.heatmap_dialog import _heatmap_to_qimage, _intensity_to_rgb

    values = np.array([[0.0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9, 1.0]], dtype=np.float32)
    img = _heatmap_to_qimage(values, cell_px=4)
    for i, v in enumerate(values[0]):
        expected = _intensity_to_rgb(float(v))
        px = img.pixel(i * 4, 0)
        actual = ((px >> 16) & 0xFF, (px >> 8) & 0xFF, px & 0xFF)
        assert actual == expected, f"Intensitaet {v}: erwartet {expected}, gerendert {actual}"
