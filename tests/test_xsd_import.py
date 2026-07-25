# -*- coding: utf-8 -*-
"""Tests fuer XSD-Import (Pattern Maker Binaerformat).

Fokus: stiller Datenverlust bei abgeschnittenen/beschaedigten Dateien
(analog zur OXS-Audit-Runde 77) -- ein reverse-engineertes Binaerformat
ohne offizielle Spezifikation ist besonders anfaellig dafuer, dass
kaputte Dateien klaglos ein unvollstaendiges Muster erzeugen.
"""

import struct


def _pm_header(
    width,
    height,
    color_count,
    has_backstitches=False,
    title=b"",
    author=b"",
    version=1,
):
    """Baut einen minimalen, gueltigen Pattern-Maker-Header (roh, Bytes)."""
    sig = b"PM\x00"
    ver = struct.pack("B", version)
    dims = struct.pack("<HH", width, height)
    cc = struct.pack("<H", color_count)
    flags = struct.pack("<H", 1 if has_backstitches else 0)
    title_field = title.ljust(64, b"\x00")[:64]
    author_field = author.ljust(32, b"\x00")[:32]
    return sig + ver + dims + cc + flags + title_field + author_field


def _pm_color(r, g, b, name=b"Red", dmc=b"310"):
    """Baut einen minimalen Palette-Eintrag (roh, Bytes)."""
    name_field = name.ljust(32, b"\x00")[:32]
    dmc_field = dmc.ljust(8, b"\x00")[:8]
    symbol_byte = b"\x00"
    return struct.pack("BBB", r, g, b) + name_field + dmc_field + symbol_byte


def test_import_valid_minimal_file(tmp_path):
    """Eine vollstaendige, gueltige Minimaldatei importiert ohne Fehler/Warnungen."""
    from pysticky.io.formats.xsd_import import import_xsd

    header = _pm_header(3, 2, 1, title=b"Test", author=b"Me")
    colors = _pm_color(255, 0, 0)
    # Roh-Grid: 3x2 = 6 Zellen, abwechselnd Farbe 0 / leer
    grid = bytes([0, 0xFE, 0, 0xFE, 0, 0xFE])
    f = tmp_path / "valid.xsd"
    f.write_bytes(header + colors + grid)

    pattern, errors, warnings = import_xsd(f)

    assert errors == []
    assert warnings == []
    assert pattern is not None
    assert (pattern.width, pattern.height) == (3, 2)
    assert pattern.get_stitch(0, 0) == 0
    assert pattern.get_stitch(1, 0) is None


def test_import_raw_grid_truncated_mid_file_produces_warning(tmp_path):
    """Bricht die Datei mitten im (unkomprimierten) Grid ab, wurde das bisher
    komplett stillschweigend verschluckt -- kein Fehler, keine Warnung, die
    fehlenden Stiche erschienen einfach als leer. Jetzt gibt es eine Warnung,
    und die bereits gelesenen Stiche bleiben unbeeinflusst."""
    from pysticky.io.formats.xsd_import import import_xsd

    header = _pm_header(5, 3, 1)  # 5x3 = 15 Zellen erwartet
    colors = _pm_color(0, 255, 0)
    grid = bytes([0, 0, 0])  # nur 3 von 15 Zellen vorhanden
    f = tmp_path / "truncated_raw.xsd"
    f.write_bytes(header + colors + grid)

    pattern, errors, warnings = import_xsd(f)

    assert errors == []
    assert pattern is not None
    # Bereits gelesene Stiche bleiben erhalten
    assert pattern.get_stitch(0, 0) == 0
    assert pattern.get_stitch(1, 0) == 0
    assert pattern.get_stitch(2, 0) == 0
    # Fehlende Zellen sind leer...
    assert pattern.get_stitch(3, 0) is None
    assert pattern.get_stitch(0, 1) is None
    # ...aber NICHT stillschweigend -- eine Warnung muss auf das Problem hinweisen
    assert any("unvollst" in w.lower() for w in warnings)
    assert any("15" in w for w in warnings)


def test_import_rle_grid_truncated_mid_file_produces_warning(tmp_path):
    """Dieselbe stille-Datenverlust-Gefahr besteht auch im RLE-komprimierten
    Zweig des Grid-Readers -- muss ebenfalls eine Warnung auslösen."""
    from pysticky.io.formats.xsd_import import import_xsd

    header = _pm_header(3, 3, 1)  # 3x3 = 9 Zellen erwartet
    colors = _pm_color(10, 20, 30)
    # Format-Marker 0xFF (RLE), dann RLE-Stream: Run-Marker 0xFF, count=3,
    # color=0 -> fuellt Zeile 0 komplett (3 Zellen). Datei endet danach
    # abrupt, Zeilen 1 und 2 fehlen.
    grid = bytes([0xFF, 0xFF, 3, 0])
    f = tmp_path / "truncated_rle.xsd"
    f.write_bytes(header + colors + grid)

    pattern, errors, warnings = import_xsd(f)

    assert errors == []
    assert pattern is not None
    assert pattern.get_stitch(0, 0) == 0
    assert pattern.get_stitch(1, 0) == 0
    assert pattern.get_stitch(2, 0) == 0
    assert pattern.get_stitch(0, 1) is None
    assert pattern.get_stitch(0, 2) is None
    assert any("unvollst" in w.lower() for w in warnings)


