# -*- coding: utf-8 -*-
"""
Tests für die Code-Verbesserungen.

Deckt die neuen/geänderten Funktionalitäten ab:
- LayerStack.replace_all_layers()
- LayerStack.append_layer_object()
- Pattern.iterate_composite_stitches() (numpy-optimiert)
- Pattern.fill_rectangle() (numpy-optimiert)
- Pattern.flatten_layers() (über öffentliche API)
- File I/O Roundtrip (über öffentliche API)
- BackstitchManager.find_at() statt _point_on_line
- Leeres Pattern / Edge Cases
"""

import pytest

from pysticky.core import (
    BackstitchManager,
    Layer,
    LayerStack,
    Pattern,
    Thread,
    load_pattern,
    save_pattern,
)

# =========================================================================
# LayerStack neue API
# =========================================================================


class TestLayerStackNewAPI:
    """Tests für replace_all_layers und append_layer_object."""

    def test_replace_all_layers(self):
        """Test: Alle Layer ersetzen."""
        stack = LayerStack(width=10, height=10)

        layer_a = Layer(name="A", width=10, height=10)
        layer_a.set_stitch(0, 0, 1)
        layer_b = Layer(name="B", width=10, height=10)
        layer_b.set_stitch(5, 5, 2)

        stack.replace_all_layers([layer_a, layer_b], active_index=1)

        assert len(stack) == 2
        assert stack[0].name == "A"
        assert stack[1].name == "B"
        assert stack.active_index == 1
        assert stack[0].get_stitch(0, 0) == 1
        assert stack[1].get_stitch(5, 5) == 2

    def test_replace_all_layers_clamps_active(self):
        """Test: active_index wird geclampt."""
        stack = LayerStack(width=10, height=10)
        layer = Layer(name="Einzig", width=10, height=10)

        stack.replace_all_layers([layer], active_index=99)
        assert stack.active_index == 0

    def test_replace_all_layers_empty_raises(self):
        """Test: Leere Liste wirft ValueError."""
        stack = LayerStack(width=10, height=10)

        with pytest.raises(ValueError):
            stack.replace_all_layers([])

    def test_append_layer_object(self):
        """Test: Existierendes Layer-Objekt hinzufügen."""
        stack = LayerStack(width=10, height=10)
        layer = Layer(name="Extern", width=10, height=10)
        layer.set_stitch(3, 3, 5)

        stack.append_layer_object(layer)

        assert len(stack) == 2  # "Hintergrund" + "Extern"
        assert stack[1].name == "Extern"
        assert stack[1].get_stitch(3, 3) == 5


# =========================================================================
# Pattern optimierte Methoden
# =========================================================================


class TestIterateCompositeStitches:
    """Tests für die optimierte iterate_composite_stitches."""

    def test_basic_iteration(self):
        """Test: Grundlegende Iteration liefert korrekte Ergebnisse."""
        pattern = Pattern(name="Test", width=10, height=10)
        pattern.set_stitch(1, 2, 0)
        pattern.set_stitch(3, 4, 0)

        stitches = list(pattern.iterate_composite_stitches())

        assert (1, 2, 0) in stitches
        assert (3, 4, 0) in stitches
        assert len(stitches) == 2

    def test_empty_pattern(self):
        """Test: Leeres Pattern liefert keine Stiche."""
        pattern = Pattern(name="Leer", width=5, height=5)
        pattern.color_entries.clear()

        # Layer manuell leeren (Pattern hat Standard-Farbe die gesetzt sein könnte)
        pattern.active_layer.clear()

        stitches = list(pattern.iterate_composite_stitches())
        assert len(stitches) == 0

    def test_multi_layer_composite(self):
        """Test: Compositing über mehrere Layer."""
        pattern = Pattern(name="Multi", width=10, height=10)
        pattern.add_color(Thread.from_hex("Rot", "#FF0000"))

        # Layer 0 (Hintergrund): Stich bei (0,0) mit Farbe 0
        pattern.layer_stack.active_index = 0
        pattern.set_stitch(0, 0, 0)

        # Layer 1: Stich bei (0,0) mit Farbe 1 (überdeckt Layer 0)
        pattern.layer_stack.add_layer("Oben")
        pattern.set_stitch(0, 0, 1)

        stitches = list(pattern.iterate_composite_stitches())
        # Das oberste Layer gewinnt
        stitch_at_00 = [s for s in stitches if s[0] == 0 and s[1] == 0]
        assert len(stitch_at_00) == 1
        assert stitch_at_00[0][2] == 1


