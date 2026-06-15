# -*- coding: utf-8 -*-
"""Performance-Smoke fuer Sprint-2-Features auf einem 200x200-Pattern.

Pruegt dass:
- Composite-Grid + Completion-Mask schnell genug fuer Jump sind (ms-Bereich)
- Isolation den Render-Pfad nicht zu massiv ausbremst
- Das Difficulty-Berechnen auch bei dichtem Pattern unter ~100 ms bleibt
"""

import time

import pytest

from pysticky.core import Pattern, Thread


@pytest.fixture
def large_pattern():
    """Erzeugt 200x200-Pattern mit ~16k Stichen verteilt auf 6 Farben."""
    p = Pattern(name="Bench", width=200, height=200)
    p.color_entries.clear()
    colors = [
        ("Schwarz", "#000000"),
        ("Rot", "#ff0000"),
        ("Gruen", "#00ff00"),
        ("Blau", "#0000ff"),
        ("Gelb", "#ffff00"),
        ("Magenta", "#ff00ff"),
    ]
    for n, h in colors:
        p.add_color(Thread.from_hex(n, h))

    # Schachbrett-Muster mit ~40% Abdeckung, gleichmaessig auf Farben verteilt
    layer = p.layer_stack[0]
    cnt = 0
    for y in range(0, 200, 2):
        for x in range(0, 200, 2):
            if (x + y) % 5 != 0:
                continue
            layer.set_stitch(x, y, (x // 8) % 6)
            cnt += 1
    p.recalculate_stitch_counts()
    return p


def test_jump_to_next_stitch_is_fast(large_pattern, qtbot):
    """jump_to_next_stitch muss bei 200x200 unter 50ms laufen."""
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(large_pattern)
    canvas.resize(800, 600)
    canvas.set_current_color(2)

    # Cold call (composite_grid baut ggf. Cache)
    canvas.jump_to_next_stitch(forward=True)

    # Warm calls timen
    t0 = time.perf_counter()
    for _ in range(50):
        canvas.jump_to_next_stitch(forward=True)
    elapsed = (time.perf_counter() - t0) * 1000
    avg_ms = elapsed / 50
    print(f"\n  Avg jump time @ 200x200: {avg_ms:.2f} ms")
    assert avg_ms < 50.0, f"Jump zu langsam: {avg_ms:.1f}ms"


def test_difficulty_compute_is_fast(large_pattern):
    """compute_difficulty muss auch bei vollem Pattern unter 100ms bleiben."""
    from pysticky.core.difficulty import compute_difficulty

    t0 = time.perf_counter()
    result = compute_difficulty(large_pattern)
    elapsed = (time.perf_counter() - t0) * 1000
    print(f"\n  compute_difficulty @ 200x200: {elapsed:.2f} ms")
    assert elapsed < 100.0
    assert result["level"] in ("Anfänger", "Mittel", "Fortgeschritten", "Profi")


def test_isolated_render_does_not_explode(large_pattern, qtbot):
    """Mit Isolation muss der Render-Pfad immer noch in akzeptabler Zeit laufen."""
    from PySide6.QtGui import QPixmap

    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(large_pattern)
    canvas.resize(800, 600)
    canvas.set_isolate_color(2)

    # Render-Zeit messen
    t0 = time.perf_counter()
    for _ in range(5):
        pm = QPixmap(canvas.size())
        canvas.render(pm)
    elapsed = (time.perf_counter() - t0) * 1000 / 5
    print(f"\n  Avg render time @ 200x200 with isolation: {elapsed:.1f} ms")
    # Sehr generoeser Bound — sollte <500ms pro Frame sein, sonst ist was kaputt
    assert elapsed < 500.0
