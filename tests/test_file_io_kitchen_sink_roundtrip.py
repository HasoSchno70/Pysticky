# -*- coding: utf-8 -*-
"""
Kitchen-Sink-Rundtrip-Test fuer core/file_io.py.

Alle bestehenden test_file_io.py-Tests pruefen jeweils EIN Feld/Feature
isoliert (Name, Groesse, Farben, Layer, Rueckstiche, Metadaten, ...). Dieser
Test kombiniert stattdessen MOEGLICHST VIELE persistierte Felder GLEICHZEITIG
in einem einzigen, maximal komplexen Pattern und vergleicht nach einem
save_pattern()/load_pattern()-Zyklus JEDES Feld exakt zwischen Original und
geladenem Pattern. Diese Art Kombination deckt Interaktionsbugs auf, die
kein Einzeltest je sehen wuerde (z.B. ein Feld, das nur unter einer
bestimmten Feld-KOMBINATION falsch serialisiert wird).

Katalogisierte Felder (siehe core/file_io.py, core/pattern.py, core/layer.py,
core/backstitch_manager.py, core/stitch.py):
    Pattern:      name, width, height, fabric_count, metadata (inkl.
                  mode_backups, total_stitch_seconds, last_session_start,
                  stitch_fabric_count), mode, active_layer,
                  source_image_path, source_image_crop, source_palette_name
    ColorEntry:   thread (name, color, manufacturer, catalog_number,
                  blend_components, strand_ratios), symbol, stitch_count,
                  skip_stitching, strands, is_bead, is_diamond, color_id
    Layer:        name, visible, locked, opacity, note, grid,
                  completion_grid, stitch_type_grid
    Backstitch:   x1, y1, x2, y2, color_index

Bewusste Design-Entscheidung zur Diamond/Stitch-Invariante: convert_to_mode()
synchronisiert is_diamond zwar auf ALLE Nicht-Bead-Farben eines Patterns,
sobald es aufgerufen wird -- das ist aber keine staendig erzwungene
Dateninvariante. Wie test_diamond.py::test_add_color_with_is_diamond_flag
bereits zeigt, kann eine einzelne Farbe manuell mit is_diamond=True zu einem
Pattern im mode="stitch" hinzugefuegt werden, ohne dass irgendetwas das
verhindert oder synchronisiert. Dieser Test nutzt genau das: ein echter
convert_to_mode()-Hin-und-Rueck-Aufruf (populiert mode_backups + stitch_
fabric_count echt), gefolgt vom manuellen Hinzufuegen einer zusaetzlichen
is_diamond=True-Farbe DANACH -- so bleiben Diamond- und Stitch-Farben im
selben, gueltigen Pattern gemischt, ohne die convert_to_mode-Restamping-Logik
(die stitch_type_grid fuer ALLE Zellen einer betroffenen Farbe ueberschreibt)
mit den bewusst vielfaeltig gesetzten Stichtypen (HALF/QUARTER/THREE_QUARTER/
FRENCH_KNOT) in Konflikt zu bringen: die Farben mit den klassischen Stich-
typen werden erst NACH den beiden convert_to_mode()-Aufrufen bestueckt.
"""

import numpy as np
import pytest

from pysticky.core import Pattern, Thread, load_pattern, save_pattern, session_timer
from pysticky.core.stitch import StitchType


