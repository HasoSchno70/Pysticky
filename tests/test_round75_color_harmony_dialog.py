# -*- coding: utf-8 -*-
"""Regressionstests (Runde 75) fuer den Farb-Harmonien-Dialog.

1. Der Dialog hielt die Auswahl in einer separaten Liste
   (`_selected_threads`), die per `in`/`remove` nach Farbwert-Gleichheit
   mutiert wurde. Wenn zwei Harmonie-Vorschläge (z.B. Triade +120°/-120°)
   auf dasselbe naechstgelegene Garn der Palette matchten (realistisch bei
   kleinen/Bead-Paletten oder naeherungsweise neutralen Ausgangsfarben),
   entfernte ein Klick auf den zweiten Swatch das gemeinsame Garn wieder aus
   der Liste -- obwohl der Swatch selbst (dessen eigener `_selected`-Haken
   unabhaengig getoggelt wird) weiterhin als ausgewaehlt angezeigt wurde.
   Der Hinzufuegen-Button zeigte dadurch einen falschen Zaehler und liess
   ausgewaehlte Garne stumm unter den Tisch fallen.

2. Der "N Farben verfügbar"-Infotext unter der Paletten-Auswahl wurde als
   rohes f-String ohne t()-Wrapper gebaut und blieb im Englisch-Modus
   dauerhaft deutsch.
"""

import pytest
from PySide6.QtCore import Qt

from pysticky.core import Pattern, Thread
from pysticky.core.i18n import set_language
from pysticky.core.palette import ThreadPalette
from pysticky.ui.dialogs.color_harmony_dialog import ColorHarmonyDialog

pytestmark = pytest.mark.usefixtures("qtbot")


def _pattern_with_one_color() -> Pattern:
    pattern = Pattern(name="Test", width=5, height=5, mode="stitch")
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.set_stitch(0, 0, 0)
    return pattern


def test_two_swatches_matching_same_thread_stay_in_sync_when_both_selected(qtbot):
    """Triade hat 2 Ziel-Farben (+120/-120) -- mit einer Ein-Farben-Palette
    matchen garantiert beide Swatches auf dasselbe Garn. Klickt man beide an,
    muessen am Ende beide visuell ausgewaehlt sein UND das Garn muss in der
    tatsaechlichen Auswahl (fuer den Hinzufuegen-Button/das Signal) enthalten
    sein -- nicht durch das zweite Toggle (das froeher blind nach
    Farbwert-Gleichheit in einer separaten Liste entfernte statt hinzufuegte)
    wieder herausgefallen sein."""
    pattern = _pattern_with_one_color()
    dialog = ColorHarmonyDialog(pattern, 0, parent=None)
    qtbot.addWidget(dialog)

    only_thread = Thread.from_hex("Blau", "#0000FF", manufacturer="Test", catalog_number="1")
    tiny_palette = ThreadPalette(name="Test", manufacturer="Test", threads=[only_thread])
    dialog._current_palette = tiny_palette

    # Triade = 2 Offsets (+120/-120) -> beide finden zwangslaeufig dasselbe
    # (einzige) Garn der Palette.
    triadic_index = dialog._harmony_combo.findData("Triade")
    assert triadic_index >= 0
    dialog._harmony_combo.setCurrentIndex(triadic_index)

    assert len(dialog._harmony_swatches) == 2
    assert all(s.thread is only_thread for s in dialog._harmony_swatches)

    # Beide Karten anklicken (wie ein Nutzer es taete).
    for swatch in dialog._harmony_swatches:
        qtbot.mouseClick(swatch, Qt.MouseButton.LeftButton)

    # Beide zeigen den Auswahl-Haken.
    assert all(s.selected for s in dialog._harmony_swatches)

    # ... und das gemeinsame Garn muss auch tatsaechlich in der Auswahl sein,
    # die beim Klick auf "Hinzufuegen" emittiert wird.
    assert only_thread in dialog.selected_threads
    assert dialog._add_btn.isEnabled()


@pytest.fixture
def english_language():
    set_language("en")
    try:
        yield
    finally:
        set_language("de")


def test_palette_info_label_translated(qtbot, english_language):
    """Der '{count} Farben verfügbar'-Text muss im Englisch-Modus englisch
    sein -- vorher war er ein rohes f-String ohne t()-Wrapper."""
    pattern = _pattern_with_one_color()
    dialog = ColorHarmonyDialog(pattern, 0, parent=None)
    qtbot.addWidget(dialog)

    dialog._on_palette_changed(dialog._palette_combo.currentText())

    assert "verfügbar" not in dialog._info_label.text()
    assert "available" in dialog._info_label.text()
