# -*- coding: utf-8 -*-
"""Regression (Nutzer-Meldung 2026-07-25): "Max. Farben" und "Confetti
reduzieren" waren im Bildimport-Dialog auf manchen Bildschirmen nicht mehr
bedienbar -- Klick/Scroll auf die Spinbox-Pfeile aenderte den Wert nicht.

Ursache: `_auto_size_to_content()` liess die Bildschirm-Kappung
(`max_height_frac` in `auto_size_dialog()`) den Dialog unter den
tatsaechlichen Platzbedarf der "Farben"-Sektion druecken. Das umschliessende
QVBoxLayout hat keine ScrollArea und keine Stretch-Faktoren -- es quetscht
seine sechs Gruppen dann unterhalb ihrer eigenen minimumSizeHint()
zusammen, u.a. `spin_colors`/`spin_confetti` auf 8-9px Hoehe. Optisch noch
als schmaler Rahmen erkennbar, aber ein Klick auf die (nicht mehr
sichtbaren) Spin-Pfeile trifft dann Nachbar-Widgets statt der Spinbox
selbst.
"""

from unittest.mock import patch

from PySide6.QtCore import QRect

from pysticky.ui.dialogs import ImageImportDialog


def test_max_colors_and_confetti_spinboxes_stay_above_own_minimum_size(qtbot):
    """Auf einem Bildschirm, der zu klein fuer den vollen Inhalts-sizeHint
    ist, darf die Bildschirm-Kappung die "Farben"-Sektion nicht unter die
    eigene minimumSizeHint() der Spinboxen quetschen."""
    small_screen = QRect(0, 0, 800, 800)
    with patch("PySide6.QtGui.QScreen.availableGeometry", return_value=small_screen):
        dlg = ImageImportDialog()
        qtbot.addWidget(dlg)
        dlg.show()

    for widget_name in ("spin_colors", "spin_confetti"):
        spin = getattr(dlg, widget_name)
        actual_height = spin.geometry().height()
        min_height = spin.minimumSizeHint().height()
        assert actual_height >= min_height, (
            f"{widget_name} wurde auf {actual_height}px gequetscht "
            f"(eigene minimumSizeHint() ist {min_height}px) -- "
            "Spin-Pfeile waeren real nicht mehr klickbar."
        )


def test_dialog_grows_beyond_screen_fraction_cap_when_content_needs_it(qtbot):
    """Der Dialog muss ueber die 92%-Bildschirm-Kappung hinauswachsen
    duerfen, wenn die "Farben"-Sektion das erfordert -- lieber ein
    (teils ausserhalb des kleinen Testbildschirms liegender) grosser
    Dialog als eine unbedienbare Eingabezeile."""
    small_screen = QRect(0, 0, 800, 800)
    with patch("PySide6.QtGui.QScreen.availableGeometry", return_value=small_screen):
        dlg = ImageImportDialog()
        qtbot.addWidget(dlg)
        dlg.show()
        capped_height = int(800 * 0.92)

    assert dlg.height() > capped_height