class TestFillRectangle:
    """Tests für das optimierte fill_rectangle."""

    def test_basic_fill(self):
        """Test: Grundlegendes Rechteck füllen."""
        pattern = Pattern(name="Fill", width=20, height=20)
        pattern.fill_rectangle(2, 3, 5, 6, 0)

        assert pattern.active_layer.get_stitch(2, 3) == 0
        assert pattern.active_layer.get_stitch(5, 6) == 0
        assert pattern.active_layer.get_stitch(3, 4) == 0
        # Außerhalb
        assert pattern.active_layer.get_stitch(1, 3) is None
        assert pattern.active_layer.get_stitch(6, 6) is None

    def test_fill_updates_stitch_count(self):
        """Test: Stichzählung wird aktualisiert."""
        pattern = Pattern(name="Count", width=10, height=10)
        pattern.fill_rectangle(0, 0, 2, 2, 0)

        # 3x3 = 9 Stiche
        assert pattern.color_entries[0].stitch_count == 9

    def test_fill_replaces_old_stitches(self):
        """Test: Alte Stiche werden korrekt ersetzt."""
        pattern = Pattern(name="Replace", width=10, height=10)
        pattern.add_color(Thread.from_hex("Rot", "#FF0000"))

        # Zuerst mit Farbe 0 füllen
        pattern.fill_rectangle(0, 0, 4, 4, 0)
        assert pattern.color_entries[0].stitch_count == 25

        # Dann mit Farbe 1 übermalen
        pattern.fill_rectangle(0, 0, 4, 4, 1)
        assert pattern.color_entries[0].stitch_count == 0
        assert pattern.color_entries[1].stitch_count == 25

    def test_fill_swapped_coords(self):
        """Test: Vertauschte Koordinaten funktionieren."""
        pattern = Pattern(name="Swap", width=10, height=10)
        pattern.fill_rectangle(5, 5, 2, 2, 0)

        # Sollte wie (2,2)-(5,5) funktionieren
        assert pattern.active_layer.get_stitch(3, 3) == 0

    def test_fill_out_of_bounds_clamped(self):
        """Test: Füllung wird an Pattern-Grenzen geclampt."""
        pattern = Pattern(name="Clamp", width=5, height=5)
        # Teilweise außerhalb
        pattern.fill_rectangle(-2, -2, 2, 2, 0)

        assert pattern.active_layer.get_stitch(0, 0) == 0
        assert pattern.active_layer.get_stitch(2, 2) == 0


class TestFlattenLayers:
    """Tests für flatten_layers über öffentliche API."""

    def test_flatten_preserves_stitches(self):
        """Test: Stiche bleiben nach Flatten erhalten."""
        pattern = Pattern(name="Flat", width=10, height=10)

        # Stich auf Hintergrund
        pattern.set_stitch(0, 0, 0)

        # Neues Layer mit Stich
        pattern.layer_stack.add_layer("Oben")
        pattern.set_stitch(5, 5, 0)

        pattern.flatten_layers()

        assert len(pattern.layer_stack) == 1
        flat = pattern.layer_stack[0]
        assert flat.get_stitch(0, 0) == 0
        assert flat.get_stitch(5, 5) == 0

    def test_flatten_top_wins(self):
        """Test: Oberstes Layer gewinnt bei Überlappung."""
        pattern = Pattern(name="Overlap", width=10, height=10)
        pattern.add_color(Thread.from_hex("Rot", "#FF0000"))

        pattern.layer_stack.active_index = 0
        pattern.set_stitch(5, 5, 0)

        pattern.layer_stack.add_layer("Oben")
        pattern.set_stitch(5, 5, 1)

        pattern.flatten_layers()

        assert pattern.layer_stack[0].get_stitch(5, 5) == 1


# =========================================================================
# File I/O Roundtrip (mit neuer API)
# =========================================================================


