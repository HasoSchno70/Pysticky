# -*- coding: utf-8 -*-
"""Tests fuer den Bundle-Export."""

import zipfile
from pathlib import Path

from pysticky.io import export_bundle


def test_bundle_creates_zip(pattern_with_stitches, tmp_path):
    out = tmp_path / "test_bundle.zip"
    result = export_bundle(pattern_with_stitches, out)
    assert out.exists()
    assert out.stat().st_size > 0
    assert result["zip_path"] == str(out)


def test_bundle_contains_pxs_html_png_csv_readme(pattern_with_stitches, tmp_path):
    out = tmp_path / "test_bundle.zip"
    export_bundle(pattern_with_stitches, out, include_pdf=False)
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
    # Mindestens diese Komponenten muessen drin sein
    assert any(n.endswith(".pxs") for n in names)
    assert any(n.endswith(".html") for n in names)
    assert any(n.endswith(".png") for n in names)
    assert "garnliste.csv" in names
    assert "README.txt" in names
    # PDF wurde explizit ausgeschlossen — darf nicht drin sein
    assert not any(n.endswith(".pdf") for n in names)


def test_bundle_pxs_is_loadable(pattern_with_stitches, tmp_path):
    """Das im Bundle enthaltene .pxs muss valide sein."""
    from pysticky.core import load_pattern

    out = tmp_path / "test_bundle.zip"
    export_bundle(pattern_with_stitches, out, include_pdf=False)

    extract_dir = tmp_path / "extracted"
    extract_dir.mkdir()
    with zipfile.ZipFile(out) as zf:
        zf.extractall(extract_dir)
    pxs_files = list(extract_dir.glob("*.pxs"))
    assert len(pxs_files) == 1
    loaded = load_pattern(pxs_files[0])
    assert loaded.name == pattern_with_stitches.name
    assert loaded.width == pattern_with_stitches.width


def test_bundle_garnliste_has_thread_rows(pattern_with_stitches, tmp_path):
    out = tmp_path / "test_bundle.zip"
    export_bundle(pattern_with_stitches, out, include_pdf=False)
    with zipfile.ZipFile(out) as zf:
        with zf.open("garnliste.csv") as f:
            content = f.read().decode("utf-8")
    lines = content.strip().split("\n")
    assert lines[0].startswith("Symbol")  # Header
    assert len(lines) >= 2  # Header + mindestens eine Datenzeile


def test_bundle_skips_pdf_when_reportlab_missing(monkeypatch, pattern_with_stitches, tmp_path):
    """Wenn reportlab fehlt, taucht 'pdf (reportlab fehlt)' in skipped auf."""
    # bundle_export macht einen lazy `from . import check_reportlab_available`
    # — wir patchen das Attribut auf dem io-Package, von dem importiert wird.
    import pysticky.io as io_mod

    monkeypatch.setattr(io_mod, "check_reportlab_available", lambda: False)

    out = tmp_path / "test_bundle.zip"
    result = export_bundle(pattern_with_stitches, out, include_pdf=True)
    assert any("pdf" in s and "reportlab" in s for s in result["skipped"])


def test_bundle_includes_source_image_when_present(pattern_with_stitches, tmp_path):
    """Wenn source_image_path gesetzt und Datei existiert, landet sie unter original/."""
    src = tmp_path / "source.png"
    # Mini-PNG erzeugen
    from PySide6.QtGui import QColor, QImage

    img = QImage(10, 10, QImage.Format.Format_RGB32)
    img.fill(QColor("red"))
    img.save(str(src), "PNG")
    pattern_with_stitches.source_image_path = str(src)

    out = tmp_path / "test_bundle.zip"
    export_bundle(pattern_with_stitches, out, include_pdf=False)
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
    assert any(n.startswith("original/") and n.endswith("source.png") for n in names)


def test_bundle_handles_missing_source_image(pattern_with_stitches, tmp_path):
    """Wenn source_image_path verweist auf nicht-existente Datei: Skip statt Crash."""
    pattern_with_stitches.source_image_path = str(tmp_path / "nicht_da.png")
    out = tmp_path / "test_bundle.zip"
    result = export_bundle(pattern_with_stitches, out, include_pdf=False)
    assert any("original" in s for s in result["skipped"])
    assert out.exists()  # Bundle wurde trotzdem erzeugt


def test_bundle_safe_basename_handles_special_chars(tmp_path):
    """Pattern-Namen mit Sonderzeichen produzieren saubere Dateinamen im ZIP."""
    from pysticky.core import Pattern

    p = Pattern(name="Mein/Muster: 2024!", width=5, height=5)
    p.set_stitch(0, 0, 0)
    out = tmp_path / "out.zip"
    export_bundle(p, out, include_pdf=False)
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
    pxs = [n for n in names if n.endswith(".pxs")][0]
    # Keine Slash/Doppelpunkt/Ausrufezeichen im Datei-Namen
    assert "/" not in Path(pxs).stem
    assert ":" not in pxs
