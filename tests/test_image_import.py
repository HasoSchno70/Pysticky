# -*- coding: utf-8 -*-
"""
Tests fuer den Bild-Importer (`core/image_import.py`).

Generiert synthetische PIL-Bilder fuer reproduzierbare Tests der
Quantisierungs-Pipelines, Dithering-Modi, Crop-Logik und Aspect-Ratio.
"""

import pytest

PIL = pytest.importorskip("PIL")
np = pytest.importorskip("numpy")

from PIL import Image

from pysticky.core.image_import import (
    ImportSettings,
    can_change_palette,
    change_palette,
    check_pillow_available,
    create_preview,
    generate_backstitches_from_edges,
    get_image_info,
    import_image,
)

# ============================================================================
# Hilfsfunktionen: synthetische Test-Bilder
# ============================================================================


def _make_solid_rgb(tmp_path, color: tuple[int, int, int], size=(20, 20)):
    """Erzeugt ein einfarbiges RGB-Bild und speichert es."""
    path = tmp_path / f"solid_{color[0]}_{color[1]}_{color[2]}.png"
    Image.new("RGB", size, color).save(path)
    return path


def _make_gradient(tmp_path, size=(40, 40)):
    """Erzeugt ein Horizontal-Gradient von Schwarz nach Weiss."""
    arr = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    for x in range(size[0]):
        gray = int(255 * x / max(1, size[0] - 1))
        arr[:, x] = [gray, gray, gray]
    path = tmp_path / "gradient.png"
    Image.fromarray(arr).save(path)
    return path


def _make_two_squares(tmp_path):
    """Bild mit zwei Quadraten: rot links, blau rechts. 20x20."""
    arr = np.zeros((20, 20, 3), dtype=np.uint8)
    arr[:, :10] = [255, 0, 0]
    arr[:, 10:] = [0, 0, 255]
    path = tmp_path / "two_squares.png"
    Image.fromarray(arr).save(path)
    return path


# ============================================================================
# ImportSettings — Backwards-Compat-Logik
# ============================================================================


def test_settings_defaults():
    s = ImportSettings()
    assert s.width == 50
    assert s.height == 50
    assert s.dithering is False
    assert s.dithering_mode == "none"


def test_settings_dithering_bool_sets_mode():
    """dithering=True alleine setzt dithering_mode auf 'floyd_steinberg'."""
    s = ImportSettings(dithering=True)
    assert s.dithering_mode == "floyd_steinberg"


def test_settings_mode_syncs_bool():
    """dithering_mode != 'none' setzt das bool-Flag."""
    s = ImportSettings(dithering_mode="ordered")
    assert s.dithering is True


def test_settings_mode_none_keeps_bool_false():
    s = ImportSettings(dithering=False, dithering_mode="none")
    assert s.dithering is False


def test_settings_has_adjustments_default_false():
    """Default-Settings: keine Bildanpassung -> has_adjustments False."""
    s = ImportSettings()
    assert s.has_adjustments is False
    assert s.brightness == 1.0
    assert s.contrast == 1.0
    assert s.saturation == 1.0


def test_settings_has_adjustments_true_with_brightness():
    assert ImportSettings(brightness=1.2).has_adjustments is True


def test_settings_has_adjustments_true_with_saturation():
    assert ImportSettings(saturation=0.0).has_adjustments is True


def test_import_brightness_makes_image_brighter(tmp_path):
    """brightness > 1.0 verschiebt das Pattern in hellere Farbtoene.

    Wir messen den durchschnittlichen Grauwert der gewaehlten Farben.
    """
    path = _make_gradient(tmp_path)

    pattern_dark = import_image(path, ImportSettings(width=20, height=20, brightness=0.5))
    pattern_bright = import_image(path, ImportSettings(width=20, height=20, brightness=1.8))

    def _avg_luma(p):
        total = 0.0
        n = 0
        for entry in p.color_entries:
            if entry.stitch_count > 0:
                c = entry.thread.color
                total += (c.r + c.g + c.b) * entry.stitch_count
                n += entry.stitch_count * 3
        return total / max(1, n)

    assert _avg_luma(pattern_bright) > _avg_luma(pattern_dark) + 20, (
        "Brightness=1.8 sollte deutlich hellere Durchschnittsfarbe ergeben"
    )


