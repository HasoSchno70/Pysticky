# -*- coding: utf-8 -*-
"""Regressionstests für einen kritischen Rendering-Bug (2026-07-18):
OptimizedCrossStitchCanvas cached gerenderte Chunks als Pixmap (aktiv bei
Mustern > 200x200 Zellen), aber `invalidate_cell`/`invalidate_region` wurde
nirgendwo aufgerufen, wenn ein Stich tatsächlich gesetzt wurde -- nur
`canvas.update()`. Der nächste paintEvent zeichnete dadurch weiterhin den
alten, gecachten (leeren) Chunk-Pixmap -- neu gezeichnete Stiche blieben auf
großen Mustern unsichtbar, sichtbar nur in Übersicht/Minimap (die direkt aus
den Pattern-Daten lesen). Beim Scrollen wurden zusätzlich alte/neue Chunks
inkonsistent gemischt sichtbar ("Artefakte")."""

import pytest

from pysticky.core import Pattern, Thread

pytestmark = pytest.mark.usefixtures("qtbot")


def _large_pattern() -> Pattern:
    """Muster über dem Chunk-Cache-Schwellwert (200x200 = 40.000 Zellen)."""
    pattern = Pattern(name="Gross", width=210, height=210)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    return pattern


def test_apply_changes_invalidates_chunk_cache(qtbot):
    """_apply_changes() (Pencil, Fill, Ellipse, ...) muss den betroffenen
    Chunk im Cache als dirty markieren, sonst rendert der nächste paintEvent
    weiterhin den alten Pixmap."""
    from pysticky.ui.canvas import OptimizedCrossStitchCanvas

    canvas = OptimizedCrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(_large_pattern())
    assert canvas._perf_manager.enabled

    # Chunk einmal rendern und cachen lassen (wie ein normaler paintEvent).
    from pysticky.ui.canvas.performance import render_chunk_to_pixmap

    chunk_size = canvas._perf_manager._chunk_size
    pixmap = render_chunk_to_pixmap(
        canvas._pattern,
        0,
        0,
        chunk_size,
        canvas._cell_size,
        canvas._empty_color,
        True,
        True,
        False,
        False,
        {},
        canvas._get_symbol_font(),
    )
    canvas._perf_manager.cache_chunk(0, 0, pixmap, canvas._cell_size, True, True, False, False)
    assert (
        canvas._perf_manager.get_cached_chunk(
            0, 0, canvas._pattern, canvas._cell_size, True, True, False, False
        )
        is not None
    )

    # Stich in genau diesem Chunk setzen -- wie es ein Tool über
    # canvas._apply_changes() tut.
    canvas._apply_changes([(3, 3, 0)])

    # Der Chunk muss jetzt als dirty gelten (get_cached_chunk gibt None
    # zurueck und zwingt damit ein Neu-Rendern im naechsten paintEvent).
    assert (
        canvas._perf_manager.get_cached_chunk(
            0, 0, canvas._pattern, canvas._cell_size, True, True, False, False
        )
        is None
    )


