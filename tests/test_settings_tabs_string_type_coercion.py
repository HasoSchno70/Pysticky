# -*- coding: utf-8 -*-
"""Regressionstest (Runde 69): canvas_tab.py, files_tab.py und colors_tab.py
lasen mehrere String-Settings (Farbwerte, Pfade, Schriftart) per
`settings.value(key, default)` OHNE `type=str`-Parameter -- anders als der
Rest der Codebase (z.B. file_handlers.py:32, pattern_library_dialog.py:99,
user_template_dialog.py:60 nutzen fuer exakt dieselben Keys "default_path"/
"library_path"/"templates_path" bereits `type=str`).

Unter QSettings' IniFormat (die Test-Isolation aus conftest.py nutzt das)
werden rein numerische gespeicherte Werte automatisch als int statt als str
zurueckgegeben, sobald kein `type=`-Hinweis vorliegt. Trifft das auf einen
Wert, der direkt an QLineEdit.setText() geht, crasht der komplette
Einstellungen-Dialog beim Oeffnen mit einem TypeError (setText() akzeptiert
nur str). Bei ColorButton.color (canvas_tab.py) crasht es zwar nicht sofort
beim Laden, aber `_update_style()` ruft `self._color.upper()` auf, was bei
einem int ebenfalls einen AttributeError wirft, sobald der Button neu
gezeichnet wird.

Ein per Registry-Bearbeitung, Schema-Drift zwischen App-Versionen oder
sonstiger Fremdeinwirkung "falsch getypt" abgelegter Wert durfte den
kompletten Dialog nicht crashen lassen -- `type=str` erzwingt eine
verlustbehaftete aber crashfreie String-Konvertierung statt eines
TypeError/AttributeError.
"""

import pytest
from PySide6.QtCore import QSettings

pytestmark = pytest.mark.usefixtures("qtbot")


def test_canvas_tab_load_settings_survives_wrong_stored_color_type(qtbot):
    from pysticky.ui.dialogs.settings_tabs.canvas_tab import CanvasTab

    settings = QSettings("PySticky", "PySticky")
    settings.clear()
    # Simuliert einen beschädigten/fremdgeschriebenen Registry-Wert: int
    # statt str unter einem Farb-Key.
    settings.setValue("grid_color_major", 12345)
    settings.setValue("grid_color_minor", 67890)
    settings.setValue("canvas_bg", 111)
    settings.setValue("empty_cell_color", 222)
    settings.sync()

    tab = CanvasTab()
    qtbot.addWidget(tab)
    tab.load_settings(settings)  # darf nicht crashen

    # ColorButton._update_style() ruft str.upper() auf -- muss also
    # tatsächlich ein str sein, kein int.
    assert isinstance(tab.btn_grid_color_major.color, str)
    assert isinstance(tab.btn_grid_color_minor.color, str)
    assert isinstance(tab.btn_canvas_bg.color, str)
    assert isinstance(tab.btn_empty_cell.color, str)
    tab.btn_grid_color_major._update_style()  # löst .upper() nicht-str aus


def test_files_tab_load_settings_survives_wrong_stored_path_type(qtbot):
    from pysticky.ui.dialogs.settings_tabs.files_tab import FilesTab

    settings = QSettings("PySticky", "PySticky")
    settings.clear()
    settings.setValue("default_path", 999)
    settings.setValue("library_path", 12345)
    settings.setValue("templates_path", 54321)
    settings.sync()

    tab = FilesTab()
    qtbot.addWidget(tab)
    tab.load_settings(settings)  # darf nicht mit TypeError crashen

    assert isinstance(tab.edit_default_path.text(), str)
    assert isinstance(tab.edit_library_path.text(), str)
    assert isinstance(tab.edit_templates_path.text(), str)


def test_colors_tab_load_settings_survives_wrong_stored_font_type(qtbot):
    from pysticky.ui.dialogs.settings_tabs.colors_tab import ColorsTab

    settings = QSettings("PySticky", "PySticky")
    settings.clear()
    settings.setValue("symbol_font", 42)
    settings.sync()

    tab = ColorsTab()
    qtbot.addWidget(tab)
    tab.load_settings(settings)  # QFont(non-str) darf nicht crashen


def test_canvas_tab_round_trip_keeps_color_strings(qtbot):
    """Normaler Rundtrip (Speichern -> Laden) muss weiterhin funktionieren --
    die neue type=str-Vorgabe darf gültige Werte nicht verfälschen."""
    from pysticky.ui.dialogs.settings_tabs.canvas_tab import CanvasTab

    settings = QSettings("PySticky", "PySticky")
    settings.clear()

    tab = CanvasTab()
    qtbot.addWidget(tab)
    tab.btn_grid_color_major.color = "#123456"
    tab.btn_canvas_bg.color = "#abcdef"
    tab.save_settings(settings)
    settings.sync()

    tab2 = CanvasTab()
    qtbot.addWidget(tab2)
    tab2.load_settings(settings)
    assert tab2.btn_grid_color_major.color == "#123456"
    assert tab2.btn_canvas_bg.color == "#abcdef"
