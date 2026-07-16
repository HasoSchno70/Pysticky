"""
Symbol-Editor Dialog.

Ermöglicht das Ändern des Symbols für eine Farbe im Muster.
"""

import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import t
from ..styles import THEME

if TYPE_CHECKING:
    from ...core import Pattern


def load_symbols() -> list[str]:
    """Lädt Symbole aus der symbols.txt Datei."""
    symbols_file = Path(__file__).parent.parent.parent / "resources" / "symbols.txt"
    if symbols_file.exists():
        with open(symbols_file, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    # Fallback
    return list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")


# Symbole aus Datei laden
AVAILABLE_SYMBOLS = load_symbols()


class SymbolButton(QFrame):
    """Button für ein einzelnes Symbol - mit eigenem Paint."""

    clicked = Signal()

    def __init__(self, symbol: str, parent=None) -> None:
        super().__init__(parent)
        self._symbol = symbol
        self._selected = False
        self._hovered = False

        self.setFixedSize(42, 42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool) -> None:
        self._selected = value
        self.update()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)

        # Hintergrund
        if self._selected:
            painter.setBrush(QColor(THEME.accent_primary))
            painter.setPen(QPen(QColor(THEME.accent_secondary), 2))
        elif self._hovered:
            painter.setBrush(QColor(THEME.bg_light))
            painter.setPen(QPen(QColor(THEME.accent_primary), 1))
        else:
            painter.setBrush(QColor(THEME.bg_medium))
            painter.setPen(QPen(QColor(THEME.border_dark), 1))

        painter.drawRoundedRect(rect, 6, 6)

        # Symbol zeichnen
        if self._selected:
            painter.setPen(QColor(255, 255, 255))
        else:
            painter.setPen(QColor(THEME.text_primary))

        # Font für Symbole
        font = QFont("Segoe UI Symbol", 18)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._symbol)


