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


def test_image_export_unwritable_path_raises(pattern_with_stitches, tmp_path):
    """Fehlschlag liefert kein stilles False mehr, sondern eine Exception
    mit Detail (Ziel-Pfad), damit das UI den Grund anzeigen kann."""
    target = tmp_path / "fehlt" / "out.png"  # Ordner existiert nicht
    with pytest.raises(OSError) as exc_info:
        ImageExporter(pattern_with_stitches).export(target, cell_size=10)
    assert "out.png" in str(exc_info.value)
