# -*- coding: utf-8 -*-
"""
Smoke- und Roundtrip-Tests fuer den Bild-Export (PNG/JPG/BMP).
"""

import pytest

from pysticky.io.image_export import ImageExporter

pytestmark = pytest.mark.usefixtures("qtbot")


def _png_magic(path) -> bytes:
    with open(path, "rb") as f:
        return f.read(8)


def test_image_export_png_writes_file(pattern_with_stitches, tmp_path):
    target = tmp_path / "out.png"
    ok = ImageExporter(pattern_with_stitches).export(target, cell_size=10)
    assert ok is True
    assert target.exists()
    assert target.stat().st_size > 0


def test_image_export_png_has_valid_magic(pattern_with_stitches, tmp_path):
    """Datei beginnt mit dem PNG-Magic-Header."""
    target = tmp_path / "out.png"
    ImageExporter(pattern_with_stitches).export(target, cell_size=10)
    assert _png_magic(target).startswith(b"\x89PNG\r\n\x1a\n")


def test_image_export_jpg_works(pattern_with_stitches, tmp_path):
    target = tmp_path / "out.jpg"
    ok = ImageExporter(pattern_with_stitches).export(target, cell_size=10)
    assert ok is True
    # JPG-Magic: FF D8 FF
    with open(target, "rb") as f:
        magic = f.read(3)
    assert magic == b"\xff\xd8\xff"


def test_image_export_bmp_works(pattern_with_stitches, tmp_path):
    target = tmp_path / "out.bmp"
    ok = ImageExporter(pattern_with_stitches).export(target, cell_size=10)
    assert ok is True
    with open(target, "rb") as f:
        assert f.read(2) == b"BM"


def test_image_export_cell_size_affects_image_size(pattern_with_stitches, tmp_path):
    """Groessere cell_size produziert proportional groessere Datei."""
    from PySide6.QtGui import QImage

    small = tmp_path / "small.png"
    large = tmp_path / "large.png"
    ImageExporter(pattern_with_stitches).export(small, cell_size=5)
    ImageExporter(pattern_with_stitches).export(large, cell_size=20)

    img_s = QImage(str(small))
    img_l = QImage(str(large))
    # Pattern ist 20x20 — bei cell_size=5 → 100px, bei cell_size=20 → 400px
    assert img_s.width() == 100
    assert img_s.height() == 100
    assert img_l.width() == 400
    assert img_l.height() == 400


def test_image_export_cell_size_clamped(pattern_with_stitches, tmp_path):
    """cell_size wird auf [4, 100] geclampt — Ausserhalb-Werte crashen nicht."""
    from PySide6.QtGui import QImage

    target = tmp_path / "huge.png"
    ImageExporter(pattern_with_stitches).export(target, cell_size=500)
    img = QImage(str(target))
    # Clamp auf 100: Pattern 20x20 -> 2000px
    assert img.width() == 2000


def test_image_export_grid_option_does_not_crash(pattern_with_stitches, tmp_path):
    """show_grid + show_symbols kombiniert."""
    target = tmp_path / "grid.png"
    ok = ImageExporter(pattern_with_stitches).export(
        target, cell_size=20, show_grid=True, show_symbols=True
    )
    assert ok is True


def test_image_export_empty_pattern(empty_pattern, tmp_path):
    """Leeres Pattern crasht den Exporter nicht."""
    target = tmp_path / "empty.png"
    ok = ImageExporter(empty_pattern).export(target, cell_size=10)
    assert ok is True
    assert target.exists()