def _build_kitchen_sink_pattern() -> Pattern:
    """Baut ein Pattern, das moeglichst viele persistierte Felder
    gleichzeitig mit Nicht-Default-Werten befuellt."""
    pattern = Pattern(name="Kitchen Sink Ultimate", width=12, height=10, fabric_count=16)

    # --- Freie Metadaten (ueberleben convert_to_mode unangetastet) ---
    pattern.metadata["author"] = "QA Bot"
    pattern.metadata["description"] = "Kitchen-Sink Testmuster — alle Felder kombiniert"

    # --- Grundfarben VOR den convert_to_mode()-Aufrufen ---
    pattern.color_entries.clear()

    idx_a = pattern.add_color(
        Thread.from_hex("Rot", "#CC2244", manufacturer="DMC", catalog_number="321")
    )
    pattern.color_entries[idx_a].strands = 3

    idx_d = pattern.add_color(
        Thread.from_hex("Stoff-Beige", "#EAD9B8", manufacturer="DMC", catalog_number="ECRU")
    )
    pattern.color_entries[idx_d].skip_stitching = True

    idx_c = pattern.add_color(
        Thread.from_hex(
            "Glasperle Klar", "#F0F0F5", manufacturer="Mill Hill", catalog_number="00161"
        ),
        is_bead=True,
    )

    # --- Echter Modus-Hin-und-Rueck-Wechsel: populiert metadata["mode_backups"]
    # fuer BEIDE Richtungen sowie metadata["stitch_fabric_count"] ---
    assert pattern.convert_to_mode("diamond") is True
    assert pattern.mode == "diamond"
    assert "stitch_fabric_count" in pattern.metadata
    assert pattern.convert_to_mode("stitch") is True
    assert pattern.mode == "stitch"
    # fabric_count muss nach dem Hin-und-Rueck wieder beim Original sein
    assert pattern.fabric_count == 16
    assert "stitch" in pattern.metadata["mode_backups"]
    assert "diamond" in pattern.metadata["mode_backups"]

    # --- Farben, die von den obigen Konvertierungen NICHT betroffen waren ---
    blend_thread = Thread.blend(
        [
            Thread.from_hex("Nachtblau", "#1A2A6C", manufacturer="DMC", catalog_number="939"),
            Thread.from_hex("Bordeaux", "#B21F66", manufacturer="Anchor", catalog_number="1028"),
        ],
        ratios=[1, 2],
        name="Tweed Nachtblau/Bordeaux",
    )
    idx_b = pattern.add_color(blend_thread)
    pattern.color_entries[idx_b].strands = 2

    idx_e = pattern.add_color(
        Thread.from_hex(
            "Dusty Rose DP", "#AB0249", manufacturer="DMC Diamond Painting", catalog_number="150"
        ),
        is_diamond=True,
    )

    # --- Zusaetzliche Layer: gesperrt, unsichtbar, mit Notiz ---
    pattern.layer_stack[0].note = "Hauptebene"
    pattern.layer_stack[0].opacity = 0.8
    pattern.layer_stack.add_layer("Schattierung")  # index 1
    pattern.layer_stack[1].note = "Schattendetails"
    pattern.layer_stack[1].opacity = 0.5
    pattern.layer_stack.add_layer("Gesperrt")  # index 2
    pattern.layer_stack.add_layer("Unsichtbar")  # index 3

    # --- Stiche mit allen StitchType-Werten auf Layer 0 (aktiv) ---
    pattern.layer_stack.active_index = 0
    pattern.set_stitch(0, 0, idx_a)  # FULL (default)
    pattern.set_stitch(1, 0, idx_a, stitch_type=StitchType.HALF_TL_BR.value)
    pattern.set_stitch(2, 0, idx_a, stitch_type=StitchType.HALF_TR_BL.value)
    pattern.set_stitch(3, 0, idx_a, stitch_type=StitchType.QUARTER_TL.value)
    pattern.set_stitch(4, 0, idx_a, stitch_type=StitchType.QUARTER_TR.value)
    pattern.set_stitch(5, 0, idx_a, stitch_type=StitchType.QUARTER_BL.value)
    pattern.set_stitch(6, 0, idx_a, stitch_type=StitchType.QUARTER_BR.value)
    pattern.set_stitch(7, 0, idx_a, stitch_type=StitchType.THREE_QUARTER.value)
    pattern.set_stitch(8, 0, idx_a, stitch_type=StitchType.FRENCH_KNOT.value)
    pattern.set_stitch(9, 0, idx_d)  # skip_stitching-Farbe, FULL
    pattern.set_stitch(10, 0, idx_c)  # Bead -> auto BEAD-Type
    pattern.set_stitch(11, 0, idx_e)  # Diamond -> auto DIAMOND-Type

    # --- Stiche auf Layer 1 (Blend-Farbe + zusaetzliche normale Farbe) ---
    pattern.layer_stack.active_index = 1
    pattern.set_stitch(0, 1, idx_b)
    pattern.set_stitch(1, 1, idx_b)
    pattern.set_stitch(2, 1, idx_a)

    # --- Stiche auf Layer 2, DANN sperren ---
    pattern.layer_stack.active_index = 2
    pattern.set_stitch(0, 2, idx_a)
    pattern.set_stitch(1, 2, idx_d)
    pattern.layer_stack[2].locked = True

    # --- Stiche auf Layer 3, DANN unsichtbar machen ---
    pattern.layer_stack.active_index = 3
    pattern.set_stitch(0, 3, idx_c)
    pattern.set_stitch(1, 3, idx_e)
    pattern.layer_stack[3].visible = False

    # Aktives Layer am Ende auf einen Nicht-Null-Index setzen (Nicht-Default)
    pattern.layer_stack.active_index = 1

    # --- Fortschritt: Completion-Zellen ueber verschiedene Layer verteilt ---
    assert pattern.mark_stitch_completed(0, 0, 0) is True
    assert pattern.mark_stitch_completed(1, 0, 0) is True
    assert pattern.mark_stitch_completed(9, 0, 0) is True
    assert pattern.mark_stitch_completed(0, 1, 1) is True
    assert pattern.mark_stitch_completed(0, 2, 2) is True  # gesperrtes Layer
    assert pattern.mark_stitch_completed(0, 3, 3) is True  # unsichtbares Layer

    # --- Rueckstiche mit unterschiedlichen Farben ---
    pattern.add_backstitch(0, 0, 2, 2, idx_a)
    pattern.add_backstitch(2, 2, 4, 0, idx_b)
    pattern.add_backstitch(6, 0, 8, 2, idx_d)
    pattern.add_backstitch(10, 0, 12, 2, idx_e)

    # --- Quell-Bild-Infos ---
    pattern.source_image_path = "C:/fake/path/import_source.png"
    pattern.source_image_crop = (0.05, 0.1, 0.95, 0.9)
    pattern.source_palette_name = "DMC"

    # --- Sitzungs-Zeitdaten (echte session_timer-API) ---
    session_timer.start_session(pattern, now=1000.0)
    session_timer.stop_session(pattern, now=1500.0)  # total_stitch_seconds = 500
    session_timer.start_session(pattern, now=2000.0)  # aktive Session bleibt offen

    # --- Finaler Modus-Wert: unabhaengiges Feld, kein convert_to_mode()-Aufruf
    # noetig (siehe Modul-Docstring fuer die Begruendung) ---
    pattern.mode = "diamond"

    return pattern


