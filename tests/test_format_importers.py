# -*- coding: utf-8 -*-
"""
Tests fuer die binaeren Format-Importer (PAT, XSD).

Die Formate sind reverse-engineered. Wir testen primaer:
- `can_import()`-Erkennungs-Logik
- Fehlerpfade (nicht-existent, falsche Signatur, leere Datei)
- Helper-Methoden (Pascal-Strings, Fixed-Strings)
- Convenience-Funktionen `import_pat()` / `import_xsd()`

Roundtrip-Tests mit synthetischen Bytes sind hier nicht praktikabel, da
die Format-Spezifikation zu komplex ist und mehrere Versionen unterstuetzt
werden (PAT v5-v10).
"""

import struct
from io import BytesIO

from pysticky.io.formats.pat_import import (
    PATHeader,
    PATImporter,
    PATImportError,
    import_pat,
)
from pysticky.io.formats.xsd_import import (
    XSDHeader,
    XSDImporter,
    XSDImportError,
    import_xsd,
)

# ============================================================================
# PAT: can_import
# ============================================================================


def test_pat_can_import_rejects_missing_file(tmp_path):
    importer = PATImporter()
    assert importer.can_import(tmp_path / "fehlt.pat") is False


def test_pat_can_import_rejects_wrong_extension(tmp_path):
    f = tmp_path / "data.xml"
    f.write_bytes(b"PAT\x08")
    importer = PATImporter()
    assert importer.can_import(f) is False


def test_pat_can_import_rejects_wrong_signature(tmp_path):
    f = tmp_path / "data.pat"
    f.write_bytes(b"XYZ\x08\x00\x00")
    importer = PATImporter()
    assert importer.can_import(f) is False


def test_pat_can_import_accepts_valid_signature(tmp_path):
    f = tmp_path / "data.pat"
    f.write_bytes(b"PAT\x08\x00\x00")
    importer = PATImporter()
    assert importer.can_import(f) is True


# ============================================================================
# PAT: import_file Error-Paths
# ============================================================================


def test_pat_import_missing_file_returns_none(tmp_path):
    importer = PATImporter()
    result = importer.import_file(tmp_path / "fehlt.pat")
    assert result is None
    assert any("nicht gefunden" in e for e in importer.errors)


def test_pat_import_wrong_signature_returns_none(tmp_path):
    f = tmp_path / "data.pat"
    f.write_bytes(b"NOPE_NO_PAT_HEADER" + b"\x00" * 100)
    importer = PATImporter()
    result = importer.import_file(f)
    assert result is None
    assert len(importer.errors) > 0


def test_pat_import_truncated_file_returns_none(tmp_path):
    f = tmp_path / "data.pat"
    # PAT-Signatur + Version, aber kein Header danach
    f.write_bytes(b"PAT\x08")
    importer = PATImporter()
    result = importer.import_file(f)
    assert result is None


def test_pat_convenience_returns_tuple(tmp_path):
    """`import_pat()` liefert (pattern, errors, warnings)."""
    f = tmp_path / "fehlt.pat"
    pattern, errors, warnings = import_pat(f)
    assert pattern is None
    assert isinstance(errors, list)
    assert isinstance(warnings, list)
    assert len(errors) > 0


# ============================================================================
# PAT: Helper-Methoden
# ============================================================================


def test_pat_read_pascal_string_basic():
    """Pascal-String: 1 Laengen-Byte + Daten."""
    importer = PATImporter()
    f = BytesIO(b"\x05Hello\x00")
    result = importer._read_pascal_string(f)
    assert result == "Hello"


def test_pat_read_pascal_string_empty():
    importer = PATImporter()
    f = BytesIO(b"\x00")
    assert importer._read_pascal_string(f) == ""


def test_pat_read_pascal_string_cp1252():
    """cp1252 dekodiert Umlaute korrekt."""
    importer = PATImporter()
    # "Müller" in cp1252: 4D FC 6C 6C 65 72 (FC = ü)
    data = b"\x06\x4d\xfc\x6c\x6c\x65\x72"
    f = BytesIO(data)
    assert importer._read_pascal_string(f) == "Müller"


def test_pat_read_fixed_string_truncates_at_null():
    """Fixed-String stoppt am ersten NULL-Byte."""
    importer = PATImporter()
    f = BytesIO(b"Hello\x00garbage_after\x00")
    assert importer._read_fixed_string(f, 16) == "Hello"


