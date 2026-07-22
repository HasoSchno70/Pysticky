"""
Rückstich-Optionen Panel.

Ermöglicht das Anpassen von Rückstich-Einstellungen:
- Liniendicke
- Linienart (durchgezogen, gestrichelt, gepunktet)
- Endstil (rund, eckig)
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import t
from ..styles import THEME


class BackstitchPreview(QFrame):
    """Vorschau eines Rückstichs."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._thickness = 2
        self._line_style = Qt.PenStyle.SolidLine
        self._cap_style = Qt.PenCapStyle.RoundCap
        self._color = QColor(THEME.accent_primary)

        self.setFixedHeight(60)
        self.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_medium};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
            }}
        """)

    def _apply_theme(self) -> None:
        self._color = QColor(THEME.accent_primary)
        self.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_medium};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
            }}
        """)
        self.update()

    def set_thickness(self, value: int) -> None:
        self._thickness = value
        self.update()

    def set_line_style(self, style: Qt.PenStyle) -> None:
        self._line_style = style
        self.update()

    def set_cap_style(self, style: Qt.PenCapStyle) -> None:
        self._cap_style = style
        self.update()

    def set_color(self, color: QColor) -> None:
        self._color = color
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Hintergrund-Raster andeuten
        painter.setPen(QPen(QColor(THEME.border_dark), 1))
        step = 20
        for x in range(0, self.width(), step):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), step):
            painter.drawLine(0, y, self.width(), y)

        # Rückstich zeichnen
        pen = QPen(self._color, self._thickness, self._line_style)
        pen.setCapStyle(self._cap_style)
        painter.setPen(pen)

        # Beispiel-Linie
        margin = 20
        painter.drawLine(margin, self.height() // 2, self.width() // 3, self.height() // 4)
        painter.drawLine(
            self.width() // 3, self.height() // 4, 2 * self.width() // 3, 3 * self.height() // 4
        )
        painter.drawLine(
            2 * self.width() // 3, 3 * self.height() // 4, self.width() - margin, self.height() // 2
        )


class BackstitchOptionsPanel(QWidget):
    """Panel für Rückstich-Optionen."""

    thickness_changed = Signal(int)
    line_style_changed = Signal(int)  # Qt.PenStyle value
    cap_style_changed = Signal(int)  # Qt.PenCapStyle value
    snap_enabled_changed = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._thickness = 2
        self._line_style = Qt.PenStyle.SolidLine
        self._cap_style = Qt.PenCapStyle.RoundCap
        self._snap_enabled = True

        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Vorschau
        self._preview_label = QLabel(t("Vorschau:"))
        self._preview_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        layout.addWidget(self._preview_label)

        self._preview = BackstitchPreview()
        layout.addWidget(self._preview)

        # Dicke
        thickness_layout = QHBoxLayout()
        thickness_layout.addWidget(QLabel(t("Dicke:")))

        self._thickness_slider = QSlider(Qt.Orientation.Horizontal)
        self._thickness_slider.setRange(1, 6)
        self._thickness_slider.setValue(self._thickness)
        self._thickness_slider.valueChanged.connect(self._on_thickness_changed)
        thickness_layout.addWidget(self._thickness_slider)

        self._thickness_label = QLabel(f"{self._thickness}px")
        self._thickness_label.setFixedWidth(35)
        thickness_layout.addWidget(self._thickness_label)

        layout.addLayout(thickness_layout)

        # Linienart
        style_layout = QHBoxLayout()
        style_layout.addWidget(QLabel(t("Linie:")))

        self._style_combo = QComboBox()
        self._style_combo.addItem(t("Durchgezogen"), Qt.PenStyle.SolidLine)
        self._style_combo.addItem(t("Gestrichelt"), Qt.PenStyle.DashLine)
        self._style_combo.addItem(t("Gepunktet"), Qt.PenStyle.DotLine)
        self._style_combo.addItem(t("Strich-Punkt"), Qt.PenStyle.DashDotLine)
        self._style_combo.currentIndexChanged.connect(self._on_style_changed)
        style_layout.addWidget(self._style_combo, 1)

        layout.addLayout(style_layout)

        # Endstil
        cap_layout = QHBoxLayout()
        cap_layout.addWidget(QLabel(t("Enden:")))

        self._cap_combo = QComboBox()
        self._cap_combo.addItem(t("Rund"), Qt.PenCapStyle.RoundCap)
        self._cap_combo.addItem(t("Eckig"), Qt.PenCapStyle.SquareCap)
        self._cap_combo.addItem(t("Flach"), Qt.PenCapStyle.FlatCap)
        self._cap_combo.currentIndexChanged.connect(self._on_cap_changed)
        cap_layout.addWidget(self._cap_combo, 1)

        layout.addLayout(cap_layout)

        # Snap-Option
        self._snap_check = QCheckBox(t("An Rasterpunkte einrasten"))
        self._snap_check.setChecked(self._snap_enabled)
        self._snap_check.toggled.connect(self._on_snap_changed)
        layout.addWidget(self._snap_check)

        layout.addStretch()

    def _apply_theme(self) -> None:
        """Re-applies styles for theme switching."""
        self._apply_styles()
        # Explizit gesetzte Widget-eigene Stylesheets gewinnen im Qt-CSS-
        # Kaskade gegen den blanket QWidget-QSS von _apply_styles() -- dieses
        # Label braucht daher ein eigenes Refresh (gleiche Bug-Klasse wie an
        # anderer Stelle im Panel-System schon mehrfach gefunden).
        self._preview_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        self._preview._apply_theme()

    def _apply_styles(self) -> None:
        self.setStyleSheet(f"""
            QWidget {{
                background: {THEME.bg_dark};
            }}
            QLabel {{
                color: {THEME.text_primary};
            }}
            QSlider::groove:horizontal {{
                background: {THEME.border_dark};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {THEME.accent_primary};
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::sub-page:horizontal {{
                background: {THEME.accent_primary};
                border-radius: 2px;
            }}
            QComboBox {{
                background: {THEME.bg_medium};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_dark};
                border-radius: 4px;
                padding: 5px;
            }}
            QComboBox:hover {{
                border-color: {THEME.accent_primary};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QCheckBox {{
                color: {THEME.text_primary};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid {THEME.border_dark};
                background: {THEME.bg_medium};
            }}
            QCheckBox::indicator:checked {{
                background: {THEME.accent_primary};
                border-color: {THEME.accent_primary};
            }}
        """)

    def _on_thickness_changed(self, value: int) -> None:
        self._thickness = value
        self._thickness_label.setText(f"{value}px")
        self._preview.set_thickness(value)
        self.thickness_changed.emit(value)

    def _on_style_changed(self, index: int) -> None:
        style = self._style_combo.itemData(index)
        self._line_style = style
        self._preview.set_line_style(style)
        # int(Qt.PenStyle.X) wirft in dieser PySide6-Version TypeError --
        # das Enum unterstuetzt keine direkte int()-Konvertierung, nur
        # .value. Dieser Bug war bisher unbemerkt, weil das Panel bis jetzt
        # ueberhaupt nirgends verdrahtet war (kein Aufrufer hat das Signal
        # je ausgeloest).
        self.line_style_changed.emit(style.value)

    def _on_cap_changed(self, index: int) -> None:
        cap = self._cap_combo.itemData(index)
        self._cap_style = cap
        self._preview.set_cap_style(cap)
        self.cap_style_changed.emit(cap.value)

    def _on_snap_changed(self, enabled: bool) -> None:
        self._snap_enabled = enabled
        self.snap_enabled_changed.emit(enabled)

    @property
    def thickness(self) -> int:
        return self._thickness

    @property
    def line_style(self) -> Qt.PenStyle:
        return self._line_style

    @property
    def cap_style(self) -> Qt.PenCapStyle:
        return self._cap_style

    @property
    def snap_enabled(self) -> bool:
        return self._snap_enabled
