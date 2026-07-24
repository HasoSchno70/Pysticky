# -*- coding: utf-8 -*-
"""Regressionstests fuer Fuellwerkzeug-Grenzfaelle (Clean-Code-Audit Runde 53).

Untersucht wurden: Fuellen sehr grosser zusammenhaengender Flaechen (Stack-
Overflow-Risiko bei rekursiver Implementierung?), No-Op bei bereits
vorhandener Zielfarbe, leere Zellen (None) in Kombination mit Farbtoleranz,
`fill_diagonal`-Konnektivitaet und Undo-Atomaritaet bei grossflaechigem
Fuellen. Ergebnis: KEIN echter Bug gefunden -- alle Faelle waren bereits
korrekt implementiert (iterative deque-BFS statt Rekursion, frueher Return
bei Farbgleichheit, `matches()` behandelt `None` als eigene Kategorie ohne
Delta-E-Berechnung, batch_started/batch_ended kapseln den gesamten
Fuellvorgang in EINE Undo-Aktion). Diese Tests fixieren das Verhalten als
Regressionsschutz, da vorher keine davon existierten."""

import random

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent

from pysticky.core import Pattern, Thread
from pysticky.ui.tools.base_tool import ToolContext
from pysticky.ui.tools.fill_tool import FillTool

pytestmark = pytest.mark.usefixtures("qtbot")


