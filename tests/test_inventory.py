# -*- coding: utf-8 -*-
"""Tests fuer die Garn-Vorratsliste (core/inventory.py)."""

import json

from pysticky.core.inventory import (
    Inventory,
    _key,
    compute_shopping_list,
    compute_shopping_list_multi,
    split_key,
)


def test_key_normalizes_none_and_empty():
    assert _key(None, None) == "unknown::unknown"
    assert _key("", "") == "unknown::unknown"
    assert _key("DMC", "310") == "DMC::310"
    assert _key("  DMC ", " 310 ") == "DMC::310"


# === Namens-Fallback fuer Farben ohne Hersteller/Katalognummer ===
#
# Zurueckgestellter Fund aus Runde 22, hier nachgeholt: `_key()` mappte
# JEDE Farbe ohne Hersteller UND Katalognummer (z.B. Custom-Farben aus
# einem Bildimport ohne Palette-Metadaten) auf den identischen Schluessel
# "unknown::unknown" -- ihr Lagerbestand wurde dadurch fuer ALLE derartigen
# Farben gemeinsam gefuehrt. `_key()`/`get()`/`set()` bekommen jetzt einen
# optionalen `name`-Fallback, der nur in genau diesem Sonderfall greift.


def test_key_uses_name_fallback_when_manufacturer_and_catalog_both_empty():
    assert _key(None, None, "Custom Rot") == "unknown::unknown::Custom Rot"
    assert _key("", "", "Custom Blau") == "unknown::unknown::Custom Blau"
    # Zwei unterschiedliche Namen ergeben unterschiedliche Schluessel.
    assert _key(None, None, "Custom Rot") != _key(None, None, "Custom Blau")


def test_key_without_name_falls_back_to_generic_unknown():
    """Rueckwaerts-kompatibel: fehlt der Name auch, bleibt der alte,
    generische Schluessel erhalten (kein Bruch fuer Aufrufer, die (noch)
    keinen Namen mitgeben, und fuer bereits gespeicherte alte Eintraege)."""
    assert _key(None, None, None) == "unknown::unknown"
    assert _key("", "", "") == "unknown::unknown"
    assert _key("", "", "   ") == "unknown::unknown"


def test_key_ignores_name_when_manufacturer_or_catalog_present():
    """Der Name wird NUR als Fallback genutzt, wenn Hersteller UND
    Katalognummer beide fehlen -- fuer bereits identifizierbare Farben
    aendert sich das Schluessel-Format nicht."""
    assert _key("DMC", "", "Irgendein Name") == "DMC::unknown"
    assert _key("", "310", "Irgendein Name") == "unknown::310"
    assert _key("DMC", "310", "Irgendein Name") == "DMC::310"


def test_split_key_roundtrip():
    assert split_key("DMC::310") == ("DMC", "310", "")
    assert split_key("unknown::unknown") == ("unknown", "unknown", "")
    assert split_key("unknown::unknown::Custom Rot") == ("unknown", "unknown", "Custom Rot")
    # Name selbst enthaelt "::" -- darf nicht am falschen Trenner geschnitten
    # werden (maxsplit=2 rejoint den Rest korrekt in das dritte Segment).
    assert split_key("unknown::unknown::Custom::Rot") == ("unknown", "unknown", "Custom::Rot")


def test_get_set_distinguish_custom_colors_by_name(tmp_path):
    """Der eigentliche Bugfix: zwei Custom-Farben ohne Hersteller/
    Katalognummer, aber mit unterschiedlichem Namen, teilen sich NICHT mehr
    denselben Lagerbestand."""
    inv = Inventory(tmp_path / "inv.json")
    inv.set(None, None, 3, "Custom Rot")
    inv.set(None, None, 7, "Custom Blau")

    assert inv.get(None, None, "Custom Rot") == 3
    assert inv.get(None, None, "Custom Blau") == 7
    # Eine dritte, noch nie gesehene "unbekannte" Farbe bleibt bei 0 --
    # vorher haette sie faelschlich einen der beiden obigen Werte geerbt.
    assert inv.get(None, None, "Custom Gruen") == 0
    assert len(inv) == 2


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


