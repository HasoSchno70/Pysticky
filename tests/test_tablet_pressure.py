# -*- coding: utf-8 -*-
"""Tests fuer Tablet-Pressure-Brush im Pencil-Tool."""

import pytest


class FakeCanvas:
    """Minimaler Canvas-Stub fuer Tool-Tests."""

    def __init__(self, pressure: float = 0.0, in_use: bool = False) -> None:
        self._tablet_pressure = pressure
        self._tablet_in_use = in_use
        self.snap_to_grid = False
        self.snap_interval = 1

    def snap_position(self, x: int, y: int) -> tuple[int, int]:
        return (x, y)


def _make_ctx(pattern, canvas, gx: int, gy: int):
    from pysticky.ui.tools.base_tool import ToolContext

    return ToolContext(
        canvas=canvas,
        pattern=pattern,
        current_color_index=0,
        grid_x=gx,
        grid_y=gy,
        screen_x=gx,
        screen_y=gy,
        cell_size=20,
        offset_x=0,
        offset_y=0,
    )


@pytest.fixture(autouse=True)
def _reset_tablet_settings(qapp):
    """Setzt Tablet-Settings vor und nach jedem Test auf die Defaults zurueck.

    Braucht den qapp-Fixture, damit QSettings den Default-Pfad (basierend
    auf QApplication-Org/App-Name) korrekt aufloest.
    """
    from PySide6.QtCore import QSettings

    def _set_defaults():
        s = QSettings()
        s.setValue("tablet/pressure_enabled", True)
        s.setValue("tablet/max_brush_size", 5)
        s.sync()

    _set_defaults()
    yield
    _set_defaults()


@pytest.fixture
def qapp():
    """Stellt eine QCoreApplication mit Org/App-Name fuer QSettings bereit."""
    from PySide6.QtCore import QCoreApplication

    existing = QCoreApplication.instance()
    if existing is None:
        from PySide6.QtWidgets import QApplication

        app = QApplication([])
    else:
        app = existing
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    yield app


