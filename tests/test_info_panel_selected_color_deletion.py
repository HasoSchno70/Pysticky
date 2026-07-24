# -*- coding: utf-8 -*-
"""Regressionstest (Runde 68): Info-Panel-Farbliste verlor/verfälschte die
Selektions-Markierung, wenn eine Farbe VOR der gerade aktiven Farbe aus dem
Muster entfernt wurde (z.B. ueber den Farbverwaltungs-Dialog).

Hintergrund: `InfoPanel._selected_color_index` (info_panel.py) war ein
reiner Zahlen-Index, der nach `Pattern.remove_color()` NICHT nachgezogen
wurde. `Pattern.remove_color()` verschiebt hoehere Farbindizes um 1 nach
unten (siehe pattern.py-Docstring) -- das Farbleisten-Widget `ColorBar`
loest genau dieses Problem bereits per Objekt-Identitaet (`_current_entry`,
color_bar.py Zeile ~450 ff.), das Info-Panel tat das nicht.

Konkret: Farben [A, B, C], Farbe C (Index 2) ist im Info-Panel selektiert.
Wird Farbe A (Index 0) geloescht, verschieben sich B->0, C->1. Der alte Code
markierte danach entweder gar keine Zeile mehr als selektiert (Index 2
existiert nicht mehr in der neuen, kuerzeren Liste) oder -- bei anderer
Konstellation -- die FALSCHE Farbe. Erwartet: C bleibt als aktive Farbe
markiert, nur an ihrem neuen Index 1.
"""

from pysticky.core import Pattern, Thread


def _pattern_abc() -> Pattern:
    pattern = Pattern(name="Selektion-Test", width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("A", "#ff0000"))
    pattern.add_color(Thread.from_hex("B", "#00ff00"))
    pattern.add_color(Thread.from_hex("C", "#0000ff"))
    return pattern


def test_selected_color_follows_entry_after_earlier_color_removed(qtbot):
    from pysticky.ui.panels.info_panel import InfoPanel

    pattern = _pattern_abc()
    c_entry = pattern.color_entries[2]

    panel = InfoPanel()
    qtbot.addWidget(panel)
    panel.update_info(pattern)
    panel.set_selected_color(2)  # Farbe "C" aktiv

    assert panel._color_items[2]._entry is c_entry
    assert panel._color_items[2]._selected is True

    # Farbe "A" (Index 0, vor der aktiven Farbe) wird entfernt --
    # "C" rutscht von Index 2 auf Index 1.
    pattern.remove_color(0)
    assert pattern.color_entries[1] is c_entry

    # Simuliert _notify_panels("palette") in main_window.py, das nach jeder
    # Farb-Loeschung info_panel.update_info(p) aufruft.
    panel.update_info(pattern)

    assert len(panel._color_items) == 2
    selected_items = [it for it in panel._color_items if getattr(it, "_selected", False)]
    assert len(selected_items) == 1, (
        f"Erwarte genau eine markierte Zeile, gefunden: {len(selected_items)}"
    )
    assert selected_items[0]._entry is c_entry, (
        "Die vormals aktive Farbe 'C' muss nach dem Loeschen einer frueheren "
        "Farbe weiterhin (an ihrem neuen Index) als ausgewaehlt markiert sein."
    )


def test_selected_color_follows_entry_after_reorder_same_count(qtbot):
    """Verwandter Fall: Farbverwaltungs-Dialog ("Nach oben"/"Nach unten")
    aendert die Reihenfolge von `pattern.color_entries`, OHNE die Anzahl zu
    aendern -- das nimmt den same_structure-Schnellpfad in
    `_update_colors_list()`. Der Schnellpfad rief bisher nirgends
    `item.set_selected()` auf, weil Items positionsgebunden wiederverwendet
    werden -- die Markierung blieb also an der alten Listenposition kleben,
    die nach dem Vertauschen eine ANDERE Farbe zeigt."""
    from pysticky.ui.panels.info_panel import InfoPanel

    pattern = _pattern_abc()
    c_entry = pattern.color_entries[2]

    panel = InfoPanel()
    qtbot.addWidget(panel)
    panel.update_info(pattern)
    panel.set_selected_color(2)  # Farbe "C" aktiv

    # Reihenfolge tauschen: C von Index 2 nach Index 0 (Anzahl bleibt 3).
    pattern.color_entries.insert(0, pattern.color_entries.pop(2))
    assert pattern.color_entries[0] is c_entry
    assert len(pattern.color_entries) == 3

    panel.update_info(pattern)

    selected_items = [it for it in panel._color_items if getattr(it, "_selected", False)]
    assert len(selected_items) == 1
    assert selected_items[0]._entry is c_entry


def test_selected_color_cleared_when_active_color_itself_removed(qtbot):
    """Wird die gerade selektierte Farbe selbst geloescht, darf danach keine
    andere (falsche) Zeile faelschlich als 'ausgewaehlt' erscheinen."""
    from pysticky.ui.panels.info_panel import InfoPanel

    pattern = _pattern_abc()

    panel = InfoPanel()
    qtbot.addWidget(panel)
    panel.update_info(pattern)
    panel.set_selected_color(1)  # Farbe "B" aktiv

    pattern.remove_color(1)  # "B" selbst wird geloescht
    panel.update_info(pattern)

    assert len(panel._color_items) == 2
    selected_items = [it for it in panel._color_items if getattr(it, "_selected", False)]
    assert selected_items == [], (
        "Nach dem Loeschen der aktiven Farbe darf keine andere Zeile "
        "faelschlich als ausgewaehlt markiert bleiben."
    )
