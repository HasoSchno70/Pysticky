# -*- coding: utf-8 -*-
"""
Tests für das Paletten-System.
"""

import pytest

from pysticky.core import (
    PaletteManager,
    Thread,
    ThreadColor,
    ThreadPalette,
    get_palette_manager,
    reset_palette_manager,
)


class TestThreadPalette:
    """Tests für ThreadPalette."""

    def _make_palette(self) -> ThreadPalette:
        """Erstellt eine Test-Palette."""
        threads = [
            Thread.from_hex("Rot", "#FF0000", manufacturer="DMC", catalog_number="321"),
            Thread.from_hex("Blau", "#0000FF", manufacturer="DMC", catalog_number="796"),
            Thread.from_hex("Grün", "#00FF00", manufacturer="DMC", catalog_number="699"),
            Thread.from_hex("Dunkelrot", "#800000", manufacturer="DMC", catalog_number="814"),
            Thread.from_hex("Schwarz", "#000000", manufacturer="DMC", catalog_number="310"),
        ]
        return ThreadPalette(name="Test", manufacturer="DMC", threads=threads)

    def test_len(self):
        """Test: Palette-Länge."""
        palette = self._make_palette()
        assert len(palette) == 5

    def test_iter(self):
        """Test: Über Palette iterieren."""
        palette = self._make_palette()
        names = [t.name for t in palette]
        assert "Rot" in names
        assert len(names) == 5

    def test_getitem(self):
        """Test: Index-Zugriff."""
        palette = self._make_palette()
        assert palette[0].name == "Rot"
        assert palette[4].name == "Schwarz"

    def test_find_by_number(self):
        """Test: Garn nach Katalognummer finden."""
        palette = self._make_palette()
        thread = palette.find_by_number("321")
        assert thread is not None
        assert thread.name == "Rot"

    def test_find_by_number_not_found(self):
        """Test: Nicht existierende Katalognummer."""
        palette = self._make_palette()
        assert palette.find_by_number("999") is None

    def test_find_by_name(self):
        """Test: Garn nach Name finden."""
        palette = self._make_palette()
        results = palette.find_by_name("rot")
        assert len(results) == 2  # "Rot" und "Dunkelrot"

    def test_find_similar_color(self):
        """Test: Ähnliche Farben finden."""
        palette = self._make_palette()
        red = ThreadColor(255, 0, 0)
        similar = palette.find_similar_color(red, max_results=2)
        assert len(similar) == 2
        # Rot sollte am ähnlichsten sein
        assert similar[0].name == "Rot"


class TestPaletteManager:
    """Tests für PaletteManager."""

    def test_load_all(self):
        """Test: Alle Paletten laden."""
        manager = PaletteManager()
        manager.load_all()
        palettes = manager.available_palettes
        assert len(palettes) > 0

    def test_get_palette(self):
        """Test: Palette abrufen."""
        manager = PaletteManager()
        manager.load_all()
        palettes = manager.available_palettes
        if palettes:
            palette = manager.get_palette(palettes[0])
            assert palette is not None
            assert len(palette) > 0

    def test_get_nonexistent_palette(self):
        """Test: Nicht existierende Palette."""
        manager = PaletteManager()
        manager.load_all()
        assert manager.get_palette("GibtEsNicht") is None

    def test_reload(self):
        """Test: Paletten neu laden."""
        manager = PaletteManager()
        manager.load_all()
        count_before = len(manager.available_palettes)
        manager.reload()
        count_after = len(manager.available_palettes)
        assert count_before == count_after

    def test_get_all_threads(self):
        """Test: Alle Garne abrufen."""
        manager = PaletteManager()
        manager.load_all()
        all_threads = manager.get_all_threads()
        assert len(all_threads) > 0

    def test_find_color_across_palettes(self):
        """Test: Farbe paletteübergreifend suchen."""
        manager = PaletteManager()
        manager.load_all()
        red = ThreadColor(255, 0, 0)
        results = manager.find_color_across_palettes(red, max_per_palette=2)
        assert len(results) > 0


class TestPaletteManagerSingleton:
    """Tests für den Singleton."""

    def test_singleton_returns_same_instance(self):
        """Test: Singleton gibt dieselbe Instanz zurück."""
        reset_palette_manager()
        m1 = get_palette_manager()
        m2 = get_palette_manager()
        assert m1 is m2

    def test_reset_creates_new_instance(self):
        """Test: Reset erstellt neue Instanz."""
        m1 = get_palette_manager()
        reset_palette_manager()
        m2 = get_palette_manager()
        assert m1 is not m2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
