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
