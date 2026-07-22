# -*- coding: utf-8 -*-
"""
Smoke- und Roundtrip-Tests fuer den HTML-Export.

Sicherstellt, dass der Export ohne Crash durchlaeuft, die Datei real
existiert und die wichtigsten erwarteten Inhalte (Titel, Farben, Symbole)
darin enthalten sind.
"""

from pysticky.io.html_export import HTMLExporter, _html_encode


def test_html_encode_passes_plain_ascii():
    assert _html_encode("hello world") == "hello world"


def test_html_encode_keeps_umlauts_as_utf8():
    """HTML deklariert charset=UTF-8 -> Umlaute brauchen kein Entity-Encoding."""
    assert _html_encode("Müller") == "Müller"
    assert _html_encode("Größe") == "Größe"


def test_html_encode_escapes_html_specials():
    """<, >, & muessen escaped werden, damit sie nicht als Markup interpretiert werden."""
    assert _html_encode("a < b") == "a &lt; b"
    assert _html_encode("a > b") == "a &gt; b"
    assert _html_encode("Tom & Jerry") == "Tom &amp; Jerry"


def test_html_encode_roundtrips_existing_entities():
    """Bereits gespeichertes &times; bleibt als ×, &amp; als &."""
    assert _html_encode("3 &times; 4") == "3 × 4"
    assert _html_encode("Tom &amp; Jerry") == "Tom &amp; Jerry"


def test_html_encode_handles_empty():
    assert _html_encode("") == ""
    assert _html_encode(None) is None


def test_html_export_writes_file(pattern_with_stitches, tmp_path):
    target = tmp_path / "muster.html"
    exporter = HTMLExporter(pattern_with_stitches)
    ok = exporter.export(target)
    assert ok is True
    assert target.exists()
    assert target.stat().st_size > 0


def test_html_export_contains_title(pattern_with_stitches, tmp_path):
    target = tmp_path / "Schoenes_Muster.html"
    exporter = HTMLExporter(pattern_with_stitches)
    exporter.export(target)
    content = target.read_text(encoding="utf-8")
    assert "<html" in content.lower()
    assert "Schoenes_Muster" in content
    assert "</html>" in content.lower()


def test_html_export_contains_color_info(pattern_with_stitches, tmp_path):
    """Der Export listet die im Pattern verwendeten DMC-Nummern."""
    target = tmp_path / "out.html"
    HTMLExporter(pattern_with_stitches).export(target)
    content = target.read_text(encoding="utf-8")
    # DMC 310 = Schwarz, im Pattern verwendet
    assert "310" in content
    # DMC 321 = Rot, im Pattern verwendet
    assert "321" in content


def test_html_export_appends_extension_if_missing(pattern_with_stitches, tmp_path):
    target = tmp_path / "ohne_endung"
    HTMLExporter(pattern_with_stitches).export(target)
    assert (tmp_path / "ohne_endung.html").exists()


def test_html_export_empty_pattern(empty_pattern, tmp_path):
    """Leeres Pattern (keine Farben, keine Stiche) crasht den Exporter nicht."""
    target = tmp_path / "leer.html"
    ok = HTMLExporter(empty_pattern).export(target)
    assert ok is True
    assert target.exists()


def test_html_export_includes_author_from_metadata(pattern_with_stitches, tmp_path):
    """Wenn Pattern-Metadaten `author` enthalten, erscheint er auf dem Deckblatt."""
    pattern_with_stitches.metadata["author"] = "Anna Müller"
    target = tmp_path / "mit_autor.html"
    HTMLExporter(pattern_with_stitches).export(target)
    content = target.read_text(encoding="utf-8")
    assert "Anna Müller" in content
    assert "von Anna Müller" in content


def test_html_export_includes_copyright_in_footer(pattern_with_stitches, tmp_path):
    """Copyright-Hinweis erscheint im Cover-Footer und im Per-Page-Footer."""
    pattern_with_stitches.metadata["copyright"] = "(c) 2026 Anna"
    target = tmp_path / "mit_cr.html"
    HTMLExporter(pattern_with_stitches).export(target)
    content = target.read_text(encoding="utf-8")
    assert content.count("(c) 2026 Anna") >= 2  # Cover + mindestens eine Seite


