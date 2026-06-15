# -*- coding: utf-8 -*-
"""Tests fuer Tweed-Blends (Multi-Strand Color Blending)."""

import pytest


def test_blend_creates_thread_with_components():
    """Thread.blend liefert einen Thread mit blend_components."""
    from pysticky.core import Thread

    a = Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310")
    b = Thread.from_hex("White", "#FFFFFF", manufacturer="DMC", catalog_number="B5200")
    blend = Thread.blend([a, b])

    assert blend.is_blend is True
    assert len(blend.blend_components) == 2
    assert blend.strand_ratios == [1, 1]


def test_blend_color_is_between_components_perceptually():
    """Lab-Mix von Schwarz + Weiss liegt im mittleren Grau-Bereich."""
    from pysticky.core import Thread

    a = Thread.from_hex("Black", "#000000")
    b = Thread.from_hex("White", "#FFFFFF")
    blend = Thread.blend([a, b])
    # In Lab ist der Mittelpunkt von L=0 und L=100 ungefaehr L=50 — RGB ist
    # dann *nicht* (127,127,127), sondern dunkler (sRGB-Gamma).
    # Sanity-Check: liegt im Graubereich, nicht extrem.
    c = blend.color
    assert 100 < c.r < 200
    assert abs(c.r - c.g) < 10
    assert abs(c.g - c.b) < 10


def test_blend_with_unequal_ratios_shifts_color():
    """Bei [1,3] liegt die Mischfarbe naeher an der zweiten Komponente."""
    from pysticky.core import Thread

    black = Thread.from_hex("Black", "#000000")
    white = Thread.from_hex("White", "#FFFFFF")
    near_black = Thread.blend([black, white], [3, 1])
    near_white = Thread.blend([black, white], [1, 3])

    # near_black sollte dunkler sein als near_white
    assert near_black.color.luminance < near_white.color.luminance


def test_blend_default_name_includes_components_and_ratios():
    """Default-Name enthaelt Hersteller/Nummer beider Komponenten + Ratio."""
    from pysticky.core import Thread

    a = Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310")
    b = Thread.from_hex("Yellow", "#FFE6A8", manufacturer="DMC", catalog_number="745")
    blend = Thread.blend([a, b], [1, 2])
    assert "DMC 310" in blend.name
    assert "DMC 745" in blend.name
    assert "1+2" in blend.name


def test_blend_with_explicit_name_overrides_default():
    """Expliziter Name ueberschreibt das Auto-Naming."""
    from pysticky.core import Thread

    a = Thread.from_hex("A", "#FF0000", manufacturer="DMC", catalog_number="321")
    b = Thread.from_hex("B", "#00FF00", manufacturer="DMC", catalog_number="699")
    blend = Thread.blend([a, b], name="Custom Tweed")
    assert blend.name == "Custom Tweed"


def test_blend_rejects_single_component():
    """Blend mit nur einer Komponente wirft ValueError."""
    from pysticky.core import Thread

    a = Thread.from_hex("A", "#FF0000")
    with pytest.raises(ValueError):
        Thread.blend([a])


def test_blend_rejects_mismatched_ratios():
    """Anzahl Ratios muss Anzahl Komponenten matchen."""
    from pysticky.core import Thread

    a = Thread.from_hex("A", "#FF0000")
    b = Thread.from_hex("B", "#00FF00")
    with pytest.raises(ValueError):
        Thread.blend([a, b], [1, 2, 3])


def test_blend_rejects_zero_ratio():
    """Ratios muessen >= 1 sein."""
    from pysticky.core import Thread

    a = Thread.from_hex("A", "#FF0000")
    b = Thread.from_hex("B", "#00FF00")
    with pytest.raises(ValueError):
        Thread.blend([a, b], [1, 0])


def test_non_blend_thread_has_is_blend_false():
    """Regulaerer Thread hat is_blend=False."""
    from pysticky.core import Thread

    t = Thread.from_hex("Red", "#FF0000")
    assert t.is_blend is False