def test_image_export_dp_mode_renders_diamond_drill_not_flat_square(tmp_path):
    """DP-Modus (Diamond Painting): FULL-Stiche muessen als facettierter
    Drill gerendert werden (analog PDF-/HTML-Export und Canvas-Renderer),
    nicht als flaches Kreuzstich-Rechteck.

    Regression: `ImageExporter` kannte weder den expliziten DIAMOND-
    Stitch-Type (11) noch die Pattern.mode=='diamond'-Konvention (FULL-
    Stiche als Drill, siehe pdf_export_drawings.py::_add_stitch_shape) und
    rendere DP-Zellen deshalb immer als schlichtes eingefaerbtes Quadrat.

    Verifikation ueber echte Pixelfarben: der Drill hat vier facettierte
    Ecken mit unterschiedlicher Helligkeit (hell oben, dunkel unten) --
    ein flaches Rechteck haette ueberall exakt dieselbe Farbe.
    """
    from PySide6.QtGui import QImage

    from pysticky.core import Pattern, Thread

    pattern = Pattern(name="DP-Test", width=4, height=4, mode="diamond")
    pattern.color_entries.clear()
    thread = Thread.from_hex(
        "Rot", "#FF0000", manufacturer="DMC Diamond Painting", catalog_number="1"
    )
    pattern.add_color(thread)
    # Ein einzelner Drill in der Mitte des kleinen Patterns.
    pattern.set_stitch(1, 1, 0)

    target = tmp_path / "dp.png"
    cell_size = 40  # gross genug, damit Facetten + Kantenrand sichtbar sind
    ok = ImageExporter(pattern).export(target, cell_size=cell_size, show_grid=False)
    assert ok is True

    img = QImage(str(target))
    cx = 1 * cell_size + cell_size // 2
    cy = 1 * cell_size + cell_size // 2
    top_px = img.pixelColor(cx, cy - cell_size // 3)
    bottom_px = img.pixelColor(cx, cy + cell_size // 3)

    # Facettierter Drill: obere Facette (Glanzlicht) ist heller als die
    # untere (Schatten) -- bei einem flachen Rechteck waeren beide exakt
    # identisch (reine Rot-Palettenfarbe #FF0000 ueberall).
    assert (top_px.red(), top_px.green(), top_px.blue()) != (
        bottom_px.red(),
        bottom_px.green(),
        bottom_px.blue(),
    )
    flat_red = (255, 0, 0)
    assert (top_px.red(), top_px.green(), top_px.blue()) != flat_red
    assert (bottom_px.red(), bottom_px.green(), bottom_px.blue()) != flat_red


def test_image_export_stitch_mode_full_stitch_stays_flat_square(pattern_with_stitches, tmp_path):
    """Gegenprobe: im normalen Kreuzstich-Modus (mode='stitch') bleibt ein
    FULL-Stich weiterhin ein flaches, einfarbiges Quadrat -- die DP-Drill-
    Sonderbehandlung darf NICHT auf Nicht-DP-Pattern durchschlagen."""
    from PySide6.QtGui import QImage

    target = tmp_path / "flat.png"
    cell_size = 10
    ImageExporter(pattern_with_stitches).export(target, cell_size=cell_size, show_grid=False)

    img = QImage(str(target))
    # (6,6) ist Teil der roten Fuellung im pattern_with_stitches-Fixture.
    cx = 6 * cell_size + cell_size // 2
    cy = 6 * cell_size + cell_size // 2
    top_px = img.pixelColor(cx, cy - 3)
    bottom_px = img.pixelColor(cx, cy + 3)
    assert (top_px.red(), top_px.green(), top_px.blue()) == (
        bottom_px.red(),
        bottom_px.green(),
        bottom_px.blue(),
    )
    assert (top_px.red(), top_px.green(), top_px.blue()) == (255, 0, 0)


def test_image_export_unwritable_path_raises(pattern_with_stitches, tmp_path):
    """Fehlschlag liefert kein stilles False mehr, sondern eine Exception
    mit Detail (Ziel-Pfad), damit das UI den Grund anzeigen kann."""
    target = tmp_path / "fehlt" / "out.png"  # Ordner existiert nicht
    with pytest.raises(OSError) as exc_info:
        ImageExporter(pattern_with_stitches).export(target, cell_size=10)
    assert "out.png" in str(exc_info.value)