def test_pat_read_fixed_string_from_bytes():
    """Direkt-Variante: aus bytes ohne File-Handle."""
    importer = PATImporter()
    assert importer._read_fixed_string_from_bytes(b"DMC310\x00") == "DMC310"
    assert importer._read_fixed_string_from_bytes(b"\x00") == ""


# ============================================================================
# PAT: PATHeader Dataclass
# ============================================================================


def test_pat_header_dataclass_construction():
    """Header laesst sich als reines Datenobjekt bauen."""
    h = PATHeader(
        signature=b"PAT",
        version=8,
        width=50,
        height=40,
        color_count=10,
        fabric_count=14,
        title="Test",
        author="Hans",
        copyright="MIT",
    )
    assert h.width == 50 and h.height == 40
    assert h.color_count == 10


def test_pat_import_error_is_exception():
    """PATImportError ist eine echte Exception-Subklasse."""
    assert issubclass(PATImportError, Exception)


def _build_pat_legacy_header(
    version: int, width: int, height: int, color_count: int = 0, fabric_count: int = 14
) -> bytes:
    """
    Baut einen minimalen Legacy-PAT-Header (Version < 8).

    Struktur: 3-Byte-Signatur "PAT", 1 Byte Version, 4 Bytes Width/Height,
    2 Bytes color_count, 1 Byte fabric_count, 1 Byte Reserved, dann je
    32 Bytes Title/Author/Copyright (null-terminierte Fixed-Strings).
    """
    return (
        b"PAT"
        + struct.pack("<B", version)
        + struct.pack("<HH", width, height)
        + struct.pack("<H", color_count)
        + struct.pack("B", fabric_count)
        + b"\x00"  # Reserved
        + b"\x00" * 32  # Title
        + b"\x00" * 32  # Author
        + b"\x00" * 32  # Copyright
    )


def test_pat_import_oversized_pattern_produces_warning(tmp_path):
    """Patterns > 1000 in einer Dimension geben eine Warnung, scheitern
    aber noch nicht (Konsistenz mit dem gleichwertigen XSD-Verhalten)."""
    f = tmp_path / "data.pat"
    f.write_bytes(_build_pat_legacy_header(version=5, width=1500, height=10))
    importer = PATImporter()
    importer.import_file(f)
    assert any("Gro" in w or "gro" in w for w in importer.warnings)


def test_pat_import_rejects_pattern_above_hard_limit(tmp_path):
    """Regression: width/height kommen aus einem ungeprueften
    struct.unpack (max. 65535 je Achse) -- ohne harte Obergrenze koennte
    eine beschaedigte Datei eine Multi-Milliarden-Zellen-Allokation
    versuchen. Muss wie der native .pxs-Loader bei > 2000x2000 fehlschlagen."""
    f = tmp_path / "data.pat"
    f.write_bytes(_build_pat_legacy_header(version=5, width=40000, height=10))
    importer = PATImporter()
    result = importer.import_file(f)
    assert result is None
    assert any("zu gro" in e.lower() for e in importer.errors)


def test_pat_import_accepts_pattern_at_hard_limit_boundary(tmp_path):
    """Exakt 2000x2000 ist noch erlaubt (nur > 2000 wird abgelehnt)."""
    f = tmp_path / "data.pat"
    f.write_bytes(_build_pat_legacy_header(version=5, width=2000, height=2000))
    importer = PATImporter()
    result = importer.import_file(f)
    assert result is not None
    assert result.width == 2000 and result.height == 2000


# ============================================================================
# XSD: can_import
# ============================================================================


def test_xsd_can_import_rejects_missing_file(tmp_path):
    importer = XSDImporter()
    assert importer.can_import(tmp_path / "fehlt.xsd") is False


def test_xsd_can_import_rejects_wrong_extension(tmp_path):
    f = tmp_path / "data.xml"
    f.write_bytes(b"PM\x05" + b"\x00" * 100)
    importer = XSDImporter()
    assert importer.can_import(f) is False


def test_xsd_can_import_accepts_pm_signature(tmp_path):
    f = tmp_path / "data.xsd"
    f.write_bytes(b"PM\x05" + b"\x00" * 100)
    importer = XSDImporter()
    assert importer.can_import(f) is True


def test_xsd_can_import_accepts_pmx_signature(tmp_path):
    f = tmp_path / "data.xsd"
    f.write_bytes(b"PMX\x01" + b"\x00" * 100)
    importer = XSDImporter()
    assert importer.can_import(f) is True


