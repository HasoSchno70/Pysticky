# -*- coding: utf-8 -*-
"""
Regressionstest: StitchPathOptimizer._group_by_color() summierte Stiche
naiv über alle sichtbaren Layer, statt das Komposit-Bild (oberster
sichtbarer Layer gewinnt pro Zelle) zu verwenden.

Ueberdeckt ein oberer sichtbarer Layer eine Zelle eines unteren Layers
mit einer anderen Farbe, erzeugte das alte Verhalten fuer die
verdeckte Farbe einen Phantom-Stich an genau dieser Zelle -- der
Stickplan schlug dort faelschlich vor, die verdeckte (nicht sichtbare)
Farbe zu sticken, obwohl in der Komposit-Ansicht (und damit im
tatsaechlichen Muster) die obere Farbe gewinnt. Ausserdem wurde
`total_stitches` um die Anzahl solcher Ueberdeckungen zu hoch
berechnet.
"""

from pysticky.core import Pattern
from pysticky.core.stitch_path_optimizer import OptimizationStrategy, StitchPathOptimizer
from pysticky.core.thread import Thread, ThreadColor


def _make_two_layer_pattern() -> tuple[Pattern, int, int]:
    """3x3-Block Rot auf dem unteren Layer, ein Blau-Stich auf dem
    oberen (sichtbaren) Layer überdeckt die Zelle (1, 1)."""
    pattern = Pattern(name="Test", width=10, height=10)
    bottom = pattern.layer_stack[0]
    top = pattern.layer_stack.add_layer("Top")

    red = pattern.add_color(Thread(name="Rot", color=ThreadColor(255, 0, 0)))
    blue = pattern.add_color(Thread(name="Blau", color=ThreadColor(0, 0, 255)))

    for y in range(3):
        for x in range(3):
            bottom.set_stitch(x, y, red)

    top.set_stitch(1, 1, blue)

    return pattern, red, blue


def test_overlapping_visible_layers_use_composite_not_union():
    """Die überdeckte Zelle darf NICHT als Stich der unteren (verdeckten)
    Farbe im optimierten Pfad auftauchen."""
    pattern, red, blue = _make_two_layer_pattern()

    optimizer = StitchPathOptimizer(pattern)
    result = optimizer.optimize(OptimizationStrategy.ROW_BY_ROW)

    paths_by_color = {p.color_index: p for p in result.color_paths}

    red_coords = {(s.x, s.y) for s in paths_by_color[red].steps}
    blue_coords = {(s.x, s.y) for s in paths_by_color[blue].steps}

    # Composite: 8 sichtbare rote Zellen (3x3 minus die überdeckte (1,1)),
    # 1 sichtbare blaue Zelle bei (1,1).
    assert red_coords == {(0, 0), (1, 0), (2, 0), (0, 1), (2, 1), (0, 2), (1, 2), (2, 2)}
    assert blue_coords == {(1, 1)}

    # Keine Zelle darf in mehr als einer Farbe auftauchen.
    assert red_coords.isdisjoint(blue_coords)

    # Gesamtanzahl entspricht der tatsächlichen Komposit-Zellenzahl (9),
    # nicht der Summe aller Layer-Stiche (9 + 1 = 10).
    assert result.total_stitches == 9


def test_invisible_layer_is_fully_excluded():
    """Ein unsichtbarer oberer Layer darf weder seine eigenen Stiche
    beitragen noch die darunterliegenden verdecken."""
    pattern, red, blue = _make_two_layer_pattern()
    pattern.layer_stack[1].visible = False

    optimizer = StitchPathOptimizer(pattern)
    result = optimizer.optimize(OptimizationStrategy.ROW_BY_ROW)

    paths_by_color = {p.color_index: p for p in result.color_paths}

    # Blau ist unsichtbar -> kein Pfad für diese Farbe.
    assert blue not in paths_by_color

    # Rot ist wieder vollständig sichtbar (3x3 = 9 Zellen).
    red_coords = {(s.x, s.y) for s in paths_by_color[red].steps}
    assert len(red_coords) == 9
    assert result.total_stitches == 9
