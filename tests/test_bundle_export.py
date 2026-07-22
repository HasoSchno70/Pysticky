# -*- coding: utf-8 -*-
"""Tests fuer den Bundle-Export."""

import zipfile
from pathlib import Path

import pytest

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


def test_bundle_garnliste_uses_drill_vocabulary_in_dp_mode(pattern_with_stitches, tmp_path):
    """Regression: die Garnliste-CSV war komplett blind gegenueber
    Pattern.mode == "diamond" -- anders als HTML-/PDF-Export und der
    Statistik-Dialog (der den Garnverbrauch/Einkaufsliste-Tab in DP
    komplett ausblendet, weil Skeins fuer Diamond-Drills keinen Sinn
    ergeben), schrieb bundle_export._write_thread_csv() fuer JEDES
    Pattern unveraendert den Header "Stiche;Strange (~)" und rechnete
    eine Straehnen-Schaetzung aus -- auch fuer DP-Muster, wo das
    bedeutungslos ist."""
    pattern_with_stitches.mode = "diamond"

    out = tmp_path / "test_bundle_dp.zip"
    export_bundle(pattern_with_stitches, out, include_pdf=False)
    with zipfile.ZipFile(out) as zf:
        with zf.open("garnliste.csv") as f:
            content = f.read().decode("utf-8")
    lines = content.strip().split("\n")

    header = lines[0]
    assert "Drills" in header
    assert "Strange" not in header
    # Datenzeilen duerfen keine zusaetzliche Skein-Spalte mehr haben
    assert len(lines) >= 2
    header_cols = header.split(";")
    data_cols = lines[1].split(";")
    assert len(data_cols) == len(header_cols)


def test_bundle_readme_uses_drill_pitch_in_dp_mode(pattern_with_stitches, tmp_path):
    """Regression: README.txt im Bundle nannte Groesse/Stoffzaehlung
    unveraendert "Stiche"/"... ct" -- selbst fuer Diamond-Painting-Muster,
    wo es "Drills"/Drill-Pitch heissen sollte (siehe export_common.py
    terms_for()/fabric_label_for(), die HTML-/PDF-Export schon nutzen)."""
    pattern_with_stitches.mode = "diamond"

    out = tmp_path / "test_bundle_dp_readme.zip"
    export_bundle(pattern_with_stitches, out, include_pdf=False)
    with zipfile.ZipFile(out) as zf:
        with zf.open("README.txt") as f:
            content = f.read().decode("utf-8")

    assert "Drills" in content
    assert "Stoffzaehlung" not in content


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


def test_bundle_survives_source_image_copy_failure(pattern_with_stitches, tmp_path, monkeypatch):
    """Regression: ein Kopierfehler beim Originalbild (Berechtigungen,
    Platte voll, Datei gerade gesperrt) brach frueher den GESAMTEN
    export_bundle()-Aufruf ab -- kein Bundle wurde erzeugt, obwohl alle
    anderen Bestandteile (HTML/PNG/CSV/README) laengst fertig waren. Die
    anderen optionalen Schritte waren schon immer fehlertolerant (landen
    in "skipped" statt zu crashen), dieser eine war es nicht."""
    from PySide6.QtGui import QColor, QImage

    src = tmp_path / "source.png"
    img = QImage(10, 10, QImage.Format.Format_RGB32)
    img.fill(QColor("red"))
    img.save(str(src), "PNG")
    pattern_with_stitches.source_image_path = str(src)

    import shutil

    def boom(*args, **kwargs):
        raise OSError("Platte voll (simuliert)")

    monkeypatch.setattr(shutil, "copy2", boom)

    out = tmp_path / "test_bundle.zip"
    result = export_bundle(pattern_with_stitches, out, include_pdf=False)

    assert out.exists()  # Bundle trotzdem erzeugt
    assert any("original" in s for s in result["skipped"])


def test_bundle_export_failure_leaves_existing_bundle_untouched(
    pattern_with_stitches, tmp_path, monkeypatch
):
    """Regression: export_bundle() schrieb die finale ZIP frueher DIREKT
    in den Zielpfad. `zipfile.ZipFile(zip_path, "w", ...)` truncated die
    Datei sofort beim Oeffnen -- schlug ein einzelner `zf.write()`-Aufruf
    mittendrin fehl (Platte voll, Abbruch), war ein am Zielpfad bereits
    vorhandenes Bundle (z.B. erneuter Export/Teilen desselben Musters)
    unwiderruflich durch eine leere/unvollstaendige ZIP ersetzt -- obwohl
    export_bundle() den Fehler weiterreicht und der Aufrufer denkt, nichts
    sei passiert. Jetzt: Temp-Datei + os.replace() wie
    core/file_io.py::save_pattern(), das bestehende Ziel wird erst nach
    vollstaendigem Schreiben ersetzt."""
    out = tmp_path / "existing_bundle.zip"
    export_bundle(pattern_with_stitches, out, include_pdf=False)
    original_bytes = out.read_bytes()

    # Den zweiten von mehreren zf.write()-Aufrufen fehlschlagen lassen,
    # um "Abbruch mitten im Schreiben der ZIP" zu simulieren.
    original_write = zipfile.ZipFile.write
    call_count = {"n": 0}

    def flaky_write(self, *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError("Platte voll (simuliert)")
        return original_write(self, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "write", flaky_write)

    with pytest.raises(OSError):
        export_bundle(pattern_with_stitches, out, include_pdf=False)

    # Bestehende Bundle-Datei unveraendert -- kein Datenverlust
    assert out.read_bytes() == original_bytes
    # Keine liegen gebliebene Temp-Datei
    assert not out.with_name(out.name + ".tmp").exists()


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
