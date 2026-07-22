# -*- coding: utf-8 -*-
"""
Erweiterte Tests für Pattern-Klasse.
"""

import pytest

from pysticky.core import (
    Pattern,
    Thread,
)


class TestPatternCreation:
    """Tests für Pattern-Erstellung."""

    def test_default_pattern(self):
        """Test: Standard-Pattern erstellen."""
        p = Pattern()
        assert p.width == 50
        assert p.height == 50
        assert p.name == "Neues Muster"

    def test_custom_size(self):
        """Test: Benutzerdefinierte Größe."""
        p = Pattern(width=100, height=80)
        assert p.width == 100
        assert p.height == 80

    def test_custom_name(self):
        """Test: Benutzerdefinierter Name."""
        p = Pattern(name="Mein Muster")
        assert p.name == "Mein Muster"

    def test_fabric_count(self):
        """Test: Stoffzählung."""
        p = Pattern(fabric_count=18)
        assert p.fabric_count == 18


class TestPatternColors:
    """Tests für Farbverwaltung."""

    def test_add_color(self):
        """Test: Farbe hinzufügen."""
        p = Pattern()
        p.color_entries.clear()
        thread = Thread.from_hex("Rot", "#FF0000")
        idx = p.add_color(thread)
        assert idx == 0
        assert len(p.color_entries) == 1

    def test_add_multiple_colors(self):
        """Test: Mehrere Farben hinzufügen."""
        p = Pattern()
        p.color_entries.clear()
        for name, hex_color in [("Rot", "#FF0000"), ("Grün", "#00FF00"), ("Blau", "#0000FF")]:
            p.add_color(Thread.from_hex(name, hex_color))
        assert len(p.color_entries) == 3

    def test_get_color_entry(self):
        """Test: Farb-Eintrag abrufen."""
        p = Pattern()
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        entry = p.get_color_entry(0)
        assert entry is not None
        assert entry.thread.name == "Rot"

    def test_get_color_entry_invalid(self):
        """Test: Ungültiger Farbindex."""
        p = Pattern()
        assert p.get_color_entry(999) is None

    def test_remove_color(self):
        """Test: Farbe entfernen."""
        p = Pattern()
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        p.add_color(Thread.from_hex("Grün", "#00FF00"))
        p.remove_color(0)
        assert len(p.color_entries) == 1
        assert p.color_entries[0].thread.name == "Grün"

    def test_remove_color_updates_backstitch_indices(self):
        """Regression (Runde 22): remove_color() rief nie
        BackstitchManager.update_color_indices() auf -- Rueckstiche auf
        einem hoeheren Farbindex zeigten danach auf die falsche
        (nachgerueckte) Farbe, oder verursachten einen IndexError, wenn
        der geloeschte Index der letzte war."""
        p = Pattern(width=10, height=10)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        p.add_color(Thread.from_hex("Grün", "#00FF00"))
        p.add_color(Thread.from_hex("Blau", "#0000FF"))
        # Rueckstich auf Farbe 1 (Gruen) und Farbe 2 (Blau)
        p.add_backstitch(0, 0, 1, 1, color_index=1)
        p.add_backstitch(2, 2, 3, 3, color_index=2)

        p.remove_color(0)  # Rot entfernen -> Gruen wird 0, Blau wird 1

        indices = sorted(bs.color_index for bs in p.backstitches)
        assert indices == [0, 1]
        # Alle verbleibenden Backstitch-Farbindizes muessen gueltig sein
        for bs in p.backstitches:
            assert 0 <= bs.color_index < len(p.color_entries)

    def test_remove_color_removes_backstitches_on_deleted_color(self):
        p = Pattern(width=10, height=10)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        p.add_color(Thread.from_hex("Grün", "#00FF00"))
        p.add_backstitch(0, 0, 1, 1, color_index=0)

        p.remove_color(0)

        assert len(p.backstitches) == 0


