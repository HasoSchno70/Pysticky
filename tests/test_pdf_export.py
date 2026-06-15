# -*- coding: utf-8 -*-
"""
Smoke- und Roundtrip-Tests fuer den PDF-Export.

Wenn reportlab nicht installiert ist, werden alle Tests uebersprungen.
"""

import pytest

from pysticky.io.pdf_export import (
    PDFExporter,
    check_reportlab_available,
    export_pdf,
)

pytestmark = pytest.mark.skipif(
    not check_reportlab_available(), reason="reportlab nicht installiert"
)


def test_pdf_export_writes_file(pattern_with_stitches, tmp_path):
    target = tmp_path / "muster.pdf"
    exporter = PDFExporter(pattern_with_stitches, include_path_preview=False)
    ok = exporter.export(target)
    assert ok is True
    assert target.exists()
    assert target.stat().st_size > 0


def test_pdf_export_appends_extension(pattern_with_stitches, tmp_path):
    target = tmp_path / "ohne_endung"
    PDFExporter(pattern_with_stitches, include_path_preview=False).export(target)
    assert (tmp_path / "ohne_endung.pdf").exists()


def test_pdf_export_starts_with_pdf_magic(pattern_with_stitches, tmp_path):
    """Die erzeugte Datei ist eine valide PDF (beginnt mit %PDF)."""
    target = tmp_path / "muster.pdf"
    PDFExporter(pattern_with_stitches, include_path_preview=False).export(target)
    with target.open("rb") as f:
        header = f.read(4)
    assert header == b"%PDF"


def test_pdf_export_supports_multiple_page_formats(pattern_with_stitches, tmp_path):
    """A4, A3, Letter laufen alle ohne Crash."""
    for fmt in ("A4", "A3", "Letter"):
        target = tmp_path / f"muster_{fmt}.pdf"
        ok = PDFExporter(pattern_with_stitches, include_path_preview=False, page_format=fmt).export(
            target
        )
        assert ok is True, f"Format {fmt} failed"
        assert target.stat().st_size > 0


def test_export_pdf_module_function(pattern_with_stitches, tmp_path):
    """Die module-level export_pdf-Convenience laeuft analog zur Klasse."""
    target = tmp_path / "convenience.pdf"
    ok = export_pdf(pattern_with_stitches, target, include_path_preview=False)
    assert ok is True
    assert target.exists()


def test_pdf_export_empty_pattern(empty_pattern, tmp_path):
    """Leeres Pattern crasht den Exporter nicht."""
    target = tmp_path / "leer.pdf"
    ok = PDFExporter(empty_pattern, include_path_preview=False).export(target)
    assert ok is True
    assert target.exists()