def test_import_saturation_zero_yields_grayscale_pattern(tmp_path):
    """saturation=0.0 -> Farbquantisierung kommt auf grauen Farben raus."""
    path = _make_two_squares(tmp_path)
    pattern = import_image(path, ImportSettings(width=15, height=15, saturation=0.0))

    # Bei voll desaturiertem Bild ist R≈G≈B fuer jede gewaehlte Farbe.
    for entry in pattern.color_entries:
        c = entry.thread.color
        max_diff = max(abs(c.r - c.g), abs(c.g - c.b), abs(c.r - c.b))
        # Grosse Toleranz, weil die Palette echte DMC-Threads sind und kein
        # exakter Grauverlauf existiert — aber gesaettigtes Rot/Blau sollte
        # NICHT vorkommen.
        assert max_diff < 80, (
            f"Bei saturation=0 sollten ausgewaehlte Farben annaehernd grau sein: {c}"
        )


# ============================================================================
# Pillow-Verfuegbarkeit + get_image_info
# ============================================================================


def test_check_pillow_available_returns_true():
    """Auf Test-System ist Pillow installiert (importorskip oben pruefte das)."""
    assert check_pillow_available() is True


def test_get_image_info_basic(tmp_path):
    path = _make_solid_rgb(tmp_path, (128, 64, 32), size=(15, 25))
    info = get_image_info(path)
    assert info["width"] == 15
    assert info["height"] == 25
    assert info["format"] == "PNG"
    assert info["mode"] in ("RGB", "RGBA")  # PNG kann mode-spezifisch sein


# ============================================================================
# import_image — Hauptpfade
# ============================================================================


def test_import_solid_color_produces_uniform_pattern(tmp_path):
    """Einfarbiges Bild -> Pattern mit nur einer Farbe."""
    path = _make_solid_rgb(tmp_path, (200, 50, 50))
    settings = ImportSettings(width=10, height=10, max_colors=5)
    pattern = import_image(path, settings)

    assert pattern.width == 10
    assert pattern.height == 10
    # Alle Stiche haben den gleichen Farb-Index (typischerweise 0)
    layer = pattern.active_layer
    indices = {layer.get_stitch(x, y) for x in range(10) for y in range(10)}
    indices.discard(None)
    assert len(indices) == 1


def test_import_from_bead_palette_stamps_bead_stitch_type(tmp_path):
    """Regression (Runde 22): import_image() schrieb Stiche per
    `layer.set_stitch()` (nicht `Pattern.set_stitch()`), das den
    is_bead/is_diamond-Stitch-Type NIE automatisch stempelt. Jeder aus
    einer Bead-Palette importierte Stich bekam dadurch stitch_type=FULL(0)
    statt BEAD(10), obwohl is_bead auf den ColorEntries korrekt gesetzt
    war -- Pattern._count_beads() zaehlt strikt stitch_type_grid==BEAD,
    also blieb `get_statistics()['bead_count']` nach einem Bead-Paletten-
    Import immer 0."""
    from pysticky.core.stitch import StitchType

    path = _make_solid_rgb(tmp_path, (255, 255, 255))
    settings = ImportSettings(width=5, height=5, max_colors=3, palette_name="Mill Hill Beads")
    pattern = import_image(path, settings)

    assert any(e.is_bead for e in pattern.color_entries)

    layer = pattern.active_layer
    stitch_types = {
        layer.get_stitch_type(x, y)
        for x in range(pattern.width)
        for y in range(pattern.height)
        if layer.get_stitch(x, y) is not None
    }
    assert stitch_types == {StitchType.BEAD.value}

    stats = pattern.get_statistics()
    assert stats["bead_count"] > 0


def test_import_two_color_image_finds_both(tmp_path):
    """Zwei klar getrennte Farben muessen beide gefunden werden."""
    path = _make_two_squares(tmp_path)
    settings = ImportSettings(width=20, height=20, max_colors=10)
    pattern = import_image(path, settings)

    used_indices = set()
    layer = pattern.active_layer
    for y in range(20):
        for x in range(20):
            idx = layer.get_stitch(x, y)
            if idx is not None:
                used_indices.add(idx)
    assert len(used_indices) >= 2, "rot + blau muessen beide im Pattern landen"


def test_import_respects_target_size(tmp_path):
    """width/height in Settings bestimmen die Pattern-Groesse."""
    path = _make_solid_rgb(tmp_path, (100, 100, 100), size=(80, 60))
    settings = ImportSettings(width=30, height=20, keep_aspect_ratio=False)
    pattern = import_image(path, settings)
    assert pattern.width == 30
    assert pattern.height == 20


def test_import_keeps_aspect_ratio_when_enabled(tmp_path):
    """Bei aspect_ratio=True wird die Groesse auf das Bild-Verhaeltnis angepasst."""
    # Quellbild 100x50 (2:1), Settings 40x40 -> sollte 40x20 ergeben
    path = _make_solid_rgb(tmp_path, (100, 100, 100), size=(100, 50))
    settings = ImportSettings(width=40, height=40, keep_aspect_ratio=True)
    pattern = import_image(path, settings)
    # 2:1 Verhaeltnis sollte erhalten bleiben
    aspect_ratio = pattern.width / pattern.height
    assert 1.8 <= aspect_ratio <= 2.2


