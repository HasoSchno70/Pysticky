# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 15): HeatmapDialog rendert die Heatmap einmalig
beim Konstruieren, basierend auf der Scroll-Viewport-Groesse zu diesem
Zeitpunkt. Ohne einen resizeEvent()-Override blieb das gerenderte Bild
dauerhaft bei dieser Anfangsgroesse haengen -- Vergroessern/Maximieren des
Dialogs aenderte am Bild nichts, bis zufaellig Achsen-Combo oder
Block-Slider angefasst wurden (beide loesen _refresh_heatmap() ohnehin
schon aus).
"""

import pytest

from pysticky.core import Pattern, Thread

pytestmark = pytest.mark.usefixtures("qtbot")


def _pattern_with_stitches():
    p = Pattern(name="Heatmap-Test", width=20, height=20)
    p.color_entries.clear()
    p.add_color(Thread.from_hex("Rot", "#FF0000"))
    p.add_color(Thread.from_hex("Blau", "#0000FF"))
    for x in range(20):
        for y in range(20):
            p.set_stitch(x, y, (x + y) % 2)
    return p


def test_resize_eventually_re_renders_heatmap(qtbot):
    from pysticky.ui.dialogs.heatmap_dialog import HeatmapDialog

    dlg = HeatmapDialog(_pattern_with_stitches())
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.waitExposed(dlg)

    pixmap_before = dlg._image_label.pixmap()
    size_before = pixmap_before.size() if pixmap_before else None

    dlg.resize(1200, 1000)
    qtbot.wait(dlg._resize_timer.interval() + 200)

    pixmap_after = dlg._image_label.pixmap()
    assert pixmap_after is not None
    assert pixmap_after.size() != size_before


def test_resize_timer_is_debounced_singleshot(qtbot):
    """Mehrere schnelle Resize-Events duerfen nur EINEN finalen Refresh
    ausloesen, nicht einen pro Event (der Timer soll neu starten, nicht
    zusaetzliche parallele Aufrufe stapeln)."""
    from pysticky.ui.dialogs.heatmap_dialog import HeatmapDialog

    dlg = HeatmapDialog(_pattern_with_stitches())
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.waitExposed(dlg)

    assert dlg._resize_timer.isSingleShot() is True

    dlg.resize(900, 800)
    dlg.resize(950, 850)
    dlg.resize(1000, 900)

    # Direkt nach mehreren schnellen Resizes ist der Timer noch am Laufen
    # (Debounce), noch nicht gefeuert.
    assert dlg._resize_timer.isActive() is True