def test_blend_same_color_produces_same_color():
    """Blend von Farbe X mit sich selbst gibt ungefaehr Farbe X zurueck."""
    from pysticky.core import Thread

    red = Thread.from_hex("Red", "#FF0000")
    blend = Thread.blend([red, red])
    # Roundtrip RGB->Lab->RGB hat Quantisierungsverluste, aber sollte
    # in jedem Kanal innerhalb von 5 sein.
    assert abs(blend.color.r - 255) <= 5
    assert blend.color.g <= 5
    assert blend.color.b <= 5


def test_file_io_preserves_blend(empty_pattern, tmp_path):
    """pxs-Roundtrip erhaelt Blend-Komponenten und -Ratios."""
    from pysticky.core import Thread, load_pattern, save_pattern

    pattern = empty_pattern
    a = Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310")
    b = Thread.from_hex("Yellow", "#FFE6A8", manufacturer="DMC", catalog_number="745")
    blend = Thread.blend([a, b], [2, 1])
    pattern.add_color(blend)

    out = tmp_path / "blend.pxs"
    save_pattern(pattern, out)
    reloaded = load_pattern(out)

    blend_entries = [e for e in reloaded.color_entries if e.thread.is_blend]
    assert len(blend_entries) == 1
    rec = blend_entries[0].thread
    assert len(rec.blend_components) == 2
    assert rec.strand_ratios == [2, 1]
    assert rec.blend_components[0].catalog_number == "310"
    assert rec.blend_components[1].catalog_number == "745"


def test_oxs_roundtrip_preserves_blend(empty_pattern, tmp_path):
    """OXS-Roundtrip erhaelt Blend via Custom-Attribute."""
    from pysticky.core import Thread
    from pysticky.io.formats import export_oxs, import_oxs

    pattern = empty_pattern
    a = Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310")
    b = Thread.from_hex("Yellow", "#FFE6A8", manufacturer="DMC", catalog_number="745")
    blend = Thread.blend([a, b], [1, 1])
    blend_idx = pattern.add_color(blend)
    pattern.set_stitch(2, 2, blend_idx)

    out = tmp_path / "blend.oxs"
    export_oxs(pattern, out)
    reloaded, errors, _ = import_oxs(out)
    assert errors == []

    blend_entries = [e for e in reloaded.color_entries if e.thread.is_blend]
    assert len(blend_entries) == 1
    components = blend_entries[0].thread.blend_components
    assert len(components) == 2
    catalog_nums = {c.catalog_number for c in components}
    assert "310" in catalog_nums
    assert "745" in catalog_nums


def test_html_legend_shows_both_blend_numbers(empty_pattern, tmp_path):
    """HTML-Legende zeigt 'DMC 310 + DMC 745' fuer Blends."""
    from pysticky.core import Thread
    from pysticky.io import HTMLExporter

    pattern = empty_pattern
    a = Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310")
    b = Thread.from_hex("Yellow", "#FFE6A8", manufacturer="DMC", catalog_number="745")
    blend = Thread.blend([a, b])
    blend_idx = pattern.add_color(blend)
    pattern.set_stitch(2, 2, blend_idx)

    out = tmp_path / "blend.html"
    HTMLExporter(pattern).export(out)
    html = out.read_text(encoding="utf-8")
    assert "DMC 310" in html
    assert "DMC 745" in html


def test_blend_with_homogeneous_manufacturer():
    """Blend von DMC+DMC hat manufacturer='DMC'."""
    from pysticky.core import Thread

    a = Thread.from_hex("A", "#FF0000", manufacturer="DMC", catalog_number="321")
    b = Thread.from_hex("B", "#00FF00", manufacturer="DMC", catalog_number="699")
    blend = Thread.blend([a, b])
    assert blend.manufacturer == "DMC"


def test_blend_with_heterogeneous_manufacturers():
    """Blend von DMC+Anchor hat manufacturer='Blend'."""
    from pysticky.core import Thread

    a = Thread.from_hex("A", "#FF0000", manufacturer="DMC", catalog_number="321")
    b = Thread.from_hex("B", "#00FF00", manufacturer="Anchor", catalog_number="245")
    blend = Thread.blend([a, b])
    assert blend.manufacturer == "Blend"
