# -*- coding: utf-8 -*-
"""
Tests für das Pattern-Modul.
"""

import pytest

from pysticky.core import (
    Layer,
    LayerStack,
    Pattern,
    Thread,
    ThreadColor,
)


class TestThreadColor:
    """Tests für ThreadColor."""

    def test_from_hex(self):
        """Test: Farbe aus Hex erstellen."""
        color = ThreadColor.from_hex("#FF0000")
        assert color.r == 255
        assert color.g == 0
        assert color.b == 0

    def test_from_hex_shorthand_3_digit(self):
        """Regression: die 3-stellige CSS-Kurzform ("#FFF" == "#FFFFFF")
        crashte vorher mit einem verwirrenden rohen int(..., 16)-ValueError
        statt entweder zu funktionieren oder klar zu fehlermelden."""
        color = ThreadColor.from_hex("#FFF")
        assert (color.r, color.g, color.b) == (255, 255, 255)

        color2 = ThreadColor.from_hex("A1F")  # ohne '#', jede Ziffer doppelt
        assert (color2.r, color2.g, color2.b) == (0xAA, 0x11, 0xFF)

    def test_to_hex(self):
        """Test: Farbe zu Hex konvertieren."""
        color = ThreadColor(r=255, g=128, b=0)
        assert color.to_hex() == "#FF8000"

    def test_luminance(self):
        """Test: Helligkeit berechnen."""
        white = ThreadColor(255, 255, 255)
        black = ThreadColor(0, 0, 0)

        assert white.luminance == 1.0
        assert black.luminance == 0.0

    def test_is_light(self):
        """Test: Hell/Dunkel erkennen."""
        white = ThreadColor(255, 255, 255)
        black = ThreadColor(0, 0, 0)

        assert white.is_light is True
        assert black.is_light is False

    def test_clamp_values(self):
        """Test: Werte werden auf 0-255 begrenzt."""
        color = ThreadColor(r=300, g=-10, b=128)
        assert color.r == 255
        assert color.g == 0
        assert color.b == 128


class TestThread:
    """Tests für Thread."""

    def test_create_from_hex(self):
        """Test: Garn aus Hex erstellen."""
        thread = Thread.from_hex("Rot", "#FF0000", manufacturer="DMC", catalog_number="321")

        assert thread.name == "Rot"
        assert thread.color.r == 255
        assert thread.manufacturer == "DMC"
        assert thread.catalog_number == "321"


class TestLayer:
    """Tests für Layer."""

    def test_create_layer(self):
        """Test: Layer erstellen."""
        layer = Layer(name="Test", width=10, height=10)

        assert layer.name == "Test"
        assert layer.width == 10
        assert layer.height == 10
        assert layer.visible is True
        assert layer.locked is False

    def test_set_and_get_stitch(self):
        """Test: Stich setzen und lesen."""
        layer = Layer(name="Test", width=10, height=10)

        layer.set_stitch(5, 5, 1)
        assert layer.get_stitch(5, 5) == 1
        assert layer.get_stitch(0, 0) is None

    def test_locked_layer(self):
        """Test: Gesperrtes Layer kann nicht bearbeitet werden."""
        layer = Layer(name="Test", width=10, height=10)
        layer.locked = True

        result = layer.set_stitch(5, 5, 1)
        assert result is False
        assert layer.get_stitch(5, 5) is None

    def test_out_of_bounds(self):
        """Test: Stich außerhalb des Bereichs."""
        layer = Layer(name="Test", width=10, height=10)

        result = layer.set_stitch(100, 100, 1)
        assert result is False

    def test_count_stitches(self):
        """Test: Stiche zählen."""
        layer = Layer(name="Test", width=10, height=10)

        layer.set_stitch(0, 0, 1)
        layer.set_stitch(1, 1, 2)
        layer.set_stitch(2, 2, 1)

        assert layer.count_stitches() == 3

    def test_is_empty(self):
        """Test: Leeres Layer erkennen."""
        layer = Layer(name="Test", width=10, height=10)
        assert layer.is_empty() is True

        layer.set_stitch(5, 5, 1)
        assert layer.is_empty() is False

    def test_clear(self):
        """Test: Layer leeren."""
        layer = Layer(name="Test", width=10, height=10)
        layer.set_stitch(5, 5, 1)

        layer.clear()

        assert layer.is_empty() is True

    def test_resize(self):
        """Test: Layer-Größe ändern."""
        layer = Layer(name="Test", width=10, height=10)
        layer.set_stitch(5, 5, 1)

        layer.resize(20, 20)

        assert layer.width == 20
        assert layer.height == 20
        assert layer.get_stitch(5, 5) == 1  # Alter Stich bleibt

    def test_copy(self):
        """Test: Layer kopieren."""
        layer = Layer(name="Original", width=10, height=10)
        layer.set_stitch(5, 5, 1)

        copy = layer.copy()

        assert copy.name == "Original (Kopie)"
        assert copy.get_stitch(5, 5) == 1

        # Änderung am Original beeinflusst Kopie nicht
        layer.set_stitch(0, 0, 2)
        assert copy.get_stitch(0, 0) is None


