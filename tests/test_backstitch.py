# -*- coding: utf-8 -*-
"""
Tests für den BackstitchManager.
"""

import pytest

from pysticky.core import (
    Backstitch,
    BackstitchManager,
)


class TestBackstitch:
    """Tests für Backstitch-Datenklasse."""

    def test_create(self):
        """Test: Backstitch erstellen."""
        bs = Backstitch(0, 0, 4, 4, 0)
        assert bs.x1 == 0
        assert bs.y1 == 0
        assert bs.x2 == 4
        assert bs.y2 == 4
        assert bs.color_index == 0

    def test_to_dict(self):
        """Test: Backstitch zu Dict."""
        bs = Backstitch(1, 2, 3, 4, 5)
        d = bs.to_dict()
        assert d == {"x1": 1, "y1": 2, "x2": 3, "y2": 4, "color_index": 5}

    def test_from_dict(self):
        """Test: Backstitch aus Dict."""
        d = {"x1": 1, "y1": 2, "x2": 3, "y2": 4, "color_index": 5}
        bs = Backstitch.from_dict(d)
        assert bs.x1 == 1
        assert bs.color_index == 5

    def test_roundtrip(self):
        """Test: Dict-Roundtrip."""
        original = Backstitch(10, 20, 30, 40, 2)
        restored = Backstitch.from_dict(original.to_dict())
        assert restored == original


