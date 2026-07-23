# -*- coding: utf-8 -*-
"""Regressionstests (HiDPI-Audit Runde 40, Nachtrag zu Runde 39):
`IconProvider._render_emoji_icon` (`ui/icons/icon_provider.py`) legte seine
`QPixmap`s immer mit 1 physischem Pixel pro logischem Pixel an, unabhängig vom
tatsächlichen `devicePixelRatio()` des Bildschirms -- derselbe Ursachen-
Grundtyp wie beim Chunk-Cache und der Aida-Textur (siehe
`tests/test_hidpi_chunk_cache.py`). Auf einem HiDPI-Display (125/150/200%
Windows-Skalierung) erscheinen Toolbar-/Panel-Icons dadurch leicht unscharf
hochskaliert.

Fix: `_render_emoji_icon` legt die Pixmap jetzt in physischen Pixeln an
(`round(size * device_pixel_ratio)`) und markiert sie per
`setDevicePixelRatio()` -- alle Zeichenoperationen bleiben unverändert in
logischen Koordinaten. `IconProvider.get_icon()` liest dafür einmalig
`QApplication.primaryScreen().devicePixelRatio()` als statische Annäherung
(IconProvider ist ein klassenweiter, widget-loser Cache -- anders als der
Chunk-Cache gibt es hier kein einzelnes Widget, dessen `devicePixelRatioF()`
man live abfragen könnte) und faltet diesen Wert mit in den Cache-Key
(`name, size, color, dpr`), damit ein Wechsel des Bildschirm-DPR nicht ein
bei anderer DPR gerendertes Icon aus dem Cache wiederverwendet."""

import pytest
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication

from pysticky.ui.icons.icon_provider import IconProvider

pytestmark = pytest.mark.usefixtures("qtbot")


@pytest.fixture(autouse=True)
def _clear_icon_cache():
    """Verhindert Verunreinigung zwischen Tests (statischer Klassen-Cache)."""
    IconProvider.clear_cache()
    yield
    IconProvider.clear_cache()


def test_render_emoji_icon_is_crisp_at_hidpi_scale_factor():
    """Bei device_pixel_ratio=1.5 (150% Windows-Skalierung) muss die
    zurückgegebene Pixmap mit 1.5 physischen Pixeln pro logischem Pixel
    angelegt sein, sonst skaliert Qt sie beim Zeichnen unscharf hoch."""
    size = 24
    pixmap = IconProvider._render_emoji_icon("✏", size, "#ffffff", device_pixel_ratio=1.5)

    assert pixmap.devicePixelRatio() == 1.5, (
        "Regression: Emoji-Icon-Pixmap wurde ohne devicePixelRatio angelegt -- "
        "auf einem HiDPI-Bildschirm rendert Qt sie dadurch unscharf hochskaliert"
    )
    assert pixmap.width() == round(size * 1.5)
    assert pixmap.height() == round(size * 1.5)
    # Logische (deviceIndependent) Größe muss unverändert bleiben, sonst
    # verschiebt sich das Icon in Layouts, die mit `size` rechnen.
    assert pixmap.size().width() / pixmap.devicePixelRatio() == size
    assert pixmap.size().height() / pixmap.devicePixelRatio() == size


def test_render_emoji_icon_defaults_to_dpr_one():
    """Ohne expliziten Parameter (Alt-Aufrufer) muss sich am bisherigen
    Verhalten (dpr=1.0, physische == logische Pixelgröße) nichts ändern."""
    size = 24
    pixmap = IconProvider._render_emoji_icon("✏", size, "#ffffff")
    assert pixmap.devicePixelRatio() == 1.0
    assert pixmap.width() == size
    assert pixmap.height() == size


def test_get_icon_bakes_in_primary_screen_device_pixel_ratio(monkeypatch):
    """`get_icon()` muss das devicePixelRatio des primären Bildschirms lesen
    und in die gerenderte Pixmap übernehmen -- sonst bleiben über den
    öffentlichen Provider bezogene Icons (Toolbar, Panels, ...) auf einem
    HiDPI-Bildschirm unscharf, selbst wenn `_render_emoji_icon` selbst
    korrekt DPR-fähig ist.

    Hinweis: `icon.pixmap(w, h)` (ohne expliziten DPR-Parameter) liefert IMMER
    eine auf dpr=1.0 heruntergerechnete Kopie zurück -- das ist Qt-Normal-
    verhalten (so bekommen Nicht-HiDPI-Aufrufer weiter exakt die angeforderte
    Pixelgröße) und keine Regression. Reale Widgets (`button.setIcon(icon)`)
    fragen beim tatsächlichen Zeichnen intern über den Fenster-Kontext nach der
    passenden Auflösung; das lässt sich ohne sichtbares Fenster nicht
    beobachten. Stattdessen wird hier über `icon.pixmap(size, devicePixelRatio)`
    (dem expliziten HiDPI-Overload) und `icon.availableSizes()` geprüft, dass
    die von `get_icon()` tatsächlich hinterlegte Pixmap-Repräsentation in
    physischen Pixeln vorliegt."""
    screen = QApplication.primaryScreen()
    assert screen is not None, "Test benötigt eine echte QApplication mit Bildschirm"
    monkeypatch.setattr(type(screen), "devicePixelRatio", lambda self: 1.5)

    icon = IconProvider.get_icon("pencil", size=24)

    physical_size = QSize(round(24 * 1.5), round(24 * 1.5))
    assert physical_size in icon.availableSizes(), (
        "Regression: get_icon() ignoriert das Bildschirm-devicePixelRatio -- "
        "die hinterlegte Icon-Pixmap liegt nicht in physischen Pixeln vor"
    )

    pixmap = icon.pixmap(QSize(24, 24), 1.5)
    assert pixmap.devicePixelRatio() == 1.5
    assert pixmap.size() == physical_size


def test_get_icon_cache_treats_different_dpr_as_cache_miss(monkeypatch):
    """Ein Icon, das bei dpr=1.0 gecacht wurde, darf nicht für eine Anfrage
    bei dpr=1.5 wiederverwendet werden -- sonst bliebe ein bei 100% gerendertes
    Icon nach einem (simulierten) Wechsel auf einen HiDPI-Bildschirm unscharf
    im Cache stecken."""
    screen = QApplication.primaryScreen()
    assert screen is not None

    monkeypatch.setattr(type(screen), "devicePixelRatio", lambda self: 1.0)
    icon_at_1x = IconProvider.get_icon("pencil", size=24)
    assert QSize(24, 24) in icon_at_1x.availableSizes()

    monkeypatch.setattr(type(screen), "devicePixelRatio", lambda self: 1.5)
    icon_at_15x = IconProvider.get_icon("pencil", size=24)

    assert icon_at_15x is not icon_at_1x
    assert QSize(36, 36) in icon_at_15x.availableSizes()


def test_get_pixmap_still_returns_a_pixmap():
    """Schmaler Konsumenten-Smoke-Test: `get_pixmap()` (von Panels/Dialogen
    genutzt) darf durch den DPR-Umbau nicht kaputtgehen."""
    pixmap = IconProvider.get_pixmap("save", size=16)
    assert not pixmap.isNull()
