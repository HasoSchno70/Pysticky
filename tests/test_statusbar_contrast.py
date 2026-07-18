# -*- coding: utf-8 -*-
"""Regressionstest für die Statusleisten-Pill-Kontraste (2026-07-18).

Gemessen (WCAG-Kontrastformel) waren 4 von 8 Pills unter der AA-Mindest-
anforderung von 4.5:1, weil Text und Hintergrund-Tint denselben Farbton
nutzten (z.B. "layer"-Pill nur 2.67:1). Fix: alle getönten Pills nutzen
jetzt THEME.text_secondary statt der jeweiligen Akzentfarbe als Textfarbe
-- betrifft beide Themes (Dark und Light), da die Farbwerte je Theme
unterschiedlich, aber das Muster "Text = Hintergrund-Akzent" identisch war.
"""

import re

import pytest
from PySide6.QtCore import QSettings

from pysticky.ui.styles import DARK_THEME, LIGHT_THEME, set_theme


def _qsettings_with_scope():
    """QSettings() braucht Org/App-Name auf der QCoreApplication, sonst
    landen setValue()-Aufrufe im Leeren (siehe test_tools.py)."""
    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    return QSettings()


def _extract_qss_color(stylesheet: str) -> str:
    """Extrahiert den 'color:'-Wert (nicht 'background') aus einem QSS-String."""
    match = re.search(r"(?<!-)color:\s*([^;]+);", stylesheet)
    assert match, f"Keine 'color:'-Deklaration gefunden in: {stylesheet!r}"
    return match.group(1).strip()


@pytest.fixture(autouse=True)
def _reset_theme():
    yield
    set_theme("dark")


@pytest.mark.parametrize("theme_name,theme", [("dark", DARK_THEME), ("light", LIGHT_THEME)])
def test_statusbar_pills_use_neutral_text_color(qtbot, theme_name, theme):
    """Alle farbig getönten Pills müssen text_secondary als Textfarbe nutzen,
    nicht die jeweilige Akzentfarbe -- sonst fällt der Kontrast unter WCAG AA."""
    # MainWindow.__init__ liest das Theme aus QSettings und ueberschreibt damit
    # jeden vorherigen set_theme()-Aufruf -- direkt in QSettings setzen statt
    # nur set_theme() zu rufen.
    s = _qsettings_with_scope()
    old_theme = s.value("theme")
    s.setValue("theme", theme_name)

    from pysticky.ui.main_window import MainWindow

    try:
        w = MainWindow()
        qtbot.addWidget(w)
    finally:
        if old_theme is None:
            s.remove("theme")
        else:
            s.setValue("theme", old_theme)

    tinted_labels = [
        w.label_tool,
        w.label_stitch_type,
        w.label_position,
        w.label_layer,
        w.label_stitches,
    ]
    for label in tinted_labels:
        color = _extract_qss_color(label.styleSheet())
        assert color == theme.text_secondary, (
            f"{label.objectName() or label.text()!r} nutzt {color}, "
            f"erwartet text_secondary ({theme.text_secondary}) fuer ausreichenden Kontrast"
        )


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    def chan(c: int) -> float:
        c_norm = c / 255.0
        return c_norm / 12.92 if c_norm <= 0.03928 else ((c_norm + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def _contrast_ratio(rgb1: tuple[int, int, int], rgb2: tuple[int, int, int]) -> float:
    l1 = _relative_luminance(rgb1) + 0.05
    l2 = _relative_luminance(rgb2) + 0.05
    return max(l1, l2) / min(l1, l2)


@pytest.mark.parametrize("theme", [DARK_THEME, LIGHT_THEME])
def test_statusbar_tinted_pill_contrast_meets_wcag_aa(theme):
    """Direkte Kontrastberechnung fuer alle vier Akzentfarben (die 'layer'-Pill
    war mit 2.67:1 der schlechteste Fall) -- muss die WCAG-AA-Mindestforderung
    fuer normalen Text (4.5:1) erreichen."""
    bg_base = _hex_to_rgb(theme.bg_light)
    text = _hex_to_rgb(theme.text_secondary)
    accents = [theme.accent_primary, theme.accent_secondary, theme.info, theme.accent_purple]

    for accent_hex in accents:
        accent = _hex_to_rgb(accent_hex)
        # Gleiche Blend-Logik wie _apply_statusbar_styles (alpha=50 von 255)
        bg = tuple(round(bg_base[i] + (accent[i] - bg_base[i]) * 50 / 255) for i in range(3))
        ratio = _contrast_ratio(text, bg)
        assert ratio >= 4.5, f"Kontrast {ratio:.2f}:1 fuer Akzent {accent_hex} unter WCAG AA"