class ColorPreview(QFrame):
    """Vorschau der Farbe mit Symbol."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._color = QColor(200, 200, 200)
        self._symbol = "●"
        self.setFixedSize(90, 90)

    def set_color(self, color: QColor) -> None:
        self._color = color
        self.update()

    def set_symbol(self, symbol: str) -> None:
        self._symbol = symbol
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Rahmen
        painter.setPen(QPen(QColor(THEME.border_light), 2))
        painter.setBrush(self._color)
        painter.drawRoundedRect(2, 2, 86, 86, 8, 8)

        # Symbol - Kontrastfarbe wählen
        if self._color.lightness() > 128:
            painter.setPen(QColor(0, 0, 0))
        else:
            painter.setPen(QColor(255, 255, 255))

        font = QFont("Segoe UI Symbol", 36)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._symbol)


class SymbolEditorDialog(QDialog):
    """Dialog zum Bearbeiten des Symbols einer Farbe."""

    symbol_changed = Signal(int, str)  # color_index, new_symbol

    def __init__(self, pattern: "Pattern", color_index: int, parent=None) -> None:
        super().__init__(parent)
        self._pattern = pattern
        self._color_index = color_index
        self._entry = pattern.color_entries[color_index]
        self._selected_symbol = self._entry.symbol
        self._symbol_buttons: list[SymbolButton] = []

        self.setWindowTitle(f"Symbol bearbeiten - {self._entry.thread.name}")
        self.setMinimumSize(580, 520)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header mit Farbinfo
        header = QHBoxLayout()
        header.setSpacing(15)

        # Farbvorschau
        self._preview = ColorPreview()
        color = self._entry.thread.color
        self._preview.set_color(QColor(color.r, color.g, color.b))
        self._preview.set_symbol(self._selected_symbol)
        header.addWidget(self._preview)

        # Farbinfo
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)

        name_label = QLabel(f"<b>{self._entry.thread.name}</b>")
        name_label.setStyleSheet(f"color: {THEME.text_primary}; font-size: 14px;")
        info_layout.addWidget(name_label)

        if self._entry.thread.manufacturer:
            mfr_label = QLabel(
                f"{self._entry.thread.manufacturer} - {self._entry.thread.catalog_number or ''}"
            )
            mfr_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
            info_layout.addWidget(mfr_label)

        stitch_label = QLabel(f"{self._entry.stitch_count} Stiche")
        stitch_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        info_layout.addWidget(stitch_label)

        current_label = QLabel(
            f"Aktuelles Symbol: <span style='font-size: 20px;'>{self._entry.symbol}</span>"
        )
        current_label.setStyleSheet(
            f"color: {THEME.accent_primary}; font-size: 12px; margin-top: 8px;"
        )
        info_layout.addWidget(current_label)

        info_layout.addStretch()
        header.addLayout(info_layout, 1)

        layout.addLayout(header)

        # Eigenes Symbol eingeben
        custom_group = QGroupBox(t("Eigenes Symbol"))
        custom_layout = QHBoxLayout(custom_group)

        self._custom_input = QLineEdit()
        self._custom_input.setMaxLength(1)
        self._custom_input.setPlaceholderText("?")
        self._custom_input.setFixedWidth(50)
        self._custom_input.setFixedHeight(40)
        self._custom_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._custom_input.textChanged.connect(self._on_custom_symbol)
        custom_layout.addWidget(self._custom_input)

        hint_label = QLabel(t("Beliebiges Zeichen eingeben"))
        hint_label.setStyleSheet(f"color: {THEME.text_muted}; font-size: 10px;")
        custom_layout.addWidget(hint_label)

        custom_layout.addStretch()
        layout.addWidget(custom_group)

        # Symbol-Auswahl
        symbols_group = QGroupBox(t("Symbol auswählen"))
        symbols_layout = QVBoxLayout(symbols_group)

        # Suchfeld (Substring auf Zeichen, Unicode-Name oder Codepoint)
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(t("🔍 Suche: Zeichen, Name oder U+25CF / 25CF"))
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._on_search_changed)
        symbols_layout.addWidget(self._search_input)

        self._empty_label = QLabel(t("Keine Treffer."))
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {THEME.text_muted}; font-style: italic; padding: 8px;"
        )
        self._empty_label.setVisible(False)
        symbols_layout.addWidget(self._empty_label)

        # Scroll-Bereich für Symbole
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(220)

        # Container für die Reihen — V-Box mit Stretch unten, damit gefilterte
        # Restmenge oben klebt statt sich vertikal zu verteilen.
        symbols_widget = QWidget()
        symbols_widget.setStyleSheet("background: transparent;")
        self._rows_container = QVBoxLayout(symbols_widget)
        self._rows_container.setSpacing(5)
        self._rows_container.setContentsMargins(8, 8, 8, 8)
        self._rows_container.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._grid_cols = 12
        self._row_layouts: list[QHBoxLayout] = []
        for symbol in AVAILABLE_SYMBOLS:
            btn = SymbolButton(symbol)
            btn.clicked.connect(lambda s=symbol: self._on_symbol_selected(s))
            if symbol == self._selected_symbol:
                btn.selected = True
            self._symbol_buttons.append(btn)
        self._repack_grid(self._symbol_buttons)

        scroll.setWidget(symbols_widget)
        symbols_layout.addWidget(scroll)

        layout.addWidget(symbols_group, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)

        ok_btn = QPushButton(t("Übernehmen"))
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_accept)
        button_box.addButton(ok_btn, QDialogButtonBox.ButtonRole.AcceptRole)

        btn_layout.addWidget(button_box)

        layout.addLayout(btn_layout)

        # Spezifisches Symbol-Font für das Custom-Symbol-Feld — alles andere
        # übernimmt das globale Theme.
        self._custom_input.setStyleSheet(
            "QLineEdit { font-size: 20px; font-family: 'Segoe UI Symbol'; }"
        )

    def _repack_grid(self, buttons: list["SymbolButton"]) -> None:
        """Baut die Reihen neu auf: je 12 Buttons pro QHBoxLayout, oben-bündig."""
        # Bestehende Reihen-Layouts leeren und entfernen
        while self._rows_container.count() > 0:
            item = self._rows_container.takeAt(0)
            inner = item.layout() if item is not None else None
            if inner is not None:
                while inner.count() > 0:
                    sub = inner.takeAt(0)
                    w = sub.widget() if sub is not None else None
                    if w is not None:
                        w.setParent(None)
                inner.deleteLater()
        self._row_layouts.clear()

        for btn in self._symbol_buttons:
            btn.setVisible(False)

        cols = self._grid_cols
        for i, btn in enumerate(buttons):
            if i % cols == 0:
                row = QHBoxLayout()
                row.setSpacing(5)
                row.setAlignment(Qt.AlignmentFlag.AlignLeft)
                self._rows_container.addLayout(row)
                self._row_layouts.append(row)
            self._row_layouts[-1].addWidget(btn)
            btn.setVisible(True)

        # Letzte (unvollständige) Reihe nach links pushen
        if self._row_layouts:
            self._row_layouts[-1].addStretch(1)

    def _symbol_matches_query(self, symbol: str, query: str) -> bool:
        """Substring-Match auf Zeichen, Unicode-Name und Codepoint."""
        if not query:
            return True
        q = query.strip().lower()
        if not q:
            return True
        if q in symbol.lower():
            return True
        # Unicode-Name (z.B. "BLACK CIRCLE", "WHITE STAR")
        try:
            name = unicodedata.name(symbol, "")
        except (ValueError, TypeError):
            name = ""
        if name and q in name.lower():
            return True
        # Codepoint: "u+25cf", "25cf", oder dezimal
        if symbol:
            cp = ord(symbol[0])
            hex_form = f"{cp:04x}"
            if q.startswith("u+") and q[2:] == hex_form:
                return True
            if q == hex_form:
                return True
            if q.isdigit() and int(q) == cp:
                return True
        return False

    def _on_search_changed(self, text: str) -> None:
        """Filtert das Symbol-Grid nach Substring/Unicode-Name/Codepoint."""
        matches = [b for b in self._symbol_buttons if self._symbol_matches_query(b.symbol, text)]
        self._repack_grid(matches)
        self._empty_label.setVisible(not matches)

    def _on_symbol_selected(self, symbol: str) -> None:
        """Symbol wurde aus der Liste gewählt."""
        self._selected_symbol = symbol
        self._preview.set_symbol(symbol)
        self._custom_input.blockSignals(True)
        self._custom_input.clear()
        self._custom_input.blockSignals(False)

        # Button-Status aktualisieren
        for btn in self._symbol_buttons:
            btn.selected = btn.symbol == symbol

    def _on_custom_symbol(self, text: str) -> None:
        """Eigenes Symbol eingegeben."""
        if text:
            self._selected_symbol = text
            self._preview.set_symbol(text)

            # Alle Buttons deselektieren
            for btn in self._symbol_buttons:
                btn.selected = False

    def _on_accept(self) -> None:
        """Änderung übernehmen."""
        if self._selected_symbol != self._entry.symbol:
            # Symbol im Pattern ändern
            self._entry.symbol = self._selected_symbol
            self.symbol_changed.emit(self._color_index, self._selected_symbol)
        self.accept()

    @property
    def selected_symbol(self) -> str:
        return self._selected_symbol
