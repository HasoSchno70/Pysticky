# -*- coding: utf-8 -*-
"""Runde 67 Untersuchung: Probe-Test fuer die mypy-Fund-Haeufung in
tools_tab.py/general_tab.py (settings.value(..., type=X) liefert laut mypy
"object" statt X). Prueft mit ECHTEM ausgefuehrtem Code (nicht nur Code-
Lesen), ob QSettings.value(..., type=bool/int/str) bei absichtlich "falsch"
gespeicherten Werten (z.B. String "false" statt echtem bool) trotzdem
zuverlaessig den korrekten Python-Typ liefert -- oder ob es sich (wie beim
sehr aehnlichen Fall in user_template_dialog.py, Runde 66) um ein reines
Stub-Artefakt handelt, weil JEDE betroffene Zeile in tools_tab.py und
general_tab.py tatsaechlich einen expliziten type=-Parameter uebergibt.

Ergebnis vorweggenommen: Dies ist ein Diagnose-/Nicht-Regressions-Test, kein
Bugfix-Regressionstest -- die Untersuchung ergab, dass PySide6 mit explizitem
type= zuverlaessig korrekt konvertiert, selbst wenn der gespeicherte Wert ein
falsch getypter String ist.
"""

import pytest

pytestmark = pytest.mark.usefixtures("qtbot")


def test_qsettings_value_with_explicit_bool_type_coerces_string_false(qtbot):
    """Ein versehentlich als String "false" gespeicherter Wert muss von
    settings.value(key, default, type=bool) trotzdem als echtes False
    zurueckgegeben werden -- nicht als truthy nicht-leerer String."""
    from PySide6.QtCore import QSettings

    settings = QSettings("PySticky-Test-Probe", "TypeCoercion")
    settings.clear()
    settings.setValue("show_grid", "false")  # absichtlich falsch getypt

    value = settings.value("show_grid", True, type=bool)
    assert value is False, (
        f"QSettings.value(..., type=bool) lieferte {value!r} (Typ "
        f"{type(value).__name__}) statt False fuer den String 'false' -- "
        "waere ein echter Bug in tools_tab.py/general_tab.py, da setChecked() "
        "dann jeden nicht-leeren String als truthy interpretieren wuerde."
    )
    settings.clear()


def test_qsettings_value_with_explicit_int_type_coerces_string_number(qtbot):
    from PySide6.QtCore import QSettings

    settings = QSettings("PySticky-Test-Probe", "TypeCoercion")
    settings.clear()
    settings.setValue("fill_tolerance", "42")  # absichtlich als String

    value = settings.value("fill_tolerance", 0, type=int)
    assert value == 42
    assert isinstance(value, int)
    settings.clear()


def test_tools_tab_load_settings_handles_wrongly_typed_stored_values(qtbot):
    """End-to-End ueber die echte ToolsTab.load_settings()-Methode: simuliert
    QSettings-Werte, die als falsch getypte Strings vorliegen (z.B. durch
    manuelle .ini-Bearbeitung oder einen aelteren Programmzustand), und prueft,
    dass die Checkboxen/Spinboxen/Combos trotzdem den korrekten Wert anzeigen."""
    from PySide6.QtCore import QSettings

    from pysticky.ui.dialogs.settings_tabs.tools_tab import ToolsTab

    settings = QSettings("PySticky-Test-Probe", "ToolsTabProbe")
    settings.clear()
    # Absichtlich falsch getypte Werte (Strings statt bool/int)
    settings.setValue("remember_tool", "false")
    settings.setValue("pipette_show_info", "false")
    settings.setValue("fill_diagonal", "true")
    settings.setValue("marching_ants", "false")
    settings.setValue("backstitch_snap", "false")
    settings.setValue("tablet/pressure_enabled", "false")
    settings.setValue("touch/gestures_enabled", "true")
    settings.setValue("fill_tolerance", "17")
    settings.setValue("backstitch_width", "3")
    settings.setValue("tablet/max_brush_size", "9")
    settings.setValue("pipette_behavior", "2")

    tab = ToolsTab()
    qtbot.addWidget(tab)
    tab.load_settings(settings)

    assert tab.chk_remember_tool.isChecked() is False
    assert tab.chk_pipette_show_info.isChecked() is False
    assert tab.chk_fill_diagonal.isChecked() is True
    assert tab.chk_marching_ants.isChecked() is False
    assert tab.chk_backstitch_snap.isChecked() is False
    assert tab.chk_tablet_pressure.isChecked() is False
    assert tab.chk_touch_gestures.isChecked() is True
    assert tab.spin_fill_tolerance.value() == 17
    assert tab.spin_backstitch_width.value() == 3
    assert tab.spin_tablet_max_brush.value() == 9
    assert tab.combo_pipette_behavior.currentIndex() == 2

    settings.clear()


