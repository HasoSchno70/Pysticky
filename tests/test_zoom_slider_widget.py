"""
Untersuchung des ZoomSlider-Widgets (Runde 66 Clean-Code-Audit).

Fokus: der mypy-Fund `Cannot assign to a method [method-assign]` in
zoom_slider.py:81 (`self._label.mousePressEvent = lambda e: ...`) sowie
Grenzfaelle bei Clamp/Sync mit dem Canvas-Zoom.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from pysticky.ui.widgets.zoom_slider import ZoomSlider


def _click_label(widget: ZoomSlider) -> None:
    """Simuliert einen echten Linksklick auf das Prozent-Label."""
    pos = widget._label.rect().center()
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        pos,
        widget._label.mapToGlobal(pos),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    # mousePressEvent direkt aufrufen (wie Qt es beim echten Klick tut)
    widget._label.mousePressEvent(event)


def test_label_click_emits_zoom_100_requested(qapp: QApplication) -> None:
    """Der mousePressEvent-Monkeypatch auf dem Label funktioniert zur
    Laufzeit trotz des mypy method-assign-Fehlers -- Instanzattribute
    haben Vorrang vor Klassenmethoden bei Python-Attributzugriff, und
    PySide ruft self._label.mousePressEvent(event) genauso auf."""
    slider = ZoomSlider()
    received = []
    slider.zoom_100_requested.connect(lambda: received.append(True))

    _click_label(slider)

    assert received == [True]


def test_label_click_still_works_after_theme_reapply(qapp: QApplication) -> None:
    """_apply_theme() setzt nur Stylesheets, nicht mousePressEvent -- der
    Monkeypatch darf durch einen Theme-Wechsel nicht verloren gehen."""
    slider = ZoomSlider()
    received = []
    slider.zoom_100_requested.connect(lambda: received.append(True))

    slider._apply_theme()
    slider._apply_theme()

    _click_label(slider)
    assert received == [True]


def test_set_zoom_clamps_to_min_max(qapp: QApplication) -> None:
    slider = ZoomSlider()

    slider.set_zoom(slider.MAX_ZOOM + 1000)
    assert slider.zoom == slider.MAX_ZOOM
    assert slider._slider.value() == slider.MAX_ZOOM

    slider.set_zoom(slider.MIN_ZOOM - 1000)
    assert slider.zoom == slider.MIN_ZOOM
    assert slider._slider.value() == slider.MIN_ZOOM


def test_zoom_in_out_do_not_exceed_slider_range(qapp: QApplication) -> None:
    slider = ZoomSlider()
    slider.set_zoom(slider.MAX_ZOOM)
    slider._on_zoom_in()
    assert slider.zoom == slider.MAX_ZOOM

    slider.set_zoom(slider.MIN_ZOOM)
    slider._on_zoom_out()
    assert slider.zoom == slider.MIN_ZOOM


def test_set_zoom_from_factor_clamps_and_does_not_emit(qapp: QApplication) -> None:
    """set_zoom_from_factor() wird von _on_canvas_zoom_changed() benutzt, um
    den Slider OHNE Rueckkopplungsschleife zu synchronisieren -- daher darf
    hier zoom_changed NICHT emittiert werden (sonst wuerde der Slider den
    Canvas-Zoom erneut setzen)."""
    slider = ZoomSlider()
    received = []
    slider.zoom_changed.connect(lambda v: received.append(v))

    # Ausserhalb des Slider-Bereichs (z.B. Canvas mit anderen
    # Min/Max-Cell-Size-Settings als der Slider abdeckt)
    slider.set_zoom_from_factor(10.0)  # 1000%
    assert slider.zoom == slider.MAX_ZOOM
    assert slider._slider.value() == slider.MAX_ZOOM
    assert received == []  # keine Rueckkopplung ausgeloest

    slider.set_zoom_from_factor(0.01)  # 1%
    assert slider.zoom == slider.MIN_ZOOM
    assert received == []
