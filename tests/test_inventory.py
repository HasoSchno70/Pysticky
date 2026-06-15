# -*- coding: utf-8 -*-
"""Tests fuer die Garn-Vorratsliste (core/inventory.py)."""

import json

from pysticky.core.inventory import Inventory, _key, compute_shopping_list


def test_key_normalizes_none_and_empty():
    assert _key(None, None) == "unknown::unknown"
    assert _key("", "") == "unknown::unknown"
    assert _key("DMC", "310") == "DMC::310"
    assert _key("  DMC ", " 310 ") == "DMC::310"


def test_set_and_get_roundtrip(tmp_path):
    inv = Inventory(tmp_path / "inv.json")
    inv.set("DMC", "310", 3)
    assert inv.get("DMC", "310") == 3
    assert inv.get("DMC", "666") == 0


def test_set_zero_removes_entry(tmp_path):
    inv = Inventory(tmp_path / "inv.json")
    inv.set("DMC", "310", 3)
    inv.set("DMC", "310", 0)
    assert inv.get("DMC", "310") == 0
    assert len(inv) == 0


def test_save_and_reload(tmp_path):
    path = tmp_path / "inv.json"
    inv1 = Inventory(path)
    inv1.set("DMC", "310", 5)
    inv1.set("Anchor", "403", 2)
    inv1.save()

    assert path.exists()
    inv2 = Inventory(path)
    assert inv2.get("DMC", "310") == 5
    assert inv2.get("Anchor", "403") == 2
    assert len(inv2) == 2


def test_load_corrupt_file_does_not_crash(tmp_path):
    path = tmp_path / "inv.json"
    path.write_text("{ not valid json", encoding="utf-8")
    inv = Inventory(path)
    assert len(inv) == 0


def test_load_flat_legacy_format(tmp_path):
    """Backward-compat: alte flache Schreibweise sollte noch lesbar sein."""
    path = tmp_path / "inv.json"
    path.write_text(json.dumps({"DMC::310": 4}), encoding="utf-8")
    inv = Inventory(path)
    assert inv.get("DMC", "310") == 4


def test_shopping_list_to_buy(tmp_path, pattern_with_stitches):
    inv = Inventory(tmp_path / "inv.json")
    p = pattern_with_stitches
    # Manueller stitches-per-skein, fabric_count irrelevant
    spk = {p.fabric_count: 30}  # alle 30 Stiche = 1 Strang

    items = compute_shopping_list(p, inv, spk)
    assert items, "Pattern should have stitches"
    for it in items:
        assert it["on_hand"] == 0
        assert it["to_buy"] == it["needed_skeins"]


def test_shopping_list_reduces_with_on_hand(tmp_path, pattern_with_stitches):
    inv = Inventory(tmp_path / "inv.json")
    p = pattern_with_stitches
    spk = {p.fabric_count: 1000}

    # Gib uns von jeder Farbe schon 10 Straenge
    for entry in p.color_entries:
        if entry.stitch_count > 0:
            inv.set(entry.thread.manufacturer, entry.thread.catalog_number, 10)

    items = compute_shopping_list(p, inv, spk)
    for it in items:
        assert it["on_hand"] == 10
        assert it["to_buy"] == max(0, it["needed_skeins"] - 10)


def test_shopping_list_skips_skip_stitching(tmp_path, pattern_with_stitches):
    """Uebersprungene Farben (Stofffarbe) gehoeren nicht in die Einkaufsliste."""
    inv = Inventory(tmp_path / "inv.json")
    p = pattern_with_stitches
    # erste Farbe als skip markieren
    if p.color_entries:
        p.color_entries[0].skip_stitching = True
    items = compute_shopping_list(p, inv, {p.fabric_count: 100})
    threads = [it["thread"] for it in items]
    assert p.color_entries[0].thread not in threads
