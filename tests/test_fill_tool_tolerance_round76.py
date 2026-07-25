# -*- coding: utf-8 -*-
"""Regressionstests fuer Fuell-Werkzeug/Flood-Fill-Farbtoleranz (Clean-Code-
Audit Runde 76).

Untersucht wurden (siehe Runde-76-Audit-Auftrag): Konsistenz zwischen
Scanline- und Diagonal-Fill bei aktiver Toleranz auf rein orthogonal
verbundenen Flaechen, Toleranz-Randfaelle (0% vs. 100% = max. Delta-E 50)
sowohl mit synthetischen als auch mit der echten DMC-Palette, leere Zellen
in Kombination mit Toleranz, sehr grosse leere Flaechen (Performance/
Vollstaendigkeit), sowie `stitch_count`-Bookkeeping nach einem echten
Fuellvorgang mit Toleranz durch die volle MainWindow-Signal-Pipeline.

Ergebnis: KEIN neuer Bug gefunden. Scanline- und Diagonal-Algorithmus nutzen
dieselbe `matches()`-Logik und liefern auf rein orthogonal verbundenen
Flaechen identische Ergebnisse; die Prozent-zu-Delta-E-Umrechnung
(`_MAX_TOLERANCE_DELTA_E * (tolerance_pct / 100)`) fuellt bei 100% Toleranz
NICHT die gesamte (farblich diverse) Palette; leere Zellen bleiben strikt
auf andere leere Zellen beschraenkt; `stitch_count` bleibt nach einem
Toleranz-Fill fuer ALLE Farben (auch die nicht beteiligten) exakt konsistent
mit der tatsaechlichen Grid-Zellenzahl. Diese Tests fixieren das (bereits
korrekte) Verhalten als Regressionsschutz, da vorher keine Toleranz-
spezifischen Tests existierten (test_fill_tool_edge_cases_round53.py deckte
nur den toleranzfreien Fall + leere-Zelle-mit-Toleranz ab)."""

import pytest
from PySide6.QtCore import QPointF, QSettings, Qt
from PySide6.QtGui import QMouseEvent

from pysticky.core import Pattern, Thread
from pysticky.core.palette import get_palette_manager
from pysticky.ui.tools.base_tool import ToolContext
from pysticky.ui.tools.fill_tool import FillTool

pytestmark = pytest.mark.usefixtures("qtbot")


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


def test_scanline_and_diagonal_fill_agree_on_orthogonal_blob_with_tolerance():
    """Ein voll 4-fach (und damit auch 8-fach) verbundener Block aus drei
    perzeptuell aehnlichen Rot-Toenen, umgeben von einer klar
    unaehnlichen Hintergrundfarbe (Blau): beide Algorithmen muessen bei
    gleicher Toleranz EXAKT dieselbe Zellmenge liefern, da hier keine
    rein-diagonale Konnektivitaet ins Spiel kommt."""
    w, h = 9, 9
    pattern = Pattern(width=w, height=h)
    pattern.color_entries.clear()
    idx_r1 = pattern.add_color(Thread.from_hex("R1", "#FF0000"))
    idx_r2 = pattern.add_color(Thread.from_hex("R2", "#F01010"))
    idx_r3 = pattern.add_color(Thread.from_hex("R3", "#E82020"))
    idx_blue = pattern.add_color(Thread.from_hex("Blue", "#0000FF"))
    idx_new = pattern.add_color(Thread.from_hex("Neu", "#00FF00"))

    for y in range(h):
        for x in range(w):
            pattern.set_stitch(x, y, idx_blue)

    reds = [idx_r1, idx_r2, idx_r3]
    ri = 0
    for y in range(2, 7):
        for x in range(2, 7):
            pattern.set_stitch(x, y, reds[ri % 3])
            ri += 1

    tool = FillTool()
    max_delta_e = 15.0
    sx, sy = 4, 4
    got_scan = {
        (x, y)
        for x, y, _ in tool._scanline_fill(
            _make_ctx(pattern, sx, sy, idx_new), sx, sy, idx_new, max_delta_e=max_delta_e
        )
    }
    got_diag = {
        (x, y)
        for x, y, _ in tool._diagonal_fill(
            _make_ctx(pattern, sx, sy, idx_new), sx, sy, idx_new, max_delta_e=max_delta_e
        )
    }
    expected = {(x, y) for x in range(2, 7) for y in range(2, 7)}
    assert got_scan == expected
    assert got_diag == expected