class TestPatternStitches:
    """Tests für Stich-Operationen."""

    def test_set_stitch(self):
        """Test: Stich setzen."""
        p = Pattern(width=10, height=10)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        p.set_stitch(5, 5, 0)
        assert p.get_stitch(5, 5) == 0

    def test_set_stitch_on_locked_layer_does_not_corrupt_stitch_count(self):
        """Regression (Runde 13): Pattern.set_stitch() dekrementierte die
        alte Farbe unbedingt VOR dem Aufruf von layer.set_stitch() -- bei
        einem gesperrten Layer gibt dieser False zurueck (Grid unveraendert),
        aber die Dekrementierung war schon passiert. Jeder Versuch, auf
        einem gesperrten Layer zu zeichnen, liess stitch_count um 1 driften,
        obwohl sich am Grid nichts aenderte (Garnverbrauch/Fortschritt/
        Einkaufsliste lesen alle stitch_count)."""
        p = Pattern(width=10, height=10)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        p.set_stitch(5, 5, 0)
        assert p.color_entries[0].stitch_count == 1

        p.active_layer.locked = True
        result = p.set_stitch(5, 5, 0)

        assert result is False
        assert p.get_stitch(5, 5) == 0  # Grid unveraendert
        assert p.color_entries[0].stitch_count == 1  # NICHT auf 0 gefallen

    def test_total_stitches(self):
        """Test: Gesamtzahl Stiche."""
        p = Pattern(width=10, height=10)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        p.set_stitch(0, 0, 0)
        p.set_stitch(1, 1, 0)
        p.set_stitch(2, 2, 0)
        assert p.total_stitches == 3

    def test_recalculate_stitch_counts(self):
        """Test: Stich-Zählung neu berechnen."""
        p = Pattern(width=10, height=10)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        p.add_color(Thread.from_hex("Blau", "#0000FF"))
        p.set_stitch(0, 0, 0)
        p.set_stitch(1, 1, 0)
        p.set_stitch(2, 2, 1)
        p.recalculate_stitch_counts()
        assert p.color_entries[0].stitch_count == 2
        assert p.color_entries[1].stitch_count == 1


class TestPatternStatistics:
    """Tests für Statistiken."""

    def test_get_statistics(self):
        """Test: Statistiken abrufen."""
        p = Pattern(width=20, height=15)
        stats = p.get_statistics()
        assert stats["width"] == 20
        assert stats["height"] == 15
        assert "total_stitches" in stats
        assert "color_count" in stats

    def test_size_in_cm(self):
        """Test: Größe in cm."""
        p = Pattern(width=14, height=14, fabric_count=14)
        stats = p.get_statistics()
        # 14 Stiche bei 14ct = 1 Inch = 2.54 cm
        assert "width_cm" in stats
        assert abs(stats["width_cm"] - 2.54) < 0.1


class TestPatternTransformations:
    """Tests für Transformationen."""

    def test_resize(self):
        """Test: Muster skalieren."""
        p = Pattern(width=10, height=10)
        p.resize(20, 15)
        assert p.width == 20
        assert p.height == 15

    def test_resize_shrink_recalculates_stitch_count(self):
        """Regression: Verkleinern verwarf Stiche ausserhalb der neuen
        Groesse, aktualisierte aber nie color_entries[i].stitch_count --
        get_statistics()/Garnverbrauch-Schaetzungen blieben dauerhaft zu
        hoch."""
        p = Pattern(width=10, height=10)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        p.set_stitch(1, 1, 0)  # bleibt nach dem Verkleinern erhalten
        p.set_stitch(8, 8, 0)  # faellt nach dem Verkleinern weg
        assert p.color_entries[0].stitch_count == 2

        p.resize(5, 5)

        assert p.color_entries[0].stitch_count == 1

    def test_crop(self):
        """Test: Muster beschneiden (x, y, width, height)."""
        p = Pattern(width=20, height=20)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        p.set_stitch(10, 10, 0)
        # Crop: ab (5,5) mit Breite 10, Höhe 10
        result = p.crop(5, 5, 10, 10)
        assert result is True
        assert p.width == 10
        assert p.height == 10
        # Stich war bei (10,10), nach Crop ab (5,5) -> relativ (5,5)
        assert p.get_stitch(5, 5) == 0

    def test_crop_recalculates_stitch_count(self):
        """Regression: crop() aktualisierte color_entries[i].stitch_count
        nie -- eine weggeschnittene Farbe blieb mit voller Alt-Zaehlung in
        der Statistik stehen."""
        p = Pattern(width=20, height=20)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        p.set_stitch(10, 10, 0)  # bleibt im Crop-Bereich
        p.set_stitch(0, 0, 0)  # faellt weg
        assert p.color_entries[0].stitch_count == 2

        p.crop(5, 5, 10, 10)

        assert p.color_entries[0].stitch_count == 1

    def test_flatten_layers(self):
        """Test: Ebenen vereinen."""
        p = Pattern(width=10, height=10)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        p.layer_stack.add_layer("Ebene 2")
        # Setze auf aktiver Ebene (Ebene 2)
        p.set_stitch(0, 0, 0)
        p.layer_stack.active_index = 0
        p.set_stitch(1, 1, 0)
        p.flatten_layers()
        assert len(p.layer_stack) == 1


