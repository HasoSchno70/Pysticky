# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 17): PatternImportDialog._update_preview() rendere
per verschachtelter Python-Schleife mit einem QPainter.fillRect()-Aufruf
pro Zelle -- bei einem grossen Muster (bis zur 2000x2000-Formatgrenze
erlaubt) bis zu 4 Millionen Iterationen auf dem GUI-Thread, ein spuerbares
UI-Einfrieren direkt nach dem Import. Jetzt vektorisiert ueber eine
numpy-Farb-LUT (gleiches Muster wie image_import/preview_mixin.py::
_pattern_to_image). Diese Tests pruefen, dass die Vorschau weiterhin
korrekt (richtige Farben, richtige Sichtbarkeits-Komposition) gerendert
wird, nicht nur schneller.
"""

import pytest

from pysticky.core import Pattern, Thread

pytestmark = pytest.mark.usefixtures("qtbot")


def test_update_preview_renders_correct_colors(qtbot):
    from pysticky.ui.dialogs.pattern_import_dialog import PatternImportDialog

    pattern = Pattern(name="Preview-Test", width=4, height=4)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    pattern.set_stitch(0, 0, 0)

    dialog = PatternImportDialog()
    qtbot.addWidget(dialog)
    dialog._pattern = pattern
    dialog._update_preview()

    pixmap = dialog._preview_label.pixmap()
    assert pixmap is not None
    assert not pixmap.isNull()

    img = pixmap.toImage()
    # Oben-links im gerenderten Bild muss die Garnfarbe (Rot) zeigen,
    # nicht der weisse Hintergrund.
    pixel = img.pixelColor(0, 0)
    assert (pixel.red(), pixel.green(), pixel.blue()) == (255, 0, 0)


def test_update_preview_respects_layer_visibility(qtbot):
    """Composite-Rendering muss unsichtbare Layer weiterhin ignorieren --
    get_composite_grid() ist bereits sichtbarkeits-bewusst, aber das war
    bei der alten p.get_stitch(x, y)-Schleife implizit auch schon so."""
    from pysticky.ui.dialogs.pattern_import_dialog import PatternImportDialog

    pattern = Pattern(name="Layer-Test", width=4, height=4)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Blau", "#0000FF"))
    pattern.active_layer.set_stitch(0, 0, 0)
    pattern.active_layer.visible = False

    dialog = PatternImportDialog()
    qtbot.addWidget(dialog)
    dialog._pattern = pattern
    dialog._update_preview()

    img = dialog._preview_label.pixmap().toImage()
    pixel = img.pixelColor(0, 0)
    # Layer unsichtbar -> Hintergrundweiss, nicht die Garnfarbe.
    assert (pixel.red(), pixel.green(), pixel.blue()) == (255, 255, 255)


def test_update_preview_handles_large_pattern_without_hanging(qtbot):
    """Kein Anspruch an eine bestimmte Zeit, aber ein 500x500-Muster (weit
    unter der 2000x2000-Grenze, aber deutlich groesser als die alte
    verschachtelte Schleife komfortabel verarbeitet haette) darf nicht
    abstuerzen und muss ein gueltiges Pixmap liefern."""
    from pysticky.ui.dialogs.pattern_import_dialog import PatternImportDialog

    pattern = Pattern(name="Gross", width=500, height=500)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Gruen", "#00FF00"))
    for i in range(0, 500, 50):
        pattern.set_stitch(i, i, 0)

    dialog = PatternImportDialog()
    qtbot.addWidget(dialog)
    dialog._pattern = pattern
    dialog._update_preview()

    pixmap = dialog._preview_label.pixmap()
    assert pixmap is not None and not pixmap.isNull()
