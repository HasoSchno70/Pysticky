"""
Hilfs-Widgets fuer den Statistik-Dialog.

Enthaelt wiederverwendbare Widgets wie Farbvorschau-Delegates
und Statistik-Karten fuer die Muster-Statistiken.
"""

from __future__ import annotations

from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..styles import THEME


class ColorPreviewDelegate(QWidget):
    """Kleine Farbvorschau fuer Tabellen."""

    def __init__(self, color: QColor, parent=None) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedSize(20, 20)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(THEME.border_light), 1))
        painter.setBrush(QBrush(self._color))
        painter.drawRoundedRect(2, 2, 16, 16, 3, 3)


class StatCard(QFrame):
    """Statistik-Karte fuer Uebersicht."""

    def __init__(self, title: str, value: str, icon: str = "", parent=None) -> None:
        super().__init__(parent)
        self._setup_ui(title, value, icon)

    def _setup_ui(self, title: str, value: str, icon: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)

        # Icon + Titel
        header = QHBoxLayout()
        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet("font-size: 20px;")
            header.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)

        # Wert
        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(f"""
            color: {THEME.text_primary};
            font-size: 22px;
            font-weight: bold;
        """)
        layout.addWidget(self._value_label)

        self.setStyleSheet(f"""
            StatCard {{
                background: {THEME.bg_medium};
                border: 1px solid {THEME.border_dark};
                border-radius: 8px;
            }}
        """)

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)
