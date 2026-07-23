# -*- coding: utf-8 -*-
"""Tests fuer OXS-Import und -Export (Open Cross Stitch XML)."""

from xml.etree import ElementTree as ET


def test_export_creates_valid_xml(pattern_with_stitches, tmp_path):
    """OXS-Export schreibt valides XML mit der erwarteten Struktur."""
    from pysticky.io.formats import export_oxs

    out = tmp_path / "test.oxs"
    export_oxs(pattern_with_stitches, out)

    assert out.exists()
    tree = ET.parse(out)
    root = tree.getroot()
    assert root.tag == "chart"
    assert root.find("format") is not None
    assert root.find("chart_info") is not None
    assert root.find("palette") is not None
    assert root.find("fullstitches") is not None
    assert root.find("backstitches") is not None
    assert root.find("ornaments_inc_knots_and_beads") is not None


def test_export_chart_info_contains_dimensions(pattern_with_stitches, tmp_path):
    """chart_info enthaelt Width und Height aus dem Pattern."""
    from pysticky.io.formats import export_oxs

    out = tmp_path / "test.oxs"
    export_oxs(pattern_with_stitches, out)

    root = ET.parse(out).getroot()
    info = root.find("chart_info")
    assert info.find("chartwidth").get("value") == "20"
    assert info.find("chartheight").get("value") == "20"


def test_export_palette_includes_cloth_entry(pattern_with_colors, tmp_path):
    """Palette enthaelt index="0" als cloth-Konvention plus alle Pattern-Farben."""
    from pysticky.io.formats import export_oxs

    out = tmp_path / "test.oxs"
    export_oxs(pattern_with_colors, out)

    root = ET.parse(out).getroot()
    items = root.find("palette").findall("palette_item")

    # Mindestens cloth-entry (index=0) + alle Farben
    indices = [int(it.get("index")) for it in items]
    assert 0 in indices
    assert len(items) == len(pattern_with_colors.color_entries) + 1


