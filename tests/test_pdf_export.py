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


def test_pdf_preview_drawing_hides_backstitches_in_dp_mode():
    """Regression: _create_preview_drawing() (geteilt von Cover/Vorschau/
    Uebersicht, siehe pdf_export_sections.py) zeichnete Rueckstich-Linien
    unbedingt, auch im DP-Modus -- obwohl Legende und Info-Texte (siehe
    test_pdf_cover_title_matches_pattern_mode-Nachbartests) das schon
    korrekt ausblenden. Passiert z.B. wenn ein Pattern per
    Pattern.convert_to_mode() von Stick- auf Diamond-Modus umgeschaltet
    wird: convert_to_mode() raeumt alte Backstitch-Daten nicht auf."""
    from reportlab.graphics.shapes import Line

    from pysticky.core import Pattern, Thread

    pattern = Pattern(width=5, height=5)
    pattern.mode = "diamond"
    idx = pattern.add_color(
        Thread.from_hex(
            "Rot", "#FF0000", manufacturer="DMC Diamond Painting", catalog_number="321"
        ),
        is_diamond=True,
    )
    for x in range(5):
        for y in range(5):
            pattern.set_stitch(x, y, idx)
    pattern.add_backstitch(0, 0, 4, 4, idx)

    exp = PDFExporter(pattern, include_path_preview=False)
    exp._calculate_statistics()
    drawing = exp._create_preview_drawing(100, 100)

    assert drawing is not None
    assert not any(isinstance(shape, Line) for shape in drawing.contents)


