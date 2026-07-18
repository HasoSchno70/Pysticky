# -*- coding: utf-8 -*-
"""Regressionstests für den Farben-Settings-Tab (2026-07-18): war zu 100%
totes UI (8 von 8 Einstellungen schrieben nur in QSettings, wurden nie
zurückgelesen) -- schlimmster Einzelfall im großen Dead-UI-Audit dieser
Session. Siehe colors-tab-wiring-2026-07.md Memory."""

from PySide6.QtCore import QSettings


def _qsettings_with_scope():
    """QSettings() braucht Org/App-Name auf der QCoreApplication, sonst
    landen setValue()-Aufrufe im Leeren (siehe test_tools.py)."""
    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    return QSettings()


def test_mainwindow_applies_colors_settings_at_startup(qtbot):
    """End-to-End: vor dem Start in QSettings hinterlegte Werte müssen beim
    Konstruieren von MainWindow direkt wirken -- nicht erst nach manuellem
    Öffnen des Einstellungen-Dialogs."""
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    keys = [
        "default_palette",
        "show_catalog",
        "symbol_font",
        "symbol_size",
        "auto_symbols",
        "color_display",
        "highlight_selected",
        "color_bar_size",
    ]
    old_values = {k: s.value(k) for k in keys}

    s.setValue("default_palette", "DMC")
    s.setValue("show_catalog", False)
    s.setValue("symbol_font", "Arial")
    s.setValue("symbol_size", 16)  # +6 gegenueber Default 10
    s.setValue("auto_symbols", True)
    s.setValue("color_display", 2)  # Nur Symbol
    s.setValue("highlight_selected", False)
    s.setValue("color_bar_size", 40)

    try:
        w = MainWindow()
        qtbot.addWidget(w)

        assert w.canvas.symbol_font_family == "Arial"
        assert w.canvas.symbol_size_offset == 6
        assert w.canvas.show_colors is False
        assert w.canvas.show_symbols is True
        assert w.palette_panel.show_catalog is False
        assert w.palette_panel.default_palette_name == "DMC"
        assert w.color_bar.swatch_size == 40
    finally:
        for k, v in old_values.items():
            if v is None:
                s.remove(k)
            else:
                s.setValue(k, v)


def test_color_display_mode_mapping(qtbot):
    """Alle vier Anzeige-Modi muessen die richtige show_colors/show_symbols-
    Kombination ergeben (3='Farbe+Name' faellt mangels Name-Rendering auf
    Farbe+Symbol zurueck)."""
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old = s.value("color_display")
    expected = {
        0: (True, False),  # Nur Farbe
        1: (True, True),  # Farbe + Symbol
        2: (False, True),  # Nur Symbol
        3: (True, True),  # Farbe + Name -> Farbe + Symbol
    }
    try:
        for mode, (colors, symbols) in expected.items():
            s.setValue("color_display", mode)
            w = MainWindow()
            qtbot.addWidget(w)
            assert w.canvas.show_colors is colors, mode
            assert w.canvas.show_symbols is symbols, mode
    finally:
        if old is None:
            s.remove("color_display")
        else:
            s.setValue("color_display", old)


def test_add_color_without_auto_symbol_uses_placeholder():
    """auto_symbol=False darf keine echten Symbole aus SYMBOLS vergeben --
    nur der Platzhalter, den auch das 'alle Symbole vergeben'-Fallback nutzt."""
    from pysticky.core import Pattern, Thread

    pattern = Pattern(width=5, height=5)
    pattern.color_entries.clear()

    idx = pattern.add_color(Thread.from_hex("Testfarbe", "#123456"), auto_symbol=False)
    assert pattern.color_entries[idx].symbol == "?"


def test_add_color_with_auto_symbol_still_default_true():
    """Bulk-Aufrufe ohne expliziten auto_symbol-Parameter (z.B. Bildimport,
    OXS-Import) muessen weiterhin echte Symbole automatisch vergeben --
    reines Hinzufuegen des Parameters darf bestehendes Verhalten nicht
    aendern."""
    from pysticky.core import Pattern, Thread

    pattern = Pattern(width=5, height=5)
    pattern.color_entries.clear()

    idx = pattern.add_color(Thread.from_hex("Testfarbe", "#123456"))
    assert pattern.color_entries[idx].symbol != "?"