def test_xsd_can_import_accepts_large_file_without_signature(tmp_path):
    """XSD ohne erkennbare Signatur, aber Datei > 100 bytes: as-import-fall."""
    f = tmp_path / "data.xsd"
    f.write_bytes(b"XYZ" + b"\x00" * 200)
    importer = XSDImporter()
    assert importer.can_import(f) is True


def test_xsd_can_import_rejects_tiny_file_without_signature(tmp_path):
    f = tmp_path / "data.xsd"
    f.write_bytes(b"XYZ" + b"\x00" * 5)  # < 100 Bytes
    importer = XSDImporter()
    assert importer.can_import(f) is False


# ============================================================================
# XSD: import_file Error-Paths
# ============================================================================


def test_xsd_import_missing_file_returns_none(tmp_path):
    importer = XSDImporter()
    result = importer.import_file(tmp_path / "fehlt.xsd")
    assert result is None
    assert any("nicht gefunden" in e for e in importer.errors)


def test_xsd_import_truncated_file_returns_none(tmp_path):
    f = tmp_path / "data.xsd"
    f.write_bytes(b"PM\x05")  # nur Header, keine Daten
    importer = XSDImporter()
    result = importer.import_file(f)
    assert result is None


def test_xsd_convenience_returns_tuple(tmp_path):
    """Regression (Test-Qualitaets-Audit): anders als die PAT-Schwester
    (test_pat_convenience_returns_tuple) fehlte hier `len(errors) > 0` --
    ein import_xsd(), das den Fehler ("Datei fehlt") verschluckt und eine
    leere errors-Liste zurueckgibt, waere durch `isinstance(errors, list)`
    allein nicht aufgefallen."""
    f = tmp_path / "fehlt.xsd"
    pattern, errors, warnings = import_xsd(f)
    assert pattern is None
    assert isinstance(errors, list)
    assert isinstance(warnings, list)
    assert len(errors) > 0


def _build_pm_header(
    version: int, width: int, height: int, color_count: int = 0, flags: int = 0
) -> bytes:
    """
    Baut einen minimalen PM-XSD-Header.

    Struktur: 3-Byte-Signatur "PMX" (passt `signature[:2] == b'PM'`),
    1 Byte Version, 4 Bytes Width/Height, 2 Bytes color_count, 2 Bytes Flags,
    64 Bytes Title, 32 Bytes Author, dann Padding.
    """
    return (
        b"PMX"  # 3-Byte-Sig
        + struct.pack("<B", version)  # 1 Byte Version
        + struct.pack("<HH", width, height)  # 4 Bytes Dimensionen
        + struct.pack("<H", color_count)  # 2 Bytes Farben
        + struct.pack("<H", flags)  # 2 Bytes Flags
        + b"\x00" * 96  # 64 Title + 32 Author
        + b"\x00" * 100  # Padding fuer Color-Reading
    )


def test_xsd_import_invalid_dimensions_fails(tmp_path):
    """Wenn der Header width=0 oder height=0 liefert, muss der Importer
    eine Fehlermeldung produzieren und None zurueckgeben."""
    f = tmp_path / "data.xsd"
    f.write_bytes(_build_pm_header(version=5, width=0, height=10))
    importer = XSDImporter()
    result = importer.import_file(f)
    assert result is None
    assert any("Ung" in e for e in importer.errors)  # "Ungueltige Dimensionen"


def test_xsd_import_oversized_pattern_produces_warning(tmp_path):
    """Patterns > 1000 in einer Dimension geben eine Warnung — aber lassen
    den Import weiterlaufen (er bricht erst beim Lesen der Daten ab)."""
    f = tmp_path / "data.xsd"
    f.write_bytes(_build_pm_header(version=5, width=2000, height=10))
    importer = XSDImporter()
    importer.import_file(f)
    # Egal ob result None ist oder nicht — warning sollte kommen
    assert any("Gro" in w or "gro" in w for w in importer.warnings)


def test_xsd_import_rejects_pattern_above_hard_limit(tmp_path):
    """Regression (Runde 20): width/height kommen aus einem ungeprueften
    struct.unpack (max. 65535 je Achse). xsd_import.py hatte -- anders als
    pat_import.py/oxs_io.py/file_io.py -- NUR eine Warnung ab 1000, aber
    KEINE harte Obergrenze. Eine beschaedigte Datei mit width=height=65535
    haette dadurch eine Multi-Milliarden-Zellen-Pattern-Allokation
    ausgeloest, statt sauber mit einer Fehlermeldung abgelehnt zu werden."""
    f = tmp_path / "data.xsd"
    f.write_bytes(_build_pm_header(version=5, width=40000, height=10))
    importer = XSDImporter()
    result = importer.import_file(f)
    assert result is None
    assert any("zu gro" in e.lower() for e in importer.errors)


