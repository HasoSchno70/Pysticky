# -*- coding: utf-8 -*-
"""
Regressionstests (Clean-Code-Audit Runde 79): Tweed-Blend-Erzeugung
umging den zentralen Dedup-Pfad `MainWindow.add_color_to_pattern()`.

`_on_blend_threads()` (ui/handlers/edit_handlers.py) rief bisher direkt
`self.current_pattern.add_color(blend)` auf -- anders als JEDER andere
Farb-Hinzufuegen-Pfad im Programm (Eyedropper, Palette-Import, manuelle
Farbwahl), die alle ueber `MainWindow.add_color_to_pattern()` laufen, um
Duplikate zu vermeiden. Ergebnis: wiederholtes Mischen exakt derselben
zwei Garne mit demselben Strang-Verhaeltnis erzeugte bei jedem Klick auf
"Zum Pattern hinzufuegen" einen komplett neuen, redundanten
Paletten-Eintrag statt den bereits vorhandenen identischen Blend
wiederzuverwenden.

Der naive Fix (`_on_blend_threads` einfach auf `add_color_to_pattern()`
umstellen) haette allerdings einen ZWEITEN, eigenstaendigen Bug aufgedeckt:
`Thread.blend()` codiert das Strang-Verhaeltnis NICHT in
`catalog_number` (nur die Katalognummern der Komponenten werden
verkettet, z.B. "310+745" -- unabhaengig davon, ob das Verhaeltnis [1,1]
oder [1,3] war). Der bisherige Dedup-Vergleich in
`add_color_to_pattern()` pruefte nur `manufacturer` + `catalog_number` --
zwei Blends aus DENSELBEN Komponenten-Garnen, aber mit UNTERSCHIEDLICHEM
Verhaeltnis (und damit unterschiedlicher Mischfarbe!), waeren faelschlich
als Duplikat erkannt und der zweite, andersfarbige Blend haette einfach
den Index des ersten zurueckbekommen -- der Nutzer haette also gedacht,
er fuegt einen 1+3-Blend hinzu, bekaeme aber weiterhin den 1+1-Blend im
Muster.

Fix:
1. `_on_blend_threads()` nutzt jetzt `add_color_to_pattern()` statt den
   Pattern direkt zu mutieren.
2. `add_color_to_pattern()` vergleicht bei uebereinstimmender
   Katalognummer zusaetzlich `strand_ratios`, damit nur WIRKLICH
   identische Blends (gleiche Komponenten UND gleiches Verhaeltnis)
   dedupliziert werden.
"""

import pytest

pytest.importorskip("PySide6")


def _make_window(qtbot, empty_pattern):
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    w.current_pattern = empty_pattern
    return w


def test_identical_blend_added_twice_reuses_existing_entry(qtbot, empty_pattern):
    """Derselbe Blend (gleiche Komponenten, gleiches Verhaeltnis) zweimal
    ueber add_color_to_pattern() hinzugefuegt darf nur EINEN Eintrag
    erzeugen."""
    from pysticky.core import Thread

    w = _make_window(qtbot, empty_pattern)
    entries_before = len(empty_pattern.color_entries)

    a = Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310")
    b = Thread.from_hex("Cream", "#FFF5DC", manufacturer="DMC", catalog_number="745")

    blend1 = Thread.blend([a, b], [1, 1])
    blend2 = Thread.blend([a, b], [1, 1])

    idx1 = w.add_color_to_pattern(blend1)
    idx2 = w.add_color_to_pattern(blend2)

    assert idx1 == idx2
    assert len(empty_pattern.color_entries) == entries_before + 1


def test_blend_with_different_ratio_same_components_is_not_collapsed(qtbot, empty_pattern):
    """Zwei Blends aus DENSELBEN Komponenten-Garnen, aber mit
    unterschiedlichem Strang-Verhaeltnis (und damit unterschiedlicher
    Mischfarbe), muessen als ZWEI getrennte Eintraege landen -- die
    gleiche `catalog_number` ("310+745") allein darf sie nicht
    kollabieren."""
    from pysticky.core import Thread

    w = _make_window(qtbot, empty_pattern)
    entries_before = len(empty_pattern.color_entries)

    a = Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310")
    b = Thread.from_hex("Cream", "#FFF5DC", manufacturer="DMC", catalog_number="745")

    blend_1_1 = Thread.blend([a, b], [1, 1])
    blend_1_3 = Thread.blend([a, b], [1, 3])
    assert blend_1_1.catalog_number == blend_1_3.catalog_number  # Sanity: gleiche Katalog-ID
    assert blend_1_1.color != blend_1_3.color  # aber unterschiedliche Mischfarbe

    idx1 = w.add_color_to_pattern(blend_1_1)
    idx2 = w.add_color_to_pattern(blend_1_3)

    assert idx1 != idx2
    assert len(empty_pattern.color_entries) == entries_before + 2
    assert empty_pattern.color_entries[idx1].thread.color == blend_1_1.color
    assert empty_pattern.color_entries[idx2].thread.color == blend_1_3.color


def test_on_blend_threads_handler_reuses_existing_identical_blend(qtbot, empty_pattern):
    """End-to-End: der tatsaechliche Menu-Handler `_on_blend_threads()`
    darf beim erneuten Mischen derselben zwei Garne mit demselben
    Verhaeltnis keinen zweiten, redundanten Paletten-Eintrag anlegen."""
    from pysticky.core import Thread

    w = _make_window(qtbot, empty_pattern)
    entries_before = len(empty_pattern.color_entries)

    a = Thread.from_hex("Black", "#000000", manufacturer="DMC", catalog_number="310")
    b = Thread.from_hex("Cream", "#FFF5DC", manufacturer="DMC", catalog_number="745")

    class _FakeDialog:
        def __init__(self, *args, **kwargs):
            self.result_thread = Thread.blend([a, b], [1, 1])

        def exec(self):
            return True

    import pysticky.ui.dialogs as dialogs_module

    original = dialogs_module.BlendThreadsDialog
    dialogs_module.BlendThreadsDialog = _FakeDialog
    try:
        w._on_blend_threads()
        w._on_blend_threads()
    finally:
        dialogs_module.BlendThreadsDialog = original

    assert len(empty_pattern.color_entries) == entries_before + 1
