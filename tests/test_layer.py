# -*- coding: utf-8 -*-
"""
Erweiterte Tests für Layer und LayerStack.
"""

import pytest

from pysticky.core import Layer, LayerStack


class TestLayerAdvanced:
    """Erweiterte Tests für Layer."""

    def test_create_default(self):
        """Test: Standard-Layer erstellen."""
        layer = Layer(name="Test", width=10, height=10)
        assert layer.width == 10
        assert layer.height == 10
        assert layer.name == "Test"
        assert layer.visible is True
        assert layer.locked is False

    def test_create_with_name(self):
        """Test: Layer mit benutzerdefiniertem Namen."""
        layer = Layer(name="Hintergrund", width=5, height=5)
        assert layer.name == "Hintergrund"

    def test_set_and_get_stitch(self):
        """Test: Stich setzen und lesen."""
        layer = Layer(name="T", width=10, height=10)
        layer.set_stitch(3, 4, 5)
        assert layer.get_stitch(3, 4) == 5

    def test_set_stitch_out_of_bounds(self):
        """Test: Stich außerhalb der Grenzen."""
        layer = Layer(name="T", width=10, height=10)
        result1 = layer.set_stitch(15, 15, 1)
        result2 = layer.set_stitch(-1, -1, 1)
        assert result1 is False
        assert result2 is False

    def test_get_stitch_out_of_bounds(self):
        """Test: Stich außerhalb lesen gibt None."""
        layer = Layer(name="T", width=10, height=10)
        assert layer.get_stitch(15, 15) is None
        assert layer.get_stitch(-1, -1) is None

    def test_locked_prevents_set(self):
        """Test: Gesperrte Ebene verhindert Setzen."""
        layer = Layer(name="T", width=10, height=10)
        layer.locked = True
        layer.set_stitch(0, 0, 1)
        assert layer.get_stitch(0, 0) is None

    def test_stitch_count(self):
        """Test: Stich-Zählung."""
        layer = Layer(name="T", width=10, height=10)
        layer.set_stitch(0, 0, 1)
        layer.set_stitch(1, 1, 2)
        layer.set_stitch(2, 2, 1)
        assert layer.count_stitches() == 3

    def test_clear(self):
        """Test: Ebene leeren."""
        layer = Layer(name="T", width=10, height=10)
        layer.set_stitch(0, 0, 1)
        layer.set_stitch(1, 1, 2)
        layer.clear()
        assert layer.count_stitches() == 0

    def test_is_empty(self):
        """Test: Leere Ebene erkennen."""
        layer = Layer(name="T", width=10, height=10)
        assert layer.is_empty() is True
        layer.set_stitch(0, 0, 1)
        assert layer.is_empty() is False

    def test_resize_larger(self):
        """Test: Ebene vergrößern."""
        layer = Layer(name="T", width=5, height=5)
        layer.set_stitch(2, 2, 1)
        layer.resize(10, 10)
        assert layer.width == 10
        assert layer.height == 10
        assert layer.get_stitch(2, 2) == 1

    def test_resize_smaller(self):
        """Test: Ebene verkleinern schneidet ab."""
        layer = Layer(name="T", width=10, height=10)
        layer.set_stitch(8, 8, 1)
        layer.resize(5, 5)
        assert layer.width == 5
        assert layer.height == 5
        assert layer.get_stitch(8, 8) is None

    def test_copy(self):
        """Test: Ebene kopieren."""
        layer = Layer(name="Original", width=10, height=10)
        layer.set_stitch(3, 3, 5)
        copy = layer.copy()
        assert "Original" in copy.name
        assert copy.get_stitch(3, 3) == 5
        # Unabhängig
        copy.set_stitch(0, 0, 9)
        assert layer.get_stitch(0, 0) is None

    def test_get_bounds_empty(self):
        """Test: Bounds einer leeren Ebene (iterate_stitches gibt nichts)."""
        layer = Layer(name="T", width=10, height=10)
        stitches = list(layer.iterate_stitches())
        assert len(stitches) == 0

    def test_get_bounds_with_stitches(self):
        """Test: Iterate liefert gesetzte Stiche."""
        layer = Layer(name="T", width=20, height=20)
        layer.set_stitch(5, 3, 1)
        layer.set_stitch(10, 8, 2)
        stitches = list(layer.iterate_stitches())
        assert len(stitches) == 2
        positions = {(s[0], s[1]) for s in stitches}
        assert (5, 3) in positions
        assert (10, 8) in positions

    def test_fill_rectangle_via_grid(self):
        """Test: Bereich füllen via numpy."""
        layer = Layer(name="T", width=20, height=20)
        layer.grid[2:6, 2:6] = 3
        assert layer.get_stitch(2, 2) == 3
        assert layer.get_stitch(5, 5) == 3
        assert layer.get_stitch(1, 1) is None
        assert layer.get_stitch(6, 6) is None

    def test_completion_tracking(self):
        """Test: Fortschrittsverfolgung."""
        layer = Layer(name="T", width=10, height=10)
        layer.set_stitch(0, 0, 1)
        assert layer.is_completed(0, 0) is False
        layer.mark_completed(0, 0)
        assert layer.is_completed(0, 0) is True
        layer.unmark_completed(0, 0)
        assert layer.is_completed(0, 0) is False

    def test_color_counts(self):
        """Test: Farbzählung."""
        layer = Layer(name="T", width=10, height=10)
        layer.set_stitch(0, 0, 1)
        layer.set_stitch(1, 1, 1)
        layer.set_stitch(2, 2, 2)
        counts = layer.get_color_counts()
        assert counts[1] == 2
        assert counts[2] == 1

    def test_replace_color(self):
        """Test: Farbe ersetzen."""
        layer = Layer(name="T", width=10, height=10)
        layer.set_stitch(0, 0, 1)
        layer.set_stitch(1, 1, 1)
        replaced = layer.replace_color(1, 2)
        assert replaced == 2
        assert layer.get_stitch(0, 0) == 2
        assert layer.get_stitch(1, 1) == 2

    def test_rotate_90_cw(self):
        """Test: 90° Drehung im Uhrzeigersinn."""
        layer = Layer(name="T", width=10, height=5)
        layer.set_stitch(0, 0, 1)
        layer.rotate_90_cw()
        assert layer.width == 5
        assert layer.height == 10

    def test_flip_horizontal(self):
        """Test: Horizontale Spiegelung."""
        layer = Layer(name="T", width=10, height=10)
        layer.set_stitch(0, 0, 1)
        layer.flip_horizontal()
        assert layer.get_stitch(9, 0) == 1
        assert layer.get_stitch(0, 0) is None