def test_load_file_with_invalid_encoding_does_not_crash(tmp_path):
    """Datei mit ungueltiger UTF-8-Kodierung (z.B. abgebrochener Schreib-
    vorgang) darf das Laden nicht mit einem rohen UnicodeDecodeError crashen
    lassen -- soll wie jede andere kaputte Datei auf eine leere Vorratsliste
    zurueckfallen."""
    path = tmp_path / "inv.json"
    # 0xFF ist in UTF-8 niemals ein gueltiges Start-Byte.
    path.write_bytes(b'{"stock": {"DMC::310": 3}}\xff\xfe')
    inv = Inventory(path)
    assert len(inv) == 0


def test_load_flat_legacy_format(tmp_path):
    """Backward-compat: alte flache Schreibweise sollte noch lesbar sein."""
    path = tmp_path / "inv.json"
    path.write_text(json.dumps({"DMC::310": 4}), encoding="utf-8")
    inv = Inventory(path)
    assert inv.get("DMC", "310") == 4


def test_load_legacy_unknown_unknown_key_still_works(tmp_path):
    """Rueckwaerts-Kompatibilitaet: eine bereits gespeicherte Datei mit dem
    alten, generischen "unknown::unknown"-Schluessel (vor dem Namens-
    Fallback-Fix) muss weiterhin ohne Crash ladbar sein und als genereller
    Fallback-Bestand erhalten bleiben."""
    path = tmp_path / "inv.json"
    path.write_text(
        json.dumps({"version": 1, "stock": {"unknown::unknown": 6, "DMC::310": 2}}),
        encoding="utf-8",
    )
    inv = Inventory(path)
    assert len(inv) == 2
    # Ohne Namen fragt get() weiterhin exakt diesen alten Schluessel ab.
    assert inv.get(None, None) == 6
    assert inv.get("DMC", "310") == 2
    # Eine Custom-Farbe MIT Namen greift nicht auf den alten generischen
    # Eintrag zu (neuer, eigener Schluessel statt Kollision).
    assert inv.get(None, None, "Custom Rot") == 0


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


def test_shopping_list_uses_waste_percent_formula_matching_thread_tab(tmp_path):
    """Regression (offener Punkt, per Nutzerentscheidung 'Garnverbrauch-
    Konvention'): compute_shopping_list() nutzte bisher `ceil(count/spk)`
    plus einen pauschalen +1 nur oberhalb 1000 Stichen -- der Garnverbrauch-
    Tab (thread_tab.py) rechnet stattdessen mit einem prozentualen
    Verschnitt-Zuschlag (`ceil(exact_skeins * (1 + waste_percent/100))`,
    Standard 20%). Beide Tabs zeigten fuer dasselbe Muster unterschiedliche
    "benoetigte Straenge"-Zahlen. Jetzt nutzt compute_shopping_list()
    dieselbe Formel wie thread_tab.py."""
    import math

    from pysticky.core import Pattern, Thread

    inv = Inventory(tmp_path / "inv.json")
    pattern = Pattern(name="Test", width=100, height=100, fabric_count=14)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.set_stitch(0, 0, 0)
    pattern.color_entries[0].stitch_count = 1234

    spk = {14: 500}
    items = compute_shopping_list(pattern, inv, spk, waste_percent=20.0)

    exact_skeins = 1234 / 500
    expected = math.ceil(exact_skeins * 1.2)
    assert items[0]["needed_skeins"] == expected
    # Die alte Formel haette ceil(1234/500) + 1 = 3+1 = 4 ergeben --
    # muss sich von der neuen (5) unterscheiden, sonst pruefte dieser Test
    # nichts Unterscheidbares.
    old_formula_result = math.ceil(1234 / 500) + 1
    assert expected != old_formula_result


def test_compute_shopping_list_multi_uses_waste_percent(tmp_path):
    from pysticky.core import Pattern, Thread

    inv = Inventory(tmp_path / "inv.json")
    pattern = Pattern(name="Test", width=100, height=100, fabric_count=14)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.set_stitch(0, 0, 0)
    pattern.color_entries[0].stitch_count = 1234

    spk = {14: 500}
    items = compute_shopping_list_multi([pattern], inv, spk, waste_percent=20.0)

    import math

    exact_skeins = 1234 / 500
    expected = math.ceil(exact_skeins * 1.2)
    assert items[0]["needed_skeins"] == expected


