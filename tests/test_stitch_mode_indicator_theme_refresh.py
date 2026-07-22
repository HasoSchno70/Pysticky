# -*- coding: utf-8 -*-
"""Regressionstest (Runde 32): Der Sticken-Modus-Indikator in der Statusbar
(`MainWindow.label_stitch_mode`) baut sein Stylesheet nur bei jedem
Ein-/Ausschalten frisch aus THEME zusammen
(`main_window.py::_update_stitch_mode_indicator`). Er ist ein rohes QLabel
ohne eigene `_apply_theme()`-Methode, wird also von der generischen
`findChildren(QWidget)`-Schleife in `_reapply_all_widget_styles()`
(misc_handlers.py) nicht erfasst.

Vorher: ein Live-Theme-Wechsel (Einstellungen-Dialog) WAEHREND aktivem
Sticken-Modus liess die Pill auf den Farben des alten Themes haengen, bis
der Modus einmal aus- und wieder eingeschaltet wurde -- derselbe
wiederkehrende "THEME staleness on live theme switch"-Bug wie bei
RulerWidget/WelcomeWidget in frueheren Runden, nur hier direkt in
MainWindow selbst statt in einem Widget mit eigener Klasse.
"""

from PySide6.QtCore import QSettings


def _qsettings_with_scope():
    """QSettings() braucht Org/App-Name auf der QCoreApplication, sonst
    landen setValue()-Aufrufe im Leeren (siehe test_statusbar_contrast.py)."""
    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    return QSettings()


def test_stitch_mode_indicator_refreshes_on_theme_switch(qtbot):
    """Bei aktivem Sticken-Modus muss ein Theme-Wechsel die Pill-Farben der
    Indikator-Statusbar sofort aktualisieren, nicht erst beim naechsten
    Toggle."""
    from pysticky.ui.main_window import MainWindow
    from pysticky.ui.styles import DARK_THEME, LIGHT_THEME, set_theme

    s = _qsettings_with_scope()
    old_theme = s.value("theme")
    s.setValue("theme", "dark")

    try:
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()
        w.show()

        # Sticken-Modus-Indikator aktivieren, wie es
        # ViewHandlersMixin._on_toggle_stitch_mode() beim Einschalten tut.
        w._update_stitch_mode_indicator(True)
        assert w.label_stitch_mode.isVisible()
        style_before = w.label_stitch_mode.styleSheet()
        assert DARK_THEME.accent_primary in style_before

        # Live-Theme-Wechsel auf "light", wie es der Einstellungen-Dialog
        # ueber set_theme() + _reapply_all_widget_styles() ausloest.
        set_theme("light")
        w._reapply_all_widget_styles()

        style_after = w.label_stitch_mode.styleSheet()
        assert LIGHT_THEME.accent_primary in style_after
        assert DARK_THEME.accent_primary not in style_after
        # Sichtbarkeit darf durch den Refresh nicht verloren gehen.
        assert w.label_stitch_mode.isVisible()
    finally:
        set_theme("dark")
        if old_theme is None:
            s.remove("theme")
        else:
            s.setValue("theme", old_theme)


def test_stitch_mode_indicator_stays_hidden_on_theme_switch_when_inactive(qtbot):
    """Wenn der Sticken-Modus NICHT aktiv ist, darf ein Theme-Wechsel die
    (versteckte) Pill nicht ploetzlich sichtbar machen."""
    from pysticky.ui.main_window import MainWindow
    from pysticky.ui.styles import set_theme

    s = _qsettings_with_scope()
    old_theme = s.value("theme")
    s.setValue("theme", "dark")

    try:
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()
        w.show()

        assert not w.label_stitch_mode.isVisible()

        set_theme("light")
        w._reapply_all_widget_styles()

        assert not w.label_stitch_mode.isVisible()
    finally:
        set_theme("dark")
        if old_theme is None:
            s.remove("theme")
        else:
            s.setValue("theme", old_theme)