def test_xsd_import_accepts_pattern_at_hard_limit_boundary(tmp_path):
    """Exakt 2000x2000 ist noch erlaubt (nur > 2000 wird abgelehnt)."""
    f = tmp_path / "data.xsd"
    f.write_bytes(_build_pm_header(version=5, width=2000, height=2000))
    importer = XSDImporter()
    result = importer.import_file(f)
    assert result is not None
    assert result.width == 2000 and result.height == 2000


# ============================================================================
# PAT/XSD: Farbindex-Clamping (Runde 20)
# ============================================================================


def test_pat_clamp_color_index_passes_through_valid_index():
    importer = PATImporter()
    assert importer._clamp_color_index(3, color_count=10) == 3
    assert importer._clamp_color_index(None, color_count=10) is None


def test_pat_clamp_color_index_drops_out_of_range_index_with_warning():
    """Regression: ein Grid-Byte, das auf einen Farbindex jenseits der
    tatsaechlich eingelesenen Palette zeigt (beschaedigte/verkuerzte
    Datei), wurde bisher klaglos an Layer.set_stitch() durchgereicht --
    Layer.set_stitch() prueft nur x/y, nicht den Farbindex. Der betroffene
    Stich fehlte dadurch stillschweigend in allen Statistiken/Exporten."""
    importer = PATImporter()
    assert importer._invalid_color_index_warned is False

    result = importer._clamp_color_index(10, color_count=5)

    assert result is None
    assert importer._invalid_color_index_warned is True
    assert any("außerhalb der Palette" in w for w in importer.warnings)


def test_pat_clamp_color_index_warns_only_once_per_import():
    importer = PATImporter()
    importer._clamp_color_index(10, color_count=5)
    importer._clamp_color_index(11, color_count=5)
    importer._clamp_color_index(12, color_count=5)
    assert sum("außerhalb der Palette" in w for w in importer.warnings) == 1


def test_xsd_clamp_color_index_passes_through_valid_index():
    importer = XSDImporter()
    assert importer._clamp_color_index(3, color_count=10) == 3
    assert importer._clamp_color_index(None, color_count=10) is None


def test_xsd_clamp_color_index_drops_out_of_range_index_with_warning():
    importer = XSDImporter()
    result = importer._clamp_color_index(10, color_count=5)
    assert result is None
    assert any("außerhalb der Palette" in w for w in importer.warnings)


# ============================================================================
# PAT/XSD: Backstitch-Farbindex-Clamping (Runde 30)
#
# Grid-Stiche laufen schon lange durch _clamp_color_index (Runde 20), aber
# Backstitches nahmen den rohen, aus der Datei gelesenen Farbindex bislang
# UNGEPRUEFT entgegen -- ein korruptes .pat/.xsd mit einem Backstitch-
# Farbindex jenseits der eingelesenen Palette landete klaglos (ohne
# Warnung) als Backstitch mit nicht existierendem Farbindex im Pattern.
# ============================================================================


def _build_xsd_with_backstitch(color_index: int) -> bytes:
    """Baut eine minimale, vollstaendige XSD-Datei (Header + 1 Farbe +
    leeres 2x2-Grid + 1 Backstitch mit dem gegebenen Farbindex)."""
    header = (
        b"PMX"
        + struct.pack("<B", 5)  # version
        + struct.pack("<HH", 2, 2)  # width, height
        + struct.pack("<H", 1)  # color_count
        + struct.pack("<H", 0x01)  # flags: has_backstitches
        + b"Title".ljust(64, b"\x00")
        + b"Author".ljust(32, b"\x00")
    )
    color_data = (
        struct.pack("BBB", 255, 0, 0)  # RGB
        + b"Red".ljust(32, b"\x00")  # Name
        + b"\x00" * 8  # DMC-Nummer
        + b"\x00"  # Symbol (verworfen)
    )
    grid_data = bytes([0xFE, 0xFE, 0xFE, 0xFE])  # 2x2, alle Zellen leer
    backstitch_data = (
        struct.pack("<H", 1)  # count
        + struct.pack("<hhhh", 0, 0, 2, 2)  # Koordinaten
        + struct.pack("B", color_index)
    )
    return header + color_data + grid_data + backstitch_data


