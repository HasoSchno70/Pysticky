# -*- coding: utf-8 -*-
"""Regressionstests (Runde 82, Audit-Thema Raster-Optionen-Dialog):
GridOptionsDialog (ui/dialogs/grid_options_dialog.py) hat frueher NUR das
live Canvas-Objekt mutiert (_apply() setzt self.canvas.major_grid_interval
etc. direkt), aber NIE in QSettings geschrieben. Damit war der komplette
Dialog effektiv nur fuer die laufende Sitzung wirksam:

- Ein Klick auf "OK" nach dem Aendern von Intervallen/Farben WIRKTE sofort
  auf dem Canvas, ging aber beim naechsten App-Start (MainWindow-Neustart
  liest Grid-Werte ausschliesslich aus QSettings, siehe misc_handlers.py
  _apply_settings_from_dialog()) verloren.
- Schlimmer: Auch ein simples Oeffnen+OK des ALLGEMEINEN Einstellungen-
  Dialogs (Einstellungen > Canvas), das _apply_settings_from_dialog() fuer
  ALLE Canvas-Settings erneut aus QSettings anwendet, ueberschrieb die per
  GridOptionsDialog gesetzten Werte sofort wieder mit den (unveraenderten)
  alten QSettings-Werten -- selbst wenn der Nutzer im allgemeinen Dialog
  gar nichts an den Grid-Einstellungen geaendert hatte.
- Fuer show_minor_grid und die "normale" Gitterfarbe (grid_color) gab es
  ueberhaupt keinen QSettings-Schluessel im gesamten Projekt -- diese zwei
  von fuenf Werten im Dialog waren *strukturell* nicht persistierbar.

Fix: GridOptionsDialog._apply() schreibt jetzt zusaetzlich zum Canvas-State
in QSettings (neue Schluessel "show_minor_grid" + "grid_color_normal",
sowie die bereits existierenden "major_grid_interval"/"minor_grid_interval"/
"grid_color_major"/"grid_color_minor"). MainWindow._apply_settings_from_dialog()
liest die zwei neuen Schluessel jetzt ebenfalls zurueck, analog zum
bestehenden Muster fuer die anderen Grid-Werte."""

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor

GRID_SETTINGS_KEYS = [
    "major_grid_interval",
    "minor_grid_interval",
    "show_minor_grid",
    "grid_color_major",
    "grid_color_minor",
    "grid_color_normal",
]


def _qsettings_with_scope():
    """QSettings() braucht Org/App-Name auf der QCoreApplication, sonst
    landen setValue()-Aufrufe im Leeren (siehe test_canvas_settings_wiring.py)."""
    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    return QSettings()


def test_minor_interval_cannot_reach_or_exceed_major_interval(qtbot):
    """Vor dem Fix akzeptierte der Dialog klaglos minor >= major (z.B.
    minor=10, major=5). Im Renderer (rendering_mixin.py::_draw_grid) gilt
    aber "if x % major == 0: major_pen / elif show_minor and x % minor == 0:
    minor_pen" -- ist minor >= major, ist JEDES Vielfache von minor
    zwangslaeufig auch ein Vielfaches von major, das elif fuer minor greift
    dann nie. Das Neben-Raster war also bei einer solchen Kombination
    komplett unsichtbar, obwohl "Neben-Raster anzeigen" aktiviert war und
    der Dialog keinerlei Hinweis darauf gab.

    Fix: spin_minor.maximum() wird live an spin_major gekoppelt (immer
    < major), sodass diese Kombination im UI gar nicht mehr einstellbar
    ist."""
    from pysticky.ui.canvas import CrossStitchCanvas
    from pysticky.ui.dialogs.grid_options_dialog import GridOptionsDialog

    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    dialog = GridOptionsDialog(canvas)
    qtbot.addWidget(dialog)

    dialog.spin_major.setValue(5)
    dialog.spin_minor.setValue(10)  # muss auf < 5 geklemmt werden
    assert dialog.spin_minor.value() < dialog.spin_major.value()

    # Auch der umgekehrte Fall: Haupt-Intervall wird NACH einer gueltigen
    # Neben-Einstellung verkleinert -- der jetzt ungueltige minor-Wert muss
    # automatisch nachgezogen werden.
    dialog.spin_major.setValue(20)
    dialog.spin_minor.setValue(15)
    assert dialog.spin_minor.value() == 15
    dialog.spin_major.setValue(10)
    assert dialog.spin_minor.value() < dialog.spin_major.value()

    # Rendering-Invariante direkt nachvollziehen: fuer jedes x, das minor
    # erfuellt, aber NICHT bereits major erfuellt, muss es tatsaechlich
    # sichtbare x-Werte geben (sonst waere das Neben-Raster nutzlos).
    major, minor = dialog.spin_major.value(), dialog.spin_minor.value()
    visible_minor_only = [x for x in range(0, 200) if x % minor == 0 and x % major != 0]
    assert visible_minor_only, "Neben-Raster darf nicht komplett vom Haupt-Raster verschluckt sein"


