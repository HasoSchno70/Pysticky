# -*- coding: utf-8 -*-
"""
Regressionstest: ToolBar.select_tool() gegen ein spezifisches Toggle-
Werkzeug (z.B. Tool.RECT_FILLED).

Bug: `_on_toggle_clicked` (fuer echte Button-Klicks gedacht: toggeln
relativ zum ZUVOR aktiven Werkzeug) wurde auch von `select_tool()`
wiederverwendet. Beim Wiederherstellen des zuletzt genutzten Werkzeugs
nach App-Start (`tool_handlers.py`, "Letztes Werkzeug merken") war
`_current_tool` noch PENCIL -- die Toggle-Heuristik griff nie, und
`select_tool(Tool.RECT_FILLED)` waehlte lautlos die Umriss-Variante
(Tool.RECT) statt der angeforderten gefuellten.
"""

from pysticky.ui.tools.tool_enum import Tool
from pysticky.ui.widgets.tool_bar import ToolBar


def test_select_tool_selects_filled_variant_directly(qtbot):
    bar = ToolBar()
    qtbot.addWidget(bar)

    # _current_tool startet als PENCIL -- die alte Toggle-Heuristik
    # (Vergleich mit dem VORHERIGEN Tool) haette hier nie gegriffen.
    assert bar.current_tool == Tool.PENCIL

    bar.select_tool(Tool.RECT_FILLED)

    assert bar.current_tool == Tool.RECT_FILLED
    assert bar._buttons[Tool.RECT_FILLED].is_filled is True


def test_select_tool_selects_outline_variant_directly(qtbot):
    bar = ToolBar()
    qtbot.addWidget(bar)

    # Erst gefuellt waehlen, dann direkt auf die Umriss-Variante wechseln --
    # muss auch in dieser Richtung explizit funktionieren, nicht nur toggeln.
    bar.select_tool(Tool.RECT_FILLED)
    bar.select_tool(Tool.RECT)

    assert bar.current_tool == Tool.RECT
    assert bar._buttons[Tool.RECT].is_filled is False


def test_select_tool_twice_on_same_filled_tool_stays_filled(qtbot):
    """select_tool() muss idempotent sein -- zweimal dasselbe gefuellte
    Tool anfordern darf nicht zurueck auf Umriss toggeln."""
    bar = ToolBar()
    qtbot.addWidget(bar)

    bar.select_tool(Tool.RECT_FILLED)
    bar.select_tool(Tool.RECT_FILLED)

    assert bar.current_tool == Tool.RECT_FILLED
    assert bar._buttons[Tool.RECT_FILLED].is_filled is True


def test_real_click_still_toggles_between_outline_and_filled(qtbot):
    """Ein echter Button-Klick (nicht select_tool()) soll weiterhin relativ
    zum aktuellen Zustand toggeln -- zweimal auf denselben Toggle-Button
    klicken wechselt Umriss <-> Gefuellt (bestehendes, gewuenschtes
    Verhalten, darf durch den Fix nicht kaputtgehen)."""
    bar = ToolBar()
    qtbot.addWidget(bar)
    btn = bar._buttons[Tool.RECT]

    btn.setChecked(True)
    bar._on_toggle_clicked(btn)  # erster Klick: Umriss (kein Toggle, da PENCIL vorher aktiv)
    assert bar.current_tool == Tool.RECT

    bar._on_toggle_clicked(btn)  # zweiter Klick auf denselben Button: toggelt zu Gefuellt
    assert bar.current_tool == Tool.RECT_FILLED

    bar._on_toggle_clicked(btn)  # dritter Klick: zurueck zu Umriss
    assert bar.current_tool == Tool.RECT