def test_xsd_import_drops_out_of_range_backstitch_color_index(tmp_path):
    f = tmp_path / "data.xsd"
    f.write_bytes(_build_xsd_with_backstitch(color_index=99))

    importer = XSDImporter()
    pattern = importer.import_file(f)

    assert pattern is not None
    assert pattern.backstitches == []
    assert any("außerhalb der Palette" in w for w in importer.warnings)


def test_xsd_import_keeps_in_range_backstitch_color_index(tmp_path):
    """Gegenprobe: ein gueltiger Farbindex (0, einzige eingelesene Farbe)
    darf weiterhin normal ankommen."""
    f = tmp_path / "data.xsd"
    f.write_bytes(_build_xsd_with_backstitch(color_index=0))

    importer = XSDImporter()
    pattern = importer.import_file(f)

    assert pattern is not None
    assert len(pattern.backstitches) == 1
    assert pattern.backstitches[0].color_index == 0


def _build_pat_with_backstitch(color_index: int) -> bytes:
    """Baut eine minimale, vollstaendige Legacy-PAT-Datei (Version 5:
    Header + 1 Farbe + leeres 2x2-Grid + 1 Backstitch)."""
    header = _build_pat_legacy_header(version=5, width=2, height=2, color_count=1)
    color_data = (
        struct.pack("BBB", 255, 0, 0)  # RGB
        + b"\x00" * 6  # DMC-Nummer (Legacy: 6 Bytes)
        + b"Red".ljust(20, b"\x00")  # Name (Legacy: 20 Bytes)
        + b"\x00"  # Symbol (optional, hier absichtlich fehlend/leer -> Fallback-Symbol)
    )
    grid_data = bytes([0xFE, 0xFE, 0xFE, 0xFE])  # 2x2, alle Zellen leer
    backstitch_data = (
        struct.pack("<I", 1)  # count (Legacy: 4 Bytes)
        + struct.pack("<hhhh", 0, 0, 2, 2)  # Koordinaten
        + struct.pack("B", color_index)  # Legacy: 1 Byte Farbe
    )
    return header + color_data + grid_data + backstitch_data


def test_pat_import_drops_out_of_range_backstitch_color_index(tmp_path):
    f = tmp_path / "data.pat"
    f.write_bytes(_build_pat_with_backstitch(color_index=99))

    importer = PATImporter()
    pattern = importer.import_file(f)

    assert pattern is not None
    assert pattern.backstitches == []
    assert any("außerhalb der Palette" in w for w in importer.warnings)


def test_pat_import_keeps_in_range_backstitch_color_index(tmp_path):
    f = tmp_path / "data.pat"
    f.write_bytes(_build_pat_with_backstitch(color_index=0))

    importer = PATImporter()
    pattern = importer.import_file(f)

    assert pattern is not None
    assert len(pattern.backstitches) == 1
    assert pattern.backstitches[0].color_index == 0


# ============================================================================
# PAT: Rueckstich-Koordinaten-Grenzen (Runde 78)
#
# Grid-Farbindizes (Runde 20) und Backstitch-Farbindizes (Runde 30) werden
# schon gegen die eingelesene Palette geprueft -- Backstitch-KOORDINATEN
# wurden aber nirgends gegen die Mustergroesse geprueft. Weder
# Pattern.add_backstitch() noch BackstitchManager.add() validieren x/y, ein
# korruptes .pat mit Koordinaten weit ausserhalb des Grids (negativ oder >
# 2x Breite/Hoehe) landete dadurch klaglos im Pattern -- der Rueckstich war
# dann irgendwo unsichtbar weit ausserhalb des Canvas "verschwunden", ohne
# dass der Nutzer je von verworfenen Daten erfuhr.
# ============================================================================


