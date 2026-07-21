"""
Canvas-Container mit Linealen und Scrollbars.
"""

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QScrollBar,
    QStackedWidget,
    QWidget,
)

from ..canvas import OptimizedCrossStitchCanvas as CrossStitchCanvas
from ..styles import THEME
from .ruler import RulerCorner, RulerWidget
from .welcome_widget import WelcomeWidget


class CanvasContainer(QWidget):
    # Weiterleitungs-Signale aus dem Welcome-Widget — MainWindow connectet sie
    welcome_new_clicked = Signal()
    welcome_open_clicked = Signal()
    welcome_import_image_clicked = Signal()
    welcome_demo_clicked = Signal()
    welcome_open_recent = Signal(str)

    """
    Container für den Canvas mit Linealen und Scrollbars.

    Features:
    - Klickbare Lineale zum Navigieren
    - Ecke zum Zentrieren
    - Scrollbars für große Muster

    Layout:
    ┌────────┬─────────────────┐
    │ Corner │  Horizontal     │
    │   +    │     Ruler       │
    ├────────┼─────────────────┤
    │Vertical│                 │▲
    │ Ruler  │     Canvas      │█
    │        │                 │▼
    ├────────┼─────────────────┤
    │        │ ◄████████████►  │
    └────────┴─────────────────┘
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Ecke (oben links) - klickbar zum Zentrieren
        self._corner = RulerCorner()
        layout.addWidget(self._corner, 0, 0)

        # Horizontales Lineal (oben) - klickbar
        self._h_ruler = RulerWidget(Qt.Orientation.Horizontal)
        layout.addWidget(self._h_ruler, 0, 1)

        # Vertikales Lineal (links) - klickbar
        self._v_ruler = RulerWidget(Qt.Orientation.Vertical)
        layout.addWidget(self._v_ruler, 1, 0)

        # Canvas + Welcome-Widget gestapelt in der Mitte
        self._canvas = CrossStitchCanvas()
        self._welcome = WelcomeWidget()
        self._welcome.new_clicked.connect(self.welcome_new_clicked.emit)
        self._welcome.open_clicked.connect(self.welcome_open_clicked.emit)
        self._welcome.import_image_clicked.connect(self.welcome_import_image_clicked.emit)
        self._welcome.demo_clicked.connect(self.welcome_demo_clicked.emit)
        self._welcome.open_recent.connect(self.welcome_open_recent.emit)
        self._stack = QStackedWidget()
        self._stack.addWidget(self._canvas)  # Index 0
        self._stack.addWidget(self._welcome)  # Index 1
        layout.addWidget(self._stack, 1, 1)

        # Scrollbar Style
        scrollbar_style = f"""
            QScrollBar:vertical {{
                background: {THEME.bg_light};
                width: 14px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {THEME.border_light};
                border-radius: 5px;
                min-height: 30px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {THEME.accent_primary};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            QScrollBar:horizontal {{
                background: {THEME.bg_light};
                height: 14px;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background: {THEME.border_light};
                border-radius: 5px;
                min-width: 30px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {THEME.accent_primary};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: transparent;
            }}
        """

        # Vertikale Scrollbar (rechts)
        self._v_scrollbar = QScrollBar(Qt.Orientation.Vertical)
        self._v_scrollbar.setStyleSheet(scrollbar_style)
        layout.addWidget(self._v_scrollbar, 1, 2)

        # Horizontale Scrollbar (unten)
        self._h_scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        self._h_scrollbar.setStyleSheet(scrollbar_style)
        layout.addWidget(self._h_scrollbar, 2, 1)

        # Ecke unten rechts (für Scrollbar-Ecke)
        corner_bottom = QWidget()
        corner_bottom.setFixedSize(14, 14)
        corner_bottom.setStyleSheet(f"background: {THEME.bg_light};")
        layout.addWidget(corner_bottom, 2, 2)

        # Leere Ecke unten links
        corner_left = QWidget()
        corner_left.setFixedSize(RulerWidget.RULER_SIZE, 14)
        corner_left.setStyleSheet(f"background: {THEME.bg_light};")
        layout.addWidget(corner_left, 2, 0)

        # Ecken speichern für Theme-Wechsel
        self._corner_bottom = corner_bottom
        self._corner_left = corner_left

        # Stretch-Faktoren
        layout.setRowStretch(1, 1)
        layout.setColumnStretch(1, 1)

    def reapply_styles(self) -> None:
        """Setzt Scrollbar- und Ecken-Styles neu (Theme-Wechsel)."""
        scrollbar_style = f"""
            QScrollBar:vertical {{
                background: {THEME.bg_light}; width: 14px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {THEME.border_light};
                border-radius: 5px; min-height: 30px; margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {THEME.accent_primary};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            QScrollBar:horizontal {{
                background: {THEME.bg_light}; height: 14px; border: none;
            }}
            QScrollBar::handle:horizontal {{
                background: {THEME.border_light};
                border-radius: 5px; min-width: 30px; margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {THEME.accent_primary};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: transparent;
            }}
        """
        self._v_scrollbar.setStyleSheet(scrollbar_style)
        self._h_scrollbar.setStyleSheet(scrollbar_style)
        self._corner_bottom.setStyleSheet(f"background: {THEME.bg_light};")
        self._corner_left.setStyleSheet(f"background: {THEME.bg_light};")
        if hasattr(self._h_ruler, "update"):
            self._h_ruler.update()
        if hasattr(self._v_ruler, "update"):
            self._v_ruler.update()

    def _connect_signals(self) -> None:
        # Canvas-Signale
        self._canvas.zoom_changed.connect(self._on_zoom_changed)
        self._canvas.offset_changed.connect(self._on_offset_changed)
        self._canvas.position_changed.connect(self._on_canvas_position_changed)

        # Event-Filter für Canvas (um leaveEvent zu erkennen)
        self._canvas.installEventFilter(self)

        # Scrollbar-Signale
        self._h_scrollbar.valueChanged.connect(self._on_h_scroll)
        self._v_scrollbar.valueChanged.connect(self._on_v_scroll)

        # Lineal-Signale (Klick-Navigation)
        self._h_ruler.position_clicked.connect(self._on_h_ruler_clicked)
        self._v_ruler.position_clicked.connect(self._on_v_ruler_clicked)

        # Ecke (Zentrieren)
        self._corner.center_clicked.connect(self._on_center_clicked)

    def _on_zoom_changed(self, factor: float) -> None:
        self._update_rulers()
        self._update_scrollbars()

    def _on_offset_changed(self, offset_x: int, offset_y: int) -> None:
        self._update_rulers()
        self._update_scrollbars()

    def _on_canvas_position_changed(self, x: int, y: int) -> None:
        """Aktualisiert die Lineal-Marker bei Mausbewegung."""
        self._h_ruler.set_canvas_position(x)
        self._v_ruler.set_canvas_position(y)
        self._corner.set_canvas_position(x, y)

    def _on_h_scroll(self, value: int) -> None:
        self._canvas._offset_x = -value
        # offset_changed emitten wie die Ruler-Klick-Handler direkt darunter --
        # MainWindow haengt daran _update_minimap_viewport() (siehe
        # mw_signals_mixin.py). Ohne das Signal blieb die Minimap-Viewport-
        # Markierung beim Scrollbar-Ziehen an der alten Position stehen, bis
        # eine unabhaengige Aktion (Zoom, Pan per Maus/Pfeiltaste, Undo) sie
        # zufaellig mit-synchronisierte.
        self._canvas.offset_changed.emit(self._canvas._offset_x, self._canvas._offset_y)
        self._update_rulers()
        self._canvas.update()

    def _on_v_scroll(self, value: int) -> None:
        self._canvas._offset_y = -value
        self._canvas.offset_changed.emit(self._canvas._offset_x, self._canvas._offset_y)
        self._update_rulers()
        self._canvas.update()

    def _on_h_ruler_clicked(self, grid_x: int) -> None:
        """Navigiert horizontal zur geklickten Grid-Position."""
        if not self._canvas._pattern:
            return

        cell_size = self._canvas._cell_size
        canvas_center_x = self._canvas.width() // 2

        # Berechne neuen Offset so dass grid_x in der Mitte ist
        new_offset_x = canvas_center_x - (grid_x * cell_size + cell_size // 2)

        self._canvas._offset_x = new_offset_x
        self._canvas.offset_changed.emit(new_offset_x, self._canvas._offset_y)
        self._update_rulers()
        self._update_scrollbars()
        self._canvas.update()

    def _on_v_ruler_clicked(self, grid_y: int) -> None:
        """Navigiert vertikal zur geklickten Grid-Position."""
        if not self._canvas._pattern:
            return

        cell_size = self._canvas._cell_size
        canvas_center_y = self._canvas.height() // 2

        # Berechne neuen Offset so dass grid_y in der Mitte ist
        new_offset_y = canvas_center_y - (grid_y * cell_size + cell_size // 2)

        self._canvas._offset_y = new_offset_y
        self._canvas.offset_changed.emit(self._canvas._offset_x, new_offset_y)
        self._update_rulers()
        self._update_scrollbars()
        self._canvas.update()

    def _on_center_clicked(self) -> None:
        """Zentriert das Muster."""
        self._canvas._center_pattern()
        self._update_rulers()
        self._update_scrollbars()
        self._canvas.update()

    def _update_rulers(self) -> None:
        if not self._canvas._pattern:
            return

        pattern = self._canvas._pattern
        cell_size = self._canvas._cell_size
        offset_x = self._canvas._offset_x
        offset_y = self._canvas._offset_y

        self._h_ruler.set_parameters(offset_x, cell_size, pattern.width)
        self._v_ruler.set_parameters(offset_y, cell_size, pattern.height)

    def _update_scrollbars(self) -> None:
        if not self._canvas._pattern:
            return

        pattern = self._canvas._pattern
        cell_size = self._canvas._cell_size
        offset_x = self._canvas._offset_x
        offset_y = self._canvas._offset_y

        pattern_width = pattern.width * cell_size
        pattern_height = pattern.height * cell_size
        canvas_width = self._canvas.width()
        canvas_height = self._canvas.height()

        h_range = max(0, pattern_width - canvas_width + 100)
        self._h_scrollbar.setRange(-50, h_range)
        self._h_scrollbar.setPageStep(canvas_width)
        self._h_scrollbar.blockSignals(True)
        self._h_scrollbar.setValue(-offset_x)
        self._h_scrollbar.blockSignals(False)

        v_range = max(0, pattern_height - canvas_height + 100)
        self._v_scrollbar.setRange(-50, v_range)
        self._v_scrollbar.setPageStep(canvas_height)
        self._v_scrollbar.blockSignals(True)
        self._v_scrollbar.setValue(-offset_y)
        self._v_scrollbar.blockSignals(False)

    @property
    def canvas(self) -> CrossStitchCanvas:
        return self._canvas

    def show_welcome(self, show: bool, recent_files: list[str] | None = None) -> None:
        """Schaltet zwischen Canvas (False) und Welcome-Screen (True)."""
        if show:
            if recent_files is not None:
                self._welcome.set_recent_files(recent_files)
            self._stack.setCurrentIndex(1)
            # Lineale und Scrollbars sind im Welcome-Modus überflüssig
            self._h_ruler.setVisible(False)
            self._v_ruler.setVisible(False)
            self._h_scrollbar.setVisible(False)
            self._v_scrollbar.setVisible(False)
            self._corner.setVisible(False)
            self._corner_bottom.setVisible(False)
            self._corner_left.setVisible(False)
        else:
            self._stack.setCurrentIndex(0)
            self._h_ruler.setVisible(True)
            self._v_ruler.setVisible(True)
            self._h_scrollbar.setVisible(True)
            self._v_scrollbar.setVisible(True)
            self._corner.setVisible(True)
            self._corner_bottom.setVisible(True)
            self._corner_left.setVisible(True)

    def set_welcome_recent_files(self, files: list[str]) -> None:
        """Aktualisiert nur die Recent-Liste im Welcome-Widget."""
        self._welcome.set_recent_files(files)

    def set_pattern(self, pattern) -> None:
        self._canvas.set_pattern(pattern)
        self._update_rulers()
        self._update_scrollbars()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_rulers()
        self._update_scrollbars()

    def eventFilter(self, obj, event: QEvent) -> bool:
        """Event-Filter für Canvas-Events."""
        if obj == self._canvas:
            if event.type() == QEvent.Type.Leave:
                # Maus hat Canvas verlassen - Lineal-Marker löschen
                self._h_ruler.clear_canvas_position()
                self._v_ruler.clear_canvas_position()
                self._corner.clear_canvas_position()
        return super().eventFilter(obj, event)
