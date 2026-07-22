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


def test_pdf_export_mystery_mode_stitch_and_diamond(tmp_path):
    """Mystery-Modus exportiert ohne Crash, sowohl Stick- als auch DP-Muster."""
    from pysticky.core import Pattern, Thread

    pattern = Pattern(width=5, height=5)
    idx = pattern.add_color(
        Thread.from_hex("Rot", "#FF0000", manufacturer="DMC", catalog_number="321")
    )
    for x in range(5):
        for y in range(5):
            pattern.set_stitch(x, y, idx)
    target = tmp_path / "mystery_stitch.pdf"
    ok = PDFExporter(pattern, mystery_mode=True, include_path_preview=False).export(target)
    assert ok is True
    assert target.stat().st_size > 0

    dp_pattern = Pattern(width=5, height=5)
    dp_pattern.mode = "diamond"
    dp_idx = dp_pattern.add_color(
        Thread.from_hex(
            "Rot", "#FF0000", manufacturer="DMC Diamond Painting", catalog_number="321"
        ),
        is_diamond=True,
    )
    for x in range(5):
        for y in range(5):
            dp_pattern.set_stitch(x, y, dp_idx)
    target_dp = tmp_path / "mystery_dp.pdf"
    ok_dp = PDFExporter(dp_pattern, mystery_mode=True, include_path_preview=False).export(target_dp)
    assert ok_dp is True
    assert target_dp.stat().st_size > 0


def test_pdf_cover_title_matches_pattern_mode():
    """Regression: das Deckblatt zeigte immer 'KREUZSTICH-MUSTER', auch im
    Diamond-Painting-Modus (der HTML-Export unterschied das schon)."""
    from pysticky.core import Pattern, Thread

    stitch_pattern = Pattern(width=5, height=5)
    stitch_pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    exp = PDFExporter(stitch_pattern, include_path_preview=False)
    exp._calculate_statistics()
    title = exp._create_cover("Titel", "2026-07-19", 10.0, 10.0, 1)[1].text
    assert "KREUZSTICH" in title
    assert "DIAMOND-PAINTING" not in title

    dp_pattern = Pattern(width=5, height=5)
    dp_pattern.mode = "diamond"
    dp_pattern.add_color(
        Thread.from_hex(
            "Rot", "#FF0000", manufacturer="DMC Diamond Painting", catalog_number="321"
        ),
        is_diamond=True,
    )
    exp_dp = PDFExporter(dp_pattern, include_path_preview=False)
    exp_dp._calculate_statistics()
    title_dp = exp_dp._create_cover("Titel", "2026-07-19", 10.0, 10.0, 1)[1].text
    assert "DIAMOND-PAINTING" in title_dp
    assert "KREUZSTICH" not in title_dp


def test_pdf_mystery_mode_hides_backstitch_count(tmp_path):
    """Regression: Mystery-Modus zeigte im PDF (anders als im HTML-Export)
    weiterhin die exakte Rueckstich-Anzahl auf Deckblatt + Vorschau-Seite --
    das allein verraet schon Konturen des Motivs."""
    from pysticky.core import Pattern, Thread

    pattern = Pattern(width=5, height=5)
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.add_backstitch(0, 0, 4, 4, 0)
    pattern.add_backstitch(0, 4, 4, 0, 0)

    exp = PDFExporter(pattern, mystery_mode=True, include_path_preview=False)
    exp._calculate_statistics()
    cover_elements = exp._create_cover("Titel", "2026-07-19", 10.0, 10.0, 1)
    cover_text = "".join(getattr(e, "text", "") for e in cover_elements)
    assert "Linien" not in cover_text  # "N Linien" fuer Rueckstiche waere hier

    preview_elements = exp._create_preview("Titel", 10.0, 10.0)
    preview_text = "".join(getattr(e, "text", "") for e in preview_elements)
    assert "Linien" not in preview_text


def test_pdf_export_survives_unescaped_angle_bracket_in_notes(pattern_with_stitches, tmp_path):
    """Regression (Runde 20): reportlab's Paragraph() parst Text als eigenes
    XML-artiges Markup -- ein rohes "<" GEFOLGT VON EINEM BUCHSTABEN (wie ein
    Tag-Name) liess `doc.build()` vorher mit einem ParaParser-ValueError
    abstuerzen und den GESAMTEN PDF-Export scheitern lassen, nicht nur die
    Notizen-Seite. Verifiziert per Hand gegen die echte reportlab-Installation:
    Paragraph("Kante<Rand", ...) wirft ValueError, waehrend z.B. "x < y" (mit
    Leerzeichen) oder "x<3" (Ziffer nach "<") vom Parser toleriert werden --
    daher bewusst ein Payload OHNE Leerzeichen/Ziffer direkt nach "<".
    """
    target = tmp_path / "notizen.pdf"
    exp = PDFExporter(
        pattern_with_stitches,
        include_path_preview=False,
        notes="Kante<Rand beachten",
    )
    ok = exp.export(target)
    assert ok is True
    assert target.exists()


def test_pdf_export_survives_unescaped_angle_bracket_in_metadata(pattern_with_stitches, tmp_path):
    """Wie oben, aber ueber Pattern-Autor/Copyright (Deckblatt) statt
    Notizen -- beide landen unescaped in Paragraph()-Aufrufen."""
    pattern_with_stitches.metadata["author"] = "A<b>Werkstatt"
    pattern_with_stitches.metadata["copyright"] = "Rot<Orange Studio"

    target = tmp_path / "metadaten.pdf"
    ok = PDFExporter(pattern_with_stitches, include_path_preview=False).export(target)
    assert ok is True
    assert target.exists()


def test_pdf_export_survives_unescaped_angle_bracket_in_thread_name(tmp_path):
    """Wie oben, aber ueber einen Garnnamen/Katalognummer mit "<" -- landet
    unescaped in der Musterseiten-Mini-Legende (pdf_export_sections.py)."""
    from pysticky.core import Pattern, Thread

    pattern = Pattern(width=5, height=5)
    idx = pattern.add_color(
        Thread.from_hex("Rot<Orange", "#FF0000", manufacturer="DMC", catalog_number="A<b>21")
    )
    for x in range(5):
        for y in range(5):
            pattern.set_stitch(x, y, idx)

    target = tmp_path / "garnname.pdf"
    ok = PDFExporter(pattern, include_path_preview=False).export(target)
    assert ok is True
    assert target.exists()
