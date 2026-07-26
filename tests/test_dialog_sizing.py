# -*- coding: utf-8 -*-
"""Tests für `dialog_sizing.py::auto_size_dialog()`.

Regression (Nutzer-Meldung 2026-07-25): Der Bildimport-Dialog quetschte
"Max. Farben"/"Confetti reduzieren" auf 8-9px Hoehe zusammen (weit unter
ihre eigene minimumSizeHint()), weil die Bildschirm-Kappung
(`max_height_frac`) den Dialog unter den tatsaechlichen Platzbedarf der
"Farben"-Sektion druecken konnte -- das umschliessende QVBoxLayout hat
keine ScrollArea und keine Stretch-Faktoren, kann also nicht mehr
ausweichen. `min_height` gibt (analog zum bereits bestehenden `min_width`)
einen harten Floor vor, den die Kappung nicht mehr unterbieten darf.
"""

from unittest.mock import patch

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

from pysticky.ui.dialogs.dialog_sizing import auto_size_dialog


def _small_screen_dialog(qtbot):
    dlg = QDialog()
    qtbot.addWidget(dlg)
    layout = QVBoxLayout(dlg)
    layout.addWidget(QLabel("x"))
    return dlg


def test_min_height_overrides_screen_cap(qtbot):
    """Ohne min_height wuerde ein kleiner Bildschirm den Dialog unter den
    per content_size angeforderten Platzbedarf kappen -- min_height muss
    das verhindern, genau wie min_width es fuer die Breite bereits tut."""
    dlg = _small_screen_dialog(qtbot)

    small_screen = QRect(0, 0, 800, 800)
    with patch("PySide6.QtGui.QScreen.availableGeometry", return_value=small_screen):
        auto_size_dialog(
            dlg,
            [],
            content_size=(400, 800),
            chrome_w=40,
            chrome_h=40,
            min_height=887,
        )

    assert dlg.height() == 887, (
        "min_height muss die Bildschirm-Kappung (0.92*800=736) ueberstimmen, "
        f"tatsaechliche Hoehe war {dlg.height()}"
    )


def test_without_min_height_screen_cap_still_applies(qtbot):
    """Gegenprobe: ohne min_height (Default 0) greift die Kappung weiterhin
    normal -- der neue Parameter darf bestehendes Verhalten nicht aendern."""
    dlg = _small_screen_dialog(qtbot)

    small_screen = QRect(0, 0, 800, 800)
    with patch("PySide6.QtGui.QScreen.availableGeometry", return_value=small_screen):
        auto_size_dialog(dlg, [], content_size=(400, 800), chrome_w=40, chrome_h=40)

    assert dlg.height() == int(800 * 0.92)


def test_min_width_and_min_height_both_respected(qtbot):
    """Beide harten Floors gleichzeitig gesetzt -- keiner darf den anderen
    verdraengen."""
    dlg = _small_screen_dialog(qtbot)

    small_screen = QRect(0, 0, 800, 800)
    with patch("PySide6.QtGui.QScreen.availableGeometry", return_value=small_screen):
        auto_size_dialog(
            dlg,
            [],
            content_size=(100, 100),
            min_width=500,
            min_height=600,
            chrome_w=0,
            chrome_h=0,
        )

    assert dlg.width() == 500
    assert dlg.height() == 600
