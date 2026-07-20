# -*- coding: utf-8 -*-
"""
Regressionstest: ColorBar hielt die ausgewaehlte Farbe nur als Zahlen-
Index fest. Pattern.remove_color() verschiebt hoehere Indizes nach unten,
behaelt aber dieselben ColorEntry-Objekte fuer ueberlebende Farben --
loeschte man eine Farbe VOR der ausgewaehlten, blieb refresh()/
_rebuild_swatches() beim alten Zahlen-Index, der jetzt aber auf eine
ANDERE Farbe zeigt.
"""

from pysticky.ui.widgets.color_bar import ColorBar


def test_selection_follows_same_color_after_earlier_color_removed(qtbot, pattern_with_colors):
    bar = ColorBar()
    qtbot.addWidget(bar)
    bar.set_pattern(pattern_with_colors)

    # Farbe an Index 2 auswaehlen und uns deren Objekt-Identitaet merken.
    bar.select_color(2)
    selected_entry = pattern_with_colors.color_entries[2]

    # Farbe VOR der ausgewaehlten entfernen -- Index 2 verschiebt sich auf 1.
    pattern_with_colors.remove_color(0)
    bar.refresh()

    assert bar.current_index == 1
    assert pattern_with_colors.color_entries[bar.current_index] is selected_entry
    assert bar._swatches[bar.current_index].selected is True
    # Kein anderer Swatch darf faelschlich als ausgewaehlt markiert sein.
    assert all(s.selected is False for i, s in enumerate(bar._swatches) if i != bar.current_index)


def test_selection_clamps_when_selected_color_itself_removed(qtbot, pattern_with_colors):
    """Wird die ausgewaehlte Farbe selbst geloescht (nicht mehr auffindbar),
    faellt die Auswahl auf einen gueltigen Index zurueck statt zu crashen."""
    bar = ColorBar()
    qtbot.addWidget(bar)
    bar.set_pattern(pattern_with_colors)

    last_index = len(pattern_with_colors.color_entries) - 1
    bar.select_color(last_index)

    pattern_with_colors.remove_color(last_index)
    bar.refresh()

    assert 0 <= bar.current_index < len(bar._swatches)