def test_html_export_mystery_mode_replaces_preview_with_placeholder(
    pattern_with_stitches, tmp_path
):
    """Mystery-Modus zeigt in Deckblatt/Vorschau/Uebersicht ein '?' statt des Bildes."""
    normal = tmp_path / "normal.html"
    HTMLExporter(pattern_with_stitches, mystery_mode=False).export(normal)
    mystery = tmp_path / "mystery.html"
    HTMLExporter(pattern_with_stitches, mystery_mode=True).export(mystery)

    normal_content = normal.read_text(encoding="utf-8")
    mystery_content = mystery.read_text(encoding="utf-8")

    assert ">?<" not in normal_content
    # 3x: Deckblatt, Vorschau-Seite, Uebersichtskarte
    assert mystery_content.count(">?<") == 3


def test_html_export_mystery_mode_diamond_cells_have_no_background(tmp_path):
    """Im DP-Modus verschwindet im Mystery-Modus die Drill-Hintergrundfarbe pro Zelle."""
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

    normal = tmp_path / "dp_normal.html"
    HTMLExporter(pattern, mystery_mode=False).export(normal)
    mystery = tmp_path / "dp_mystery.html"
    HTMLExporter(pattern, mystery_mode=True).export(mystery)

    normal_content = normal.read_text(encoding="utf-8")
    mystery_content = mystery.read_text(encoding="utf-8")

    # Per-Zelle-Markup hat ein Semikolon vor dem schliessenden Anfuehrungs-
    # zeichen (style='background:rgb(...);'), die Legende/Mini-Legende
    # nicht (style='background:rgb(...)') -- so bleibt der Legenden-Treffer
    # (bewusst weiterhin farbig) von der Pruefung ausgenommen.
    cell_bg = "background:rgb(255,0,0);'"
    assert cell_bg in normal_content
    assert cell_bg not in mystery_content


def test_html_export_marks_skip_stitching_colors(pattern_with_stitches, tmp_path):
    """Regression: HTML-Export ignorierte skip_stitching komplett (PDF hatte
    die Unterscheidung schon) -- eine als 'Stofffarbe' markierte Farbe muss
    in der Legende gekennzeichnet sein und nicht in die 'zu sticken'-Summe
    einfliessen."""
    pattern_with_stitches.color_entries[0].skip_stitching = True

    target = tmp_path / "skip.html"
    HTMLExporter(pattern_with_stitches).export(target)
    content = target.read_text(encoding="utf-8")

    assert "[⊘]" in content
    assert "Stofffarbe" in content
    # "Zu sticken:" statt "Gesamt:" in der Legenden-Summenzeile, sobald
    # mindestens eine Farbe uebersprungen wird.
    assert "Zu sticken:" in content


def test_html_export_no_skip_marker_when_nothing_skipped(pattern_with_stitches, tmp_path):
    """Kein Skip-Marker/Footnote, wenn keine Farbe uebersprungen wird (keine
    falsch-positive Kennzeichnung)."""
    target = tmp_path / "noskip.html"
    HTMLExporter(pattern_with_stitches).export(target)
    content = target.read_text(encoding="utf-8")

    assert "[⊘]" not in content
    assert "wird nicht gestickt" not in content


def test_html_export_stats_base_has_skip_fields():
    """_ExportBase deklariert jetzt _skipped_colors/_stitches_to_do fuer
    BEIDE Exporter (vorher nur fuer PDF) -- reiner Typing-/Attribut-Check."""
    from pysticky.io._export_base import _ExportBase

    assert hasattr(_ExportBase, "__annotations__")
    assert "_skipped_colors" in _ExportBase.__annotations__
    assert "_stitches_to_do" in _ExportBase.__annotations__


