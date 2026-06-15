"""Tests für die neuen Features: Stichtypen, Fadenstärke, Farbblindheit, Bild-Export."""

import numpy as np

from pysticky.core.color_blindness import ColorBlindType, clear_cache, simulate_color
from pysticky.core.file_io import load_pattern, save_pattern
from pysticky.core.layer import NO_STITCH, Layer
from pysticky.core.pattern import ColorEntry, Pattern
from pysticky.core.stitch import FLIP_H_MAP, StitchType
from pysticky.core.thread import Thread

# =========================================================================
# StitchType Enum
# =========================================================================


class TestStitchType:
    """Tests für StitchType mit festen Werten."""

    def test_fixed_values(self):
        assert StitchType.FULL.value == 0
        assert StitchType.HALF_TL_BR.value == 1
        assert StitchType.HALF_TR_BL.value == 2
        assert StitchType.QUARTER_TL.value == 3
        assert StitchType.QUARTER_TR.value == 4

    def test_lookup_maps_symmetric(self):
        for k, v in FLIP_H_MAP.items():
            assert FLIP_H_MAP[v] == k, f"FLIP_H_MAP not symmetric: {k} -> {v} -> {FLIP_H_MAP[v]}"


# =========================================================================
# Layer stitch_type_grid
# =========================================================================


class TestLayerStitchTypes:
    """Tests für Stichtyp-Grid im Layer."""

    def test_default_stitch_type_is_full(self):
        layer = Layer("test", 10, 10)
        assert layer.stitch_type_grid is not None
        assert layer.stitch_type_grid.shape == (10, 10)
        assert np.all(layer.stitch_type_grid == 0)

    def test_set_stitch_with_type(self):
        layer = Layer("test", 10, 10)
        layer.set_stitch(5, 5, 0, stitch_type=1)
        assert layer.get_stitch(5, 5) == 0
        assert layer.get_stitch_type(5, 5) == 1

    def test_remove_stitch_clears_type(self):
        layer = Layer("test", 10, 10)
        layer.set_stitch(3, 3, 0, stitch_type=2)
        layer.set_stitch(3, 3, None)
        assert layer.get_stitch(3, 3) is None
        assert layer.get_stitch_type(3, 3) == 0

    def test_copy_preserves_stitch_types(self):
        layer = Layer("test", 5, 5)
        layer.set_stitch(2, 2, 0, stitch_type=1)
        copy = layer.copy()
        assert copy.get_stitch_type(2, 2) == 1

    def test_clear_resets_stitch_types(self):
        layer = Layer("test", 5, 5)
        layer.set_stitch(2, 2, 0, stitch_type=1)
        layer.clear()
        assert layer.get_stitch_type(2, 2) == 0

    def test_resize_preserves_stitch_types(self):
        layer = Layer("test", 5, 5)
        layer.set_stitch(2, 2, 0, stitch_type=2)
        layer.resize(10, 10)
        assert layer.get_stitch_type(2, 2) == 2
        assert layer.get_stitch_type(8, 8) == 0

    def test_crop_preserves_stitch_types(self):
        layer = Layer("test", 10, 10)
        layer.set_stitch(5, 5, 0, stitch_type=1)
        layer.crop(4, 4, 3, 3)
        assert layer.get_stitch_type(1, 1) == 1

    def test_flip_horizontal_remaps_types(self):
        layer = Layer("test", 5, 5)
        layer.set_stitch(2, 2, 0, stitch_type=1)  # HALF_TL_BR
        layer.flip_horizontal()
        # After horizontal flip, TL_BR (1) -> TR_BL (2)
        assert layer.get_stitch_type(2, 2) == 2

    def test_flip_vertical_remaps_types(self):
        layer = Layer("test", 5, 5)
        layer.set_stitch(2, 2, 0, stitch_type=1)  # HALF_TL_BR
        layer.flip_vertical()
        assert layer.get_stitch_type(2, 2) == 2

    def test_rotate_cw_remaps_types(self):
        layer = Layer("test", 5, 5)
        layer.set_stitch(2, 2, 0, stitch_type=1)  # HALF_TL_BR
        layer.rotate_90_cw()
        assert layer.get_stitch_type(2, 2) == 2  # -> TR_BL

    def test_replace_color_with_nostitch_clears_type(self):
        layer = Layer("test", 5, 5)
        layer.set_stitch(1, 1, 0, stitch_type=1)
        layer.replace_color(0, NO_STITCH)
        assert layer.get_stitch_type(1, 1) == 0


