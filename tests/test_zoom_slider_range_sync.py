"""
Regressionstest: ZoomSlider-Wertebereich muss mit individuell konfigurierten
Canvas-Zellgroessen-Grenzen synchron bleiben (Runde 66 Clean-Code-Audit).

Bug: `_apply_settings_from_dialog()` in misc_handlers.py aktualisiert
`canvas.MIN_CELL_SIZE`/`MAX_CELL_SIZE`/`DEFAULT_CELL_SIZE` PRO INSTANZ aus
den gespeicherten Einstellungen (Einstellungen -> Leinwand), siehe der
Kommentar in canvas.py ("bewusst Instanz-ueberschreibbar"). Der Zoom-Slider
in der Statusleiste behielt dabei aber seinen HARTCODIERTEN Bereich
20%-300% (MIN_ZOOM_PERCENT/MAX_ZOOM_PERCENT aus core/constants.py).

Weichen die Nutzer-Einstellungen vom Default ab (z.B. min_cell_size=2,
max_cell_size=100, default_cell_size=4 -> gueltiger Zoom-Bereich
50%-2500%), zeigte der Slider nach einem Zoom ausserhalb 20-300% einen
geklemmten, FALSCHEN Wert an -- und ein anschliessendes Ziehen des Sliders
haette den echten Canvas-Zoom unerwartet in den zu engen Default-Bereich
zurueckgerissen.

Fix: ZoomSlider.set_zoom_range() macht MIN_ZOOM/MAX_ZOOM instanz-
ueberschreibbar (analog zu Canvas.MIN_CELL_SIZE & Co) und wird von
_apply_settings_from_dialog() nach jeder Zellgroessen-Aenderung aufgerufen.
"""

from pysticky.ui.canvas import CrossStitchCanvas
from pysticky.ui.widgets.zoom_slider import ZoomSlider


def _wire_like_main_window(canvas: CrossStitchCanvas, slider: ZoomSlider) -> None:
    """Repliziert die Verdrahtung aus main_window.py/view_handlers.py:
    canvas.zoom_changed -> zoom_slider.set_zoom_from_factor() (Sync ohne
    Rueckkopplung), zoom_slider.zoom_changed -> canvas.set_zoom() (User
    bewegt den Slider)."""
    canvas.zoom_changed.connect(lambda factor: slider.set_zoom_from_factor(factor))
    slider.zoom_changed.connect(lambda percent: canvas.set_zoom(percent / 100.0))


def test_zoom_slider_range_follows_custom_cell_size_settings(qtbot):
    canvas = CrossStitchCanvas()
    qtbot.addWidget(canvas)
    slider = ZoomSlider()
    qtbot.addWidget(slider)
    _wire_like_main_window(canvas, slider)

    # Simuliert eine Nutzer-Einstellung wie in _apply_settings_from_dialog()
    # angewandt (Einstellungen -> Leinwand -> Min/Max/Standard-Zellgroesse),
    # bei der der gueltige Zoom-Bereich (50%-2500%) NICHT mit dem
    # Default-Bereich des Sliders (20%-300%) uebereinstimmt.
    canvas.MIN_CELL_SIZE = 2
    canvas.MAX_CELL_SIZE = 100
    canvas.DEFAULT_CELL_SIZE = 4
    canvas._cell_size = canvas.DEFAULT_CELL_SIZE

    min_percent = round(canvas.MIN_CELL_SIZE / canvas.DEFAULT_CELL_SIZE * 100)
    max_percent = round(canvas.MAX_CELL_SIZE / canvas.DEFAULT_CELL_SIZE * 100)
    slider.set_zoom_range(min_percent, max_percent)

    # Canvas zoomt auf sein neues, individuell konfiguriertes Maximum (z.B.
    # durch zoom_fit() bei einem winzigen Muster oder wiederholtes zoom_in()).
    canvas._set_cell_size(canvas.MAX_CELL_SIZE)

    assert canvas.get_zoom_percent() == 2500.0
    # Der Slider muss den ECHTEN Wert zeigen, nicht auf 300% geklemmt sein.
    assert slider.zoom == 2500
    assert slider._slider.maximum() == 2500


def test_set_zoom_range_reclamps_current_value_without_emitting(qtbot):
    """set_zoom_range() darf keine Rueckkopplung ausloesen (sonst wuerde
    eine reine Einstellungsaenderung nebenbei den Canvas-Zoom verstellen) --
    analog zu set_zoom_from_factor()."""
    slider = ZoomSlider()
    qtbot.addWidget(slider)
    slider.set_zoom(250)  # innerhalb des Default-Bereichs 20-300

    received = []
    slider.zoom_changed.connect(lambda v: received.append(v))

    # Bereich wird auf 20-100 verengt -- der aktuelle Wert 250 liegt jetzt
    # ausserhalb und muss geklemmt werden.
    slider.set_zoom_range(20, 100)

    assert slider.zoom == 100
    assert slider._slider.value() == 100
    assert received == []  # keine Rueckkopplung an den Canvas


def test_set_zoom_range_ignores_invalid_bounds(qtbot):
    """min >= max darf den Slider nicht kaputt machen (defensiv)."""
    slider = ZoomSlider()
    qtbot.addWidget(slider)
    slider.set_zoom(150)

    slider.set_zoom_range(100, 100)

    assert slider.zoom == 150
    assert slider._slider.minimum() == slider.MIN_ZOOM
    assert slider._slider.maximum() == slider.MAX_ZOOM