def test_high_tolerance_does_not_treat_black_and_white_as_similar():
    """Toleranz = 100% => max. Delta-E = 50. Schwarz und Weiss (Delta-E
    ~100) duerfen trotz maximaler Toleranz NICHT als aehnlich gelten."""
    pattern = Pattern(width=1, height=2)
    pattern.color_entries.clear()
    idx_black = pattern.add_color(Thread.from_hex("Schwarz", "#000000"))
    idx_white = pattern.add_color(Thread.from_hex("Weiss", "#FFFFFF"))
    idx_new = pattern.add_color(Thread.from_hex("Neu", "#FF00FF"))
    pattern.set_stitch(0, 0, idx_black)
    pattern.set_stitch(0, 1, idx_white)

    tool = FillTool()
    changes = tool._scanline_fill(
        _make_ctx(pattern, 0, 0, idx_new), 0, 0, idx_new, max_delta_e=50.0
    )
    got = {(x, y) for x, y, _ in changes}
    assert got == {(0, 0)}


def test_real_dmc_palette_high_tolerance_does_not_swallow_the_whole_palette():
    """Regressionsschutz mit der echten DMC-Palette (nicht nur synthetischen
    Testfarben): ein Fuellvorgang bei maximaler Toleranz (100%) ueber eine
    Reihe farblich diverser echter DMC-Faeden darf nicht versehentlich die
    komplette Palette einschliessen -- waere ein Hinweis auf einen Fehler
    in der Prozent-zu-Delta-E-Umrechnung oder der Delta-E-Berechnung
    selbst."""
    pm = get_palette_manager()
    palette = pm.get_palette("DMC")
    assert palette is not None, "DMC-Palette konnte nicht geladen werden"

    threads = list(palette.threads)[:80]
    w = len(threads)
    pattern = Pattern(width=w, height=1)
    pattern.color_entries.clear()
    indices = [pattern.add_color(th) for th in threads]
    for x, idx in enumerate(indices):
        pattern.set_stitch(x, 0, idx)

    idx_new = pattern.add_color(threads[0])
    tool = FillTool()
    changes = tool._scanline_fill(
        _make_ctx(pattern, 0, 0, idx_new), 0, 0, idx_new, max_delta_e=50.0
    )
    got = {(x, y) for x, y, _ in changes}
    assert len(got) < w, "Bei maximaler Toleranz wurde die GESAMTE bunte Palette gefuellt"


def test_large_empty_pattern_scanline_fill_completes_and_counts_correctly():
    """500x500 komplett leeres (NO_STITCH) Muster fuellen: `matches()` muss
    `None` als eigene Kategorie behandeln (kein Delta-E-Aufruf auf eine
    nicht existierende Farbe) und in vertretbarer Zeit alle Zellen
    erfassen."""
    import time

    w, h = 500, 500
    pattern = Pattern(width=w, height=h)
    pattern.color_entries.clear()
    idx_new = pattern.add_color(Thread.from_hex("Neu", "#0000FF"))

    tool = FillTool()
    t0 = time.time()
    changes = tool._scanline_fill(_make_ctx(pattern, 250, 250, idx_new), 250, 250, idx_new)
    elapsed = time.time() - t0

    assert len(changes) == w * h
    assert elapsed < 15.0


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


def test_stitch_count_bookkeeping_correct_after_tolerance_fill_via_main_window(main_window):
    """Ein echter Fuellvorgang mit aktiver Toleranz ueber die volle
    MainWindow-Signal-Pipeline (Canvas -> stitch_placed -> _place_stitch ->
    PlaceStitchCommand -> Pattern.set_stitch) darf color_entries[i].stitch_count
    fuer KEINE Farbe (auch nicht die unbeteiligten) von der tatsaechlichen
    Grid-Zellenzahl abweichen lassen."""
    from pysticky.ui.tools.tool_enum import Tool

    settings = QSettings()
    settings.setValue("fill_tolerance", 30)
    settings.setValue("fill_diagonal", False)

    w = main_window
    width, height = 12, 12
    pattern = Pattern(name="Test", width=width, height=height)
    pattern.color_entries.clear()
    idx_r1 = pattern.add_color(Thread.from_hex("R1", "#FF0000"))
    idx_r2 = pattern.add_color(Thread.from_hex("R2", "#F41414"))
    idx_r3 = pattern.add_color(Thread.from_hex("R3", "#EC0808"))
    idx_new = pattern.add_color(Thread.from_hex("Neu", "#00FF00"))
    reds = [idx_r1, idx_r2, idx_r3]
    for i, (y, x) in enumerate((y, x) for y in range(height) for x in range(width)):
        pattern.set_stitch(x, y, reds[i % 3])
    w.set_pattern(pattern)

    canvas = w.canvas
    canvas._cell_size = 20
    canvas._offset_x = 0
    canvas._offset_y = 0
    w.tool_bar.select_tool(Tool.FILL)
    w.canvas._current_color_index = idx_new

    _press(canvas, 5 * 20 + 5, 5 * 20 + 5)
    _release(canvas, 5 * 20 + 5, 5 * 20 + 5)

    layer = pattern.active_layer
    for i, entry in enumerate(pattern.color_entries):
        actual = sum(1 for y in range(height) for x in range(width) if layer.get_stitch(x, y) == i)
        assert entry.stitch_count == actual, (
            f"stitch_count-Drift fuer Farbe {i} ({entry.thread.name})"
        )
