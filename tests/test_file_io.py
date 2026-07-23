# -*- coding: utf-8 -*-
"""
Tests für Datei-Operationen.
"""

import json

import pytest

from pysticky.core import (
    Pattern,
    Thread,
    load_pattern,
    save_pattern,
)


class TestFileIO:
    """Tests für save_pattern und load_pattern."""

    def test_save_and_load_basic(self, tmp_path):
        """Test: Muster speichern und laden."""
        # Erstellen
        pattern = Pattern(name="Test", width=20, height=20)
        pattern.set_stitch(5, 5, 0)
        pattern.set_stitch(10, 10, 0)

        # Speichern
        filepath = tmp_path / "test.pxs"
        save_pattern(pattern, str(filepath))

        assert filepath.exists()

        # Laden
        loaded = load_pattern(str(filepath))

        assert loaded.name == "Test"
        assert loaded.width == 20
        assert loaded.height == 20
        assert loaded.get_stitch(5, 5) == 0
        assert loaded.get_stitch(10, 10) == 0

    def test_locked_layer_preserves_stitches_on_roundtrip(self, tmp_path):
        """Regressionstest: Gesperrte Ebenen verlieren ihre Stiche nicht beim Laden.

        Bug: locked wurde im _layer_from_dict VOR den set_stitch-Aufrufen
        gesetzt — was alle Stiche silent verwarf. Fix: locked erst NACH den
        Stichen setzen.
        """
        pattern = Pattern(name="Lock-Test", width=20, height=20)
        pattern.layer_stack.add_layer("LockedHeart")
        pattern.layer_stack.active_index = 1
        pattern.set_stitch(5, 5, 0)
        pattern.set_stitch(6, 6, 0)
        pattern.set_stitch(7, 7, 0)
        # Diese Ebene jetzt sperren
        pattern.layer_stack[1].locked = True

        filepath = tmp_path / "locked.pxs"
        save_pattern(pattern, str(filepath))
        loaded = load_pattern(str(filepath))

        assert len(loaded.layer_stack) >= 2
        locked_layer = loaded.layer_stack[1]
        assert locked_layer.locked is True
        # Die Stiche muessen erhalten geblieben sein — bevor dem Fix waren
        # diese drei alle weg.
        assert locked_layer.get_stitch(5, 5) == 0
        assert locked_layer.get_stitch(6, 6) == 0
        assert locked_layer.get_stitch(7, 7) == 0

    def test_color_stitch_counts_recalculated_on_load(self, tmp_path):
        """Stitch-Counts sollten beim Laden aus den Grids neu berechnet werden,
        statt veraltete gespeicherte Werte zu nutzen."""
        pattern = Pattern(name="Count-Test", width=10, height=10)
        pattern.set_stitch(0, 0, 0)
        pattern.set_stitch(1, 1, 0)
        # Manueller Eingriff: stitch_count manipulieren (so wie es passieren
        # koennte wenn eine Layer-Edit-Operation die Counts vergessen hat)
        pattern.color_entries[0].stitch_count = 999

        filepath = tmp_path / "counts.pxs"
        save_pattern(pattern, str(filepath))
        loaded = load_pattern(str(filepath))

        # Nach Load: Count muss zur Realitaet passen (2 Stiche), nicht 999
        assert loaded.color_entries[0].stitch_count == 2

    def test_save_with_colors(self, tmp_path):
        """Test: Muster mit Farben speichern."""
        pattern = Pattern(width=10, height=10)

        # Mehrere Farben hinzufügen
        red = Thread.from_hex("Rot", "#FF0000", manufacturer="DMC", catalog_number="321")
        blue = Thread.from_hex("Blau", "#0000FF", manufacturer="DMC", catalog_number="796")

        pattern.add_color(red)
        pattern.add_color(blue)

        pattern.set_stitch(0, 0, 1)  # Rot
        pattern.set_stitch(1, 1, 2)  # Blau

        # Speichern und laden
        filepath = tmp_path / "colors.pxs"
        save_pattern(pattern, str(filepath))
        loaded = load_pattern(str(filepath))

        assert len(loaded.color_entries) >= 3  # Standard + 2 neue
        assert loaded.get_stitch(0, 0) == 1
        assert loaded.get_stitch(1, 1) == 2

    def test_save_with_layers(self, tmp_path):
        """Test: Muster mit Ebenen speichern."""
        pattern = Pattern(width=10, height=10)

        pattern.layer_stack.add_layer("Layer 1")
        pattern.layer_stack.add_layer("Layer 2")

        pattern.set_stitch(0, 0, 0)  # Auf Layer 2

        pattern.layer_stack.active_index = 1
        pattern.set_stitch(5, 5, 0)  # Auf Layer 1

        filepath = tmp_path / "layers.pxs"
        save_pattern(pattern, str(filepath))
        loaded = load_pattern(str(filepath))

        assert len(loaded.layer_stack) == 3

    def test_save_with_backstitches(self, tmp_path):
        """Test: Muster mit Rückstichen speichern."""
        pattern = Pattern(width=10, height=10)

        pattern.add_backstitch(0, 0, 4, 4, 0)
        pattern.add_backstitch(10, 0, 10, 10, 0)

        filepath = tmp_path / "backstitches.pxs"
        save_pattern(pattern, str(filepath))
        loaded = load_pattern(str(filepath))

        assert len(loaded.backstitches) == 2
        assert loaded.backstitches[0].x1 == 0
        assert loaded.backstitches[0].x2 == 4

    def test_file_format_version(self, tmp_path):
        """Test: Dateiformat-Version wird gespeichert."""
        pattern = Pattern(width=10, height=10)

        filepath = tmp_path / "version.pxs"
        save_pattern(pattern, str(filepath))

        # JSON direkt lesen
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["format"] == "pysticky"
        assert "version" in data

    def test_load_nonexistent_file(self):
        """Test: Nicht existierende Datei laden."""
        with pytest.raises(FileNotFoundError):
            load_pattern("/nicht/vorhanden/test.pxs")

    def test_load_invalid_json(self, tmp_path):
        """Test: Ungültige JSON-Datei laden."""
        filepath = tmp_path / "invalid.pxs"
        filepath.write_text("{ ungültiges json }")

        with pytest.raises(Exception):  # json.JSONDecodeError oder ähnlich
            load_pattern(str(filepath))

    def test_load_raises_value_error_for_non_dict_top_level_json(self, tmp_path):
        """Regression (Autosave-Recovery-Audit): json.load() akzeptiert jedes
        gueltige JSON-Dokument als Top-Level-Wert, nicht nur Objekte -- eine
        versehentlich unter dem Autosave-Namen abgelegte fremde Datei (z.B.
        eine JSON-Liste) liess frueher `data.get("format")` mit einem rohen
        AttributeError crashen, statt des von load_pattern()'s eigenem
        Docstring versprochenen ValueError. Besonders relevant fuer
        _check_autosave_recovery(), das genau diesen Fall abfangen koennen
        muss."""
        filepath = tmp_path / "fremde_datei.pxs"
        filepath.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

        with pytest.raises(ValueError):
            load_pattern(str(filepath))

    def test_load_raises_value_error_for_non_dict_pattern_field(self, tmp_path):
        """Wie oben, aber der Fehler steckt eine Ebene tiefer: "pattern" ist
        vorhanden, aber kein Objekt. _dict_to_pattern() griff hier vorher mit
        `field not in data` zu, was fuer eine Zahl einen rohen TypeError statt
        eines ValueError ausloest."""
        filepath = tmp_path / "kaputtes_pattern_feld.pxs"
        filepath.write_text(
            json.dumps({"format": "pysticky", "version": "1.5", "pattern": 42}),
            encoding="utf-8",
        )

        with pytest.raises(ValueError):
            load_pattern(str(filepath))

    def test_load_falls_back_to_default_fabric_count_when_zero(self, tmp_path):
        """Regression (Runde 26): eine beschaedigte/handbearbeitete .pxs-
        Datei mit "fabric_count": 0 (oder negativ) wurde bisher unveraendert
        uebernommen -- fabric_count wird an mehreren Stellen als Divisor
        benutzt (info_panel.py::_calculate_thread_usage,
        pattern.py::size_cm), ein ZeroDivisionError waere die Folge. Jetzt
        faellt ein nicht-positiver Wert auf DEFAULT_FABRIC_COUNT zurueck,
        genau wie width/height bereits validiert werden."""
        from pysticky.core.constants import DEFAULT_FABRIC_COUNT

        pattern = Pattern(name="Test", width=10, height=10)
        filepath = tmp_path / "zero_fabric.pxs"
        save_pattern(pattern, str(filepath))

        data = json.loads(filepath.read_text(encoding="utf-8"))
        data["pattern"]["fabric_count"] = 0
        filepath.write_text(json.dumps(data), encoding="utf-8")

        loaded = load_pattern(str(filepath))

        assert loaded.fabric_count == DEFAULT_FABRIC_COUNT
        assert loaded.size_cm[0] > 0  # darf nicht crashen

    def test_load_falls_back_to_default_fabric_count_when_nan(self, tmp_path):
        """Regression (Runde 27): json.load() akzeptiert die nicht-
        standardkonformen Literale NaN/Infinity -- `nan <= 0` und `inf <= 0`
        sind beide False in Python, die reine Round-26-Pruefung
        ("<=0") liess "fabric_count": NaN also unbemerkt durchrutschen und
        erzeugte stillschweigend NaN-Groessen (size_cm) statt zu crashen
        oder auf den Default zurueckzufallen."""
        from pysticky.core.constants import DEFAULT_FABRIC_COUNT

        pattern = Pattern(name="Test", width=10, height=10)
        filepath = tmp_path / "nan_fabric.pxs"
        save_pattern(pattern, str(filepath))

        text = filepath.read_text(encoding="utf-8")
        text = text.replace(f'"fabric_count": {DEFAULT_FABRIC_COUNT}', '"fabric_count": NaN')
        filepath.write_text(text, encoding="utf-8")

        loaded = load_pattern(str(filepath))

        assert loaded.fabric_count == DEFAULT_FABRIC_COUNT
        assert loaded.size_cm[0] > 0  # darf nicht NaN sein

    def test_load_raises_value_error_for_backstitch_missing_field(self, tmp_path):
        """Regression (Runde 27): _dict_to_backstitch() griff direkt per
        data["color_index"] etc. zu, ohne vorher auf Vollstaendigkeit zu
        pruefen -- ein Rueckstich-Eintrag mit fehlendem Feld liess einen
        rohen KeyError durchschlagen statt des von load_pattern()'s eigenem
        Docstring versprochenen ValueError (gleiche Fehlerklasse wie
        _dict_to_color_entry(), die das bereits korrekt macht)."""
        pattern = Pattern(name="Test", width=10, height=10)
        filepath = tmp_path / "broken_backstitch.pxs"
        save_pattern(pattern, str(filepath))

        data = json.loads(filepath.read_text(encoding="utf-8"))
        # color_index fehlt
        data["pattern"]["backstitches"] = [{"x1": 0, "y1": 0, "x2": 2, "y2": 2}]
        filepath.write_text(json.dumps(data), encoding="utf-8")

        with pytest.raises(ValueError):
            load_pattern(str(filepath))

    def test_save_is_atomic_no_leftover_tmp_file(self, tmp_path):
        """Regression: save_pattern() schrieb frueher direkt in die
        Zieldatei -- ein Crash mitten in json.dump() haette die echte
        Musterdatei truncated/korrupt zurueckgelassen. Jetzt: Temp-Datei +
        os.replace(), kein sichtbares .tmp nach erfolgreichem Speichern."""
        pattern = Pattern(name="Atomic-Test", width=10, height=10)
        filepath = tmp_path / "atomic.pxs"

        save_pattern(pattern, str(filepath))

        assert filepath.exists()
        assert not filepath.with_name(filepath.name + ".tmp").exists()

    def test_save_failure_leaves_original_file_untouched(self, tmp_path, monkeypatch):
        """Schlaegt der Schreibvorgang fehl (z.B. Platte voll mitten im
        json.dump), muss die bereits vorhandene Datei unveraendert bleiben --
        NICHT truncated/korrupt sein. Simuliert per monkeypatch auf
        os.replace(), das erst nach vollstaendigem Schreiben der Temp-Datei
        aufgerufen wird."""
        import os as os_module

        pattern = Pattern(name="Original", width=10, height=10)
        filepath = tmp_path / "existing.pxs"
        save_pattern(pattern, str(filepath))
        original_content = filepath.read_text(encoding="utf-8")

        def boom(*args, **kwargs):
            raise OSError("Platte voll (simuliert)")

        monkeypatch.setattr(os_module, "replace", boom)

        modified_pattern = Pattern(name="Sollte nie ankommen", width=10, height=10)
        with pytest.raises(OSError):
            save_pattern(modified_pattern, str(filepath))

        # Originaldatei unveraendert -- kein Datenverlust
        assert filepath.read_text(encoding="utf-8") == original_content
        # Keine liegen gebliebene Temp-Datei
        assert not filepath.with_name(filepath.name + ".tmp").exists()


class TestPatternMetadata:
    """Tests für Muster-Metadaten."""

    def test_metadata_saved(self, tmp_path):
        """Test: Metadaten werden gespeichert."""
        pattern = Pattern(width=10, height=10)
        pattern.metadata["author"] = "Test User"
        pattern.metadata["description"] = "Test-Beschreibung"

        filepath = tmp_path / "meta.pxs"
        save_pattern(pattern, str(filepath))
        loaded = load_pattern(str(filepath))

        assert loaded.metadata.get("author") == "Test User"
        assert loaded.metadata.get("description") == "Test-Beschreibung"

    def test_fabric_count_saved(self, tmp_path):
        """Test: Stoffzählung wird gespeichert."""
        pattern = Pattern(width=10, height=10)
        pattern.fabric_count = 18

        filepath = tmp_path / "fabric.pxs"
        save_pattern(pattern, str(filepath))
        loaded = load_pattern(str(filepath))

        assert loaded.fabric_count == 18


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
