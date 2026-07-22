# -*- coding: utf-8 -*-
"""Regressionstests (Runde 25): mehrere Dialoge bauten dynamisch erzeugte
Texte (Combo-Box-Eintraege, Buttons, Meldungen) aus rohen deutschen Strings
statt sie durch t() zu schicken -- im Englisch-Modus blieben diese Texte
dauerhaft deutsch. Zusaetzlich: color_harmony_dialog.py und
pattern_library_dialog.py lasen `currentText()` der jeweiligen Combo-Box
direkt als Lookup-Key -- nach dem Uebersetzen des sichtbaren Texts haette das
den internen Lookup gebrochen (itemData-Fix, analog zum Round-23-Muster in
mw_menus_mixin.py)."""

import pytest

from pysticky.core import Pattern, Thread
from pysticky.core.i18n import set_language

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture
def english_language():
    set_language("en")
    try:
        yield
    finally:
        set_language("de")


def _pattern_with_two_colors(mode: str = "stitch") -> Pattern:
    pattern = Pattern(name="Test", width=10, height=10, mode=mode)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.add_color(Thread.from_hex("Blau", "#0000FF"))
    pattern.set_stitch(0, 0, 0)
    pattern.set_stitch(1, 1, 1)
    return pattern


def test_color_harmony_combo_translated_and_lookup_still_works(qtbot, english_language):
    from pysticky.ui.dialogs.color_harmony_dialog import ColorHarmonyDialog

    pattern = _pattern_with_two_colors()
    dialog = ColorHarmonyDialog(pattern, 0, parent=None)
    qtbot.addWidget(dialog)

    # Sichtbarer Text ist uebersetzt ...
    assert dialog._harmony_combo.itemText(0) == "Complementary"
    # ... aber der interne Lookup (ueber itemData) funktioniert trotzdem noch
    # und liefert eine echte Beschreibung/Angebote statt leer zu bleiben.
    assert dialog._harmony_combo.currentData() == "Komplementär"
    assert "opposite" in dialog._harmony_desc.text().lower()


def test_color_harmony_add_button_translated(qtbot, english_language):
    from pysticky.ui.dialogs.color_harmony_dialog import ColorHarmonyDialog

    pattern = _pattern_with_two_colors()
    dialog = ColorHarmonyDialog(pattern, 0, parent=None)
    qtbot.addWidget(dialog)

    assert dialog._add_btn.text() == "Add (0)"
    assert "Hinzufügen" not in dialog._add_btn.text()


def test_swap_colors_info_label_translated(qtbot, english_language):
    from pysticky.ui.dialogs.swap_colors_dialog import SwapColorsDialog

    pattern = _pattern_with_two_colors()
    dialog = SwapColorsDialog(pattern, current_color_index=0, parent=None)
    qtbot.addWidget(dialog)

    assert "will be swapped" in dialog.info_label.text()
    assert "getauscht" not in dialog.info_label.text()


def test_swap_colors_uses_drills_unit_for_diamond_mode(qtbot, english_language):
    from pysticky.ui.dialogs.swap_colors_dialog import SwapColorsDialog

    pattern = _pattern_with_two_colors(mode="diamond")
    dialog = SwapColorsDialog(pattern, current_color_index=0, parent=None)
    qtbot.addWidget(dialog)

    assert "Drills" in dialog.info_label.text()
    assert "Stitches" not in dialog.info_label.text()


def test_replace_color_dialog_uses_drills_for_diamond_mode(qtbot, english_language):
    from pysticky.ui.dialogs.replace_color_dialog import ReplaceColorDialog

    pattern = _pattern_with_two_colors(mode="diamond")
    dialog = ReplaceColorDialog(pattern, current_color_index=0, parent=None)
    qtbot.addWidget(dialog)

    assert "Drill" in dialog.source_count_label.text()
    assert "Stitch" not in dialog.source_count_label.text()


def test_pattern_library_sort_combo_translated_and_sorting_still_works(qtbot, english_language):
    from pysticky.ui.dialogs.pattern_library_data import LibraryData, LibraryEntry
    from pysticky.ui.dialogs.pattern_library_dialog import PatternLibraryDialog

    dialog = PatternLibraryDialog(parent=None)
    qtbot.addWidget(dialog)
    dialog._library = LibraryData()
    dialog._library.entries = [
        LibraryEntry(
            name="Zebra",
            filepath="z.pxs",
            width=1,
            height=1,
            color_count=1,
            stitch_count=1,
            added_date="2026-01-01",
        ),
        LibraryEntry(
            name="Apple",
            filepath="a.pxs",
            width=1,
            height=1,
            color_count=1,
            stitch_count=1,
            added_date="2026-01-02",
        ),
    ]

    sort_combo = dialog.findChild(__import__("PySide6.QtWidgets", fromlist=["QComboBox"]).QComboBox)
    # Der erste Eintrag (Index 0) muss "Name" sein und uebersetzt sein.
    assert sort_combo.itemText(0) == "Name"
    assert sort_combo.itemData(0) == "Name"

    dialog._sort_changed(sort_combo.itemData(0))
    assert [e.name for e in dialog._library.entries] == ["Apple", "Zebra"]