def test_html_export_dp_mode_hides_backstitch_lines_in_preview(tmp_path):
    """Regression: die Vorschau-Seite (_generate_preview) zeichnete
    Rueckstich-Linien/-Text im DP-Modus trotzdem -- Deckblatt und
    Uebersichtskarte hatten den is_diamond_mode()-Check schon, die
    Vorschau-Seite fehlte ihn. Passiert z.B. wenn ein Pattern per
    Pattern.convert_to_mode() von Stick- auf Diamond-Modus umgeschaltet
    wird: convert_to_mode() raeumt die alten Backstitch-Daten nicht auf,
    DP kennt aber gar kein Rueckstich-Konzept (siehe Legende, die das
    schon korrekt ausblendet)."""
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

    target = tmp_path / "dp_with_backstitch.html"
    HTMLExporter(pattern).export(target)
    content = target.read_text(encoding="utf-8")

    # Kein Rueckstich-Konzept im DP-Modus -> darf nirgends auftauchen
    # (weder als SVG-Linie noch als Text).
    assert "R&uuml;ckstiche" not in content


def test_html_export_mystery_mode_hides_overview_backstitch_note(pattern_with_stitches, tmp_path):
    """Regression: die Uebersichtskarte (_generate_overview) nannte im
    Mystery-Modus weiterhin die exakte Rueckstich-Anzahl als Text -- die
    SVG-Linien der Vorschau waren im selben Abschnitt schon korrekt
    ausgeblendet, der Info-Text darunter aber nicht. Die reine Anzahl
    verraet schon Konturen des Motivs (PDF-Export hat diesen Text-Leak
    nicht, siehe test_pdf_mystery_mode_hides_backstitch_count)."""
    pattern_with_stitches.add_backstitch(0, 0, 4, 4, 0)

    target = tmp_path / "mystery_overview.html"
    HTMLExporter(pattern_with_stitches, mystery_mode=True).export(target)
    content = target.read_text(encoding="utf-8")

    start = content.index("id='uebersicht'")
    end = content.index("id='seite1'")
    overview_section = content[start:end]

    assert "R&uuml;ckstiche" not in overview_section


def test_html_export_escapes_script_tag_in_thread_fields(tmp_path):
    """Security-Regression: Garnname/Hersteller/Katalognummer sind Freitext
    (color_management_dialog.py) und landen in Legende + Mini-Legende jeder
    Musterseite. Ein Muster mit einem Garnnamen wie "<script>alert(1)</script>"
    wuerde -- ohne Escaping -- eine Stored-XSS-Payload in die exportierte
    HTML-Datei schreiben, die beim spaeteren Oeffnen im Browser (durch den
    Nutzer selbst oder jemanden, mit dem die Datei geteilt wird) ausgefuehrt
    wird. PDF-Export hat dieselbe Absicherung ueber pdf_text_escape()
    (siehe test_pdf_export_survives_unescaped_angle_bracket_in_thread_name);
    HTML-Export nutzt dafuer durchgaengig _html_encode()."""
    from pysticky.core import Pattern, Thread

    pattern = Pattern(width=3, height=3)
    idx = pattern.add_color(
        Thread.from_hex(
            "<script>alert(1)</script>",
            "#FF0000",
            manufacturer='"><img src=x onerror=alert(1)>',
            catalog_number="<b>310",
        )
    )
    for x in range(3):
        for y in range(3):
            pattern.set_stitch(x, y, idx)

    target = tmp_path / "xss_thread.html"
    ok = HTMLExporter(pattern).export(target)
    assert ok is True

    content = target.read_text(encoding="utf-8")

    # Die rohen Payloads duerfen an keiner Stelle unescaped im HTML landen.
    assert "<script>alert(1)</script>" not in content
    assert "<img src=x onerror=alert(1)>" not in content
    assert "<b>310" not in content

    # Escapte Form muss stattdessen auftauchen (Beweis, dass der Test
    # tatsaechlich den Escaping-Pfad trifft statt nur zu fehlen).
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content
    assert "&lt;img src=x onerror=alert(1)&gt;" in content
    assert "&lt;b&gt;310" in content
