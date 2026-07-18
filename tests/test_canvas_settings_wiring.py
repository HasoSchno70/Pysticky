# -*- coding: utf-8 -*-
"""Regressionstests für die Canvas-Einstellungen im Settings-Dialog
(Einstellungen → Canvas): 10 von 14 Werten schrieben früher nur in
QSettings, wurden aber nirgends zurückgelesen -- ein Bildimport in eine
der 10 betroffenen Paletten (siehe catalog-number-field-bug-2026-07) war
ein unabhängiger, aber ähnlich gelagerter Dead-UI-Fund. Jetzt verdrahtet
über MainWindow._apply_settings_from_dialog(), die sowohl beim App-Start
als auch beim Schließen des Einstellungen-Dialogs läuft."""

from PySide6.QtCore import QSettings


def _qsettings_with_scope():
    """QSettings() braucht Org/App-Name auf der QCoreApplication, sonst
    landen setValue()-Aufrufe im Leeren (siehe test_tools.py)."""
    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    return QSettings()


def test_mainwindow_applies_canvas_settings_at_startup(qtbot):
    """End-to-End: Werte, die vor dem Start in QSettings liegen, müssen
    beim Konstruieren von MainWindow direkt auf dem Canvas landen -- nicht
    erst nach manuellem Öffnen des Einstellungen-Dialogs."""
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    keys = [
        "major_grid_interval",
        "minor_grid_interval",
        "grid_color_major",
        "grid_color_minor",
        "min_cell_size",
        "max_cell_size",
        "default_cell_size",
        "zoom_speed",
        "canvas_bg",
        "empty_cell_color",
    ]
    old_values = {k: s.value(k) for k in keys}

    s.setValue("major_grid_interval", 7)
    s.setValue("minor_grid_interval", 3)
    s.setValue("grid_color_major", "#ab00cd")
    s.setValue("grid_color_minor", "#112233")
    s.setValue("min_cell_size", 5)
    s.setValue("max_cell_size", 55)
    s.setValue("default_cell_size", 18)
    s.setValue("zoom_speed", 20)  # -> 2.0x ZOOM_STEP
    s.setValue("canvas_bg", "#010203")
    s.setValue("empty_cell_color", "#040506")

    try:
        w = MainWindow()
        qtbot.addWidget(w)

        assert w.canvas.major_grid_interval == 7
        assert w.canvas.minor_grid_interval == 3
        assert w.canvas.grid_major_color.name() == "#ab00cd"
        assert w.canvas.grid_minor_color.name() == "#112233"
        assert w.canvas.MIN_CELL_SIZE == 5
        assert w.canvas.MAX_CELL_SIZE == 55
        assert w.canvas.DEFAULT_CELL_SIZE == 18
        assert w.canvas.ZOOM_STEP == 2.0
        assert w.canvas.bg_color.name() == "#010203"
        assert w.canvas.empty_cell_color.name() == "#040506"
    finally:
        for k, v in old_values.items():
            if v is None:
                s.remove(k)
            else:
                s.setValue(k, v)


def test_zoom_in_out_multiplicative_with_guaranteed_progress(qtbot):
    """zoom_in/zoom_out skalieren jetzt multiplikativ mit ZOOM_STEP (statt
    fest +/-2px) -- garantierte Mindestbewegung von 1px, damit kleine
    Zellgrößen bei ZOOM_STEP nahe 1.0 nicht steckenbleiben."""
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    canvas.ZOOM_STEP = 1.5

    canvas._cell_size = 10
    canvas.zoom_in()
    assert canvas._cell_size == 15  # round(10 * 1.5)

    canvas._cell_size = canvas.MIN_CELL_SIZE
    canvas.zoom_out()
    assert canvas._cell_size == canvas.MIN_CELL_SIZE  # darf Untergrenze nicht unterschreiten

    # Mindestbewegung: bei sehr kleiner Zellgroesse wuerde reines Runden
    # manchmal keine Aenderung ergeben (z.B. round(4*1.01)=4) -- die
    # +1/-1-Garantie verhindert das.
    canvas.ZOOM_STEP = 1.01
    canvas._cell_size = max(canvas.MIN_CELL_SIZE, 4)
    before = canvas._cell_size
    canvas.zoom_in()
    assert canvas._cell_size > before