def _build_pat_with_backstitch_coords(x1: int, y1: int, x2: int, y2: int) -> bytes:
    """Baut eine minimale, vollstaendige Legacy-PAT-Datei (Version 5:
    Header + 1 Farbe + leeres 2x2-Grid + 1 Backstitch mit den gegebenen
    Koordinaten in ganzen Stichen)."""
    header = _build_pat_legacy_header(version=5, width=2, height=2, color_count=1)
    color_data = (
        struct.pack("BBB", 255, 0, 0)  # RGB
        + b"\x00" * 6  # DMC-Nummer (Legacy: 6 Bytes)
        + b"Red".ljust(20, b"\x00")  # Name (Legacy: 20 Bytes)
        + b"\x00"  # Symbol (optional, fehlt hier -> Fallback-Symbol)
    )
    grid_data = bytes([0xFF, 0xFF, 0xFF, 0xFF])  # 2x2, alle Zellen leer (Sentinel 0xFF)
    backstitch_data = (
        struct.pack("<I", 1)  # count (Legacy: 4 Bytes)
        + struct.pack("<hhhh", x1, y1, x2, y2)
        + struct.pack("B", 0)  # Farbindex (gueltig, einzige eingelesene Farbe)
    )
    return header + color_data + grid_data + backstitch_data


def test_pat_import_drops_backstitch_far_outside_pattern_bounds(tmp_path):
    """Regression: Koordinaten weit ausserhalb (2x2-Muster -> halbe Stiche
    max. 4x4) wurden bislang klaglos, ohne Warnung uebernommen."""
    f = tmp_path / "data.pat"
    f.write_bytes(_build_pat_with_backstitch_coords(0, 0, 5000, 5000))

    importer = PATImporter()
    pattern = importer.import_file(f)

    assert pattern is not None
    assert pattern.backstitches == []
    assert any("außerhalb der Mustergrenzen" in w for w in importer.warnings)


def test_pat_import_drops_backstitch_with_negative_coords(tmp_path):
    """Negative Koordinaten sind ebenso ausserhalb des gueltigen Bereichs
    wie zu grosse -- beide Richtungen muessen abgefangen werden."""
    f = tmp_path / "data.pat"
    f.write_bytes(_build_pat_with_backstitch_coords(-50, -50, 2, 2))

    importer = PATImporter()
    pattern = importer.import_file(f)

    assert pattern is not None
    assert pattern.backstitches == []
    assert any("außerhalb der Mustergrenzen" in w for w in importer.warnings)


def test_pat_import_keeps_backstitch_within_pattern_bounds(tmp_path):
    """Gegenprobe: Koordinaten innerhalb des 2x2-Musters (max. 4x4 halbe
    Stiche) duerfen weiterhin normal ankommen."""
    f = tmp_path / "data.pat"
    f.write_bytes(_build_pat_with_backstitch_coords(0, 0, 2, 2))

    importer = PATImporter()
    pattern = importer.import_file(f)

    assert pattern is not None
    assert len(pattern.backstitches) == 1
    assert not any("außerhalb der Mustergrenzen" in w for w in importer.warnings)


def test_pat_import_warns_only_once_for_multiple_bad_backstitch_coords(tmp_path):
    """Wie beim Farbindex-Clamping (Runde 20): mehrere kaputte Rueckstiche
    sollen nur eine einzige Sammel-Warnung erzeugen, keine Spam-Flut."""
    header = _build_pat_legacy_header(version=5, width=2, height=2, color_count=1)
    color_data = struct.pack("BBB", 255, 0, 0) + b"\x00" * 6 + b"Red".ljust(20, b"\x00") + b"\x00"
    grid_data = bytes([0xFF, 0xFF, 0xFF, 0xFF])
    backstitch_data = (
        struct.pack("<I", 3)  # count: 3 kaputte Rueckstiche
        + struct.pack("<hhhh", 0, 0, 5000, 5000)
        + struct.pack("B", 0)
        + struct.pack("<hhhh", -10, -10, 0, 0)
        + struct.pack("B", 0)
        + struct.pack("<hhhh", 0, 0, 9999, 0)
        + struct.pack("B", 0)
    )
    f = tmp_path / "data.pat"
    f.write_bytes(header + color_data + grid_data + backstitch_data)

    importer = PATImporter()
    pattern = importer.import_file(f)

    assert pattern is not None
    assert pattern.backstitches == []
    assert sum("außerhalb der Mustergrenzen" in w for w in importer.warnings) == 1


# ============================================================================
# XSD: Rueckstich-Koordinaten-Grenzen (Runde 79, analog PAT Runde 78)
#
# Dieselbe Luecke wie beim PAT-Importer: XSD-Rueckstich-Koordinaten wurden
# nirgends gegen die Mustergroesse geprueft, bevor sie an
# Pattern.add_backstitch() weitergereicht wurden.
# ============================================================================


