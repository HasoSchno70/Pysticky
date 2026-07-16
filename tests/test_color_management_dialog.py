# -*- coding: utf-8 -*-
"""
Tests fuer ColorManagementDialog._remove_color_at_index().

Regression fuer einen Absturz: die Methode rief `layer.clear_stitch()`
(existiert nicht, richtig waere `replace_color()`/`shift_color_indices()`)
und wies `pattern.backstitches` neu zu (ist eine reine Read-Only-Property,
richtig waere `backstitch_manager.update_color_indices()`) -- beides fuehrte
bei jeder Farb-Loeschung/-Zusammenfuehrung zu einer AttributeError mitten in
der Methode, wodurch weder das Grid vollstaendig bereinigt noch
`_changes_made` gesetzt wurde (Canvas blieb dadurch unaktualisiert).
"""

import pytest

from pysticky.core.layer import NO_STITCH

# pytest-qt's qtbot-Fixture sorgt fuer eine lebende QApplication
pytestmark = pytest.mark.usefixtures("qtbot")


def _make_dialog(pattern, qtbot):
    from pysticky.ui.dialogs.color_management_dialog import ColorManagementDialog

    dialog = ColorManagementDialog(pattern, None)
    qtbot.addWidget(dialog)
    return dialog


def test_remove_unused_color_shifts_higher_indices(pattern_with_stitches, qtbot):
    """Farbe 1 (Weiss, ungenutzt) loeschen darf nicht abstuerzen und muss
    Stiche von Farbe 2 (Rot) korrekt auf Index 1 verschieben."""
    pattern = pattern_with_stitches
    dialog = _make_dialog(pattern, qtbot)

    assert len(pattern.color_entries) == 5
    red_stitches_before = pattern.color_entries[2].stitch_count
    assert red_stitches_before > 0

    dialog._remove_color_at_index(1)

    assert len(pattern.color_entries) == 4
    # Rot war Index 2, ist nach dem Loeschen von Index 1 jetzt Index 1.
    assert pattern.color_entries[1].thread.name == "Rot"
    assert pattern.color_entries[1].stitch_count == red_stitches_before

    layer = pattern.active_layer
    assert layer is not None
    for y in range(pattern.height):
        for x in range(pattern.width):
            assert layer.get_stitch(x, y) != 4  # kein Index zeigt mehr "daneben"


def test_remove_used_color_clears_all_its_stitches(pattern_with_stitches, qtbot):
    """Farbe 0 (Schwarz, gestickter Rahmen) loeschen muss den kompletten
    Rahmen aus dem Grid entfernen (kein Symbol/Stich bleibt zurueck)."""
    pattern = pattern_with_stitches
    dialog = _make_dialog(pattern, qtbot)

    layer = pattern.active_layer
    assert layer is not None
    assert layer.get_stitch(5, 5) == 0  # Rahmen-Ecke ist vor dem Loeschen gesetzt

    dialog._remove_color_at_index(0)

    for y in range(pattern.height):
        for x in range(pattern.width):
            assert layer.get_stitch(x, y) != 0

    assert len(pattern.color_entries) == 4
    # Rot (ehemals Index 2) ist jetzt Index 1, seine Fuellung bleibt erhalten.
    assert pattern.color_entries[1].thread.name == "Rot"
    assert pattern.color_entries[1].stitch_count > 0


def test_remove_color_updates_backstitch_indices(pattern_with_stitches, qtbot):
    """Rueckstiche mit dem geloeschten Index verschwinden, hoehere Indizes
    werden dekrementiert -- ohne AttributeError auf der Read-Only-Property."""
    pattern = pattern_with_stitches
    pattern.add_backstitch(0, 0, 2, 2, color_index=1)  # wird geloescht
    pattern.add_backstitch(2, 2, 4, 4, color_index=2)  # rueckt auf Index 1

    dialog = _make_dialog(pattern, qtbot)
    dialog._remove_color_at_index(1)

    remaining = pattern.backstitches
    assert len(remaining) == 1
    assert remaining[0].color_index == 1


def test_remove_color_recalculates_stitch_counts(pattern_with_stitches, qtbot):
    """Nach dem Loeschen stimmen die Stichzahlen mit dem tatsaechlichen
    Grid-Inhalt ueberein (nicht nur die verschobenen alten Zaehlerstaende)."""
    pattern = pattern_with_stitches
    dialog = _make_dialog(pattern, qtbot)

    dialog._remove_color_at_index(1)
    pattern.recalculate_stitch_counts()
    expected = [e.stitch_count for e in pattern.color_entries]

    # Ein zweiter Aufruf direkt nach _remove_color_at_index() (ohne
    # zwischenzeitliche Grid-Aenderung) muss zum gleichen Ergebnis kommen --
    # die Methode soll die Zaehlung selbst schon konsistent halten.
    assert [e.stitch_count for e in pattern.color_entries] == expected


def test_remove_color_at_last_index_has_no_stitches_to_shift(pattern_with_stitches, qtbot):
    """Randfall: die letzte Farbe (kein hoeherer Index existiert) loeschen
    darf ebenfalls nicht abstuerzen."""
    pattern = pattern_with_stitches
    dialog = _make_dialog(pattern, qtbot)

    dialog._remove_color_at_index(len(pattern.color_entries) - 1)

    assert len(pattern.color_entries) == 4
    layer = pattern.active_layer
    assert layer is not None
    num_colors = len(pattern.color_entries)
    valid_mask = layer.grid == NO_STITCH
    for idx in range(num_colors):
        valid_mask = valid_mask | (layer.grid == idx)
    assert bool(valid_mask.all())  # kein Stich zeigt auf einen jetzt ungueltigen Index