def _assert_thread_equal(original: Thread, loaded: Thread, context: str) -> None:
    assert loaded.name == original.name, context
    assert loaded.color.to_hex() == original.color.to_hex(), context
    assert loaded.manufacturer == original.manufacturer, context
    assert loaded.catalog_number == original.catalog_number, context
    assert loaded.is_blend == original.is_blend, context
    if original.is_blend:
        assert loaded.strand_ratios == original.strand_ratios, context
        assert len(loaded.blend_components) == len(original.blend_components), context
        for i, (orig_c, loaded_c) in enumerate(
            zip(original.blend_components, loaded.blend_components)
        ):
            sub_ctx = f"{context} blend_component[{i}]"
            assert loaded_c.name == orig_c.name, sub_ctx
            assert loaded_c.color.to_hex() == orig_c.color.to_hex(), sub_ctx
            assert loaded_c.manufacturer == orig_c.manufacturer, sub_ctx
            assert loaded_c.catalog_number == orig_c.catalog_number, sub_ctx


def test_kitchen_sink_roundtrip_every_field_matches_exactly(tmp_path):
    """Kombinierter Belastungstest: EIN maximal komplexes Pattern mit fast
    allen persistierten Feldern gleichzeitig auf Nicht-Default-Werten,
    Speichern/Laden-Zyklus, dann Feld-fuer-Feld exakter Vergleich."""
    pattern = _build_kitchen_sink_pattern()

    filepath = tmp_path / "kitchen_sink.pxs"
    save_pattern(pattern, str(filepath))
    loaded = load_pattern(str(filepath))

    # --- Pattern-Grundfelder ---
    assert loaded.name == pattern.name
    assert loaded.width == pattern.width
    assert loaded.height == pattern.height
    assert loaded.fabric_count == pattern.fabric_count
    assert loaded.mode == pattern.mode
    assert loaded.source_image_path == pattern.source_image_path
    assert tuple(loaded.source_image_crop) == tuple(pattern.source_image_crop)
    assert loaded.source_palette_name == pattern.source_palette_name
    assert loaded.layer_stack.active_index == pattern.layer_stack.active_index

    # --- Metadata (inkl. mode_backups, Sitzungs-Zeitdaten, stitch_fabric_count) ---
    assert loaded.metadata == pattern.metadata
    assert loaded.metadata["author"] == "QA Bot"
    assert loaded.metadata["total_stitch_seconds"] == 500
    assert loaded.metadata["last_session_start"] == 2000.0
    assert loaded.metadata["stitch_fabric_count"] == 16
    assert loaded.metadata["mode_backups"]["stitch"] == pattern.metadata["mode_backups"]["stitch"]
    assert loaded.metadata["mode_backups"]["diamond"] == pattern.metadata["mode_backups"]["diamond"]

    # --- Farben ---
    assert len(loaded.color_entries) == len(pattern.color_entries)
    for i, (orig, load) in enumerate(zip(pattern.color_entries, loaded.color_entries)):
        ctx = f"color_entries[{i}] ({orig.thread.name})"
        assert load.symbol == orig.symbol, ctx
        assert load.stitch_count == orig.stitch_count, ctx
        assert load.skip_stitching == orig.skip_stitching, ctx
        assert load.strands == orig.strands, ctx
        assert load.is_bead == orig.is_bead, ctx
        assert load.is_diamond == orig.is_diamond, ctx
        assert load.color_id == orig.color_id, ctx
        _assert_thread_equal(orig.thread, load.thread, ctx)

    # Ausdruecklich gemischte is_diamond-Zustaende im selben Pattern bestaetigen
    assert any(e.is_diamond for e in loaded.color_entries)
    assert any(not e.is_diamond and not e.is_bead for e in loaded.color_entries)
    assert any(e.is_bead for e in loaded.color_entries)
    assert any(e.thread.is_blend for e in loaded.color_entries)
    assert any(e.skip_stitching for e in loaded.color_entries)

    # --- Layer ---
    assert len(loaded.layer_stack) == len(pattern.layer_stack)
    for i, (orig_layer, load_layer) in enumerate(zip(pattern.layer_stack, loaded.layer_stack)):
        ctx = f"layer[{i}] ({orig_layer.name})"
        assert load_layer.name == orig_layer.name, ctx
        assert load_layer.visible == orig_layer.visible, ctx
        assert load_layer.locked == orig_layer.locked, ctx
        assert load_layer.opacity == orig_layer.opacity, ctx
        assert load_layer.note == orig_layer.note, ctx
        assert np.array_equal(load_layer.grid, orig_layer.grid), ctx
        assert np.array_equal(load_layer.completion_grid, orig_layer.completion_grid), ctx
        assert np.array_equal(load_layer.stitch_type_grid, orig_layer.stitch_type_grid), ctx

    # Layer-spezifische Stichproben (gesperrt/unsichtbar behalten ihre Stiche)
    assert loaded.layer_stack[2].locked is True
    assert loaded.layer_stack[2].get_stitch(0, 2) == idx_of(loaded, "Rot")
    assert loaded.layer_stack[3].visible is False
    assert loaded.layer_stack[3].get_stitch(0, 3) is not None

    # Stichtypen auf Layer 0 muessen alle exakt erhalten geblieben sein
    l0 = loaded.layer_stack[0]
    assert l0.get_stitch_type(0, 0) == StitchType.FULL.value
    assert l0.get_stitch_type(1, 0) == StitchType.HALF_TL_BR.value
    assert l0.get_stitch_type(2, 0) == StitchType.HALF_TR_BL.value
    assert l0.get_stitch_type(3, 0) == StitchType.QUARTER_TL.value
    assert l0.get_stitch_type(4, 0) == StitchType.QUARTER_TR.value
    assert l0.get_stitch_type(5, 0) == StitchType.QUARTER_BL.value
    assert l0.get_stitch_type(6, 0) == StitchType.QUARTER_BR.value
    assert l0.get_stitch_type(7, 0) == StitchType.THREE_QUARTER.value
    assert l0.get_stitch_type(8, 0) == StitchType.FRENCH_KNOT.value
    assert l0.get_stitch_type(10, 0) == StitchType.BEAD.value
    assert l0.get_stitch_type(11, 0) == StitchType.DIAMOND.value

    # Completion-Zellen ueber mehrere Layer verteilt
    assert loaded.layer_stack[0].is_completed(0, 0) is True
    assert loaded.layer_stack[0].is_completed(1, 0) is True
    assert loaded.layer_stack[0].is_completed(9, 0) is True
    assert loaded.layer_stack[1].is_completed(0, 1) is True
    assert loaded.layer_stack[2].is_completed(0, 2) is True
    assert loaded.layer_stack[3].is_completed(0, 3) is True

    # --- Rueckstiche ---
    assert len(loaded.backstitches) == len(pattern.backstitches)
    orig_bs = [(bs.x1, bs.y1, bs.x2, bs.y2, bs.color_index) for bs in pattern.backstitches]
    load_bs = [(bs.x1, bs.y1, bs.x2, bs.y2, bs.color_index) for bs in loaded.backstitches]
    assert load_bs == orig_bs


def idx_of(pattern: Pattern, thread_name: str) -> int:
    """Hilfsfunktion: findet den Farbindex per Garn-Name (fuer Stichproben)."""
    for i, entry in enumerate(pattern.color_entries):
        if entry.thread.name == thread_name:
            return i
    raise ValueError(f"Farbe '{thread_name}' nicht gefunden")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