def _build_xsd_with_backstitch_coords(x1: int, y1: int, x2: int, y2: int) -> bytes:
    """Baut eine minimale, vollstaendige XSD-Datei (Header + 1 Farbe +
    leeres 2x2-Grid + 1 Backstitch mit den gegebenen Koordinaten in
    halben Stichen -- XSD liefert diese bereits unskaliert)."""
    header = (
        b"PMX"
        + struct.pack("<B", 5)  # version
        + struct.pack("<HH", 2, 2)  # width, height
        + struct.pack("<H", 1)  # color_count
        + struct.pack("<H", 0x01)  # flags: has_backstitches
        + b"Title".ljust(64, b"\x00")
        + b"Author".ljust(32, b"\x00")
    )
    color_data = (
        struct.pack("BBB", 255, 0, 0)  # RGB
        + b"Red".ljust(32, b"\x00")  # Name
        + b"\x00" * 8  # DMC-Nummer
        + b"\x00"  # Symbol (verworfen)
    )
    grid_data = bytes([0xFE, 0xFE, 0xFE, 0xFE])  # 2x2, alle Zellen leer
    backstitch_data = (
        struct.pack("<H", 1)  # count
        + struct.pack("<hhhh", x1, y1, x2, y2)  # Koordinaten
        + struct.pack("B", 0)  # Farbindex (gueltig, einzige eingelesene Farbe)
    )
    return header + color_data + grid_data + backstitch_data


def test_xsd_import_drops_backstitch_far_outside_pattern_bounds(tmp_path):
    """Regression: Koordinaten weit ausserhalb (2x2-Muster -> halbe Stiche
    max. 4x4) wurden bislang klaglos, ohne Warnung uebernommen."""
    f = tmp_path / "data.xsd"
    f.write_bytes(_build_xsd_with_backstitch_coords(0, 0, 5000, 5000))

    importer = XSDImporter()
    pattern = importer.import_file(f)

    assert pattern is not None
    assert pattern.backstitches == []
    assert any("außerhalb der Mustergrenzen" in w for w in importer.warnings)


def test_xsd_import_drops_backstitch_with_negative_coords(tmp_path):
    f = tmp_path / "data.xsd"
    f.write_bytes(_build_xsd_with_backstitch_coords(-50, -50, 2, 2))

    importer = XSDImporter()
    pattern = importer.import_file(f)

    assert pattern is not None
    assert pattern.backstitches == []
    assert any("außerhalb der Mustergrenzen" in w for w in importer.warnings)


def test_xsd_import_keeps_backstitch_within_pattern_bounds(tmp_path):
    """Gegenprobe: Koordinaten innerhalb des 2x2-Musters (max. 4x4 halbe
    Stiche) duerfen weiterhin normal ankommen."""
    f = tmp_path / "data.xsd"
    f.write_bytes(_build_xsd_with_backstitch_coords(0, 0, 2, 2))

    importer = XSDImporter()
    pattern = importer.import_file(f)

    assert pattern is not None
    assert len(pattern.backstitches) == 1
    assert not any("außerhalb der Mustergrenzen" in w for w in importer.warnings)


def test_xsd_import_warns_only_once_for_multiple_bad_backstitch_coords(tmp_path):
    header = (
        b"PMX"
        + struct.pack("<B", 5)
        + struct.pack("<HH", 2, 2)
        + struct.pack("<H", 1)
        + struct.pack("<H", 0x01)
        + b"Title".ljust(64, b"\x00")
        + b"Author".ljust(32, b"\x00")
    )
    color_data = struct.pack("BBB", 255, 0, 0) + b"Red".ljust(32, b"\x00") + b"\x00" * 8 + b"\x00"
    grid_data = bytes([0xFE, 0xFE, 0xFE, 0xFE])
    backstitch_data = (
        struct.pack("<H", 3)  # count: 3 kaputte Rueckstiche
        + struct.pack("<hhhh", 0, 0, 5000, 5000)
        + struct.pack("B", 0)
        + struct.pack("<hhhh", -10, -10, 0, 0)
        + struct.pack("B", 0)
        + struct.pack("<hhhh", 0, 0, 9999, 0)
        + struct.pack("B", 0)
    )
    f = tmp_path / "data.xsd"
    f.write_bytes(header + color_data + grid_data + backstitch_data)

    importer = XSDImporter()
    pattern = importer.import_file(f)

    assert pattern is not None
    assert pattern.backstitches == []
    assert sum("außerhalb der Mustergrenzen" in w for w in importer.warnings) == 1