def _second_pattern_same_thread(stitch_count: int):
    """Zweites, unabhaengiges Pattern mit derselben DMC-310-Farbe wie
    `pattern_with_colors`, damit Multi-Pattern-Aggregation testbar ist."""
    from pysticky.core import Pattern, Thread

    p = Pattern(name="Zweites Muster", width=10, height=10)
    p.color_entries.clear()
    thread = Thread.from_hex("Schwarz", "#000000", manufacturer="DMC", catalog_number="310")
    p.add_color(thread)
    for i in range(stitch_count):
        p.set_stitch(i % 10, i // 10, 0)
    return p


def test_shopping_list_multi_sums_needed_skeins_across_patterns(tmp_path, pattern_with_colors):
    """Bedarf wird PRO Pattern gerundet und dann summiert (nicht die Stichzahlen)."""
    inv = Inventory(tmp_path / "inv.json")
    p1 = pattern_with_colors
    for i in range(10):
        p1.set_stitch(i, 0, 0)  # 10 Stiche, DMC 310
    p2 = _second_pattern_same_thread(20)  # 20 Stiche, DMC 310

    spk = {p1.fabric_count: 100, p2.fabric_count: 100}  # je ceil(n/100) = 1
    items = compute_shopping_list_multi([p1, p2], inv, spk)

    black = next(it for it in items if it["thread"].catalog_number == "310")
    assert black["needed_skeins"] == 2
    assert black["on_hand"] == 0
    assert black["to_buy"] == 2


def test_shopping_list_multi_deducts_stock_only_once(tmp_path, pattern_with_colors):
    """Der Vorrat darf nur EINMAL insgesamt abgezogen werden, nicht pro Projekt."""
    inv = Inventory(tmp_path / "inv.json")
    inv.set("DMC", "310", 1)
    p1 = pattern_with_colors
    for i in range(10):
        p1.set_stitch(i, 0, 0)
    p2 = _second_pattern_same_thread(20)

    spk = {p1.fabric_count: 100, p2.fabric_count: 100}
    items = compute_shopping_list_multi([p1, p2], inv, spk)

    black = next(it for it in items if it["thread"].catalog_number == "310")
    assert black["needed_skeins"] == 2
    assert black["on_hand"] == 1
    assert black["to_buy"] == 1


def test_shopping_list_multi_skips_skip_stitching(tmp_path, pattern_with_stitches):
    inv = Inventory(tmp_path / "inv.json")
    p = pattern_with_stitches
    p.color_entries[0].skip_stitching = True
    items = compute_shopping_list_multi([p], inv, {p.fabric_count: 100})
    threads = [it["thread"] for it in items]
    assert p.color_entries[0].thread not in threads


def test_shopping_list_multi_empty_pattern_list(tmp_path):
    inv = Inventory(tmp_path / "inv.json")
    assert compute_shopping_list_multi([], inv, {}) == []


# === Diamond-Painting-Bewusstsein (Runde 22/25-Nachfolge) ===
#
# DP-Muster kennen keine Strang-pro-Stoffzaehlung-Umrechnung -- ein Drill
# wird stueckweise verbraucht. compute_shopping_list()/_multi() muessen
# fuer solche Muster die absolute (mit Sicherheitszuschlag versehene)
# Drill-Anzahl liefern statt durch stitches_per_skein zu teilen, und die
# Eintraege als is_diamond=True markieren.


def test_shopping_list_diamond_mode_ignores_stitches_per_skein(tmp_path):
    import math

    from pysticky.core import Pattern, Thread

    inv = Inventory(tmp_path / "inv.json")
    pattern = Pattern(name="DP-Test", width=10, height=10, mode="diamond")
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"), is_diamond=True)
    pattern.set_stitch(0, 0, 0)
    pattern.color_entries[0].stitch_count = 1234

    # Absichtlich winziger spk-Wert -- wuerde bei Kreuzstich-Rechnung die
    # Anzahl massiv in die Hoehe treiben. Fuer DP muss das komplett ignoriert
    # werden: needed_skeins == ceil(count * waste_factor), NICHT
    # ceil((count / spk) * waste_factor).
    spk = {14: 5}
    items = compute_shopping_list(pattern, inv, spk, waste_percent=20.0)

    assert len(items) == 1
    expected = math.ceil(1234 * 1.2)
    assert items[0]["needed_skeins"] == expected
    assert items[0]["is_diamond"] is True


def test_shopping_list_stitch_mode_sets_is_diamond_false(tmp_path, pattern_with_stitches):
    inv = Inventory(tmp_path / "inv.json")
    items = compute_shopping_list(pattern_with_stitches, inv, {14: 100})
    assert items
    assert all(it["is_diamond"] is False for it in items)


def test_shopping_list_multi_per_pattern_mode(tmp_path):
    """Ein Kreuzstich- und ein DP-Projekt zusammen registriert: jedes
    Pattern behaelt seine eigene Rechnung (Strang-Umrechnung vs. absolute
    Drill-Anzahl), auch wenn beide in derselben Einkaufsliste landen."""
    import math

    from pysticky.core import Pattern, Thread

    inv = Inventory(tmp_path / "inv.json")

    stitch_pattern = Pattern(name="Kreuzstich", width=10, height=10, fabric_count=14)
    stitch_pattern.color_entries.clear()
    stitch_pattern.add_color(Thread.from_hex("Rot", "#FF0000", catalog_number="321"))
    stitch_pattern.set_stitch(0, 0, 0)
    stitch_pattern.color_entries[0].stitch_count = 500

    dp_pattern = Pattern(name="DP", width=10, height=10, mode="diamond")
    dp_pattern.color_entries.clear()
    dp_pattern.add_color(
        Thread.from_hex("Blau", "#0000FF", catalog_number="DB123"), is_diamond=True
    )
    dp_pattern.set_stitch(0, 0, 0)
    dp_pattern.color_entries[0].stitch_count = 300

    spk = {14: 500}
    items = compute_shopping_list_multi([stitch_pattern, dp_pattern], inv, spk, waste_percent=20.0)

    stitch_item = next(it for it in items if it["thread"].catalog_number == "321")
    dp_item = next(it for it in items if it["thread"].catalog_number == "DB123")

    assert stitch_item["is_diamond"] is False
    assert stitch_item["needed_skeins"] == math.ceil((500 / 500) * 1.2)

    assert dp_item["is_diamond"] is True
    # Keine Division durch spk -- absolute Drill-Anzahl mit Zuschlag.
    assert dp_item["needed_skeins"] == math.ceil(300 * 1.2)


# === Custom-Farben ohne Hersteller/Katalognummer in der Einkaufslisten-Rechnung ===
#
# compute_shopping_list()/_multi() reichen den Farbnamen jetzt an
# Inventory.get() durch -- zwei Custom-Farben ohne Palette-Metadaten
# duerfen sich nicht mehr denselben Bestand teilen, nur weil beide
# manufacturer/catalog_number leer sind.


def test_shopping_list_distinguishes_unknown_colors_by_name(tmp_path):
    from pysticky.core import Pattern, Thread

    inv = Inventory(tmp_path / "inv.json")
    # Vorrat fuer eine Custom-Farbe eintragen -- die andere bleibt bei 0.
    inv.set(None, None, 5, "Custom Rot")

    pattern = Pattern(name="Test", width=10, height=10)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Custom Rot", "#FF0000"))
    pattern.add_color(Thread.from_hex("Custom Blau", "#0000FF"))
    pattern.set_stitch(0, 0, 0)
    pattern.set_stitch(1, 0, 1)
    pattern.color_entries[0].stitch_count = 100
    pattern.color_entries[1].stitch_count = 100

    items = compute_shopping_list(pattern, inv, {pattern.fabric_count: 1000})
    red = next(it for it in items if it["thread"].name == "Custom Rot")
    blue = next(it for it in items if it["thread"].name == "Custom Blau")

    assert red["on_hand"] == 5
    # Ohne den Namens-Fallback haette "Custom Blau" faelschlich denselben
    # Bestand (5) wie "Custom Rot" geerbt (beide "unknown::unknown").
    assert blue["on_hand"] == 0


def test_shopping_list_multi_distinguishes_unknown_colors_by_name(tmp_path):
    from pysticky.core import Pattern, Thread

    inv = Inventory(tmp_path / "inv.json")
    inv.set(None, None, 8, "Custom Gelb")

    pattern = Pattern(name="Test", width=10, height=10)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Custom Gelb", "#FFFF00"))
    pattern.add_color(Thread.from_hex("Custom Lila", "#800080"))
    pattern.set_stitch(0, 0, 0)
    pattern.set_stitch(1, 0, 1)
    pattern.color_entries[0].stitch_count = 100
    pattern.color_entries[1].stitch_count = 100

    items = compute_shopping_list_multi([pattern], inv, {pattern.fabric_count: 1000})
    yellow = next(it for it in items if it["thread"].name == "Custom Gelb")
    purple = next(it for it in items if it["thread"].name == "Custom Lila")

    assert yellow["on_hand"] == 8
    assert purple["on_hand"] == 0


# === Tweed-Blends in der Einkaufsliste (Runde 58) ===
#
# Ein Tweed-Blend-Thread (Thread.blend()) traegt manufacturer="DMC" (bei
# homogenem Blend) bzw. "Blend" und einen zusammengesetzten
# catalog_number wie "310+745" -- ein rein synthetischer Schluessel, unter
# dem niemals echter Vorrat abgelegt ist. Ohne Aufloesung auf die echten
# Komponenten-Garne erschien fuer jeden Blend ein Phantom-Eintrag mit
# on_hand=0 (der Nutzer wurde aufgefordert, ein nicht kaufbares "Garn
# 310+745" zu besorgen), waehrend der tatsaechlich vorhandene Vorrat der
# beiden echten Garne (DMC 310, DMC 745) komplett ignoriert wurde und
# diese auch nicht als eigene Zeilen in der Liste auftauchten.


def _blend_pattern(stitch_count: int):
    from pysticky.core import Pattern, Thread

    a = Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310")
    b = Thread.from_hex("Cream", "#FFF0D0", manufacturer="DMC", catalog_number="745")
    blend = Thread.blend([a, b], [1, 1])

    pattern = Pattern(name="Blend-Test", width=10, height=10, fabric_count=14)
    pattern.color_entries.clear()
    idx = pattern.add_color(blend)
    pattern.set_stitch(0, 0, idx)
    pattern.color_entries[0].stitch_count = stitch_count
    return pattern


def test_shopping_list_splits_blend_into_real_components(tmp_path):
    """compute_shopping_list() darf fuer einen Tweed-Blend keinen
    synthetischen 'DMC 310+745'-Phantomeintrag erzeugen, sondern muss
    Bedarf und Vorrat je Komponente einzeln (DMC 310, DMC 745) fuehren."""
    inv = Inventory(tmp_path / "inv.json")
    inv.set("DMC", "310", 5)
    inv.set("DMC", "745", 5)

    pattern = _blend_pattern(500)
    items = compute_shopping_list(pattern, inv, {14: 500}, waste_percent=20.0)

    catalog_numbers = {it["thread"].catalog_number for it in items}
    assert catalog_numbers == {"310", "745"}, (
        "Erwartet je einen Eintrag pro echter Komponente, kein kombinierter "
        f"Blend-Schluessel; erhalten: {catalog_numbers}"
    )

    entry_310 = next(it for it in items if it["thread"].catalog_number == "310")
    entry_745 = next(it for it in items if it["thread"].catalog_number == "745")
    # Beide Faeden laufen gemeinsam durch jede Nadel -- jede Komponente
    # braucht die volle Stichzahl an Straengen, nicht die Haelfte.
    assert entry_310["needed_skeins"] == entry_745["needed_skeins"] == 2
    assert entry_310["on_hand"] == 5
    assert entry_745["on_hand"] == 5
    assert entry_310["to_buy"] == 0
    assert entry_745["to_buy"] == 0


def test_shopping_list_blend_reports_missing_component_stock(tmp_path):
    """Ist nur eine der beiden Blend-Komponenten auf Lager, muss die
    Einkaufsliste genau die fehlende Komponente als 'zu kaufen' ausweisen."""
    inv = Inventory(tmp_path / "inv.json")
    inv.set("DMC", "310", 10)
    # DMC 745 bewusst NICHT im Vorrat

    pattern = _blend_pattern(500)
    items = compute_shopping_list(pattern, inv, {14: 500}, waste_percent=20.0)

    entry_310 = next(it for it in items if it["thread"].catalog_number == "310")
    entry_745 = next(it for it in items if it["thread"].catalog_number == "745")
    assert entry_310["to_buy"] == 0
    assert entry_745["on_hand"] == 0
    assert entry_745["to_buy"] == entry_745["needed_skeins"] == 2


def test_shopping_list_multi_splits_blend_into_real_components(tmp_path):
    inv = Inventory(tmp_path / "inv.json")
    inv.set("DMC", "310", 5)

    pattern = _blend_pattern(500)
    items = compute_shopping_list_multi([pattern], inv, {14: 500}, waste_percent=20.0)

    catalog_numbers = {it["thread"].catalog_number for it in items}
    assert catalog_numbers == {"310", "745"}

    entry_310 = next(it for it in items if it["thread"].catalog_number == "310")
    entry_745 = next(it for it in items if it["thread"].catalog_number == "745")
    assert entry_310["on_hand"] == 5
    assert entry_745["on_hand"] == 0
