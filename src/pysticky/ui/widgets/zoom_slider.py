"""
Zoom-Slider Widget für die Statusleiste.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QWidget,
)

from ...core.constants import DEFAULT_ZOOM_PERCENT, MAX_ZOOM_PERCENT, MIN_ZOOM_PERCENT
from ...core.i18n import t
from ..styles import THEME


class ZoomSlider(QWidget):
    """Zoom-Slider für die Statusleiste."""

    zoom_changed = Signal(int)
    zoom_fit_requested = Signal()
    zoom_100_requested = Signal()

    MIN_ZOOM = MIN_ZOOM_PERCENT
    MAX_ZOOM = MAX_ZOOM_PERCENT
    DEFAULT_ZOOM = DEFAULT_ZOOM_PERCENT

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._zoom = self.DEFAULT_ZOOM
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(3)

        # Einpassen-Button
        self._fit_btn = QPushButton("⊡")
        self._fit_btn.setFixedSize(20, 18)
        self._fit_btn.setToolTip(t("Einpassen (Ctrl+0)"))
        self._fit_btn.clicked.connect(self.zoom_fit_requested.emit)
        layout.addWidget(self._fit_btn)

        # Minus-Button
        self._minus_btn = QPushButton("−")
        self._minus_btn.setFixedSize(20, 18)
        self._minus_btn.setToolTip(t("Verkleinern (Ctrl+-)"))
        self._minus_btn.clicked.connect(self._on_zoom_out)
        self._minus_btn.setAutoRepeat(True)
        self._minus_btn.setAutoRepeatInterval(100)
        layout.addWidget(self._minus_btn)

        # Slider
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(self.MIN_ZOOM, self.MAX_ZOOM)
        self._slider.setValue(self.DEFAULT_ZOOM)
        self._slider.setFixedWidth(80)
        self._slider.setFixedHeight(18)
        self._slider.setToolTip(t("Zoom-Level"))
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider)

        # Plus-Button
        self._plus_btn = QPushButton("+")
        self._plus_btn.setFixedSize(20, 18)
        self._plus_btn.setToolTip(t("Vergrößern (Ctrl++)"))
        self._plus_btn.clicked.connect(self._on_zoom_in)
        self._plus_btn.setAutoRepeat(True)
        self._plus_btn.setAutoRepeatInterval(100)
        layout.addWidget(self._plus_btn)

        # Prozent-Label
        self._label = QLabel("100%")
        self._label.setFixedWidth(50)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setToolTip(t("Klicken für 100%"))
        self._label.mousePressEvent = lambda e: self.zoom_100_requested.emit()
        layout.addWidget(self._label)

        self._apply_theme()

    def _apply_theme(self) -> None:
        """Aktualisiert alle Stylesheets fuer aktuellen Theme — sonst bleiben
        die Buttons im Light-Mode unleserlich (war frueher: color: white)."""
        btn_style = f"""
            QPushButton {{
                background: {THEME.bg_lighter};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_medium};
                border-radius: 3px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{
                background: {THEME.accent_primary};
                color: {THEME.bg_dark};
                border-color: {THEME.accent_primary};
            }}
            QPushButton:pressed {{
                background: {THEME.accent_primary};
                color: {THEME.bg_dark};
            }}
        """
        for btn in (self._fit_btn, self._minus_btn, self._plus_btn):
            btn.setStyleSheet(btn_style)

        self._slider.setStyleSheet(f"""
            QSlider {{ background: transparent; }}
            QSlider::groove:horizontal {{
                background: {THEME.border_medium};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {THEME.accent_primary};
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }}
            QSlider::sub-page:horizontal {{
                background: {THEME.accent_primary};
                border-radius: 2px;
            }}
        """)

        self._label.setStyleSheet(f"""
            QLabel {{
                color: {THEME.text_primary};
                font-size: 11px;
                font-weight: bold;
            }}
        """)

    def _on_slider_changed(self, value: int) -> None:
        if value != self._zoom:
            self._zoom = value
            self._update_label()
            self.zoom_changed.emit(value)

    def _on_zoom_in(self) -> None:
        step = self._get_step()
        new_zoom = min(self._zoom + step, self.MAX_ZOOM)
        self.set_zoom(new_zoom)

    def _on_zoom_out(self) -> None:
        step = self._get_step()
        new_zoom = max(self._zoom - step, self.MIN_ZOOM)
        self.set_zoom(new_zoom)

    def _get_step(self) -> int:
        if self._zoom < 50:
            return 5
        elif self._zoom < 100:
            return 10
        elif self._zoom < 200:
            return 20
        else:
            return 25

    def _update_label(self) -> None:
        self._label.setText(f"{self._zoom}%")

    def set_zoom(self, percent: int) -> None:
        percent = max(self.MIN_ZOOM, min(self.MAX_ZOOM, percent))
        if percent != self._zoom:
            self._zoom = percent
            self._slider.blockSignals(True)
            self._slider.setValue(percent)
            self._slider.blockSignals(False)
            self._update_label()
            self.zoom_changed.emit(percent)

    def set_zoom_from_factor(self, factor: float) -> None:
        percent = int(factor * 100)
        percent = max(self.MIN_ZOOM, min(self.MAX_ZOOM, percent))
        if percent != self._zoom:
            self._zoom = percent
            self._slider.blockSignals(True)
            self._slider.setValue(percent)
            self._slider.blockSignals(False)
            self._update_label()

    @property
    def zoom(self) -> int:
        return self._zoom
