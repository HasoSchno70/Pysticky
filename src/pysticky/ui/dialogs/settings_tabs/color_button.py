"""
Gemeinsame Widgets für Settings-Dialog.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QPushButton, QWidget

from ....core.i18n import t
from ...styles import THEME


class ColorButton(QPushButton):
    """Button zur Farbauswahl mit farbigem Quadrat."""

    color_changed = Signal(str)

    def __init__(self, color: str = "#ffffff", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedSize(100, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._pick_color)
        self._update_style()

    @property
    def color(self) -> str:
        return self._color

    @color.setter
    def color(self, value: str) -> None:
        self._color = value
        self._update_style()

    def _apply_theme(self) -> None:
        """Live-Theme-Wechsel: _update_style() liest THEME ohnehin live,
        einfach erneut aufrufen. SettingsDialog bleibt bei "Anwenden" offen,
        _restyle_widget_tree() findet dieses Widget ueber findChildren()
        automatisch -- ohne diese Methode blieben Grenzfarbe/Text-Farbe des
        Buttons (border_medium/text_secondary) nach einem Theme-Wechsel auf
        den alten Werten haengen, nur der Farbverlauf des eigentlichen
        Farbfeldes selbst ist THEME-unabhaengig."""
        self._update_style()

    def _update_style(self) -> None:
        """Aktualisiert das Button-Styling mit Farbquadrat."""
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self._color},
                    stop:0.35 {self._color},
                    stop:0.36 {THEME.bg_dark},
                    stop:1 {THEME.bg_dark});
                color: {THEME.text_secondary};
                border: 2px solid {THEME.border_medium};
                border-radius: 4px;
                padding: 2px 8px 2px 40px;
                text-align: right;
                font-size: 11px;
                font-family: monospace;
            }}
            QPushButton:hover {{
                border-color: {THEME.accent_primary};
            }}
        """)
        self.setText(self._color.upper())

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self, t("Farbe wählen"))
        if color.isValid():
            self._color = color.name()
            self._update_style()
            self.color_changed.emit(self._color)