def test_pencil_with_no_tablet_yields_single_stitch(pattern_with_colors):
    """Ohne Tablet-Pressure: einzelner Stich wie bisher."""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    from pysticky.ui.tools.pencil_tool import PencilTool

    canvas = FakeCanvas(pressure=0.0, in_use=False)
    ctx = _make_ctx(pattern_with_colors, canvas, 5, 5)
    tool = PencilTool()

    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(0, 0),
        QPointF(0, 0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    changes = tool.on_mouse_press(ctx, press)
    assert changes == [(5, 5, 0)]


def test_pencil_with_pressure_creates_brush(pattern_with_colors):
    """Mit Pressure=1.0 entsteht ein groesserer Brush (kreisfoermig)."""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    from pysticky.ui.tools.pencil_tool import PencilTool

    canvas = FakeCanvas(pressure=1.0, in_use=True)
    ctx = _make_ctx(pattern_with_colors, canvas, 10, 10)
    tool = PencilTool()

    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(0, 0),
        QPointF(0, 0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    changes = tool.on_mouse_press(ctx, press)

    # max_size = 5 -> radius = round(1.0 * (5-1)) = 4
    # Kreis mit Radius 4 hat etwa pi*16 ~ 50 Pixel
    assert len(changes) > 1
    # Mittelpunkt (10, 10) muss enthalten sein
    coords = {(c[0], c[1]) for c in changes}
    assert (10, 10) in coords
    # Pixel ausserhalb des Radius (radius=4) sollten NICHT drin sein
    assert (10 + 5, 10) not in coords  # dx=5 > radius=4
    # Pixel am Rand des Radius
    assert (10 + 4, 10) in coords  # dx=4 == radius


def test_pencil_with_half_pressure_creates_smaller_brush(pattern_with_colors):
    """Pressure=0.5 ergibt halbe Brush-Groesse."""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    from pysticky.ui.tools.pencil_tool import PencilTool

    canvas = FakeCanvas(pressure=0.5, in_use=True)
    ctx = _make_ctx(pattern_with_colors, canvas, 10, 10)
    tool = PencilTool()

    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(0, 0),
        QPointF(0, 0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    full_count = len(tool.on_mouse_press(ctx, press))

    # Mit Pressure=1.0 mehr Zellen
    canvas_full = FakeCanvas(pressure=1.0, in_use=True)
    ctx_full = _make_ctx(pattern_with_colors, canvas_full, 10, 10)
    tool2 = PencilTool()
    full_pressure_count = len(tool2.on_mouse_press(ctx_full, press))

    assert full_count < full_pressure_count


def test_pencil_with_pressure_disabled_in_settings(pattern_with_colors):
    """Auch mit Tablet-Pressure: wenn Setting deaktiviert, einzelner Stich."""
    from PySide6.QtCore import QPointF, QSettings, Qt
    from PySide6.QtGui import QMouseEvent

    from pysticky.ui.tools.pencil_tool import PencilTool

    s = QSettings()
    s.setValue("tablet/pressure_enabled", False)
    s.sync()

    canvas = FakeCanvas(pressure=1.0, in_use=True)
    ctx = _make_ctx(pattern_with_colors, canvas, 10, 10)
    tool = PencilTool()

    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(0, 0),
        QPointF(0, 0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    changes = tool.on_mouse_press(ctx, press)
    # Setting aus -> einzelner Stich trotz Pressure
    assert changes == [(10, 10, 0)]

    # Reset fuer andere Tests
    s.setValue("tablet/pressure_enabled", True)


def test_pencil_with_max_brush_size_1_disables_brush(pattern_with_colors):
    """max_brush_size=1 ist die Aus-Position (immer einzelner Stich)."""
    from PySide6.QtCore import QPointF, QSettings, Qt
    from PySide6.QtGui import QMouseEvent

    from pysticky.ui.tools.pencil_tool import PencilTool

    s = QSettings()
    s.setValue("tablet/max_brush_size", 1)
    s.sync()

    canvas = FakeCanvas(pressure=1.0, in_use=True)
    ctx = _make_ctx(pattern_with_colors, canvas, 10, 10)
    tool = PencilTool()

    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(0, 0),
        QPointF(0, 0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    changes = tool.on_mouse_press(ctx, press)
    assert changes == [(10, 10, 0)]

    s.setValue("tablet/max_brush_size", 5)


def test_pencil_pressure_zero_means_single_stitch(pattern_with_colors):
    """Pressure=0 (Stift hebt ab) -> einzelner Stich."""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    from pysticky.ui.tools.pencil_tool import PencilTool

    canvas = FakeCanvas(pressure=0.0, in_use=True)
    ctx = _make_ctx(pattern_with_colors, canvas, 10, 10)
    tool = PencilTool()

    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(0, 0),
        QPointF(0, 0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    changes = tool.on_mouse_press(ctx, press)
    assert changes == [(10, 10, 0)]


def test_tablet_pressure_clamped_to_valid_range(qapp):
    """CrossStitchCanvas.tabletEvent() clamped Pressure auf [0, 1].

    Regression (Test-Qualitaets-Audit): die vorherige Version dieses Tests
    rief tabletEvent() nie auf -- sie rechnete `max(0.0, min(1.0, x))`
    direkt im Test nach und pruefte nur diese eigene Kopie der Formel. Eine
    echte Regression im Handler selbst (z.B. clamp()-Aufruf entfernt oder
    mit falschen Grenzen) waere nie aufgefallen. Jetzt wird der echte
    Handler mit einem QTabletEvent-Mock (spec=QTabletEvent besteht den
    isinstance-Check, den Qt-typisierte Handler oft brauchen) aufgerufen."""
    from unittest.mock import MagicMock

    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QTabletEvent

    from pysticky.core import Pattern
    from pysticky.ui.canvas import CrossStitchCanvas

    canvas = CrossStitchCanvas()
    canvas.set_pattern(Pattern(name="Test", width=5, height=5))

    too_high = MagicMock(spec=QTabletEvent)
    too_high.pressure.return_value = 1.5  # ungueltig, ueber dem Maximum
    too_high.type.return_value = QEvent.Type.TabletMove
    canvas.tabletEvent(too_high)
    assert canvas._tablet_pressure == 1.0, "Regression: Pressure > 1.0 wurde nicht auf 1.0 geclampt"

    too_low = MagicMock(spec=QTabletEvent)
    too_low.pressure.return_value = -0.2  # ungueltig, unter dem Minimum
    too_low.type.return_value = QEvent.Type.TabletMove
    canvas.tabletEvent(too_low)
    assert canvas._tablet_pressure == 0.0, (
        "Regression: negative Pressure wurde nicht auf 0.0 geclampt"
    )