class TestLayerStack:
    """Tests für LayerStack."""

    def test_create_with_default_layer(self):
        """Test: Stack hat Standard-Layer."""
        stack = LayerStack(width=10, height=10)

        assert len(stack) == 1
        assert stack[0].name == "Hintergrund"

    def test_add_layer(self):
        """Test: Layer hinzufügen."""
        stack = LayerStack(width=10, height=10)

        layer = stack.add_layer("Neues Layer")

        assert len(stack) == 2
        assert stack.active_layer == layer

    def test_remove_layer(self):
        """Test: Layer entfernen."""
        stack = LayerStack(width=10, height=10)
        stack.add_layer("Layer 2")

        removed = stack.remove_layer(1)

        assert len(stack) == 1
        assert removed.name == "Layer 2"

    def test_cannot_remove_last_layer(self):
        """Test: Letztes Layer kann nicht entfernt werden."""
        stack = LayerStack(width=10, height=10)

        result = stack.remove_layer(0)

        assert result is None
        assert len(stack) == 1

    def test_move_layer(self):
        """Test: Layer verschieben."""
        stack = LayerStack(width=10, height=10)
        stack.add_layer("Layer 1")
        stack.add_layer("Layer 2")

        stack.move_layer(0, 2)

        assert stack[2].name == "Hintergrund"

    def test_get_composite_stitch(self):
        """Test: Zusammengesetzter Stich (oberstes Layer gewinnt)."""
        stack = LayerStack(width=10, height=10)
        stack.add_layer("Layer 1")

        stack[0].set_stitch(5, 5, 1)  # Hintergrund
        stack[1].set_stitch(5, 5, 2)  # Layer 1 (oben)

        # Oberstes Layer gewinnt
        assert stack.get_composite_stitch(5, 5) == 2


class TestPattern:
    """Tests für Pattern."""

    def test_create_pattern(self):
        """Test: Muster erstellen."""
        pattern = Pattern(name="Test", width=50, height=50)

        assert pattern.name == "Test"
        assert pattern.width == 50
        assert pattern.height == 50
        assert len(pattern.layer_stack) == 1

    def test_resize(self):
        """Test: Muster-Größe ändern."""
        pattern = Pattern(width=50, height=50)

        pattern.resize(100, 100)

        assert pattern.width == 100
        assert pattern.height == 100

    def test_resize_invalid(self):
        """Test: Ungültige Größe."""
        pattern = Pattern(width=50, height=50)

        with pytest.raises(ValueError):
            pattern.resize(0, 0)

    def test_add_color(self):
        """Test: Farbe hinzufügen."""
        pattern = Pattern(width=50, height=50)
        pattern.color_entries.clear()

        thread = Thread.from_hex("Rot", "#FF0000")
        index = pattern.add_color(thread)

        assert index == 0
        assert len(pattern.color_entries) == 1

    def test_add_color_symbol_pool_exhaustion_stays_unique(self):
        """Regression: Sobald mehr Farben als len(SYMBOLS) hinzugefügt
        werden, fiel add_color(auto_symbol=True) auf ein hartkodiertes "?"
        zurück -- OHNE zu prüfen, ob "?" nicht schon regulär vergeben war.
        Jede weitere Farbe jenseits des Symbol-Pools bekam ebenfalls "?",
        wodurch beliebig viele Farben in Legende/Export ununterscheidbar
        wurden (genau die Garantie, die auto_symbol laut Docstring geben
        soll: "sonst waere jede importierte Farbe ununterscheidbar")."""
        from pysticky.core.pattern import SYMBOLS

        pattern = Pattern(width=10, height=10)
        pattern.color_entries.clear()

        num_colors = len(SYMBOLS) + 15
        for i in range(num_colors):
            pattern.add_color(Thread.from_hex(f"C{i}", f"#{i:06x}"))

        symbols = [entry.symbol for entry in pattern.color_entries]
        assert len(symbols) == len(set(symbols)), (
            f"Symbole nicht eindeutig, Duplikate: {[s for s in symbols if symbols.count(s) > 1]}"
        )

    def test_add_color_symbol_freed_after_removal(self):
        """Regression-Absicherung (bereits korrektes Verhalten): Wird eine
        Farbe entfernt, muss ihr Symbol beim nächsten automatischen
        add_color() wiederverwendet werden können, statt für immer als
        "belegt" zu gelten."""
        pattern = Pattern(width=10, height=10)
        pattern.color_entries.clear()

        idx_a = pattern.add_color(Thread.from_hex("A", "#111111"))
        idx_b = pattern.add_color(Thread.from_hex("B", "#222222"))
        freed_symbol = pattern.color_entries[idx_a].symbol

        pattern.remove_color(idx_a)
        idx_c = pattern.add_color(Thread.from_hex("C", "#333333"))

        # idx_b ist nach dem Löschen von idx_a auf 0 nachgerückt, idx_c ist 1
        assert idx_b == 1
        assert pattern.color_entries[idx_c].symbol == freed_symbol

    def test_set_stitch(self):
        """Test: Stich setzen."""
        pattern = Pattern(width=50, height=50)

        pattern.set_stitch(10, 10, 0)

        assert pattern.get_stitch(10, 10) == 0

    def test_stitch_count_update(self):
        """Test: Stichzahl wird aktualisiert."""
        pattern = Pattern(width=50, height=50)

        pattern.set_stitch(10, 10, 0)
        pattern.set_stitch(11, 11, 0)

        assert pattern.color_entries[0].stitch_count == 2

    def test_get_statistics(self):
        """Test: Statistiken abrufen."""
        pattern = Pattern(name="Test", width=50, height=50)

        stats = pattern.get_statistics()

        assert stats["name"] == "Test"
        assert stats["width"] == 50
        assert stats["height"] == 50
        assert stats["layer_count"] == 1

    def test_size_cm(self):
        """Test: Größe in cm berechnen."""
        pattern = Pattern(width=14, height=14, fabric_count=14)

        w_cm, h_cm = pattern.size_cm

        # 14 Stiche bei 14ct = 1 inch = 2.54 cm
        assert abs(w_cm - 2.54) < 0.01
        assert abs(h_cm - 2.54) < 0.01