def test_general_tab_load_settings_handles_wrongly_typed_stored_values(qtbot):
    from PySide6.QtCore import QSettings

    from pysticky.ui.dialogs.settings_tabs.general_tab import GeneralTab

    settings = QSettings("PySticky-Test-Probe", "GeneralTabProbe")
    settings.clear()
    settings.setValue("autosave_enabled", "false")
    settings.setValue("autosave_backup", "false")
    settings.setValue("stitch_timer_enabled", "false")
    settings.setValue("restore_window", "false")
    settings.setValue("confirm_exit", "true")
    settings.setValue("confirm_overwrite", "false")
    settings.setValue("file_logging_enabled", "true")
    settings.setValue("autosave_interval", "22")
    settings.setValue("snapshot_interval_minutes", "45")
    settings.setValue("max_recent_files", "3")
    settings.setValue("status_timeout", "8")
    settings.setValue("start_action", "2")

    tab = GeneralTab()
    qtbot.addWidget(tab)
    tab.load_settings(settings)

    assert tab.chk_autosave.isChecked() is False
    assert tab.chk_autosave_backup.isChecked() is False
    assert tab.chk_stitch_timer.isChecked() is False
    assert tab.chk_restore_window.isChecked() is False
    assert tab.chk_confirm_exit.isChecked() is True
    assert tab.chk_confirm_overwrite.isChecked() is False
    assert tab.chk_file_logging.isChecked() is True
    assert tab.spin_autosave_interval.value() == 22
    assert tab.spin_snapshot_interval.value() == 45
    assert tab.spin_recent_files.value() == 3
    assert tab.spin_status_timeout.value() == 8
    assert tab.combo_start_action.currentIndex() == 2

    settings.clear()


def test_tools_tab_reset_to_defaults_restores_documented_defaults(qtbot):
    """Reset-auf-Standard-Check: nachdem alle Widgets auf abweichende Werte
    gesetzt wurden, muss reset_to_defaults() zuverlaessig die dokumentierten
    Standardwerte herstellen (kein Feld bleibt auf altem Wert stehen)."""
    from pysticky.ui.dialogs.settings_tabs.tools_tab import ToolsTab

    tab = ToolsTab()
    qtbot.addWidget(tab)

    # Alle Widgets auf Nicht-Standardwerte setzen
    tab.combo_default_tool.setCurrentIndex(tab.combo_default_tool.count() - 1)
    tab.chk_remember_tool.setChecked(True)
    tab.combo_pipette_behavior.setCurrentIndex(2)
    tab.chk_pipette_show_info.setChecked(False)
    tab.chk_fill_diagonal.setChecked(True)
    tab.spin_fill_tolerance.setValue(55)
    tab.chk_marching_ants.setChecked(False)
    tab.spin_backstitch_width.setValue(5)
    tab.chk_backstitch_snap.setChecked(False)
    tab.chk_tablet_pressure.setChecked(False)
    tab.spin_tablet_max_brush.setValue(20)
    tab.chk_touch_gestures.setChecked(True)

    tab.reset_to_defaults()

    assert tab.combo_default_tool.currentIndex() == 0
    assert tab.chk_remember_tool.isChecked() is False
    assert tab.combo_pipette_behavior.currentIndex() == 0
    assert tab.chk_pipette_show_info.isChecked() is True
    assert tab.chk_fill_diagonal.isChecked() is False
    assert tab.spin_fill_tolerance.value() == 0
    assert tab.chk_marching_ants.isChecked() is True
    assert tab.spin_backstitch_width.value() == 2
    assert tab.chk_backstitch_snap.isChecked() is True
    assert tab.chk_tablet_pressure.isChecked() is True
    assert tab.spin_tablet_max_brush.value() == 5
    assert tab.chk_touch_gestures.isChecked() is False


def test_general_tab_reset_to_defaults_restores_documented_defaults(qtbot):
    from pysticky.ui.dialogs.settings_tabs.general_tab import GeneralTab

    tab = GeneralTab()
    qtbot.addWidget(tab)

    tab.chk_autosave.setChecked(False)
    tab.spin_autosave_interval.setValue(59)
    tab.chk_autosave_backup.setChecked(False)
    tab.spin_snapshot_interval.setValue(240)
    tab.chk_stitch_timer.setChecked(False)
    tab.combo_start_action.setCurrentIndex(3)
    tab.spin_recent_files.setValue(20)
    tab.chk_restore_window.setChecked(False)
    tab.combo_theme.setCurrentIndex(1)
    tab.chk_confirm_exit.setChecked(True)
    tab.chk_confirm_overwrite.setChecked(False)
    tab.spin_status_timeout.setValue(30)
    tab.edit_default_author.setText("Test Author")
    tab.edit_default_copyright.setText("(c) Test")
    tab.chk_file_logging.setChecked(True)

    tab.reset_to_defaults()

    assert tab.chk_autosave.isChecked() is True
    assert tab.spin_autosave_interval.value() == 5
    assert tab.chk_autosave_backup.isChecked() is True
    assert tab.spin_snapshot_interval.value() == 30
    assert tab.chk_stitch_timer.isChecked() is True
    assert tab.combo_start_action.currentIndex() == 0
    assert tab.spin_recent_files.value() == 10
    assert tab.chk_restore_window.isChecked() is True
    assert tab.combo_theme.currentIndex() == 0
    assert tab.chk_confirm_exit.isChecked() is False
    assert tab.chk_confirm_overwrite.isChecked() is True
    assert tab.spin_status_timeout.value() == 3
    assert tab.edit_default_author.text() == ""
    assert tab.edit_default_copyright.text() == ""
    assert tab.chk_file_logging.isChecked() is False
    assert tab.combo_language.itemData(tab.combo_language.currentIndex()) == "auto"


