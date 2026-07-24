# -*- coding: utf-8 -*-
"""Regressionstest (Runde 52): mehrzeichige "#N"-Ersatzsymbole wurden in der
Info-Panel-Farbliste (_ColorListItem.lbl_symbol) am Zellrand abgeschnitten.

Hintergrund: Pattern.add_color(auto_symbol=True) faellt bei mehr als
len(SYMBOLS) (86) unterschiedlichen Farben auf ein garantiert eindeutiges
"#N"-Ersatzsymbol zurueck (z.B. "#1", "#12" -- siehe pattern.py, Runde 48).
Das reguläre Symbol-Alphabet besteht ausschliesslich aus EINZELNEN
Zeichen; "#N" ist dagegen mehrzeichig. Die Symbol-Spalte in der
Info-Panel-Farbliste (ui/panels/info_panel_widgets.py::_ColorListItem)
hatte eine feste Breite von 14px, kalibriert auf genau ein Zeichen --
"#12" (3 Zeichen, ~19px Textbreite bei diesem Font) wurde dadurch
stillschweigend abgeschnitten, wodurch z.B. "#1" und "#12" im Panel
identisch aussahen.
"""

import pytest
from PySide6.QtGui import QFontMetrics

from pysticky.core import Pattern, Thread


@pytest.fixture(autouse=True)
def _reset_theme():
    yield
    from pysticky.ui.styles import set_theme

    set_theme("dark")


def _pattern_with_many_colors(n: int) -> Pattern:
    """Baut ein Pattern mit `n` unterschiedlichen Farben (>86 -> "#N"-Fallback)."""
    pattern = Pattern(name="Symbol-Erschoepfung", width=10, height=10)
    pattern.color_entries.clear()
    for i in range(n):
        r = i % 256
        g = (i * 3) % 256
        b = (i * 7) % 256
        pattern.add_color(Thread.from_hex(f"Farbe {i}", f"#{r:02x}{g:02x}{b:02x}"))
    return pattern


def test_add_color_exhausts_symbol_pool_to_hash_n_fallback():
    """Sicherstellen, dass unser Repro tatsaechlich "#N"-Symbole erzeugt
    (Voraussetzung fuer den eigentlichen Test unten) -- schuetzt außerdem
    gegen eine stille Regression von Runde 48."""
    pattern = _pattern_with_many_colors(97)
    symbols = [e.symbol for e in pattern.color_entries]
    multi_char = [s for s in symbols if len(s) > 1]
    assert multi_char, "Erwarte mind. ein mehrzeichiges '#N'-Symbol bei 97 Farben"
    assert all(s.startswith("#") for s in multi_char)
    # 97 - 86 = 11 Fallback-Symbole ("#1".."#11") -- das letzte ist
    # garantiert 3-stellig, damit der Breiten-Test unten nicht zufällig an
    # einem einstelligen "#N" vorbeirutscht (bei 14px Spaltenbreite passt
    # "#9" gerade noch, "#11" nicht mehr).
    assert "#11" in symbols
    # Eindeutigkeit über alle Farben hinweg (auch untereinander).
    assert len(symbols) == len(set(symbols))


def test_color_list_item_symbol_label_wide_enough_for_hash_n_symbol(qtbot):
    """Der eigentliche Bug: lbl_symbol.width() muss >= der tatsaechlichen
    Textbreite des Symbols sein, sonst schneidet Qt es beim Rendern ab."""
    from pysticky.ui.panels.info_panel_widgets import _ColorListItem

    pattern = _pattern_with_many_colors(97)
    # Der letzte Eintrag ist garantiert "#11" (3-stellig, siehe Test oben).
    entry = pattern.color_entries[-1]
    assert entry.symbol == "#11"

    def calc_thread(stitch_count, fabric_count, mode="stitch"):
        return "1.0m"

    item = _ColorListItem(len(pattern.color_entries) - 1, entry, 14, calc_thread)
    qtbot.addWidget(item)

    fm = QFontMetrics(item.lbl_symbol.font())
    needed = fm.horizontalAdvance(entry.symbol)
    assert item.lbl_symbol.width() >= needed, (
        f"Symbol {entry.symbol!r} braucht {needed}px, Label ist aber nur "
        f"{item.lbl_symbol.width()}px breit -- wird abgeschnitten"
    )


def test_color_list_item_single_char_symbol_keeps_original_width(qtbot):
    """Normale Einzelzeichen-Symbole duerfen ihre bisherige 14px-Spaltenbreite
    behalten -- der Fix darf das normale Layout nicht aufblaehen."""
    from pysticky.ui.panels.info_panel_widgets import _ColorListItem

    pattern = Pattern(name="Normal", width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    entry = pattern.color_entries[0]
    assert len(entry.symbol) == 1

    def calc_thread(stitch_count, fabric_count, mode="stitch"):
        return "1.0m"

    item = _ColorListItem(0, entry, 14, calc_thread)
    qtbot.addWidget(item)

    # Exakt 14px sind ein Implementierungsdetail (haengt an Font-Metriken,
    # die je nach Umgebung/DPI um 1-2px schwanken koennen) -- worauf es
    # ankommt: ein Einzelzeichen-Symbol darf die Spalte nicht aufblaehen,
    # sie muss beim alten, kompakten Wert bleiben.
    assert item.lbl_symbol.width() <= 16


def test_color_list_item_update_entry_resizes_symbol_column(qtbot):
    """update_entry() (der Incremental-Update-Pfad) muss die Spaltenbreite
    mitziehen, wenn sich das Symbol einer Farbe zur Laufzeit aendert (z.B.
    ueber den Symbol-Editor) -- vorher blieb die Breite auf der Zeichenlaenge
    des ürsprünglichen Symbols eingefroren."""
    from pysticky.ui.panels.info_panel_widgets import _ColorListItem

    pattern = Pattern(name="Update", width=5, height=5)
    pattern.color_entries.clear()
    pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    entry = pattern.color_entries[0]

    def calc_thread(stitch_count, fabric_count, mode="stitch"):
        return "1.0m"

    item = _ColorListItem(0, entry, 14, calc_thread)
    qtbot.addWidget(item)
    assert item.lbl_symbol.width() <= 16  # siehe Kommentar im Test oben

    entry.symbol = "#12"
    item.update_entry(entry, 14, calc_thread)

    fm = QFontMetrics(item.lbl_symbol.font())
    needed = fm.horizontalAdvance(entry.symbol)
    assert item.lbl_symbol.width() >= needed
