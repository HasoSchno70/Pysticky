# -*- coding: utf-8 -*-
"""
Regressionstest: Text-Werkzeug (ui/tools/text_tool.py) muss eingebettete
Zeilenumbrueche ("\n") als echte Zeilenumbrueche rendern.

Hintergrund (Runde 84 Audit): `_update_preview()` nutzte die
Einzelstring-Ueberladung von `QFontMetrics.boundingRect(text)` und
`QPainter.drawText(x, y, text)`. Beide ignorieren eingebettete "\n"-Zeichen
komplett (kein Zeilenumbruch, kein sichtbarer Vorschub) -- ein Text wie
"AB\nCD" wurde dadurch als "ABCD" auf EINER Zeile in ein Bitmap gerendert,
statt "AB" und "CD" als zwei Zeilen untereinander.

Der Zeilenumbruch ist ueber die Text-Tool-UI erreichbar: `QLineEdit.setText()`
bzw. `.insert()` behaelt eingebettete "\n"-Zeichen bei (z.B. beim Einfuegen
von mehrzeiligem Text aus der Zwischenablage per Ctrl+V) -- das Text-Tool
bekommt den Rohstring unveraendert per `set_text()`.
"""

from pysticky.ui.tools.text_tool import TextTool

pytestmark = []


def _make_tool(text: str, size: int = 14) -> TextTool:
    tool = TextTool()
    tool.set_font_family("Arial")
    tool.set_font_size(size)
    tool.set_text(text)
    return tool


def test_multiline_text_renders_taller_than_wide(qtbot):
    """
    "AB\\nCD" hat pro Zeile nur 2 Zeichen -- bei korrektem Zeilenumbruch ist
    die Vorschau (2 Zeilen hoch, 2 Zeichen breit) deutlich hoeher als breit.

    Vor dem Fix wurden alle 4 Zeichen nebeneinander auf einer Zeile
    gezeichnet -- die Vorschau war dann breiter als hoch.
    """
    tool = _make_tool("AB\nCD")

    assert tool._preview_pixels is not None
    width, height = tool._preview_size

    assert height > width, (
        f"Erwartet: mehrzeilige Vorschau ist hoeher als breit (2 Zeilen a 2 "
        f"Zeichen), tatsaechlich width={width}, height={height} -- "
        f"Zeilenumbruch wird nicht korrekt verarbeitet."
    )


def test_multiline_text_lines_do_not_overlap(qtbot):
    """
    Die zweite Zeile ("CD") muss klar unterhalb der ersten Zeile ("AB")
    liegen -- keine ueberlappenden oder identischen Y-Bereiche.
    """
    single_line = _make_tool("AB")
    multi_line = _make_tool("AB\nCD")

    assert single_line._preview_pixels is not None
    assert multi_line._preview_pixels is not None

    single_height = single_line._preview_size[1]
    multi_height = multi_line._preview_size[1]

    # Zwei gestapelte Zeilen muessen deutlich mehr Hoehe brauchen als eine
    # einzelne Zeile alleine (mind. das 1.5-fache, um Rundungs-/Padding-
    # Unterschiede zu tolerieren).
    assert multi_height > single_height * 1.5, (
        f"Mehrzeilige Vorschau (Hoehe={multi_height}) sollte deutlich hoeher "
        f"sein als eine einzeilige Vorschau (Hoehe={single_height})."
    )

    # Die schwarzen Pixel muessen ueber (mindestens) zwei getrennte
    # Y-Cluster verteilt sein statt alle in einem schmalen Y-Band zu liegen.
    ys = sorted({y for _, y in multi_line._preview_pixels})
    y_span = ys[-1] - ys[0]
    assert y_span > single_height, (
        f"Y-Spannweite der Textpixel ({y_span}) sollte groesser sein als "
        f"die Hoehe einer einzelnen Zeile ({single_height}) -- die Zeilen "
        f"muessen vertikal versetzt sein."
    )


def test_singleline_text_still_renders(qtbot):
    """Regressionsschutz: normaler einzeiliger Text funktioniert weiterhin."""
    tool = _make_tool("Hallo")
    assert tool._preview_pixels is not None
    assert len(tool._preview_pixels) > 0
    width, height = tool._preview_size
    assert width > height  # "Hallo" ist ein breites Wort auf einer Zeile