def _naive_flood_fill(layer, width, height, start_x, start_y, diagonal=False):
    """Referenz-Flood-Fill (einfacher DFS mit Liste als Stack) zum Abgleich
    gegen den optimierten Scanline-/Diagonal-Algorithmus."""
    target = layer.get_stitch(start_x, start_y)
    visited = set()
    stack = [(start_x, start_y)]
    if diagonal:
        neighbors = [
            (dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if not (dx == 0 and dy == 0)
        ]
    else:
        neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    while stack:
        x, y = stack.pop()
        if (x, y) in visited:
            continue
        if not (0 <= x < width and 0 <= y < height):
            continue
        if layer.get_stitch(x, y) != target:
            continue
        visited.add((x, y))
        for dx, dy in neighbors:
            nx, ny = x + dx, y + dy
            if (nx, ny) not in visited:
                stack.append((nx, ny))
    return visited


def _make_ctx(pattern, x, y, color_index):
    return ToolContext(
        canvas=None,
        pattern=pattern,
        current_color_index=color_index,
        grid_x=x,
        grid_y=y,
        screen_x=0,
        screen_y=0,
        cell_size=20,
        offset_x=0,
        offset_y=0,
    )


def test_scanline_fill_matches_naive_4_connected_fuzz():
    """200 zufaellige kleine Muster: der Scanline-Algorithmus (4-fach
    verbunden) muss exakt dieselbe Zellmenge liefern wie eine einfache
    DFS-Referenzimplementierung -- deckt insbesondere Randfaelle am
    Musterrand ab (Startpositionen werden zufaellig ueber die GESAMTE
    Flaeche inkl. Ecken/Kanten gewaehlt)."""
    random.seed(42)
    for _trial in range(200):
        w = random.randint(1, 15)
        h = random.randint(1, 15)
        pattern = Pattern(width=w, height=h)
        pattern.color_entries.clear()
        idx_a = pattern.add_color(Thread.from_hex("A", "#FF0000"))
        idx_b = pattern.add_color(Thread.from_hex("B", "#00FF00"))
        idx_new = pattern.add_color(Thread.from_hex("Neu", "#0000FF"))
        for y in range(h):
            for x in range(w):
                pattern.set_stitch(x, y, idx_a if random.random() < 0.5 else idx_b)
        sx, sy = random.randint(0, w - 1), random.randint(0, h - 1)
        layer = pattern.active_layer
        if layer.get_stitch(sx, sy) == idx_new:
            continue
        expected = _naive_flood_fill(layer, w, h, sx, sy, diagonal=False)
        tool = FillTool()
        changes = tool._scanline_fill(_make_ctx(pattern, sx, sy, idx_new), sx, sy, idx_new)
        got = {(x, y) for x, y, _ in changes}
        assert got == expected


def test_diagonal_fill_matches_naive_8_connected_fuzz():
    """Analog, aber fuer den 8-fach verbundenen `fill_diagonal`-Pfad."""
    random.seed(11)
    for _trial in range(200):
        w = random.randint(1, 12)
        h = random.randint(1, 12)
        pattern = Pattern(width=w, height=h)
        pattern.color_entries.clear()
        idx_a = pattern.add_color(Thread.from_hex("A", "#FF0000"))
        idx_b = pattern.add_color(Thread.from_hex("B", "#00FF00"))
        idx_new = pattern.add_color(Thread.from_hex("Neu", "#0000FF"))
        for y in range(h):
            for x in range(w):
                pattern.set_stitch(x, y, idx_a if random.random() < 0.5 else idx_b)
        sx, sy = random.randint(0, w - 1), random.randint(0, h - 1)
        layer = pattern.active_layer
        if layer.get_stitch(sx, sy) == idx_new:
            continue
        expected = _naive_flood_fill(layer, w, h, sx, sy, diagonal=True)
        tool = FillTool()
        changes = tool._diagonal_fill(_make_ctx(pattern, sx, sy, idx_new), sx, sy, idx_new)
        got = {(x, y) for x, y, _ in changes}
        assert got == expected


def test_empty_cell_with_tolerance_spreads_only_to_other_empty_cells():
    """Start-Zelle ist leer (kein Stich gesetzt) und die Toleranz ist aktiv:
    `matches()` darf keine Delta-E-Distanz zu einer nicht existierenden
    Farbe berechnen (moeglicher Crash), sondern muss "leer" als eigene
    Kategorie behandeln, die nur zu anderen leeren Zellen passt."""
    pattern = Pattern(width=3, height=1)
    pattern.color_entries.clear()
    idx_red = pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    idx_new = pattern.add_color(Thread.from_hex("Neu", "#0000FF"))
    # (0,0) und (2,0) bleiben leer, (1,0) ist rot.
    pattern.set_stitch(1, 0, idx_red)

    tool = FillTool()
    ctx = _make_ctx(pattern, 0, 0, idx_new)
    changes = tool._scanline_fill(ctx, 0, 0, idx_new, max_delta_e=50.0)

    got = {(x, y) for x, y, _ in changes}
    assert got == {(0, 0)}, "Toleranz darf leere Zelle nicht mit der roten Nachbarzelle fuellen"


def test_stack_overflow_free_on_large_fully_connected_pattern():
    """Fuellen einer grossen vollstaendig zusammenhaengenden Flaeche (150x150
    = 22500 Zellen) darf nicht rekursiv implementiert sein -- mit stark
    reduziertem Rekursionslimit provoziert ein rekursiver Algorithmus einen
    RecursionError, eine iterative deque-BFS/Scanline-Implementierung bleibt
    unbeeindruckt."""
    import sys

    pattern = Pattern(width=150, height=150)
    pattern.color_entries.clear()
    idx_a = pattern.add_color(Thread.from_hex("A", "#FF0000"))
    idx_new = pattern.add_color(Thread.from_hex("Neu", "#0000FF"))
    for y in range(150):
        for x in range(150):
            pattern.set_stitch(x, y, idx_a)

    tool = FillTool()
    ctx = _make_ctx(pattern, 0, 0, idx_new)

    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(80)
    try:
        changes = tool._scanline_fill(ctx, 0, 0, idx_new)
    finally:
        sys.setrecursionlimit(old_limit)

    assert len(changes) == 150 * 150


@pytest.fixture
def main_window(qtbot):
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    return w


def _press(canvas, x, y):
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(event)


def _release(canvas, x, y):
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseReleaseEvent(event)


def _setup_filled_pattern(main_window, width, height):
    from pysticky.ui.tools.tool_enum import Tool

    w = main_window
    pattern = Pattern(name="Test", width=width, height=height)
    pattern.color_entries.clear()
    idx_a = pattern.add_color(Thread.from_hex("A", "#FF0000"))
    idx_b = pattern.add_color(Thread.from_hex("B", "#00FF00"))
    for y in range(height):
        for x in range(width):
            pattern.set_stitch(x, y, idx_a)
    w.set_pattern(pattern)

    canvas = w.canvas
    canvas._cell_size = 20
    canvas._offset_x = 0
    canvas._offset_y = 0
    w.tool_bar.select_tool(Tool.FILL)
    return w, pattern, canvas, idx_a, idx_b


def test_fill_large_region_is_one_undo_action(main_window):
    """Ein Flood-Fill ueber eine grosse zusammenhaengende Flaeche (30x30 =
    900 Zellen) muss GENAU EINE Undo-Aktion erzeugen -- sonst waere ein
    einzelnes Rueckgaengig nach einem Fuellvorgang unbrauchbar."""
    w, pattern, canvas, idx_a, idx_b = _setup_filled_pattern(main_window, width=30, height=30)
    w.canvas._current_color_index = idx_b

    before = w.undo_manager.undo_count
    _press(canvas, 5 * 20 + 5, 5 * 20 + 5)
    _release(canvas, 5 * 20 + 5, 5 * 20 + 5)

    layer = pattern.active_layer
    filled = [(x, y) for x in range(30) for y in range(30) if layer.get_stitch(x, y) == idx_b]
    assert len(filled) == 900

    assert w.undo_manager.undo_count == before + 1, (
        "Flood-Fill muss EINE Undo-Aktion erzeugen, nicht eine pro Zelle"
    )

    w.undo_manager.undo()
    filled_after_undo = [
        (x, y) for x in range(30) for y in range(30) if layer.get_stitch(x, y) == idx_b
    ]
    assert filled_after_undo == [], "Ein einzelnes Undo muss den GESAMTEN Fill rueckgaengig machen"


def test_fill_same_color_no_op_creates_no_undo_entry(main_window):
    """Klick mit der bereits vorhandenen Farbe darf keinen (leeren) Undo-
    Eintrag erzeugen."""
    w, pattern, canvas, idx_a, idx_b = _setup_filled_pattern(main_window, width=10, height=10)
    w.canvas._current_color_index = idx_a  # bereits vorhandene Farbe

    before = w.undo_manager.undo_count
    _press(canvas, 5 * 20 + 5, 5 * 20 + 5)
    _release(canvas, 5 * 20 + 5, 5 * 20 + 5)

    assert w.undo_manager.undo_count == before, (
        "No-Op-Fill (Zielfarbe == neue Farbe) darf keinen Undo-Eintrag erzeugen"
    )
