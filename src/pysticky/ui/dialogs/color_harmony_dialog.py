"""
Farb-Harmonien Dialog.

Findet harmonische Farben basierend auf Farbtheorie und zeigt
passende Garne aus den verfügbaren Paletten an.
"""

import colorsys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.color_math import delta_e
from ...core.i18n import t
from ...core.palette import ThreadPalette, get_palette_manager
from ...core.thread import Thread
from ..styles import THEME, Styles

if TYPE_CHECKING:
    from ...core import Pattern


@dataclass
class HarmonyColor:
    """Eine harmonische Farbe mit passendem Garn."""

    name: str  # z.B. "Komplementär", "Analog Links"
    target_hsl: tuple[float, float, float]  # Ziel-Farbe in HSL
    target_rgb: tuple[int, int, int]  # Ziel-Farbe in RGB
    thread: Thread | None = None  # Passendes Garn
    distance: float = 0.0  # Farbabstand


class HarmonyType:
    """Harmonie-Typen mit ihren Winkel-Offsets im Farbkreis."""

    COMPLEMENTARY = "Komplementär"
    ANALOGOUS = "Analog"
    TRIADIC = "Triade"
    SPLIT_COMPLEMENTARY = "Split-Komplementär"
    TETRADIC = "Tetrade"

    DESCRIPTIONS = {
        COMPLEMENTARY: "Eine Farbe — direkt gegenüber im Farbkreis. Maximaler Kontrast.",
        ANALOGOUS: "Zwei Nachbarfarben (±30°). Sanfter, harmonischer Übergang.",
        TRIADIC: "Zwei Farben gleichmäßig verteilt (±120°). Lebhaft, ausgewogen.",
        SPLIT_COMPLEMENTARY: "Zwei Farben neben dem Komplementär (±150°). Spannung ohne Kollision.",
        TETRADIC: "Drei Farben im Rechteck (90°/180°/270°). Reichhaltiges Schema.",
    }

    @staticmethod
    def get_offsets(harmony_type: str) -> list[tuple[str, float]]:
        """Gibt die Winkel-Offsets für einen Harmonie-Typ zurück."""
        if harmony_type == HarmonyType.COMPLEMENTARY:
            return [("Komplementär", 180)]
        elif harmony_type == HarmonyType.ANALOGOUS:
            return [
                ("Analog −30°", -30),
                ("Analog +30°", 30),
            ]
        elif harmony_type == HarmonyType.TRIADIC:
            return [
                ("Triade +120°", 120),
                ("Triade −120°", -120),
            ]
        elif harmony_type == HarmonyType.SPLIT_COMPLEMENTARY:
            return [
                ("Split +150°", 150),
                ("Split −150°", -150),
            ]
        elif harmony_type == HarmonyType.TETRADIC:
            return [
                ("Tetrade +90°", 90),
                ("Tetrade +180°", 180),
                ("Tetrade +270°", 270),
            ]
        return []


def rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Konvertiert RGB (0-255) zu HSL (0-360, 0-1, 0-1)."""
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
    h, l, s = colorsys.rgb_to_hls(r_norm, g_norm, b_norm)
    return h * 360, s, l


def hsl_to_rgb(h: float, s: float, l: float) -> tuple[int, int, int]:
    """Konvertiert HSL (0-360, 0-1, 0-1) zu RGB (0-255)."""
    h_norm = (h % 360) / 360.0
    r, g, b = colorsys.hls_to_rgb(h_norm, l, s)
    return int(r * 255), int(g * 255), int(b * 255)


def color_distance(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    """Perzeptueller Farbabstand (CIE76 Delta-E in Lab)."""
    return delta_e(c1, c2)


def find_closest_thread(
    target_rgb: tuple[int, int, int], palette: ThreadPalette
) -> tuple[Thread | None, float]:
    """Findet das Garn mit der ähnlichsten Farbe."""
    best_thread = None
    best_distance = float("inf")

    for thread in palette.threads:
        thread_rgb = (thread.color.r, thread.color.g, thread.color.b)
        dist = color_distance(target_rgb, thread_rgb)
        if dist < best_distance:
            best_distance = dist
            best_thread = thread

    return best_thread, best_distance


class ColorSwatch(QFrame):
    """Klickbare Farb-Karte mit Harmonie-Info, Wunschfarbe vs. echtem Garn,
    Distanz-Indikator und prominentem Selected-State.

    Layout pro Karte (180×170):
        ┌─────────────────────┐
        │ Komplementär  +180° │  ← Harmonie-Name + Winkel
        ├─────┬───────────────┤
        │Soll │  Garn-Farbe   │  ← Wunsch (klein) | Garn (groß)
        │     │               │
        ├─────┴───────────────┤
        │ ▲ Anchor 215         │  ← Hersteller + Nr (fett)
        │   Emerald Green-LT   │  ← Name
        │   ●●●○ Sehr nah      │  ← Distanz-Indikator
        └─────────────────────┘
    Klick → toggelt Auswahl (ganzer Hintergrund grün, Haken oben rechts).
    """

    clicked = Signal(object)  # Thread

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._color = QColor(128, 128, 128)
        self._target_color = QColor(128, 128, 128)
        self._thread: Thread | None = None
        self._harmony_name = ""
        self._distance = 0.0
        self._selected = False
        self._hovered = False

        self.setFixedSize(180, 170)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    def set_data(
        self,
        harmony_name: str,
        target_rgb: tuple[int, int, int],
        thread: Thread | None,
        distance: float = 0.0,
    ) -> None:
        self._harmony_name = harmony_name
        self._target_color = QColor(*target_rgb)
        self._thread = thread
        self._distance = distance
        if thread:
            self._color = QColor(thread.color.r, thread.color.g, thread.color.b)
        else:
            self._color = self._target_color
        self.update()

    @property
    def thread(self) -> Thread | None:
        return self._thread

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
        if event.button() == Qt.MouseButton.LeftButton and self._thread:
            self._selected = not self._selected
            self.clicked.emit(self._thread)
            self.update()

    def _distance_label(self) -> tuple[str, str, int]:
        """Liefert (Symbol, Text, Punkte) für den Distanz-Indikator."""
        # CIE76 Delta-E statt RGB-Euklid (früher 25/60/120).
        d = self._distance
        if d < 5:
            return ("●●●●", "Perfekt", 4)
        if d < 10:
            return ("●●●○", "Sehr nah", 3)
        if d < 20:
            return ("●●○○", "Akzeptabel", 2)
        return ("●○○○", "Weit weg", 1)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)

        # Hintergrund + Rahmen
        if self._selected:
            # Selected: kräftiger Akzent-Hintergrund + dicker Border
            bg = QColor(THEME.accent_primary)
            bg.setAlpha(40)
            painter.setBrush(bg)
            painter.setPen(QPen(QColor(THEME.accent_primary), 3))
        elif self._hovered:
            painter.setBrush(QColor(THEME.bg_lighter))
            painter.setPen(QPen(QColor(THEME.accent_primary), 2))
        else:
            painter.setBrush(QColor(THEME.bg_medium))
            painter.setPen(QPen(QColor(THEME.border_medium), 1))
        painter.drawRoundedRect(rect, 10, 10)

        # === Header: Harmonie-Name ===
        header_h = 24
        header_rect = rect.adjusted(10, 6, -10, -rect.height() + 6 + header_h)
        painter.setPen(QColor(THEME.accent_primary if self._selected else THEME.text_secondary))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(
            header_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._harmony_name,
        )

        # === Farbflächen (Wunsch vs. Garn) ===
        colors_top = 32
        colors_h = 56
        gap = 4
        # Wunschfarbe (links, schmal — ca 1/3)
        target_w = (rect.width() - 20 - gap) // 3
        target_rect = rect.adjusted(
            10, colors_top, -rect.width() + 10 + target_w, -rect.height() + colors_top + colors_h
        )
        painter.setBrush(self._target_color)
        painter.setPen(QPen(QColor(THEME.border_dark), 1))
        painter.drawRoundedRect(target_rect, 5, 5)
        # "Soll"-Label oben links auf der Wunschfarbe
        painter.setPen(
            QColor(0, 0, 0, 140)
            if self._target_color.lightnessF() > 0.5
            else QColor(255, 255, 255, 200)
        )
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(
            target_rect.adjusted(4, 2, -4, -2),
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
            t("Wunsch"),
        )

        # Garn-Farbe (rechts, breit — ca 2/3)
        thread_rect = rect.adjusted(
            10 + target_w + gap, colors_top, -10, -rect.height() + colors_top + colors_h
        )
        painter.setBrush(self._color)
        painter.setPen(QPen(QColor(THEME.border_dark), 1))
        painter.drawRoundedRect(thread_rect, 5, 5)
        painter.setPen(
            QColor(0, 0, 0, 140) if self._color.lightnessF() > 0.5 else QColor(255, 255, 255, 200)
        )
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(
            thread_rect.adjusted(4, 2, -4, -2),
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
            t("Garn"),
        )

        # === Garn-Info ===
        info_y = colors_top + colors_h + 8
        if self._thread:
            # Hersteller + Nr (fett)
            mfr = (self._thread.manufacturer or "—")[:8]
            num = self._thread.catalog_number or "?"
            painter.setPen(QColor(THEME.text_primary))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(
                rect.adjusted(10, info_y, -10, 0),
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                f"{mfr} {num}",
            )

            # Name (eine Zeile, gekürzt)
            name = self._thread.name
            if len(name) > 24:
                name = name[:23] + "…"
            painter.setPen(QColor(THEME.text_secondary))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(
                rect.adjusted(10, info_y + 18, -10, 0),
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                name,
            )

            # Distanz-Indikator: Dots + Text
            dots, dlabel, _n = self._distance_label()
            # Punkte in Akzent-Farbe (Anzahl je nach Nähe)
            dist_color = QColor(THEME.accent_primary) if _n >= 3 else QColor(THEME.text_muted)
            painter.setPen(dist_color)
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(
                rect.adjusted(10, info_y + 36, -10, 0),
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                dots,
            )
            painter.setPen(QColor(THEME.text_muted))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(
                rect.adjusted(50, info_y + 38, -10, 0),
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                dlabel,
            )
        else:
            painter.setPen(QColor(THEME.text_disabled))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
            painter.drawText(
                rect.adjusted(10, info_y, -10, 0),
                Qt.AlignmentFlag.AlignTop,
                t("Kein passendes Garn"),
            )

        # === Auswahl-Indikator: groß und klar ===
        if self._selected:
            badge_size = 22
            bx = rect.right() - badge_size - 6
            by = rect.top() + 6
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(THEME.accent_primary))
            painter.drawEllipse(bx, by, badge_size, badge_size)
            # Weisser Haken in der Mitte
            painter.setPen(
                QPen(
                    QColor("white"),
                    2.5,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
            )
            painter.drawLine(bx + 6, by + 11, bx + 10, by + 16)
            painter.drawLine(bx + 10, by + 16, bx + 17, by + 7)
        elif self._hovered and self._thread:
            # Hover-Hint: kleines "+ Klick zum Auswählen" rechts oben
            painter.setPen(QColor(THEME.accent_primary))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(
                rect.adjusted(0, 6, -8, -rect.height() + 22),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
                t("+ wählen"),
            )


class SourceColorWidget(QFrame):
    """Anzeige der Ausgangsfarbe."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._color = QColor(128, 128, 128)
        self._thread: Thread | None = None
        self.setFixedSize(120, 80)

    def set_thread(self, thread: Thread) -> None:
        self._thread = thread
        self._color = QColor(thread.color.r, thread.color.g, thread.color.b)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)

        # Rahmen
        painter.setPen(QPen(QColor(THEME.border_light), 2))
        painter.setBrush(self._color)
        painter.drawRoundedRect(rect.adjusted(0, 0, 0, -25), 8, 8)

        # Info
        if self._thread:
            painter.setPen(QColor(THEME.text_primary))
            font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(
                rect.adjusted(0, rect.height() - 22, 0, 0),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                f"{self._thread.catalog_number or '?'}",
            )