def test_apply_changes_with_mirror_invalidates_mirrored_chunk(qtbot):
    """Auch bei aktiver Spiegelung muss die gespiegelte Zielzelle invalidiert
    werden, nicht nur die Quellzelle."""
    from pysticky.ui.canvas import OptimizedCrossStitchCanvas
    from pysticky.ui.canvas.enums import MirrorMode

    canvas = OptimizedCrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(_large_pattern())
    canvas._mirror_mode = MirrorMode.HORIZONTAL

    mirrored_positions = [p for p in canvas.get_mirrored_positions(3, 3) if p != (3, 3)]
    assert mirrored_positions, "Spiegelung muss eine zweite Position liefern"
    mirrored_x, mirrored_y = mirrored_positions[0]
    chunk_size = canvas._perf_manager._chunk_size
    mirrored_chunk = (mirrored_x // chunk_size, mirrored_y // chunk_size)

    from PySide6.QtGui import QPixmap

    canvas._perf_manager.cache_chunk(*mirrored_chunk, QPixmap(1, 1))
    canvas._apply_changes_with_mirror([(3, 3, 0)])

    # invalidate_cell markiert den Chunk nur als dirty (verzögertes Evict) --
    # get_cached_chunk() muss die naechste Anfrage mit None beantworten,
    # sonst wuerde der naechste paintEvent den alten Pixmap wiederverwenden.
    assert mirrored_chunk in canvas._perf_manager._dirty_chunks


def test_invalidate_all_clears_chunk_cache(qtbot):
    """invalidate_all() (Undo/Redo, Farbe ersetzen, Einfügen, ...) muss den
    kompletten Chunk-Cache verwerfen, da diese Operationen beliebige Zellen
    ohne bekannte Koordinatenliste ändern können."""
    from PySide6.QtGui import QPixmap

    from pysticky.ui.canvas import OptimizedCrossStitchCanvas

    canvas = OptimizedCrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(_large_pattern())
    canvas._perf_manager.cache_chunk(0, 0, QPixmap(1, 1))
    canvas._perf_manager.cache_chunk(1, 1, QPixmap(1, 1))
    assert len(canvas._perf_manager._chunk_cache) == 2

    canvas.invalidate_all()

    assert len(canvas._perf_manager._chunk_cache) == 0


def test_get_cached_chunk_rejects_pixmap_rendered_at_different_cell_size(qtbot):
    """Ein bei alter Zellgröße gerenderter Chunk-Pixmap darf nach einem
    Zoom-Wechsel nicht mehr als gültig gelten -- sonst zeichnet
    _draw_cells_chunked() ihn falsch skaliert an der neuen Bildschirm-
    position (die 'verschobene, falsch große Blöcke'-Artefakte beim Zoomen)."""
    from PySide6.QtGui import QPixmap

    from pysticky.ui.canvas import OptimizedCrossStitchCanvas

    canvas = OptimizedCrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(_large_pattern())

    canvas._perf_manager.cache_chunk(0, 0, QPixmap(1, 1), 20, True, True, False, False)
    assert (
        canvas._perf_manager.get_cached_chunk(0, 0, canvas._pattern, 20, True, True, False, False)
        is not None
    )

    # Andere Zellgröße (Zoom-Wechsel) -- derselbe (cx, cy)-Key, aber der
    # gecachte Pixmap passt nicht mehr zur angeforderten Skalierung.
    assert (
        canvas._perf_manager.get_cached_chunk(0, 0, canvas._pattern, 7, True, True, False, False)
        is None
    )


def test_set_cell_size_invalidates_chunk_cache_on_zoom(qtbot):
    """_set_cell_size() (zoom_in/zoom_out/set_zoom/zoom_fit/zoom_reset) muss
    den Chunk-Cache verwerfen, wenn sich die Zellgröße tatsächlich ändert."""
    from PySide6.QtGui import QPixmap

    from pysticky.ui.canvas import OptimizedCrossStitchCanvas

    canvas = OptimizedCrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.set_pattern(_large_pattern())
    canvas._perf_manager.cache_chunk(
        0, 0, QPixmap(1, 1), canvas._cell_size, True, True, False, False
    )
    assert len(canvas._perf_manager._chunk_cache) == 1

    canvas.zoom_in()

    assert len(canvas._perf_manager._chunk_cache) == 0


def test_chunked_render_path_draws_fabric_texture(qtbot):
    """render_chunk_to_pixmap() (chunk-cache-Pfad, aktiv bei großen Mustern)
    füllte leere Zellen bisher immer mit einer flachen Farbe -- die
    Aida-Textur, die der Direkt-Renderpfad (_draw_all_cells) für leere
    Zellen zeichnet, fehlte dort komplett. Chunk-Pixmap mit Textur muss sich
    optisch von einer flachen Füllung unterscheiden (nicht uniform)."""
    from PySide6.QtGui import QColor, QFont, QImage

    from pysticky.ui.canvas.performance import render_chunk_to_pixmap

    pattern = _large_pattern()
    empty_color = QColor(60, 60, 90)
    font = QFont()
    flat = render_chunk_to_pixmap(
        pattern, 0, 0, 8, 20, empty_color, True, True, False, False, {}, font
    )

    fabric_tile = QImage(20, 20, QImage.Format.Format_ARGB32)
    fabric_tile.fill(empty_color)
    from PySide6.QtGui import QPainter as _QPainter

    p = _QPainter(fabric_tile)
    p.fillRect(4, 4, 4, 4, QColor(180, 170, 150, 200))
    p.end()

    from PySide6.QtGui import QPixmap

    textured = render_chunk_to_pixmap(
        pattern,
        0,
        0,
        8,
        20,
        empty_color,
        True,
        True,
        False,
        False,
        {},
        font,
        QPixmap.fromImage(fabric_tile),
        False,
    )

    flat_img = flat.toImage()
    textured_img = textured.toImage()
    assert flat_img.pixelColor(4, 4) != textured_img.pixelColor(4, 4)


def test_notify_panels_visual_and_palette_invalidate_canvas(qtbot):
    """_notify_panels('visual') und ('palette') -- die von Undo/Redo,
    Farbe-ersetzen, Einfuegen etc. genutzten Scopes -- muessen invalidate_all()
    auf dem Canvas ausloesen."""
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    from PySide6.QtGui import QPixmap

    w.set_pattern(_large_pattern())
    assert w.canvas._perf_manager.enabled
    w.canvas._perf_manager.cache_chunk(0, 0, QPixmap(1, 1))

    w._notify_panels("visual")
    assert len(w.canvas._perf_manager._chunk_cache) == 0

    w.canvas._perf_manager.cache_chunk(0, 0, QPixmap(1, 1))
    w._notify_panels("palette")
    assert len(w.canvas._perf_manager._chunk_cache) == 0