def test_export_full_stitches_use_1_indexed_coords(empty_pattern, tmp_path):
    """OXS-Konvention: Koordinaten sind 1-indiziert (pattern (0,0) -> oxs (1,1))."""
    from pysticky.core import Thread
    from pysticky.io.formats import export_oxs

    pattern = empty_pattern
    pattern.add_color(Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310"))
    pattern.set_stitch(0, 0, 1)  # color_entries[1] (nach Default-Black bei Index 0)
    pattern.set_stitch(3, 5, 1)

    out = tmp_path / "test.oxs"
    export_oxs(pattern, out)

    root = ET.parse(out).getroot()
    stitches = root.find("fullstitches").findall("stitch")
    coords = {(int(s.get("x")), int(s.get("y"))) for s in stitches}
    assert (1, 1) in coords  # pattern (0,0) -> oxs (1,1)
    assert (4, 6) in coords  # pattern (3,5) -> oxs (4,6)


def test_roundtrip_preserves_dimensions(pattern_with_stitches, tmp_path):
    """Roundtrip (write -> read) erhaelt die Dimensionen."""
    from pysticky.io.formats import export_oxs, import_oxs

    out = tmp_path / "test.oxs"
    export_oxs(pattern_with_stitches, out)

    reloaded, errors, warnings = import_oxs(out)
    assert errors == []
    assert reloaded is not None
    assert reloaded.width == pattern_with_stitches.width
    assert reloaded.height == pattern_with_stitches.height


def test_roundtrip_preserves_stitch_positions(pattern_with_stitches, tmp_path):
    """Roundtrip erhaelt Position aller Vollstiche."""
    import numpy as np

    from pysticky.core import NO_STITCH
    from pysticky.io.formats import export_oxs, import_oxs

    out = tmp_path / "test.oxs"
    export_oxs(pattern_with_stitches, out)
    reloaded, _, _ = import_oxs(out)

    orig_composite = pattern_with_stitches.layer_stack.get_composite_grid()
    reloaded_composite = reloaded.layer_stack.get_composite_grid()

    # Maske: wo sind ueberhaupt Stiche? Die SOLLEN matchen.
    orig_mask = orig_composite != NO_STITCH
    reloaded_mask = reloaded_composite != NO_STITCH
    assert np.array_equal(orig_mask, reloaded_mask)


def test_roundtrip_preserves_color_count(pattern_with_stitches, tmp_path):
    """Roundtrip erhaelt die Anzahl der verwendeten Farben."""
    from pysticky.io.formats import export_oxs, import_oxs

    out = tmp_path / "test.oxs"
    export_oxs(pattern_with_stitches, out)
    reloaded, _, _ = import_oxs(out)

    assert len(reloaded.color_entries) == len(pattern_with_stitches.color_entries)


def test_roundtrip_preserves_dmc_thread_metadata(pattern_with_stitches, tmp_path):
    """Roundtrip mappt DMC-Threads zurueck zu echten DMC-Threads aus der Palette."""
    from pysticky.io.formats import export_oxs, import_oxs

    out = tmp_path / "test.oxs"
    export_oxs(pattern_with_stitches, out)
    reloaded, _, _ = import_oxs(out)

    # Original-Threads sind alle DMC mit catalog_number
    for orig, reload in zip(pattern_with_stitches.color_entries, reloaded.color_entries):
        if orig.thread.manufacturer == "DMC" and orig.thread.catalog_number:
            assert reload.thread.manufacturer == "DMC"
            assert reload.thread.catalog_number == orig.thread.catalog_number


def test_roundtrip_preserves_backstitches(empty_pattern, tmp_path):
    """Backstitches mit Halb-Stich-Koords ueberleben den Roundtrip."""
    from pysticky.core import Thread
    from pysticky.io.formats import export_oxs, import_oxs

    pattern = empty_pattern
    pattern.add_color(Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310"))
    # Backstitch von (0,0) nach (2,2) in halben Stichen
    pattern.add_backstitch(0, 0, 2, 2, 1)
    # Diagonal mit Mittelpunkt: (1,1) -> (3,1) (entspricht Mitte->Kante)
    pattern.add_backstitch(1, 1, 3, 1, 1)

    out = tmp_path / "test.oxs"
    export_oxs(pattern, out)
    reloaded, _, _ = import_oxs(out)

    orig_bs = pattern.backstitch_manager.backstitches
    new_bs = reloaded.backstitch_manager.backstitches
    assert len(orig_bs) == len(new_bs)

    orig_coords = {(b.x1, b.y1, b.x2, b.y2) for b in orig_bs}
    new_coords = {(b.x1, b.y1, b.x2, b.y2) for b in new_bs}
    assert orig_coords == new_coords


def test_roundtrip_preserves_french_knots(empty_pattern, tmp_path):
    """Franzoesische Knoten (stitch_type=9) ueberleben den Roundtrip."""
    from pysticky.core import Thread
    from pysticky.core.stitch import StitchType
    from pysticky.io.formats import export_oxs, import_oxs

    pattern = empty_pattern
    pattern.add_color(Thread.from_hex("Red", "#FF0000", manufacturer="DMC", catalog_number="321"))
    pattern.set_stitch(2, 3, 1, stitch_type=StitchType.FRENCH_KNOT.value)
    pattern.set_stitch(5, 7, 1, stitch_type=StitchType.FRENCH_KNOT.value)

    out = tmp_path / "test.oxs"
    export_oxs(pattern, out)
    reloaded, _, _ = import_oxs(out)

    # Reloaded muss Knots an gleichen Positionen haben
    layer = reloaded.layer_stack.active_layer
    assert layer.stitch_type_grid[3, 2] == StitchType.FRENCH_KNOT.value
    assert layer.stitch_type_grid[7, 5] == StitchType.FRENCH_KNOT.value


def test_roundtrip_preserves_half_stitches(empty_pattern, tmp_path):
    """Halbstiche (TL_BR und TR_BL) ueberleben den Roundtrip."""
    from pysticky.core import Thread
    from pysticky.core.stitch import StitchType
    from pysticky.io.formats import export_oxs, import_oxs

    pattern = empty_pattern
    pattern.add_color(Thread.from_hex("Blue", "#0000FF", manufacturer="DMC", catalog_number="796"))
    pattern.set_stitch(1, 1, 1, stitch_type=StitchType.HALF_TL_BR.value)
    pattern.set_stitch(2, 2, 1, stitch_type=StitchType.HALF_TR_BL.value)

    out = tmp_path / "test.oxs"
    export_oxs(pattern, out)
    reloaded, _, _ = import_oxs(out)

    layer = reloaded.layer_stack.active_layer
    assert layer.stitch_type_grid[1, 1] == StitchType.HALF_TL_BR.value
    assert layer.stitch_type_grid[2, 2] == StitchType.HALF_TR_BL.value


def test_roundtrip_preserves_quarter_stitches(empty_pattern, tmp_path):
    """Alle 4 Viertelstich-Positionen ueberleben den Roundtrip."""
    from pysticky.core import Thread
    from pysticky.core.stitch import StitchType
    from pysticky.io.formats import export_oxs, import_oxs

    pattern = empty_pattern
    pattern.add_color(Thread.from_hex("Green", "#00FF00", manufacturer="DMC", catalog_number="699"))
    pattern.set_stitch(0, 0, 1, stitch_type=StitchType.QUARTER_TL.value)
    pattern.set_stitch(1, 0, 1, stitch_type=StitchType.QUARTER_TR.value)
    pattern.set_stitch(0, 1, 1, stitch_type=StitchType.QUARTER_BL.value)
    pattern.set_stitch(1, 1, 1, stitch_type=StitchType.QUARTER_BR.value)

    out = tmp_path / "test.oxs"
    export_oxs(pattern, out)
    reloaded, _, _ = import_oxs(out)

    layer = reloaded.layer_stack.active_layer
    assert layer.stitch_type_grid[0, 0] == StitchType.QUARTER_TL.value
    assert layer.stitch_type_grid[0, 1] == StitchType.QUARTER_TR.value
    assert layer.stitch_type_grid[1, 0] == StitchType.QUARTER_BL.value
    assert layer.stitch_type_grid[1, 1] == StitchType.QUARTER_BR.value


def test_roundtrip_preserves_beads(empty_pattern, tmp_path):
    """Perlen (BEAD, stitch_type=10) ueberleben den Roundtrip."""
    from pysticky.core import Thread
    from pysticky.core.stitch import StitchType
    from pysticky.io.formats import export_oxs, import_oxs

    pattern = empty_pattern
    pattern.add_color(
        Thread.from_hex("Silver", "#C0C0C0", manufacturer="DMC", catalog_number="168")
    )
    pattern.set_stitch(4, 5, 1, stitch_type=StitchType.BEAD.value)

    out = tmp_path / "test.oxs"
    export_oxs(pattern, out)
    reloaded, _, _ = import_oxs(out)

    layer = reloaded.layer_stack.active_layer
    assert layer.stitch_type_grid[5, 4] == StitchType.BEAD.value


def test_import_handles_missing_optional_sections(empty_pattern, tmp_path):
    """Importer toleriert fehlende optionale Sections (z.B. nur fullstitches)."""
    from pysticky.io.formats import import_oxs

    # Minimal-OXS handgeschrieben — nur fullstitches, kein backstitches etc.
    oxs_content = """<?xml version="1.0"?>
<chart>
  <format><FormatVersion value="1.0" /></format>
  <chart_info>
    <title value="Mini" />
    <chartwidth value="5" />
    <chartheight value="5" />
    <stitchesperinch value="14" />
  </chart_info>
  <palette>
    <palette_item index="0" name="cloth" color="FFFFFF" />
    <palette_item index="1" number="310" name="DMC 310 - Black" symbol="X" color="000000" />
  </palette>
  <fullstitches>
    <stitch x="1" y="1" palindex="1" />
    <stitch x="2" y="2" palindex="1" />
  </fullstitches>
</chart>
"""
    f = tmp_path / "minimal.oxs"
    f.write_text(oxs_content, encoding="utf-8")

    pattern, errors, warnings = import_oxs(f)
    assert errors == []
    assert pattern is not None
    assert pattern.width == 5
    assert pattern.height == 5
    assert pattern.name == "Mini"
    # Stiche an (0,0) und (1,1) gesetzt (OXS 1-indiziert -> Pattern 0-indiziert)
    assert pattern.get_stitch(0, 0) is not None
    assert pattern.get_stitch(1, 1) is not None
    assert pattern.get_stitch(4, 4) is None


def test_import_rejects_invalid_dimensions(tmp_path):
    """Importer liefert Fehler bei chartwidth=0."""
    from pysticky.io.formats import import_oxs

    bad = """<?xml version="1.0"?>
<chart>
  <chart_info><chartwidth value="0" /><chartheight value="0" /></chart_info>
  <palette></palette>
</chart>
"""
    f = tmp_path / "bad.oxs"
    f.write_text(bad, encoding="utf-8")

    pattern, errors, warnings = import_oxs(f)
    assert pattern is None
    assert any("Dimensionen" in e for e in errors)


def test_import_rejects_oversized_dimensions(tmp_path):
    """Regression: chartwidth/chartheight hatten keine Obergrenze -- eine
    manipulierte/beschaedigte Datei mit riesigen Werten haette eine
    Multi-Gigabyte-Grid-Allokation ausgeloest (MemoryError statt
    kontrolliertem Fehler). Gleiche 2000x2000-Grenze wie pat_import.py."""
    from pysticky.io.formats import import_oxs

    bad = """<?xml version="1.0"?>
<chart>
  <chart_info><chartwidth value="200000" /><chartheight value="200000" /></chart_info>
  <palette></palette>
</chart>
"""
    f = tmp_path / "huge.oxs"
    f.write_text(bad, encoding="utf-8")

    pattern, errors, warnings = import_oxs(f)
    assert pattern is None
    assert any("gross" in e or "groß" in e for e in errors)


def test_import_accepts_pattern_at_hard_limit_boundary(tmp_path):
    """Groessen-Grenzfaelle-Audit (2026-07-23): exakt 2000x2000 muss --
    konsistent zu pat_import.py/xsd_import.py/file_io.py, die diesen
    exakten Grenzwert bereits per Regressionstest absichern -- noch
    erlaubt sein (nur > 2000 wird abgelehnt)."""
    from pysticky.io.formats import import_oxs

    ok = """<?xml version="1.0"?>
<chart>
  <chart_info><chartwidth value="2000" /><chartheight value="2000" /></chart_info>
  <palette></palette>
</chart>
"""
    f = tmp_path / "boundary_ok.oxs"
    f.write_text(ok, encoding="utf-8")

    pattern, errors, warnings = import_oxs(f)
    assert pattern is not None
    assert pattern.width == 2000 and pattern.height == 2000


def test_import_rejects_pattern_one_above_hard_limit(tmp_path):
    """2001x2001 (ein Stich ueber der Grenze) muss abgelehnt werden --
    dieselbe Off-by-one-Stelle, an der sich Inkonsistenzen zwischen den
    Importern typischerweise verstecken."""
    from pysticky.io.formats import import_oxs

    bad = """<?xml version="1.0"?>
<chart>
  <chart_info><chartwidth value="2001" /><chartheight value="2001" /></chart_info>
  <palette></palette>
</chart>
"""
    f = tmp_path / "boundary_bad.oxs"
    f.write_text(bad, encoding="utf-8")

    pattern, errors, warnings = import_oxs(f)
    assert pattern is None
    assert any("gross" in e or "groß" in e for e in errors)


def test_import_catches_unexpected_parse_errors(tmp_path, monkeypatch):
    """Regression: import_file() fing nur OXSImportError -- jeder andere
    unerwartete Fehler beim Parsen (z.B. ein Bug in einer Hilfsfunktion,
    oder frueher: ein MemoryError bei riesigen Dimensionen) propagierte
    ungefangen aus import_file() heraus, statt als kontrollierter Fehler
    in der errors-Liste zu landen."""
    from pysticky.io.formats.oxs_io import OXSImporter

    oxs_content = """<?xml version="1.0"?>
<chart>
  <chart_info><chartwidth value="5" /><chartheight value="5" /></chart_info>
  <palette>
    <palette_item index="0" name="cloth" color="FFFFFF" />
  </palette>
</chart>
"""
    f = tmp_path / "boom.oxs"
    f.write_text(oxs_content, encoding="utf-8")

    importer = OXSImporter()

    def boom(*args, **kwargs):
        raise RuntimeError("simulierter unerwarteter Fehler")

    monkeypatch.setattr(importer, "_read_palette", boom)

    pattern = importer.import_file(f)
    assert pattern is None
    assert any("Unerwarteter Fehler" in e for e in importer.errors)


def test_import_rejects_non_oxs_root(tmp_path):
    """Importer lehnt XML mit anderem Root-Tag ab."""
    from pysticky.io.formats import import_oxs

    bad = "<?xml version='1.0'?><wrongroot/>"
    f = tmp_path / "bad.oxs"
    f.write_text(bad, encoding="utf-8")

    pattern, errors, warnings = import_oxs(f)
    assert pattern is None
    assert any("chart" in e for e in errors)


def test_import_handles_xml_parse_error(tmp_path):
    """Importer liefert Fehler bei kaputtem XML."""
    from pysticky.io.formats import import_oxs

    f = tmp_path / "bad.oxs"
    f.write_text("<chart><not closing", encoding="utf-8")

    pattern, errors, warnings = import_oxs(f)
    assert pattern is None
    assert any("XML" in e or "Parse" in e for e in errors)


def test_import_missing_file_returns_error():
    """Importer liefert Fehler bei nicht-existierender Datei."""
    from pysticky.io.formats import import_oxs

    pattern, errors, warnings = import_oxs("/nonexistent/path/file.oxs")
    assert pattern is None
    assert any("nicht gefunden" in e for e in errors)


def test_can_import_recognizes_oxs(tmp_path):
    """OXSImporter.can_import erkennt eine gueltige .oxs-Datei."""
    from pysticky.io.formats import OXSImporter

    valid = tmp_path / "valid.oxs"
    valid.write_text(
        "<?xml version='1.0'?><chart><chart_info><chartwidth value='1'/>"
        "<chartheight value='1'/></chart_info><palette/></chart>",
        encoding="utf-8",
    )
    importer = OXSImporter()
    assert importer.can_import(valid) is True


def test_can_import_rejects_wrong_extension(tmp_path):
    """can_import lehnt nicht-.oxs-Endung ab."""
    from pysticky.io.formats import OXSImporter

    f = tmp_path / "valid.xml"
    f.write_text("<chart/>", encoding="utf-8")
    importer = OXSImporter()
    assert importer.can_import(f) is False


def test_export_with_explicit_author_and_copyright(empty_pattern, tmp_path):
    """export_oxs uebernimmt explizit gesetzte Author/Copyright-Werte."""
    from pysticky.io.formats import export_oxs, import_oxs

    out = tmp_path / "with_meta.oxs"
    export_oxs(empty_pattern, out, author="Hans", copyright_="(C) 2026")
    reloaded, _, _ = import_oxs(out)

    assert reloaded.metadata.get("author") == "Hans"
    assert reloaded.metadata.get("copyright") == "(C) 2026"


def test_export_uses_pattern_metadata_author(empty_pattern, tmp_path):
    """Wenn kein expliziter Author, wird pattern.metadata['author'] genutzt."""
    from pysticky.io.formats import export_oxs, import_oxs

    empty_pattern.metadata["author"] = "Auto-Author"
    out = tmp_path / "meta.oxs"
    export_oxs(empty_pattern, out)
    reloaded, _, _ = import_oxs(out)

    assert reloaded.metadata.get("author") == "Auto-Author"


# --- Sicherheit: defusedxml schuetzt vor XXE / Entity-Expansion ---

_BILLION_LAUGHS = """<?xml version="1.0"?>
<!DOCTYPE chart [
  <!ENTITY a "aaaaaaaaaa">
  <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">
]>
<chart><chart_info><title value="&b;"/></chart_info></chart>"""

_XXE_EXTERNAL = """<?xml version="1.0"?>
<!DOCTYPE chart [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<chart><chart_info><title value="&xxe;"/></chart_info></chart>"""


def test_import_rejects_billion_laughs(tmp_path):
    """Entity-Expansion-Bombe wird abgelehnt, nicht expandiert."""
    from pysticky.io.formats import import_oxs

    out = tmp_path / "evil.oxs"
    out.write_text(_BILLION_LAUGHS, encoding="utf-8")
    pattern, errors, _ = import_oxs(out)

    assert pattern is None
    assert errors  # mit Fehlermeldung, nicht still


def test_import_rejects_xxe_external_entity(tmp_path):
    """Externe Entity (XXE, z.B. file:///etc/passwd) wird abgelehnt."""
    from pysticky.io.formats import import_oxs

    out = tmp_path / "xxe.oxs"
    out.write_text(_XXE_EXTERNAL, encoding="utf-8")
    pattern, errors, _ = import_oxs(out)

    assert pattern is None
    assert errors


def test_can_import_returns_false_for_malicious_xml(tmp_path):
    """can_import lehnt bösartiges XML ab statt zu werfen."""
    from pysticky.io.formats.oxs_io import OXSImporter

    out = tmp_path / "evil.oxs"
    out.write_text(_BILLION_LAUGHS, encoding="utf-8")

    assert OXSImporter().can_import(out) is False