class ColorHarmonyDialog(QDialog):
    """Dialog für Farb-Harmonien."""

    colors_selected = Signal(list)  # Liste von Threads

    def __init__(self, pattern: "Pattern", source_color_index: int, parent=None) -> None:
        super().__init__(parent)
        self._pattern = pattern
        self._source_index = source_color_index
        self._source_entry = pattern.color_entries[source_color_index]
        self._source_thread = self._source_entry.thread

        self._palette_manager = get_palette_manager()
        self._current_palette: ThreadPalette | None = None
        self._harmony_swatches: list[ColorSwatch] = []
        self._selected_threads: list[Thread] = []

        self.setWindowTitle(t("Farb-Harmonien"))
        self.setMinimumSize(780, 620)
        self.resize(820, 660)

        self._setup_ui()
        self._apply_styles()

        # Initiale Palette setzen (gleicher Hersteller oder DMC)
        self._select_initial_palette()
        self._update_harmonies()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 18, 20, 16)

        # === Einführungs-Text: erklärt was der Dialog tut ===
        intro = QLabel(
            t(
                "Diese Funktion schlägt Garne vor, die mit der gewählten Ausgangsfarbe "
                "nach <b>Farbtheorie</b> harmonieren. Wähle den Harmonie-Typ und klicke "
                "auf die Karten, die du in deine Palette übernehmen willst."
            )
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(
            f"color: {THEME.text_secondary}; font-size: 12px; "
            f"background: {THEME.bg_light}; border-left: 3px solid {THEME.accent_primary}; "
            f"border-radius: 6px; padding: 10px 12px;"
        )
        layout.addWidget(intro)

        # === Header: Ausgangsfarbe + Einstellungen ===
        header = QHBoxLayout()
        header.setSpacing(16)

        # Ausgangsfarbe
        source_group = QGroupBox(t("Ausgangsfarbe"))
        source_layout = QVBoxLayout(source_group)
        source_layout.setContentsMargins(14, 18, 14, 12)
        source_layout.setSpacing(8)

        self._source_widget = SourceColorWidget()
        self._source_widget.set_thread(self._source_thread)
        source_layout.addWidget(self._source_widget, 0, Qt.AlignmentFlag.AlignCenter)

        source_name = QLabel(f"<b>{self._source_thread.name}</b>")
        source_name.setStyleSheet(
            f"color: {THEME.text_primary}; font-size: 11px; background: transparent;"
        )
        source_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        source_name.setWordWrap(True)
        source_layout.addWidget(source_name)

        header.addWidget(source_group)

        # Einstellungen
        settings_group = QGroupBox(t("Einstellungen"))
        settings_layout = QGridLayout(settings_group)
        settings_layout.setContentsMargins(14, 18, 14, 12)
        settings_layout.setHorizontalSpacing(12)
        settings_layout.setVerticalSpacing(10)

        # Harmonie-Typ
        settings_layout.addWidget(QLabel(t("Harmonie-Typ:")), 0, 0)
        self._harmony_combo = QComboBox()
        self._harmony_combo.addItems(
            [
                HarmonyType.COMPLEMENTARY,
                HarmonyType.ANALOGOUS,
                HarmonyType.TRIADIC,
                HarmonyType.SPLIT_COMPLEMENTARY,
                HarmonyType.TETRADIC,
            ]
        )
        self._harmony_combo.currentTextChanged.connect(self._update_harmonies)
        settings_layout.addWidget(self._harmony_combo, 0, 1)

        # Beschreibung des aktuellen Harmonie-Typs
        self._harmony_desc = QLabel("")
        self._harmony_desc.setWordWrap(True)
        self._harmony_desc.setStyleSheet(
            f"color: {THEME.text_muted}; font-size: 10px; font-style: italic; "
            f"padding: 2px 0 4px 0; background: transparent;"
        )
        settings_layout.addWidget(self._harmony_desc, 1, 0, 1, 2)

        # Palette
        settings_layout.addWidget(QLabel(t("Garn-Palette:")), 2, 0)
        self._palette_combo = QComboBox()
        self._palette_combo.addItems(self._palette_manager.available_palettes)
        self._palette_combo.currentTextChanged.connect(self._on_palette_changed)
        settings_layout.addWidget(self._palette_combo, 2, 1)

        # Info
        self._info_label = QLabel("")
        self._info_label.setStyleSheet(
            f"color: {THEME.text_muted}; font-size: 10px; background: transparent;"
        )
        settings_layout.addWidget(self._info_label, 3, 0, 1, 2)

        header.addWidget(settings_group, 1)

        layout.addLayout(header)

        # === Harmonische Farben ===
        harmonies_group = QGroupBox(t("Vorschläge — Karte anklicken zum Auswählen"))
        harmonies_layout = QVBoxLayout(harmonies_group)
        harmonies_layout.setContentsMargins(12, 18, 12, 12)

        # Scroll-Bereich
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(220)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self._harmonies_widget = QWidget()
        self._harmonies_widget.setStyleSheet("background: transparent;")
        self._harmonies_layout = QHBoxLayout(self._harmonies_widget)
        self._harmonies_layout.setSpacing(12)
        self._harmonies_layout.setContentsMargins(6, 6, 6, 6)
        self._harmonies_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self._harmonies_widget)
        harmonies_layout.addWidget(scroll)

        layout.addWidget(harmonies_group, 1)

        # Buttons
        btn_layout = QHBoxLayout()

        self._select_all_btn = QPushButton(t("Alle auswählen"))
        self._select_all_btn.clicked.connect(self._select_all)
        btn_layout.addWidget(self._select_all_btn)

        self._select_none_btn = QPushButton(t("Keine auswählen"))
        self._select_none_btn.clicked.connect(self._select_none)
        btn_layout.addWidget(self._select_none_btn)

        btn_layout.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)

        self._add_btn = QPushButton("Hinzufügen (0)")
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self._on_add)
        # _apply_styles() setzt einen eigenen dialogweiten QPushButton-Stil,
        # der die globale :default-Hervorhebung überschreibt.
        self._add_btn.setStyleSheet(Styles.button_primary())
        button_box.addButton(self._add_btn, QDialogButtonBox.ButtonRole.AcceptRole)

        btn_layout.addWidget(button_box)

        layout.addLayout(btn_layout)

    def _apply_styles(self) -> None:
        # Identisches Akzent-Pillen-Pattern wie SettingsDialog — visuell konsistent.
        self.setStyleSheet(f"""
            QDialog {{
                background: {THEME.bg_dark};
            }}
            QGroupBox {{
                font-weight: 700;
                color: {THEME.accent_primary};
                background: {THEME.bg_light};
                border: 1px solid {THEME.border_medium};
                border-left: 3px solid {THEME.accent_primary};
                border-radius: 8px;
                margin-top: 14px;
                padding: 0;
                padding-top: 26px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 14px;
                top: 2px;
                padding: 2px 10px;
                background: {THEME.bg_lighter};
                border-radius: 4px;
                color: {THEME.accent_primary};
                font-size: 12px;
                letter-spacing: 0.5px;
            }}
            QLabel {{
                color: {THEME.text_secondary};
                background: transparent;
            }}
            QComboBox {{
                background: {THEME.bg_dark};
                color: {THEME.text_primary};
                border: 2px solid {THEME.border_medium};
                border-radius: 6px;
                padding: 6px 12px;
                min-height: 28px;
                min-width: 150px;
            }}
            QComboBox:hover {{
                border-color: {THEME.accent_primary};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {THEME.accent_primary};
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QPushButton {{
                background: {THEME.bg_light};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_medium};
                border-radius: 6px;
                padding: 8px 16px;
                min-height: 28px;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background: {THEME.bg_lighter};
                border-color: {THEME.accent_primary};
            }}
        """)

    def _select_initial_palette(self) -> None:
        """Wählt die initiale Palette basierend auf der Ausgangsfarbe."""
        # Versuche gleichen Hersteller
        mfr = self._source_thread.manufacturer
        if mfr and mfr in self._palette_manager.available_palettes:
            index = self._palette_combo.findText(mfr)
            if index >= 0:
                self._palette_combo.setCurrentIndex(index)
                return

        # Fallback: DMC
        dmc_index = self._palette_combo.findText("DMC")
        if dmc_index >= 0:
            self._palette_combo.setCurrentIndex(dmc_index)

    def _on_palette_changed(self, palette_name: str) -> None:
        """Palette wurde geändert."""
        self._current_palette = self._palette_manager.get_palette(palette_name)
        if self._current_palette:
            self._info_label.setText(f"{len(self._current_palette)} Farben verfügbar")
        self._update_harmonies()

    def _update_harmonies(self) -> None:
        """Berechnet und zeigt die harmonischen Farben."""
        # Alte Swatches entfernen — wichtig: erst aus dem Layout, dann
        # deleteLater. Sonst bleiben sie sichtbar (deleteLater hängt nur
        # die Lebensdauer ab, nicht das Parent-Verhältnis).
        for swatch in self._harmony_swatches:
            self._harmonies_layout.removeWidget(swatch)
            swatch.setParent(None)
            swatch.deleteLater()
        self._harmony_swatches.clear()
        self._selected_threads.clear()

        if not self._current_palette:
            self._current_palette = self._palette_manager.get_palette(
                self._palette_combo.currentText()
            )

        if not self._current_palette:
            return

        # Ausgangsfarbe in HSL
        src_rgb = (
            self._source_thread.color.r,
            self._source_thread.color.g,
            self._source_thread.color.b,
        )
        src_hsl = rgb_to_hsl(*src_rgb)

        # Harmonie-Offsets + Beschreibung
        harmony_type = self._harmony_combo.currentText()
        offsets = HarmonyType.get_offsets(harmony_type)
        # Beschreibung aktualisieren
        desc = HarmonyType.DESCRIPTIONS.get(harmony_type, "")
        self._harmony_desc.setText(desc)

        # Harmonische Farben berechnen
        for name, offset in offsets:
            # Neuen Farbton berechnen
            new_h = (src_hsl[0] + offset) % 360
            target_hsl = (new_h, src_hsl[1], src_hsl[2])
            target_rgb = hsl_to_rgb(*target_hsl)

            # Nächstes Garn finden
            thread, distance = find_closest_thread(target_rgb, self._current_palette)

            # Swatch erstellen
            swatch = ColorSwatch()
            swatch.set_data(name, target_rgb, thread, distance)
            swatch.clicked.connect(self._on_swatch_clicked)

            self._harmonies_layout.addWidget(swatch)
            self._harmony_swatches.append(swatch)

        self._update_add_button()

    def _on_swatch_clicked(self, thread: Thread) -> None:
        """Ein Swatch wurde geklickt."""
        if thread in self._selected_threads:
            self._selected_threads.remove(thread)
        else:
            self._selected_threads.append(thread)
        self._update_add_button()

    def _update_add_button(self) -> None:
        """Aktualisiert den Hinzufügen-Button."""
        count = len(self._selected_threads)
        self._add_btn.setText(f"Hinzufügen ({count})")
        self._add_btn.setEnabled(count > 0)

    def _select_all(self) -> None:
        """Wählt alle Farben aus."""
        self._selected_threads.clear()
        for swatch in self._harmony_swatches:
            if swatch.thread:
                swatch.selected = True
                self._selected_threads.append(swatch.thread)
        self._update_add_button()

    def _select_none(self) -> None:
        """Wählt keine Farben aus."""
        self._selected_threads.clear()
        for swatch in self._harmony_swatches:
            swatch.selected = False
        self._update_add_button()

    def _on_add(self) -> None:
        """Fügt die ausgewählten Farben hinzu."""
        if self._selected_threads:
            self.colors_selected.emit(self._selected_threads)
        self.accept()

    @property
    def selected_threads(self) -> list[Thread]:
        return self._selected_threads