def test_tools_tab_save_load_roundtrip(qtbot):
    """Uebernehmen-Button-Check: Werte aendern -> save_settings() -> neue
    Tab-Instanz -> load_settings() muss denselben Wert zurueckliefern."""
    from PySide6.QtCore import QSettings

    from pysticky.ui.dialogs.settings_tabs.tools_tab import ToolsTab

    settings = QSettings("PySticky-Test-Probe", "ToolsTabRoundtrip")
    settings.clear()

    tab1 = ToolsTab()
    qtbot.addWidget(tab1)
    tab1.chk_remember_tool.setChecked(True)
    tab1.combo_pipette_behavior.setCurrentIndex(1)
    tab1.chk_pipette_show_info.setChecked(False)
    tab1.chk_fill_diagonal.setChecked(True)
    tab1.spin_fill_tolerance.setValue(33)
    tab1.chk_marching_ants.setChecked(False)
    tab1.spin_backstitch_width.setValue(4)
    tab1.chk_backstitch_snap.setChecked(False)
    tab1.chk_tablet_pressure.setChecked(False)
    tab1.spin_tablet_max_brush.setValue(11)
    tab1.chk_touch_gestures.setChecked(True)
    tab1.save_settings(settings)

    tab2 = ToolsTab()
    qtbot.addWidget(tab2)
    tab2.load_settings(settings)

    assert tab2.chk_remember_tool.isChecked() is True
    assert tab2.combo_pipette_behavior.currentIndex() == 1
    assert tab2.chk_pipette_show_info.isChecked() is False
    assert tab2.chk_fill_diagonal.isChecked() is True
    assert tab2.spin_fill_tolerance.value() == 33
    assert tab2.chk_marching_ants.isChecked() is False
    assert tab2.spin_backstitch_width.value() == 4
    assert tab2.chk_backstitch_snap.isChecked() is False
    assert tab2.chk_tablet_pressure.isChecked() is False
    assert tab2.spin_tablet_max_brush.value() == 11
    assert tab2.chk_touch_gestures.isChecked() is True

    settings.clear()


def test_general_tab_save_load_roundtrip(qtbot):
    from PySide6.QtCore import QSettings

    from pysticky.ui.dialogs.settings_tabs.general_tab import GeneralTab

    settings = QSettings("PySticky-Test-Probe", "GeneralTabRoundtrip")
    settings.clear()

    tab1 = GeneralTab()
    qtbot.addWidget(tab1)
    tab1.chk_autosave.setChecked(False)
    tab1.spin_autosave_interval.setValue(19)
    tab1.chk_autosave_backup.setChecked(False)
    tab1.spin_snapshot_interval.setValue(60)
    tab1.chk_stitch_timer.setChecked(False)
    tab1.combo_start_action.setCurrentIndex(2)
    tab1.spin_recent_files.setValue(7)
    tab1.chk_restore_window.setChecked(False)
    tab1.combo_theme.setCurrentIndex(1)
    tab1.chk_confirm_exit.setChecked(True)
    tab1.chk_confirm_overwrite.setChecked(False)
    tab1.spin_status_timeout.setValue(9)
    tab1.edit_default_author.setText("  Anna Mueller  ")
    tab1.edit_default_copyright.setText("  (c) 2026  ")
    tab1.chk_file_logging.setChecked(True)
    tab1.save_settings(settings)

    tab2 = GeneralTab()
    qtbot.addWidget(tab2)
    tab2.load_settings(settings)

    assert tab2.chk_autosave.isChecked() is False
    assert tab2.spin_autosave_interval.value() == 19
    assert tab2.chk_autosave_backup.isChecked() is False
    assert tab2.spin_snapshot_interval.value() == 60
    assert tab2.chk_stitch_timer.isChecked() is False
    assert tab2.combo_start_action.currentIndex() == 2
    assert tab2.spin_recent_files.value() == 7
    assert tab2.chk_restore_window.isChecked() is False
    assert tab2.combo_theme.currentIndex() == 1
    assert tab2.chk_confirm_exit.isChecked() is True
    assert tab2.chk_confirm_overwrite.isChecked() is False
    assert tab2.spin_status_timeout.value() == 9
    assert tab2.edit_default_author.text() == "Anna Mueller"
    assert tab2.edit_default_copyright.text() == "(c) 2026"
    assert tab2.chk_file_logging.isChecked() is True

    settings.clear()