# ============================================================================
# PAT: Unvollstaendige komprimierte Grid-Daten (Runde 78, Version 8+)
#
# _read_raw_grid() (Legacy-Versionen) warnt schon lange bei einer
# unvollstaendigen Zeile. _read_compressed_grid() (Version 8+) lief bei
# genau demselben Szenario -- Datei/behaupteter Grid-Block endet, bevor
# alle Zeilen gelesen sind -- bislang klaglos aus. Die fehlenden unteren
# Zeilen blieben stillschweigend leer.
# ============================================================================


def _pat_v8_pascal(s: str) -> bytes:
    b = s.encode("cp1252")
    return struct.pack("B", len(b)) + b


def _build_pat_v8_header(width: int, height: int, color_count: int = 1) -> bytes:
    body = (
        struct.pack("<HH", width, height)
        + struct.pack("<H", color_count)
        + struct.pack("<H", 14)  # fabric_count
        + _pat_v8_pascal("Test")  # title
        + _pat_v8_pascal("")  # author
        + _pat_v8_pascal("")  # copyright
    )
    return b"PAT" + struct.pack("B", 8) + struct.pack("<I", len(body)) + body


def _build_pat_v8_color(r: int, g: int, b: int) -> bytes:
    return (
        struct.pack("BBB", r, g, b)
        + _pat_v8_pascal("310")  # DMC-Nummer
        + _pat_v8_pascal("Black")  # Name
        + struct.pack("B", ord("X"))  # Symbol
    )


def test_pat_import_warns_on_incomplete_compressed_grid(tmp_path):
    """Header behauptet eine 4x4-Datei mit grid_size=1000, tatsaechlich
    stehen nur 2 Bytes (RLE fuer 2 Zellen) zur Verfuegung -- die Datei
    endet mitten im Grid-Block."""
    data = _build_pat_v8_header(width=4, height=4, color_count=1)
    data += _build_pat_v8_color(255, 0, 0)
    truncated_grid = bytes([0x82, 0x00])  # RLE: 2 Zellen Farbe 0
    data += struct.pack("<I", 1000) + truncated_grid  # behauptete Groesse: 1000

    f = tmp_path / "data.pat"
    f.write_bytes(data)

    importer = PATImporter()
    pattern = importer.import_file(f)

    assert pattern is not None
    assert any("Unvollständige komprimierte Grid-Daten" in w for w in importer.warnings)


def test_pat_import_no_warning_for_complete_compressed_grid(tmp_path):
    """Gegenprobe: ein vollstaendiges komprimiertes Grid darf keine
    Unvollstaendigkeits-Warnung ausloesen."""
    data = _build_pat_v8_header(width=2, height=2, color_count=1)
    data += _build_pat_v8_color(255, 0, 0)
    full_grid = bytes([0x84, 0xFF])  # RLE: 4 Zellen (2x2), alle leer (0xFF)
    data += struct.pack("<I", len(full_grid)) + full_grid

    f = tmp_path / "data.pat"
    f.write_bytes(data)

    importer = PATImporter()
    pattern = importer.import_file(f)

    assert pattern is not None
    assert not any("Unvollständige komprimierte Grid-Daten" in w for w in importer.warnings)


# ============================================================================
# XSD: Helper-Klassen
# ============================================================================


def test_xsd_header_dataclass():
    h = XSDHeader(
        signature=b"PM",
        version=5,
        width=50,
        height=40,
        color_count=8,
        has_backstitches=True,
        title="Test",
        author="Hans",
    )
    assert h.has_backstitches is True


def test_xsd_import_error_is_exception():
    assert issubclass(XSDImportError, Exception)


# ============================================================================
# Importer-Sammelstatus
# ============================================================================


def test_pat_importer_clears_errors_between_calls(tmp_path):
    """`import_file()` cleart errors/warnings am Anfang jedes Aufrufs."""
    importer = PATImporter()
    importer.errors.append("alter Fehler")
    importer.warnings.append("alte Warnung")

    importer.import_file(tmp_path / "fehlt.pat")
    # Nach Aufruf gibt's neue Fehler (nicht-existent), aber NICHT die alten
    assert "alter Fehler" not in importer.errors
    assert "alte Warnung" not in importer.warnings


def test_xsd_importer_clears_errors_between_calls(tmp_path):
    importer = XSDImporter()
    importer.errors.append("alter Fehler")
    importer.warnings.append("alte Warnung")

    importer.import_file(tmp_path / "fehlt.xsd")
    assert "alter Fehler" not in importer.errors
    assert "alte Warnung" not in importer.warnings
