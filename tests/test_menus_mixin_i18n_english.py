# -*- coding: utf-8 -*-
"""
Regressionstests (Runde 23): mw_menus_mixin.py::_on_stitch_type_changed()
und _on_colorblind_changed() bauten das Status-Label/die Statusleisten-
Meldung aus dem rohen deutschen entry_label (bzw. cb_type.value/hart-
codiertem "keine") statt es zuerst durch t() zu schicken -- im Englisch-
Modus zeigten Status-Label und Statusleiste dauerhaft deutschen Text
bzw. den rohen Enum-Wert.
"""

import pytest

from pysticky.core.i18n import set_language


@pytest.fixture
def english_language():
    set_language("en")
    try:
        yield
    finally:
        set_language("de")


def test_stitch_type_status_label_is_translated(qtbot, english_language):
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    w._on_stitch_type_changed(1)  # HALF_TL_BR

    assert "Half" in w.label_stitch_type.text()
    assert "Halber" not in w.label_stitch_type.text()


def test_stitch_type_status_bar_message_is_translated(qtbot, english_language):
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    w._on_stitch_type_changed(1)

    assert "Stitch type:" in w.status_bar.currentMessage()
    assert "Stichtyp" not in w.status_bar.currentMessage()


def test_colorblind_status_message_is_translated(qtbot, english_language):
    from pysticky.core.color_blindness import ColorBlindType
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    w._on_colorblind_changed(ColorBlindType.PROTANOPIA)

    msg = w.status_bar.currentMessage()
    assert "Colorblind simulation:" in msg
    assert "Protanopia" in msg or "Protanopie" not in msg
    assert "Farbblindheits" not in msg


def test_colorblind_none_status_message_is_translated(qtbot, english_language):
    from pysticky.core.color_blindness import ColorBlindType
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()

    w._on_colorblind_changed(ColorBlindType.NONE)

    msg = w.status_bar.currentMessage()
    assert "keine" not in msg