def test_import_complete_rle_grid_produces_no_truncation_warning(tmp_path):
    """Ein vollstaendiger RLE-Grid-Stream (alle Zeilen gefuellt) darf die neue
    Truncation-Warnung NICHT ausloesen -- Regressionsschutz gegen falsch-positive
    Warnungen bei regulaer beendeten Dateien."""
    from pysticky.io.formats.xsd_import import import_xsd

    header = _pm_header(3, 1, 1)  # 3x1 = 3 Zellen
    colors = _pm_color(10, 20, 30)
    # Format-Marker 0xFF, RLE-Stream: Run-Marker 0xFF, count=3, color=0
    grid = bytes([0xFF, 0xFF, 3, 0])
    f = tmp_path / "complete_rle.xsd"
    f.write_bytes(header + colors + grid)

    pattern, errors, warnings = import_xsd(f)

    assert errors == []
    assert warnings == []
    assert pattern.get_stitch(0, 0) == 0
    assert pattern.get_stitch(2, 0) == 0


def test_import_grid_color_index_out_of_palette_range_produces_warning(tmp_path):
    """Ein Grid-Byte, das auf einen Palette-Index ausserhalb der eingelesenen
    Farbanzahl zeigt (kaputte/manipulierte Datei), wird als leere Zelle
    behandelt -- mit Warnung, nicht stillschweigend."""
    from pysticky.io.formats.xsd_import import import_xsd

    header = _pm_header(3, 1, 1)  # nur 1 Farbe (Index 0 gueltig)
    colors = _pm_color(0, 0, 255)
    grid = bytes([0, 5, 0xFE])  # Index 5 existiert nicht in der Palette
    f = tmp_path / "bad_index.xsd"
    f.write_bytes(header + colors + grid)

    pattern, errors, warnings = import_xsd(f)

    assert errors == []
    assert pattern.get_stitch(0, 0) == 0
    assert pattern.get_stitch(1, 0) is None
    assert any("5" in w and "Palette" in w for w in warnings)


def test_import_cp1252_umlauts_in_title_and_author(tmp_path):
    """Titel/Autor werden im Pattern-Maker-Format als cp1252 (Windows-1252)
    gespeichert -- deutsche Umlaute muessen korrekt dekodiert werden, kein
    Mojibake und kein UnicodeDecodeError."""
    from pysticky.io.formats.xsd_import import import_xsd

    title = "Kreuzstichmuster für Öl-Läufer".encode("cp1252")
    author = "Björn Müller".encode("cp1252")
    header = _pm_header(1, 1, 0, title=title, author=author)
    grid = bytes([0xFE])
    f = tmp_path / "umlauts.xsd"
    f.write_bytes(header + grid)

    pattern, errors, warnings = import_xsd(f)

    assert errors == []
    assert pattern.name == "Kreuzstichmuster für Öl-Läufer"
    assert pattern.metadata["author"] == "Björn Müller"


def test_import_truncated_header_yields_clean_error_not_crash(tmp_path):
    """Bricht die Datei bereits mitten im Header ab, darf der Import nicht
    mit einer rohen, fuer den Nutzer unverstaendlichen struct.error-Exception
    crashen -- import_file() muss None + eine lesbare Fehlermeldung liefern."""
    from pysticky.io.formats.xsd_import import import_xsd

    # Nur Signatur + Version vorhanden, Rest (Dimensionen etc.) fehlt
    truncated = b"PM\x001"
    f = tmp_path / "truncated_header.xsd"
    f.write_bytes(truncated)

    pattern, errors, warnings = import_xsd(f)

    assert pattern is None
    assert len(errors) == 1
    # Fehlermeldung muss auf das abgeschnittene Feld hinweisen, keine
    # rohe "unpack requires a buffer of X bytes" struct.error-Meldung
    assert "truct.error" not in errors[0]
    assert "kurz" in errors[0] or "Dimensionen" in errors[0]


def test_import_backstitch_color_index_out_of_range_skipped_with_warning(tmp_path):
    """Rueckstich mit kaputtem Farbindex wird uebersprungen, nicht klaglos
    mit ungueltigem Index im Pattern hinterlassen (Regressionsschutz fuer
    bereits bestehenden Clamp aus Runde 30)."""
    from pysticky.io.formats.xsd_import import import_xsd

    header = _pm_header(2, 2, 1, has_backstitches=True)
    colors = _pm_color(10, 20, 30)
    grid = bytes([0, 0, 0, 0])
    bs_count = struct.pack("<H", 1)
    bs_coords = struct.pack("<hhhh", 0, 0, 2, 2)
    bs_color = struct.pack("B", 99)  # existiert nicht in der Palette
    f = tmp_path / "bad_backstitch_color.xsd"
    f.write_bytes(header + colors + grid + bs_count + bs_coords + bs_color)

    pattern, errors, warnings = import_xsd(f)

    assert errors == []
    assert pattern.backstitches == []
    assert any("99" in w for w in warnings)