def test_pdf_preview_drawing_keeps_backstitch_exactly_on_pattern_edge():
    """Regression-Check (Runde 51): Der HTML-Export hatte einen Off-by-One-Bug
    (Runde 47-50, html_export.py), bei dem ein Rueckstich-Endpunkt exakt auf
    der rechten/unteren Musterkante (Halbstich-Koordinate == 2*width/2*height)
    per rohem `// 2` auf den nicht existierenden Zell-Index `width`/`height`
    abgebildet wurde und die Linie dadurch lautlos aus dem Export verschwand.

    _create_preview_drawing() im PDF-Export (pdf_export_drawings.py) rechnet
    Rueckstich-Endpunkte NICHT per Ganzzahldivision auf einen Zell-Index um --
    es skaliert die halben-Stich-Koordinaten direkt proportional in
    Zeichnungs-Koordinaten (`bs.x1 * half_cell_w` usw.), ohne Rundung auf
    einen Bucket-Index. Deshalb existiert die HTML-Bugklasse hier strukturell
    nicht. Dieser Test haelt das fest, falls jemand die Skalierung spaeter
    durch eine Zell-Index-basierte Logik ersetzt."""
    from reportlab.graphics.shapes import Line

    from pysticky.core import Pattern, Thread

    pattern = Pattern(width=5, height=5)
    idx = pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    for x in range(5):
        for y in range(5):
            pattern.set_stitch(x, y, idx)

    # Endpunkt exakt auf der rechten/unteren Musterkante: (8,8) -> (10,10),
    # wobei 10 == 2*width == 2*height (die problematische Grenz-Koordinate).
    pattern.add_backstitch(8, 8, 10, 10, idx)

    exp = PDFExporter(pattern, include_path_preview=False)
    exp._calculate_statistics()
    drawing = exp._create_preview_drawing(100, 100)

    assert drawing is not None
    lines = [shape for shape in drawing.contents if isinstance(shape, Line)]
    # Erwarteter Endpunkt: exakt an der rechten (x=100) unteren (y=0) Kante
    # der 100x100-Zeichnung -- keine Verschiebung, kein Verschwinden.
    matching = [ln for ln in lines if abs(ln.x2 - 100.0) < 0.01 and abs(ln.y2 - 0.0) < 0.01]
    coords = [(ln.x1, ln.y1, ln.x2, ln.y2) for ln in lines]
    assert len(matching) == 1, f"Rueckstich am Musterrand fehlt oder falsch platziert: {coords}"


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


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Minimaler PDF-Content-Stream-Text-Extractor -- nur fuer reportlab-
    generierte PDFs (ASCII85Decode + FlateDecode content streams, Standard-
    Fonts/WinAnsiEncoding). Bewusst ohne externe Abhaengigkeit (kein
    pypdf/pdfplumber im Projekt) -- reicht aus, um Tj/TJ-Textoperatoren aus
    den dekomprimierten Streams zu extrahieren und auf Vollstaendigkeit /
    Wiederholung (Kopfzeile) zu pruefen.
    """
    import base64
    import re
    import zlib

    texts: list[bytes] = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", pdf_bytes, re.DOTALL):
        raw = m.group(1).rstrip(b"\r\n")
        if raw.endswith(b"~>"):
            raw = raw[:-2]
        try:
            decompressed = zlib.decompress(base64.a85decode(raw, adobe=False))
        except (ValueError, zlib.error):
            continue
        for tm in re.finditer(rb"\((?:[^()\\]|\\.)*\)\s*Tj", decompressed):
            s = tm.group(0)
            texts.append(s[1 : s.rfind(b")")])
        for tm in re.finditer(rb"\[((?:[^\[\]\\]|\\.)*)\]\s*TJ", decompressed):
            parts = re.findall(rb"\((?:[^()\\]|\\.)*\)", tm.group(1))
            texts.append(b"".join(p[1:-1] for p in parts))
    return b" ".join(texts).decode("latin-1", errors="replace")


def _pattern_with_many_colors(n: int):
    """Baut ein Pattern mit `n` Farben (jenseits des 86er-Symbol-Pools ab
    Runde 48 -- dann greift der "#N"-Fallback statt eines echten Symbols)."""
    from pysticky.core import Pattern, Thread

    pattern = Pattern(width=10, height=10)
    pattern.color_entries.clear()
    for i in range(n):
        pattern.add_color(
            Thread.from_hex(
                f"Farbe{i}",
                f"#{i % 16:01x}{(i * 3) % 16:01x}{(i * 7) % 16:01x}",
                manufacturer="DMC",
                catalog_number=f"XCAT{i:04d}",
            )
        )
    return pattern


def test_pdf_legend_header_repeats_on_continuation_pages(tmp_path):
    """Regression: Bei sehr vielen Farben (Symbol-Pool-Erschoepfung, Runde 48)
    bricht die Legenden-Tabelle ueber mehrere PDF-Seiten um (reportlab
    Table-Flowable-Split). Ohne repeatRows=1 (Table in
    pdf_export_sections.py::_create_legend) erscheint die Spaltenkopfzeile
    (Nr./Symbol/Farbe/Garnnummer/...) nur auf der ersten Seite -- alle
    Folgeseiten der Legende zeigen nackte Zahlenkolonnen ohne jede
    Beschriftung. Pruefung ueber echten PDF-Content (nicht nur den
    reportlab-Story-Objektbaum), damit ein tatsaechlicher Seitenumbruch
    verifiziert wird."""
    pattern = _pattern_with_many_colors(130)

    target = tmp_path / "viele_farben.pdf"
    ok = PDFExporter(pattern, include_path_preview=False).export(target)
    assert ok is True

    text = _extract_pdf_text(target.read_bytes())

    # Kopfzeilen-Text muss mehrfach auftauchen -- sonst wuerde er nur auf
    # der ersten Legenden-Seite stehen.
    assert text.count("Garnnummer") > 1


def test_pdf_legend_all_colors_present_exactly_once_across_page_break(tmp_path):
    """Regression-Absicherung (bereits korrektes Verhalten): Trotz des
    mehrseitigen Legenden-Umbruchs bei sehr vielen Farben darf reportlabs
    automatischer Table-Split keine Zeile verlieren oder duplizieren --
    jede Katalognummer muss in der erzeugten PDF-Legende genau einmal
    auftauchen, auch fuer Farben jenseits des 86er-Symbol-Pools (die dort
    ein mehrstelliges "#N"-Fallback-Symbol statt eines echten Symbols
    bekommen, siehe Pattern.add_color)."""
    n = 130
    pattern = _pattern_with_many_colors(n)

    target = tmp_path / "viele_farben_vollstaendig.pdf"
    ok = PDFExporter(pattern, include_path_preview=False).export(target)
    assert ok is True

    text = _extract_pdf_text(target.read_bytes())

    import re
    from collections import Counter

    codes = re.findall(r"XCAT\d{4}", text)
    counts = Counter(codes)

    missing = [f"XCAT{i:04d}" for i in range(n) if f"XCAT{i:04d}" not in counts]
    duplicated = {code: c for code, c in counts.items() if c > 1}

    assert missing == [], f"Farben in der Legende verschwunden: {missing}"
    assert duplicated == {}, f"Farben in der Legende dupliziert: {duplicated}"

    # "#N"-Fallback-Symbole (ab Farbe 87, Runde 48) muessen unbeschaedigt
    # (nicht abgeschnitten auf ein einzelnes Zeichen) im PDF-Text auftauchen.
    hash_symbols = set(re.findall(r"#\d+", text))
    assert "#1" in hash_symbols
    assert "#44" in hash_symbols  # 130 - 86 = 44 Fallback-Symbole erwartet