def test_apply_persists_all_grid_options_to_qsettings(qtbot):
    """dialog._apply() (== Klick auf "Anwenden"/"OK") muss ALLE fuenf
    Werte (2 Intervalle, show_minor_grid, 3 Farben) in QSettings
    schreiben, nicht nur das Canvas-Objekt live veraendern."""
    from pysticky.ui.canvas import CrossStitchCanvas
    from pysticky.ui.dialogs.grid_options_dialog import GridOptionsDialog

    s = _qsettings_with_scope()
    old_values = {k: s.value(k) for k in GRID_SETTINGS_KEYS}
    try:
        for k in GRID_SETTINGS_KEYS:
            s.remove(k)

        canvas = CrossStitchCanvas()
        qtbot.addWidget(canvas)

        dialog = GridOptionsDialog(canvas)
        qtbot.addWidget(dialog)

        dialog.spin_major.setValue(20)
        dialog.spin_minor.setValue(4)
        dialog.chk_minor.setChecked(False)
        dialog.btn_color_normal.color = QColor("#123456")
        dialog.btn_color_minor.color = QColor("#654321")
        dialog.btn_color_major.color = QColor("#abcdef")

        dialog._apply()

        s2 = _qsettings_with_scope()
        assert s2.value("major_grid_interval", type=int) == 20
        assert s2.value("minor_grid_interval", type=int) == 4
        assert s2.value("show_minor_grid", type=bool) is False
        assert s2.value("grid_color_normal", type=str).lower() == "#123456"
        assert s2.value("grid_color_minor", type=str).lower() == "#654321"
        assert s2.value("grid_color_major", type=str).lower() == "#abcdef"
    finally:
        for k, v in old_values.items():
            if v is None:
                s.remove(k)
            else:
                s.setValue(k, v)


def test_mainwindow_restores_grid_options_dialog_settings_after_restart(qtbot):
    """End-to-End: Werte, die GridOptionsDialog persistiert hat, muessen
    nach einem (simulierten) App-Neustart -- MainWindow()-Konstruktion --
    wieder auf dem Canvas landen. Deckt insbesondere show_minor_grid und
    die normale Gitterfarbe (grid_color) ab, fuer die es vorher gar keinen
    QSettings-Schluessel gab."""
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old_values = {k: s.value(k) for k in GRID_SETTINGS_KEYS}
    try:
        s.setValue("major_grid_interval", 15)
        s.setValue("minor_grid_interval", 3)
        s.setValue("show_minor_grid", False)
        s.setValue("grid_color_normal", "#0a0b0c")
        s.setValue("grid_color_minor", "#0d0e0f")
        s.setValue("grid_color_major", "#101112")

        w = MainWindow()
        qtbot.addWidget(w)

        assert w.canvas.major_grid_interval == 15
        assert w.canvas.minor_grid_interval == 3
        assert w.canvas.show_minor_grid is False
        assert w.canvas.grid_color.name() == "#0a0b0c"
        assert w.canvas.grid_minor_color.name() == "#0d0e0f"
        assert w.canvas.grid_major_color.name() == "#101112"
    finally:
        for k, v in old_values.items():
            if v is None:
                s.remove(k)
            else:
                s.setValue(k, v)