class TestBackstitchManager:
    """Tests für BackstitchManager."""

    def test_add(self):
        """Test: Backstitch hinzufügen."""
        mgr = BackstitchManager()
        bs = mgr.add(0, 0, 4, 4, 0)
        assert mgr.count() == 1
        assert bs.x1 == 0

    def test_remove(self):
        """Test: Backstitch entfernen."""
        mgr = BackstitchManager()
        bs = mgr.add(0, 0, 4, 4, 0)
        assert mgr.remove(bs) is True
        assert mgr.count() == 0

    def test_remove_nonexistent(self):
        """Test: Nicht vorhandenen Backstitch entfernen."""
        mgr = BackstitchManager()
        fake = Backstitch(99, 99, 99, 99, 99)
        assert mgr.remove(fake) is False

    def test_remove_uses_identity_not_value_equality(self):
        """Regression: zwei wertgleiche, aber unterschiedliche Backstitch-
        Instanzen (z.B. zweimal dieselbe Linie gezeichnet) muessen von
        remove() unterschieden werden -- remove(bs_a) darf NICHT
        stattdessen die wertgleiche bs_b loeschen (list.remove()/`in`
        nutzen sonst Backstitch's automatisch generiertes wertbasiertes
        __eq__, nicht Objekt-Identitaet)."""
        mgr = BackstitchManager()
        bs_a = mgr.add(0, 0, 4, 4, 0)
        bs_b = Backstitch(0, 0, 4, 4, 0)  # wertgleich zu bs_a, aber eigenes Objekt
        mgr._backstitches.append(bs_b)
        assert mgr.count() == 2

        assert mgr.remove(bs_a) is True

        assert mgr.count() == 1
        assert mgr.backstitches[0] is bs_b  # bs_b muss ueberleben, nicht bs_a

    def test_remove_at(self):
        """Test: Backstitch an Position entfernen."""
        mgr = BackstitchManager()
        mgr.add(0, 0, 10, 10, 0)
        removed = mgr.remove_at(5, 5, tolerance=2)
        assert removed is not None
        assert mgr.count() == 0

    def test_remove_at_miss(self):
        """Test: Kein Backstitch an Position."""
        mgr = BackstitchManager()
        mgr.add(0, 0, 10, 10, 0)
        removed = mgr.remove_at(0, 10, tolerance=1)
        assert removed is None
        assert mgr.count() == 1

    def test_remove_at_deletes_the_exact_scanned_instance(self):
        """Regression (Runde 18): remove_at() loeschte per
        self._backstitches.remove(bs) -- ein erneuter, wertbasierter Scan
        von vorn, statt die waehrend der eigenen Positions-Suche bereits
        gefundene Instanz per Index zu entfernen. Gleiche Identitaets-
        Semantik wie remove() (Runde 8): remove_at() gibt jetzt garantiert
        exakt die Instanz zurueck, die auch tatsaechlich aus der Liste
        entfernt wurde."""
        mgr = BackstitchManager()
        bs_a = mgr.add(0, 0, 10, 10, 0)
        bs_b = mgr.add(20, 20, 30, 30, 0)

        removed = mgr.remove_at(5, 5, tolerance=2)

        assert removed is bs_a
        assert mgr.count() == 1
        assert mgr.backstitches[0] is bs_b

    def test_find_at(self):
        """Test: Backstitch an Position finden."""
        mgr = BackstitchManager()
        mgr.add(0, 0, 10, 10, 0)
        found = mgr.find_at(5, 5, tolerance=2)
        assert found is not None
        assert found.x1 == 0

    def test_find_at_empty(self):
        """Test: Leerer Manager."""
        mgr = BackstitchManager()
        assert mgr.find_at(5, 5) is None

    def test_get_in_area(self):
        """Test: Backstitches in Bereich."""
        mgr = BackstitchManager()
        mgr.add(0, 0, 4, 4, 0)
        mgr.add(10, 10, 14, 14, 0)
        mgr.add(20, 20, 24, 24, 0)
        result = mgr.get_in_area(0, 0, 5, 5)
        assert len(result) == 1

    def test_get_by_color(self):
        """Test: Backstitches nach Farbe."""
        mgr = BackstitchManager()
        mgr.add(0, 0, 4, 4, 0)
        mgr.add(5, 5, 9, 9, 1)
        mgr.add(10, 10, 14, 14, 0)
        result = mgr.get_by_color(0)
        assert len(result) == 2

    def test_update_color_indices(self):
        """Test: Farbindizes nach Entfernen aktualisieren."""
        mgr = BackstitchManager()
        mgr.add(0, 0, 4, 4, 0)
        mgr.add(5, 5, 9, 9, 1)
        mgr.add(10, 10, 14, 14, 2)

        # Farbe 1 entfernen
        mgr.update_color_indices(1)

        assert mgr.count() == 2
        colors = [bs.color_index for bs in mgr]
        assert 0 in colors
        assert 1 in colors  # war vorher 2

    def test_clear(self):
        """Test: Alle Backstitches löschen."""
        mgr = BackstitchManager()
        mgr.add(0, 0, 4, 4, 0)
        mgr.add(5, 5, 9, 9, 1)
        mgr.clear()
        assert mgr.count() == 0

    def test_len(self):
        """Test: __len__ Methode."""
        mgr = BackstitchManager()
        assert len(mgr) == 0
        mgr.add(0, 0, 4, 4, 0)
        assert len(mgr) == 1

    def test_iter(self):
        """Test: __iter__ Methode."""
        mgr = BackstitchManager()
        mgr.add(0, 0, 4, 4, 0)
        mgr.add(5, 5, 9, 9, 1)
        items = list(mgr)
        assert len(items) == 2

    def test_to_list_and_from_list(self):
        """Test: Serialisierung und Deserialisierung."""
        mgr = BackstitchManager()
        mgr.add(0, 0, 4, 4, 0)
        mgr.add(5, 5, 9, 9, 1)

        data = mgr.to_list()
        assert len(data) == 2

        mgr2 = BackstitchManager()
        mgr2.from_list(data)
        assert mgr2.count() == 2
        assert mgr2.backstitches[0].x1 == 0
        assert mgr2.backstitches[1].color_index == 1

    def test_point_on_line_degenerate(self):
        """Test: Punkt auf degenerierter Linie (Start == Ende)."""
        mgr = BackstitchManager()
        assert mgr._point_on_line(5, 5, 5, 5, 5, 5, 1) is True
        assert mgr._point_on_line(7, 7, 5, 5, 5, 5, 1) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