class TestUndoRedo:
    """Tests für Undo/Redo."""

    def test_place_and_undo(self):
        """Test: Stich setzen und rückgängig machen."""
        from pysticky.core import PlaceStitchCommand, UndoManager

        pattern = Pattern(width=50, height=50)
        undo = UndoManager()
        undo.set_pattern(pattern)

        # Stich platzieren
        cmd = PlaceStitchCommand(pattern, 10, 10, 0, 0)
        undo.execute(cmd)

        assert pattern.active_layer.get_stitch(10, 10) == 0

        # Rückgängig
        undo.undo()

        assert pattern.active_layer.get_stitch(10, 10) is None

    def test_redo(self):
        """Test: Wiederholen."""
        from pysticky.core import PlaceStitchCommand, UndoManager

        pattern = Pattern(width=50, height=50)
        undo = UndoManager()
        undo.set_pattern(pattern)

        cmd = PlaceStitchCommand(pattern, 10, 10, 0, 0)
        undo.execute(cmd)
        undo.undo()
        undo.redo()

        assert pattern.active_layer.get_stitch(10, 10) == 0


class TestStitchCounting:
    """Tests für Stichzählung."""

    def test_recalculate_stitch_counts(self):
        """Test: Stichzahlen werden korrekt neu berechnet."""
        pattern = Pattern(width=10, height=10)
        pattern.color_entries.clear()
        pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
        pattern.add_color(Thread.from_hex("Blau", "#0000FF"))

        # Manuell Stiche setzen ohne Zählung (numpy array)
        layer = pattern.active_layer
        layer.grid[0, 0] = 0
        layer.grid[0, 1] = 0
        layer.grid[1, 0] = 1

        # Stichzahlen sind noch falsch
        assert pattern.color_entries[0].stitch_count == 0

        # Neu berechnen
        pattern.recalculate_stitch_counts()

        assert pattern.color_entries[0].stitch_count == 2
        assert pattern.color_entries[1].stitch_count == 1

    def test_set_stitch_invalid_color_index(self):
        """Test: Ungültiger Farbindex wird abgelehnt."""
        pattern = Pattern(width=10, height=10)
        # Pattern hat nur 1 Farbe (Index 0)

        # Ungültiger positiver Index
        result = pattern.set_stitch(5, 5, 999)
        assert result is False
        assert pattern.get_stitch(5, 5) is None

        # Negativer Index
        result = pattern.set_stitch(5, 5, -1)
        assert result is False

    def test_set_stitch_none_clears(self):
        """Test: None als color_index löscht den Stich."""
        pattern = Pattern(width=10, height=10)

        pattern.set_stitch(5, 5, 0)
        assert pattern.get_stitch(5, 5) == 0

        pattern.set_stitch(5, 5, None)
        assert pattern.get_stitch(5, 5) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