# =========================================================================
# ColorEntry strands
# =========================================================================


class TestColorEntryStrands:
    """Tests für Fadenstärke."""

    def test_default_strands_is_2(self):
        thread = Thread.from_hex("Test", "#ff0000")
        entry = ColorEntry(thread=thread, symbol="X")
        assert entry.strands == 2

    def test_custom_strands(self):
        thread = Thread.from_hex("Test", "#ff0000")
        entry = ColorEntry(thread=thread, symbol="X", strands=4)
        assert entry.strands == 4


# =========================================================================
# File I/O roundtrip mit Stichtypen und Strands
# =========================================================================


class TestFileIONewFeatures:
    """Tests für Serialisierung neuer Features."""

    def test_strands_roundtrip(self, tmp_path):
        pattern = Pattern(width=5, height=5)
        thread = Thread.from_hex("Rot", "#ff0000")
        pattern.add_color(thread)
        pattern.color_entries[0].strands = 4
        pattern.set_stitch(2, 2, 0)

        filepath = tmp_path / "test_strands.pxs"
        save_pattern(pattern, filepath)
        loaded = load_pattern(filepath)

        assert loaded.color_entries[0].strands == 4

    def test_strands_default_for_old_files(self, tmp_path):
        """Alte Dateien ohne strands sollten Default 2 verwenden."""
        pattern = Pattern(width=5, height=5)
        thread = Thread.from_hex("Blau", "#0000ff")
        pattern.add_color(thread)

        filepath = tmp_path / "test_default.pxs"
        save_pattern(pattern, filepath)
        loaded = load_pattern(filepath)

        assert loaded.color_entries[0].strands == 2

    def test_stitch_types_roundtrip(self, tmp_path):
        pattern = Pattern(width=5, height=5)
        thread = Thread.from_hex("Rot", "#ff0000")
        pattern.add_color(thread)

        layer = pattern.active_layer
        layer.set_stitch(1, 1, 0, stitch_type=0)  # FULL
        layer.set_stitch(2, 2, 0, stitch_type=1)  # HALF_TL_BR
        layer.set_stitch(3, 3, 0, stitch_type=2)  # HALF_TR_BL

        filepath = tmp_path / "test_stitch_types.pxs"
        save_pattern(pattern, filepath)
        loaded = load_pattern(filepath)

        loaded_layer = loaded.active_layer
        assert loaded_layer.get_stitch_type(1, 1) == 0
        assert loaded_layer.get_stitch_type(2, 2) == 1
        assert loaded_layer.get_stitch_type(3, 3) == 2


# =========================================================================
# Color Blindness Simulation
# =========================================================================


class TestColorBlindness:
    """Tests für Farbblindheits-Simulation."""

    def setup_method(self):
        clear_cache()

    def test_none_returns_unchanged(self):
        assert simulate_color(255, 0, 0, ColorBlindType.NONE) == (255, 0, 0)
        assert simulate_color(0, 128, 255, ColorBlindType.NONE) == (0, 128, 255)

    def test_protanopia_transforms_red(self):
        r, g, b = simulate_color(255, 0, 0, ColorBlindType.PROTANOPIA)
        # Red should be perceived differently
        assert r != 255 or g != 0 or b != 0

    def test_deuteranopia_transforms_green(self):
        r, g, b = simulate_color(0, 255, 0, ColorBlindType.DEUTERANOPIA)
        assert r != 0 or g != 255 or b != 0

    def test_tritanopia_transforms_blue(self):
        r, g, b = simulate_color(0, 0, 255, ColorBlindType.TRITANOPIA)
        assert r != 0 or g != 0 or b != 255

    def test_values_clamped_0_255(self):
        for cb_type in [
            ColorBlindType.PROTANOPIA,
            ColorBlindType.DEUTERANOPIA,
            ColorBlindType.TRITANOPIA,
        ]:
            r, g, b = simulate_color(255, 255, 255, cb_type)
            assert 0 <= r <= 255
            assert 0 <= g <= 255
            assert 0 <= b <= 255

    def test_cache_works(self):
        r1 = simulate_color(100, 50, 200, ColorBlindType.PROTANOPIA)
        r2 = simulate_color(100, 50, 200, ColorBlindType.PROTANOPIA)
        assert r1 == r2

    def test_clear_cache(self):
        simulate_color(100, 50, 200, ColorBlindType.PROTANOPIA)
        clear_cache()
        # Should still work after clearing
        r = simulate_color(100, 50, 200, ColorBlindType.PROTANOPIA)
        assert len(r) == 3
