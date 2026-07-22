# -*- coding: utf-8 -*-
"""Tests fuer Hersteller-Cross-Reference (Threads)."""

import pytest


@pytest.fixture(autouse=True)
def _clear_cache():
    """Vor jedem Test den Cache leeren."""
    from pysticky.core.thread_cross_ref import clear_cache

    clear_cache()


def test_finds_equivalent_in_target_palette():
    """find_equivalent liefert einen Thread aus der Ziel-Palette."""
    from pysticky.core import Thread
    from pysticky.core.thread_cross_ref import find_equivalent

    dmc_black = Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310")
    anchor_equiv = find_equivalent(dmc_black, "Anchor")

    assert anchor_equiv is not None
    assert anchor_equiv.manufacturer == "Anchor"


def test_returns_thread_unchanged_for_same_manufacturer():
    """find_equivalent gibt Thread unveraendert zurueck, wenn schon Ziel-Hersteller."""
    from pysticky.core import Thread
    from pysticky.core.thread_cross_ref import find_equivalent

    dmc = Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310")
    same = find_equivalent(dmc, "DMC")
    assert same is dmc


def test_returns_none_for_unknown_palette():
    """Bei nicht existierender Palette wird None geliefert."""
    from pysticky.core import Thread
    from pysticky.core.thread_cross_ref import find_equivalent

    t = Thread.from_hex("Test", "#FF0000", manufacturer="DMC", catalog_number="321")
    result = find_equivalent(t, "NonexistentPalette")
    assert result is None


def test_find_equivalents_returns_dict():
    """find_equivalents liefert ein Dict mit allen angefragten Paletten."""
    from pysticky.core import Thread
    from pysticky.core.thread_cross_ref import find_equivalents

    t = Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310")
    result = find_equivalents(t, ["Anchor", "Madeira"])

    assert "Anchor" in result
    assert "Madeira" in result
    assert result["Anchor"].manufacturer == "Anchor"


def test_find_equivalents_isolates_failure_to_one_palette(monkeypatch):
    """Regression (Runde 22): find_equivalents() baute vorher ein Dict-
    Comprehension ohne jede Fehlerbehandlung -- wenn die Aufloesung fuer
    EINE angefragte Ziel-Palette warf (z.B. fehlerhafte Thread-/Farbdaten
    in genau dieser Palette), riss das die GESAMTE Cross-Reference-
    Aufloesung fuer alle anderen angefragten Paletten mit ab. PDF-/HTML-
    Export rufen dies ungeschuetzt in einer Pro-Thread-Schleife auf -- ein
    einzelner kaputter Eintrag haette sonst den kompletten Export
    abgebrochen."""
    import pysticky.core.thread_cross_ref as cross_ref_module
    from pysticky.core import Thread

    real_find_equivalent = cross_ref_module.find_equivalent

    def _flaky_find_equivalent(thread, target_palette_name):
        if target_palette_name == "Kaputt":
            raise TypeError("simulierter Absturz durch fehlerhafte Palettendaten")
        return real_find_equivalent(thread, target_palette_name)

    monkeypatch.setattr(cross_ref_module, "find_equivalent", _flaky_find_equivalent)

    t = Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310")
    result = cross_ref_module.find_equivalents(t, ["Anchor", "Kaputt", "Madeira"])

    assert result["Kaputt"] is None
    assert result["Anchor"] is not None
    assert result["Madeira"] is not None


def test_black_maps_to_black_across_manufacturers():
    """Schwarz aus einer Palette sollte zu einem dunklen Thread mappen."""
    from pysticky.core import Thread
    from pysticky.core.thread_cross_ref import find_equivalent

    dmc_black = Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310")
    anchor_equiv = find_equivalent(dmc_black, "Anchor")
    assert anchor_equiv is not None
    # Anchor-Match fuer #000000 muss sehr dunkel sein (Luminanz < 0.2)
    assert anchor_equiv.color.luminance < 0.2


def test_white_maps_to_white_across_manufacturers():
    """Weiss sollte zu einem hellen Thread mappen."""
    from pysticky.core import Thread
    from pysticky.core.thread_cross_ref import find_equivalent

    dmc_white = Thread.from_hex("White", "#FFFFFF", manufacturer="DMC", catalog_number="blanc")
    anchor_equiv = find_equivalent(dmc_white, "Anchor")
    assert anchor_equiv is not None
    assert anchor_equiv.color.luminance > 0.9


def test_cache_returns_same_object_on_repeated_calls():
    """Mehrfache Aufrufe mit gleichen Argumenten liefern dasselbe Ergebnis."""
    from pysticky.core import Thread
    from pysticky.core.thread_cross_ref import find_equivalent

    t = Thread.from_hex("Test", "#FF0000", manufacturer="DMC", catalog_number="321")
    r1 = find_equivalent(t, "Anchor")
    r2 = find_equivalent(t, "Anchor")
    assert r1 is r2  # Cache liefert exakt das gleiche Objekt


def test_html_exporter_accepts_cross_ref_palettes(pattern_with_stitches):
    """HTMLExporter akzeptiert cross_ref_palettes-Argument."""
    from pysticky.io import HTMLExporter

    exporter = HTMLExporter(pattern_with_stitches, cross_ref_palettes=["Anchor"])
    assert exporter.cross_ref_palettes == ["Anchor"]

    # Default ist leere Liste
    exporter_default = HTMLExporter(pattern_with_stitches)
    assert exporter_default.cross_ref_palettes == []


def test_pdf_exporter_accepts_cross_ref_palettes(pattern_with_stitches):
    """PDFExporter akzeptiert cross_ref_palettes-Argument."""
    pytest.importorskip("reportlab")
    from pysticky.io import PDFExporter

    exporter = PDFExporter(pattern_with_stitches, cross_ref_palettes=["Anchor", "Madeira"])
    assert exporter.cross_ref_palettes == ["Anchor", "Madeira"]


def test_html_legend_includes_cross_ref_column(pattern_with_stitches, tmp_path):
    """HTML-Export mit cross_ref_palettes enthaelt entsprechende Spalte."""
    from pysticky.io import HTMLExporter

    out = tmp_path / "with_xref.html"
    exporter = HTMLExporter(pattern_with_stitches, cross_ref_palettes=["Anchor"])
    success = exporter.export(out)

    assert success
    html_text = out.read_text(encoding="utf-8")
    # Header-Zelle mit "Anchor" muss in der Legende auftauchen
    assert "<th>Anchor</th>" in html_text


def test_html_legend_without_cross_ref_has_no_extra_columns(pattern_with_stitches, tmp_path):
    """Ohne cross_ref_palettes erscheinen keine Cross-Reference-Spalten."""
    from pysticky.io import HTMLExporter

    out = tmp_path / "no_xref.html"
    exporter = HTMLExporter(pattern_with_stitches)
    exporter.export(out)

    html_text = out.read_text(encoding="utf-8")
    # Standard-Header ohne extra Spalten
    assert "<th>Anchor</th>" not in html_text
    assert "<th>Madeira</th>" not in html_text


def test_clear_cache_resets_lookups():
    """clear_cache leert den Lookup-Cache (fuer Hot-Reload-Tests)."""
    from pysticky.core import Thread
    from pysticky.core.thread_cross_ref import _cached_find, clear_cache, find_equivalent

    t = Thread.from_hex("Test", "#FF0000", manufacturer="DMC", catalog_number="321")
    find_equivalent(t, "Anchor")
    assert _cached_find.cache_info().currsize > 0

    clear_cache()
    assert _cached_find.cache_info().currsize == 0