class TestLayerStackAdvanced:
    """Erweiterte Tests für LayerStack."""

    def test_create_default(self):
        """Test: Standard-Stack erstellen."""
        stack = LayerStack(10, 10)
        assert len(stack) == 1
        assert stack.active_index == 0

    def test_add_layer(self):
        """Test: Ebene hinzufügen."""
        stack = LayerStack(10, 10)
        layer = stack.add_layer("Neue Ebene")
        assert isinstance(layer, Layer)
        assert len(stack) == 2

    def test_remove_layer(self):
        """Test: Ebene entfernen."""
        stack = LayerStack(10, 10)
        stack.add_layer("Ebene 2")
        assert len(stack) == 2
        stack.remove_layer(1)
        assert len(stack) == 1

    def test_remove_last_layer_fails(self):
        """Test: Letzte Ebene kann nicht entfernt werden."""
        stack = LayerStack(10, 10)
        stack.remove_layer(0)
        assert len(stack) == 1

    def test_move_layer(self):
        """Test: Ebene verschieben."""
        stack = LayerStack(10, 10)
        stack.add_layer("Ebene 2")
        stack.add_layer("Ebene 3")
        names_before = [l.name for l in stack.layers]
        stack.move_layer(0, 2)
        names_after = [l.name for l in stack.layers]
        assert names_before != names_after

    def test_active_layer(self):
        """Test: Aktive Ebene."""
        stack = LayerStack(10, 10)
        stack.add_layer("Ebene 2")
        stack.active_index = 0
        assert stack.active_layer.name == "Hintergrund"

    def test_active_index_clamp(self):
        """Test: Aktiver Index wird ignoriert bei ungültigem Wert."""
        stack = LayerStack(10, 10)
        old_idx = stack.active_index
        stack.active_index = 99
        assert stack.active_index == old_idx  # Bleibt unverändert

    def test_composite_stitch(self):
        """Test: Komposit-Stich (obere Ebene überschreibt)."""
        stack = LayerStack(10, 10)
        stack.add_layer("Ebene 2")

        stack.layers[0].set_stitch(0, 0, 1)
        stack.layers[1].set_stitch(0, 0, 2)

        # Die obere Ebene (1) sollte gewinnen
        assert stack.get_composite_stitch(0, 0) == 2

    def test_composite_hidden_layer(self):
        """Test: Unsichtbare Ebene wird übersprungen."""
        stack = LayerStack(10, 10)
        stack.add_layer("Ebene 2")

        stack.layers[0].set_stitch(0, 0, 1)
        stack.layers[1].set_stitch(0, 0, 2)
        stack.layers[1].visible = False

        assert stack.get_composite_stitch(0, 0) == 1

    def test_flatten(self):
        """Test: Ebenen zusammenführen gibt neues Layer."""
        stack = LayerStack(10, 10)
        stack.add_layer("Ebene 2")

        stack.layers[0].set_stitch(0, 0, 1)
        stack.layers[0].set_stitch(1, 1, 2)
        stack.layers[1].set_stitch(2, 2, 3)

        flat = stack.flatten()
        assert isinstance(flat, Layer)
        assert flat.get_stitch(0, 0) == 1
        assert flat.get_stitch(2, 2) == 3

    def test_replace_all_layers(self):
        """Test: Alle Ebenen ersetzen."""
        stack = LayerStack(10, 10)
        new_layers = [
            Layer(name="A", width=10, height=10),
            Layer(name="B", width=10, height=10),
        ]
        stack.replace_all_layers(new_layers)
        assert len(stack) == 2
        assert stack.layers[0].name == "A"

    def test_duplicate_layer(self):
        """Test: Ebene duplizieren."""
        stack = LayerStack(10, 10)
        stack.layers[0].set_stitch(5, 5, 3)
        copy = stack.duplicate_layer(0)
        assert copy is not None
        assert len(stack) == 2
        assert copy.get_stitch(5, 5) == 3

    def test_merge_down(self):
        """Test: Layer nach unten zusammenführen."""
        stack = LayerStack(10, 10)
        stack.add_layer("Oben")
        stack.layers[0].set_stitch(0, 0, 1)
        stack.layers[1].set_stitch(1, 1, 2)
        result = stack.merge_down(1)
        assert result is True
        assert len(stack) == 1
        assert stack.layers[0].get_stitch(0, 0) == 1
        assert stack.layers[0].get_stitch(1, 1) == 2

    def test_get_composite_grid(self):
        """Test: Composite Grid erstellen."""
        stack = LayerStack(5, 5)
        stack.layers[0].set_stitch(0, 0, 1)
        grid = stack.get_composite_grid()
        assert grid.shape == (5, 5)
        assert grid[0, 0] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