def test_import_median_cut_quantization(tmp_path):
    """median_cut ist ein anderer Pfad als nearest — darf nicht crashen."""
    path = _make_two_squares(tmp_path)
    settings = ImportSettings(width=15, height=15, max_colors=5, quantization_method="median_cut")
    pattern = import_image(path, settings)
    assert pattern.width == 15


def test_import_more_than_symbol_pool_assigns_unique_symbols(tmp_path):
    """Regression: max_colors ist bis 100 waehlbar (Settings-Dialog UND
    Wizard-Recall koennen das gespeicherte max_colors aus einem alten
    Muster wiederverwenden), aber resources/symbols.txt hat nur 86
    Eintraege. import_image() wies Symbole frueher per
    "SYMBOLS[i % len(SYMBOLS)]" zu -- Farbe 87 bekam also dasselbe
    Symbol wie Farbe 1, Farbe 88 dasselbe wie Farbe 2 usw. Zwei
    verschiedene Farben mit identischem Symbol sind in Legende/Export
    nicht mehr unterscheidbar. Pattern.add_color() hat fuer den
    manuellen Farbe-hinzufuegen-Pfad schon einen "#N"-Fallback (Runde
    48) -- import_image() baut ColorEntries aber direkt und nutzte
    diesen Fallback nicht mit."""
    import random

    rng = random.Random(42)
    size = 32
    arr = np.zeros((size, size, 3), dtype=np.uint8)
    for y in range(size):
        for x in range(size):
            arr[y, x] = [rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)]
    path = tmp_path / "viele_farben.png"
    Image.fromarray(arr).save(path)

    settings = ImportSettings(
        width=size, height=size, max_colors=95, quantization_method="median_cut"
    )
    pattern = import_image(path, settings)

    assert len(pattern.color_entries) > 86, "Testbild muss tatsaechlich >86 Farben liefern"
    symbols = [entry.symbol for entry in pattern.color_entries]
    assert len(symbols) == len(set(symbols)), "jede Farbe braucht ein eindeutiges Symbol"


def test_import_floyd_steinberg_dithering(tmp_path):
    """Dithering-Pfad laeuft ohne Crash und produziert valides Pattern."""
    path = _make_gradient(tmp_path)
    settings = ImportSettings(width=20, height=20, max_colors=4, dithering_mode="floyd_steinberg")
    pattern = import_image(path, settings)

    # Gradient + 4 Farben + Dithering -> mehrere Farben in der Mitte
    used = set()
    layer = pattern.active_layer
    for y in range(20):
        for x in range(20):
            idx = layer.get_stitch(x, y)
            if idx is not None:
                used.add(idx)
    assert len(used) >= 2


def test_import_ordered_dithering(tmp_path):
    """Ordered Dithering: anderer Pfad, anderes Pattern, kein Crash."""
    path = _make_gradient(tmp_path)
    settings = ImportSettings(width=20, height=20, max_colors=4, dithering_mode="ordered")
    pattern = import_image(path, settings)
    assert pattern.width == 20


def test_import_crop_uses_subregion(tmp_path):
    """Crop = rechte Haelfte des two_squares-Bildes -> nur blau."""
    path = _make_two_squares(tmp_path)
    settings = ImportSettings(width=10, height=10, max_colors=5)
    # Rechte Haelfte: x von 0.5 bis 1.0
    pattern = import_image(path, settings, crop=(0.5, 0.0, 1.0, 1.0))

    # Nur eine Farbe (blau) sollte verwendet sein
    used = set()
    layer = pattern.active_layer
    for y in range(10):
        for x in range(10):
            idx = layer.get_stitch(x, y)
            if idx is not None:
                used.add(idx)
    assert len(used) == 1, "Crop nur auf blaue Haelfte -> eine Farbe"


def test_import_remembers_source_image_path(tmp_path):
    """Pattern speichert source_image_path fuer spaeteren Palettenwechsel."""
    path = _make_solid_rgb(tmp_path, (50, 100, 150))
    pattern = import_image(path, ImportSettings(width=8, height=8))
    assert pattern.source_image_path == str(path)