class TestFileIORoundtrip:
    """Tests für Save/Load Roundtrip mit der neuen replace_all_layers API."""

    def test_roundtrip_preserves_layers(self, tmp_path):
        """Test: Layer werden korrekt gespeichert und geladen."""
        pattern = Pattern(name="Roundtrip", width=15, height=15)
        pattern.layer_stack.add_layer("Layer 1")
        pattern.layer_stack.add_layer("Layer 2")
        pattern.layer_stack.active_index = 1

        # Stiche auf verschiedenen Layern
        pattern.layer_stack.active_index = 0
        pattern.set_stitch(0, 0, 0)
        pattern.layer_stack.active_index = 1
        pattern.set_stitch(5, 5, 0)
        pattern.layer_stack.active_index = 2
        pattern.set_stitch(10, 10, 0)

        filepath = tmp_path / "roundtrip.pxs"
        save_pattern(pattern, str(filepath))
        loaded = load_pattern(str(filepath))

        assert len(loaded.layer_stack) == 3
        assert loaded.layer_stack[0].name == "Hintergrund"
        assert loaded.layer_stack[1].name == "Layer 1"
        assert loaded.layer_stack[2].name == "Layer 2"

        # Stiche prüfen
        assert loaded.layer_stack[0].get_stitch(0, 0) == 0
        assert loaded.layer_stack[1].get_stitch(5, 5) == 0
        assert loaded.layer_stack[2].get_stitch(10, 10) == 0

    def test_roundtrip_preserves_active_layer(self, tmp_path):
        """Test: Aktives Layer wird beibehalten."""
        pattern = Pattern(name="Active", width=10, height=10)
        pattern.layer_stack.add_layer("L1")
        pattern.layer_stack.add_layer("L2")
        pattern.layer_stack.active_index = 2

        filepath = tmp_path / "active.pxs"
        save_pattern(pattern, str(filepath))
        loaded = load_pattern(str(filepath))

        assert loaded.layer_stack.active_index == 2

    def test_roundtrip_empty_pattern(self, tmp_path):
        """Test: Leeres Pattern speichern/laden."""
        pattern = Pattern(name="Leer", width=5, height=5)

        filepath = tmp_path / "empty.pxs"
        save_pattern(pattern, str(filepath))
        loaded = load_pattern(str(filepath))

        assert loaded.name == "Leer"
        assert loaded.width == 5
        assert loaded.height == 5


# =========================================================================
# BackstitchManager
# =========================================================================


class TestBackstitchManagerFindAt:
    """Tests für BackstitchManager.find_at()."""

    def test_find_at_on_line(self):
        """Test: Backstitch auf der Linie finden."""
        manager = BackstitchManager()
        manager.add(0, 0, 10, 10, 0)

        found = manager.find_at(5, 5, tolerance=2)
        assert found is not None
        assert found.x1 == 0
        assert found.y2 == 10

    def test_find_at_miss(self):
        """Test: Kein Backstitch an der Position."""
        manager = BackstitchManager()
        manager.add(0, 0, 10, 10, 0)

        found = manager.find_at(0, 10, tolerance=1)
        assert found is None

    def test_find_at_empty(self):
        """Test: Leerer Manager."""
        manager = BackstitchManager()
        assert manager.find_at(5, 5) is None


# =========================================================================
# Edge Cases
# =========================================================================


class TestEdgeCases:
    """Tests für Randfälle."""

    def test_pattern_zero_colors(self):
        """Test: Pattern mit geleerten Farben."""
        pattern = Pattern(name="NoColor", width=5, height=5)
        pattern.color_entries.clear()

        stats = pattern.get_statistics()
        assert stats["color_count"] == 0
        assert stats["total_stitches"] == 0

    def test_pattern_1x1(self):
        """Test: Minimales 1x1 Pattern."""
        pattern = Pattern(name="Tiny", width=1, height=1)
        pattern.set_stitch(0, 0, 0)

        assert pattern.get_stitch(0, 0) == 0
        assert pattern.total_stitches == 1

    def test_large_pattern_bounds(self):
        """Test: Bounds-Berechnung bei größerem Pattern."""
        pattern = Pattern(name="Large", width=100, height=100)
        pattern.set_stitch(10, 20, 0)
        pattern.set_stitch(80, 90, 0)

        bounds = pattern.get_bounds()
        assert bounds == (10, 20, 80, 90)

    def test_bounds_empty_pattern(self):
        """Test: Bounds bei leerem Pattern."""
        pattern = Pattern(name="Empty", width=10, height=10)
        pattern.active_layer.clear()

        bounds = pattern.get_bounds()
        assert bounds == (0, 0, 0, 0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
