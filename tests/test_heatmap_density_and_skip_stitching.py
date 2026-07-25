# -*- coding: utf-8 -*-
"""
Regressionstests (Runde 83): Zwei Bugs bei der Heatmap-Berechnung
(ui/dialogs/heatmap_dialog.py), gefunden durch gezielte Randfall-Suche.

Bug 1 -- Randblock-Normalisierung: Geht block_size nicht glatt in
pattern.width/height auf, sind die Blöcke am rechten/unteren Rand kleiner
als block_size x block_size. _density_heatmap() normalisierte die
Stichzahl pro Block bislang gegen den GLOBALEN max_count (die absolute
Stichzahl des dichtesten Blocks), ohne die unterschiedliche Blockfläche zu
berücksichtigen. Ein voll gestickter Randblock erschien dadurch dunkler
(blauer) als ein voll gestickter Innenblock, obwohl beide zu 100% ihrer
jeweiligen Fläche gefüllt waren.

Bug 2 -- skip_stitching-Farben: Farben mit ColorEntry.skip_stitching=True
(z.B. eine Stofffarbe, die absichtlich nicht gestickt wird) flossen in die
Dichte- und Farbenvielfalt-Achsen der Heatmap ein, obwohl an diesen Zellen
tatsächlich kein Stich gesetzt wird -- inkonsistent zur bestehenden
skip_stitching-Behandlung in core/difficulty.py.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pysticky.core import Pattern, Thread
from pysticky.ui.dialogs.heatmap_dialog import (
    _color_variety_heatmap,
    _composite_color_grid,
    _density_heatmap,
)


def test_fully_stitched_edge_block_has_full_density_despite_smaller_area():
    """27x23-Pattern, block_size=10 -> Randblöcke sind nur 7x3 statt 10x10.
    Ein komplett vollgestochenes Pattern muss in JEDEM Block (auch am Rand)
    Dichte 1.0 zeigen, weil jeder Block zu 100% seiner eigenen Fläche
    gefüllt ist."""
    p = Pattern(name="EdgeCase", width=27, height=23)
    p.color_entries.clear()
    p.add_color(Thread.from_hex("Rot", "#FF0000"))
    for y in range(23):
        for x in range(27):
            p.set_stitch(x, y, 0)

    comp = _composite_color_grid(p)
    values = _density_heatmap(comp, block_size=10)

    assert values.shape == (3, 3)
    interior = values[0, 0]  # 10x10, voll gestochen
    edge_col = values[0, 2]  # 10x7, voll gestochen
    edge_row = values[2, 0]  # 3x10, voll gestochen
    corner = values[2, 2]  # 3x7, voll gestochen
    assert interior == 1.0
    assert edge_col == 1.0, f"Randblock (Spalte) zeigt {edge_col} statt 1.0"
    assert edge_row == 1.0, f"Randblock (Zeile) zeigt {edge_row} statt 1.0"
    assert corner == 1.0, f"Eckblock zeigt {corner} statt 1.0"


def test_density_still_relative_to_busiest_block_for_uniform_block_sizes():
    """Regressionsschutz fuer die bestehende (gewollte) Relativ-Skalierung:
    bei gleich grossen Bloecken muss der dichteste Block weiterhin auf 1.0
    normalisiert werden und andere Bloecke proportional dazu skaliert sein."""
    import numpy as np

    comp = np.full((4, 8), -1, dtype=np.int32)
    comp[0:2, 0:2] = 0  # linker Block: 4 Stiche
    comp[0, 4] = 0  # rechter Block: 1 Stich
    out = _density_heatmap(comp, 4)
    assert out.shape == (1, 2)
    assert float(out[0, 0]) == 1.0
    assert float(out[0, 1]) == 0.25


def test_skip_stitching_color_treated_as_empty_in_density_and_variety():
    """Ein Block, der ausschliesslich mit einer skip_stitching-Farbe (z.B.
    Stofffarbe) gefuellt ist, darf weder Dichte noch Farbenvielfalt zeigen,
    weil dort tatsaechlich nichts gestickt wird."""
    p = Pattern(name="SkipTest", width=4, height=4)
    p.color_entries.clear()
    p.add_color(Thread.from_hex("Rot", "#FF0000"))
    p.add_color(Thread.from_hex("Stoff", "#FFFFFF"))
    p.color_entries[1].skip_stitching = True
    for x in range(4):
        for y in range(4):
            p.set_stitch(x, y, 1)  # nur die skip_stitching-Farbe

    comp = _composite_color_grid(p)
    density = _density_heatmap(comp, block_size=8)
    variety = _color_variety_heatmap(comp, block_size=8)

    assert density[0, 0] == 0.0, "skip_stitching-Farbe zaehlt faelschlich als Dichte"
    assert variety[0, 0] == 0.0, "skip_stitching-Farbe zaehlt faelschlich als Farbenvielfalt"


def test_skip_stitching_color_excluded_but_real_stitches_still_counted():
    """Mischblock aus einer echten Farbe und einer skip_stitching-Farbe:
    nur die echte Farbe darf in Dichte/Farbenvielfalt einfliessen."""
    p = Pattern(name="MixedSkip", width=4, height=4)
    p.color_entries.clear()
    p.add_color(Thread.from_hex("Rot", "#FF0000"))
    p.add_color(Thread.from_hex("Stoff", "#FFFFFF"))
    p.color_entries[1].skip_stitching = True
    # Halb echte Farbe, halb skip_stitching-Farbe.
    for x in range(4):
        p.set_stitch(x, 0, 0)
        p.set_stitch(x, 1, 1)

    comp = _composite_color_grid(p)
    density = _density_heatmap(comp, block_size=8)
    variety = _color_variety_heatmap(comp, block_size=8)

    # Nur 4 von 16 Zellen sind "echt" gestickt -> einziger Block, relativ
    # zum dichtesten (= einzigen) Block normalisiert -> 1.0.
    assert density[0, 0] == 1.0
    # Nur eine tatsaechlich gestickte Farbe (Rot) -> 1.0.
    assert variety[0, 0] == 1.0