class TestPatternBackstitchTransforms:
    """Regression: rotate/flip/crop/resize aktualisierten die Grids, ließen
    Rückstich-Koordinaten (absolute Pattern-Position in halben Stichen)
    aber komplett unangetastet -- Konturen wären nach jeder dieser
    Operationen an der alten, jetzt falschen Stelle stehen geblieben,
    völlig losgelöst vom (rotierten/gespiegelten/verschobenen) Grid."""

    def _pattern(self, width=4, height=6):
        p = Pattern(width=width, height=height)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        return p

    def test_rotate_90_cw_transforms_backstitch(self):
        p = self._pattern(width=4, height=6)
        p.add_backstitch(0, 0, 2, 2, 0)

        p.rotate_90_cw()

        assert p.width == 6 and p.height == 4
        bs = p.backstitches[0]
        # Herleitung: altes (x,y) -> neues (2*H_alt - y, x), H_alt=6
        assert (bs.x1, bs.y1, bs.x2, bs.y2) == (12, 0, 10, 2)

    def test_rotate_90_ccw_transforms_backstitch(self):
        p = self._pattern(width=4, height=6)
        p.add_backstitch(0, 0, 2, 2, 0)

        p.rotate_90_ccw()

        assert p.width == 6 and p.height == 4
        bs = p.backstitches[0]
        # Herleitung: altes (x,y) -> neues (y, 2*W_alt - x), W_alt=4
        assert (bs.x1, bs.y1, bs.x2, bs.y2) == (0, 8, 2, 6)

    def test_rotate_180_transforms_backstitch(self):
        p = self._pattern(width=4, height=6)
        p.add_backstitch(0, 0, 2, 2, 0)

        p.rotate_180()

        assert p.width == 4 and p.height == 6
        bs = p.backstitches[0]
        assert (bs.x1, bs.y1, bs.x2, bs.y2) == (8, 12, 6, 10)

    def test_flip_horizontal_transforms_backstitch(self):
        p = self._pattern(width=4, height=6)
        p.add_backstitch(0, 0, 2, 2, 0)

        p.flip_horizontal()

        bs = p.backstitches[0]
        assert (bs.x1, bs.y1, bs.x2, bs.y2) == (8, 0, 6, 2)

    def test_flip_vertical_transforms_backstitch(self):
        p = self._pattern(width=4, height=6)
        p.add_backstitch(0, 0, 2, 2, 0)

        p.flip_vertical()

        bs = p.backstitches[0]
        assert (bs.x1, bs.y1, bs.x2, bs.y2) == (0, 12, 2, 10)

    def test_crop_shifts_and_keeps_backstitch_inside_new_bounds(self):
        p = self._pattern(width=4, height=6)
        # Zelle (1,1) in Stich-Koordinaten -> (2,2)-(4,4) in halben Stichen.
        p.add_backstitch(2, 2, 4, 4, 0)

        p.crop(1, 1, 2, 2)

        assert len(p.backstitches) == 1
        bs = p.backstitches[0]
        assert (bs.x1, bs.y1, bs.x2, bs.y2) == (0, 0, 2, 2)

    def test_crop_drops_backstitch_outside_new_bounds(self):
        p = self._pattern(width=4, height=6)
        # Liegt komplett vor dem Crop-Bereich (der bei (1,1) beginnt).
        p.add_backstitch(0, 0, 2, 2, 0)

        p.crop(1, 1, 2, 2)

        assert len(p.backstitches) == 0

    def test_resize_shrink_drops_backstitch_outside_new_bounds(self):
        p = self._pattern(width=4, height=6)
        p.add_backstitch(0, 0, 2, 2, 0)  # bleibt erhalten
        p.add_backstitch(6, 6, 8, 8, 0)  # faellt weg (x=6/8 > neue Breite*2=4)

        p.resize(2, 3)

        assert len(p.backstitches) == 1
        bs = p.backstitches[0]
        assert (bs.x1, bs.y1, bs.x2, bs.y2) == (0, 0, 2, 2)

    def test_resize_grow_keeps_backstitch_unchanged(self):
        p = self._pattern(width=4, height=6)
        p.add_backstitch(0, 0, 2, 2, 0)

        p.resize(10, 10)

        assert len(p.backstitches) == 1
        bs = p.backstitches[0]
        assert (bs.x1, bs.y1, bs.x2, bs.y2) == (0, 0, 2, 2)