def test_import_metadata_carries_full_settings_for_recall(tmp_path):
    """metadata speichert genug, um den Import spaeter identisch zu
    wiederholen (Wizard Recall) -- insbesondere Groesse und Bildanpassung,
    die vorher fehlten."""
    path = _make_solid_rgb(tmp_path, (50, 100, 150))
    settings = ImportSettings(
        width=12,
        height=9,
        keep_aspect_ratio=False,
        brightness=1.2,
        contrast=0.8,
        saturation=1.5,
    )
    pattern = import_image(path, settings)
    assert pattern.metadata["keep_aspect_ratio"] is False
    assert pattern.metadata["brightness"] == pytest.approx(1.2)
    assert pattern.metadata["contrast"] == pytest.approx(0.8)
    assert pattern.metadata["saturation"] == pytest.approx(1.5)


def test_import_invalid_file_raises(tmp_path):
    """Nicht-existierende oder kaputte Datei -> ValueError."""
    fake = tmp_path / "doesnt_exist.png"
    with pytest.raises(ValueError):
        import_image(fake, ImportSettings(width=10, height=10))


def test_import_grayscale_image(tmp_path):
    """L-Mode Bild muss zu RGB konvertiert werden — kein Crash."""
    path = tmp_path / "gray.png"
    Image.new("L", (20, 20), 128).save(path)
    pattern = import_image(path, ImportSettings(width=10, height=10, max_colors=3))
    assert pattern.width == 10


def test_import_rgba_image_handles_alpha(tmp_path):
    """RGBA-Bilder werden auf RGB konvertiert."""
    arr = np.zeros((20, 20, 4), dtype=np.uint8)
    arr[..., :3] = [200, 100, 50]
    arr[..., 3] = 255  # voll-opak
    path = tmp_path / "rgba.png"
    Image.fromarray(arr, "RGBA").save(path)
    pattern = import_image(path, ImportSettings(width=10, height=10))
    assert pattern.width == 10


# ============================================================================
# create_preview
# ============================================================================


def test_create_preview_returns_pil_image(tmp_path):
    path = _make_two_squares(tmp_path)
    img = create_preview(path, ImportSettings(width=10, height=10), preview_size=100)
    assert isinstance(img, Image.Image)
    # Preview-Groesse: cell_size = 100 // max(10,10) = 10 -> 100x100
    assert img.size == (100, 100)


# ============================================================================
# generate_backstitches_from_edges
# ============================================================================


def test_backstitches_uniform_image_produces_nothing(tmp_path):
    """Einfarbiges Bild hat keine echten Kanten — Sobel-Rauschen
    wird durch epsilon-Floor herausgefiltert."""
    path = _make_solid_rgb(tmp_path, (100, 100, 100))
    result = generate_backstitches_from_edges(path, 20, 20, threshold=0.3)
    assert result == []


def test_backstitches_two_squares_produces_edge_segments(tmp_path):
    """Bei zwei kontrastierenden Quadraten muss mindestens ein Backstitch entstehen."""
    path = _make_two_squares(tmp_path)
    result = generate_backstitches_from_edges(path, 20, 20, threshold=0.3)
    assert len(result) > 0
    # Jeder Backstitch ist ein 4-Tupel von Ints
    for seg in result:
        assert len(seg) == 4
        assert all(isinstance(v, (int, np.integer)) for v in seg)


# ============================================================================
# change_palette / can_change_palette
# ============================================================================


def test_can_change_palette_requires_source_image(empty_pattern):
    """Ohne source_image_path keine Paletten-Konvertierung moeglich."""
    assert can_change_palette(empty_pattern) is False


def test_can_change_palette_with_imported_pattern(tmp_path):
    path = _make_two_squares(tmp_path)
    pattern = import_image(path, ImportSettings(width=10, height=10))
    assert can_change_palette(pattern) is True


def test_change_palette_no_source_returns_none(empty_pattern):
    assert change_palette(empty_pattern, "DMC") is None


def test_change_palette_preserves_image_adjustments(tmp_path):
    """change_palette() muss Helligkeit/Kontrast/Saettigung aus den
    metadata des Originalimports uebernehmen -- sonst faellt ein
    Palettenwechsel bei einem mit Bildanpassung importierten Muster
    stillschweigend auf das UNangepasste Originalbild zurueck (die drei
    Werte fehlten in der ImportSettings-Rekonstruktion, obwohl
    import_image() sie extra in metadata speichert)."""
    path = _make_solid_rgb(tmp_path, (120, 60, 200))
    settings = ImportSettings(
        width=8,
        height=8,
        palette_name="DMC",
        brightness=1.4,
        contrast=0.6,
        saturation=0.2,
    )
    pattern = import_image(path, settings)

    new_pattern = change_palette(pattern, "Anchor")

    assert new_pattern is not None
    assert new_pattern.metadata["brightness"] == pytest.approx(1.4)
    assert new_pattern.metadata["contrast"] == pytest.approx(0.6)
    assert new_pattern.metadata["saturation"] == pytest.approx(0.2)