class TestPatternProgress:
    """Tests für Fortschrittsverfolgung."""

    def test_mark_completed(self):
        """Test: Stich als erledigt markieren."""
        p = Pattern(width=10, height=10)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        p.set_stitch(0, 0, 0)
        result = p.mark_stitch_completed(0, 0, layer_index=0)
        assert result is True

    def test_progress_statistics(self):
        """Test: Fortschritts-Statistiken."""
        p = Pattern(width=10, height=10)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        p.set_stitch(0, 0, 0)
        p.set_stitch(1, 1, 0)
        p.mark_stitch_completed(0, 0, layer_index=0)
        progress = p.get_progress_statistics()
        assert progress["total_stitches"] == 2
        assert progress["completed_stitches"] == 1
        assert progress["progress_percent"] == 50.0

    def test_reset_progress(self):
        """Test: Fortschritt zurücksetzen."""
        p = Pattern(width=10, height=10)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        p.set_stitch(0, 0, 0)
        p.mark_stitch_completed(0, 0, layer_index=0)
        p.reset_progress()
        progress = p.get_progress_statistics()
        assert progress["completed_stitches"] == 0


class TestPatternBackstitches:
    """Tests für Backstitches im Pattern."""

    def test_add_backstitch(self):
        """Test: Backstitch hinzufügen."""
        p = Pattern(width=10, height=10)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Schwarz", "#000000"))
        p.add_backstitch(0, 0, 4, 4, 0)
        assert len(p.backstitches) == 1

    def test_backstitches_property(self):
        """Test: Backstitches-Eigenschaft."""
        p = Pattern(width=10, height=10)
        assert len(p.backstitches) == 0


class TestPatternIterateComposite:
    """Tests für iterate_composite_stitches."""

    def test_iterate_composite(self):
        """Test: Komposit-Stiche iterieren."""
        p = Pattern(width=10, height=10)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        p.set_stitch(0, 0, 0)
        p.set_stitch(1, 1, 0)
        stitches = list(p.iterate_composite_stitches())
        assert len(stitches) == 2

    def test_iterate_composite_empty(self):
        """Test: Leeres Pattern iterieren."""
        p = Pattern(width=5, height=5)
        p.color_entries.clear()
        stitches = list(p.iterate_composite_stitches())
        assert len(stitches) == 0


class TestPatternFillRectangle:
    """Tests für fill_rectangle."""

    def test_fill(self):
        """Test: Rechteck füllen."""
        p = Pattern(width=20, height=20)
        p.color_entries.clear()
        p.add_color(Thread.from_hex("Rot", "#FF0000"))
        p.fill_rectangle(2, 2, 5, 5, 0)
        assert p.get_stitch(2, 2) == 0
        assert p.get_stitch(5, 5) == 0
        assert p.get_stitch(1, 1) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
