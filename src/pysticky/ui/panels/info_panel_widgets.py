"""
Hilfs-Widgets des Info-Panels: Statistik-Kacheln, Farblisten-Eintrag,
Sektions-Überschrift.

Aus info_panel.py ausgelagert — dort wohnt nur noch das Panel selbst.
Achtung: NICHT dasselbe wie widgets/statistics_widgets.StatCard (die
Variante des Statistik-Dialogs hat eine andere Signatur und Optik).
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import t
from ..styles import THEME


class StatCard(QFrame):
    """Statistik-Karte mit dunklem Gradient und farbigem Glow."""

    def __init__(self, icon: str, label: str, color: str = None, parent=None) -> None:
        super().__init__(parent)
        self._color = QColor(color or THEME.accent_primary)
        self._icon = icon
        self._label = label
        self._value = "0"
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setMinimumHeight(68)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        # Icon mit Gradient-Hintergrund
        icon_container = QFrame()
        icon_container.setFixedSize(44, 44)

        c1 = self._color.lighter(130).name()
        c2 = self._color.name()
        icon_container.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {c1}, stop:1 {c2});
                border-radius: 12px;
            }}
        """)
        icon_layout = QHBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        self.icon_label = QLabel(self._icon)
        self.icon_label.setStyleSheet(
            f"font-size: 20px; background: transparent; color: {THEME.text_primary};"
        )
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(self.icon_label)
        layout.addWidget(icon_container)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)

        self.lbl_label = QLabel(self._label)
        self.lbl_label.setStyleSheet(f"""
            font-size: 10px;
            color: {THEME.text_muted};
            background: transparent;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        """)
        text_layout.addWidget(self.lbl_label)

        self.lbl_value = QLabel(self._value)
        self.lbl_value.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 700;
            color: {THEME.text_primary};
            background: transparent;
        """)
        text_layout.addWidget(self.lbl_value)

        layout.addLayout(text_layout)
        layout.addStretch()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        base_color = QColor(THEME.bg_light)
        tinted = QColor(
            min(255, base_color.red() + self._color.red() // 12),
            min(255, base_color.green() + self._color.green() // 12),
            min(255, base_color.blue() + self._color.blue() // 12),
        )

        gradient.setColorAt(0, QColor(THEME.bg_lighter))
        gradient.setColorAt(0.5, tinted)
        gradient.setColorAt(1, QColor(THEME.bg_medium))

        path = QPainterPath()
        path.addRoundedRect(1, 1, rect.width() - 2, rect.height() - 2, 14, 14)

        painter.fillPath(path, gradient)

        # Oberer Highlight
        highlight = QLinearGradient(0, 0, 0, 20)
        highlight.setColorAt(0, QColor(255, 255, 255, 15))
        highlight.setColorAt(1, QColor(255, 255, 255, 0))

        highlight_path = QPainterPath()
        highlight_path.addRoundedRect(2, 2, rect.width() - 4, 18, 12, 12)
        painter.fillPath(highlight_path, highlight)

        # Rahmen mit Farbakzent
        border_color = QColor(self._color)
        border_color.setAlpha(60)
        painter.setPen(QPen(border_color, 1.5))
        painter.drawPath(path)

        # Linker Glow-Streifen
        glow_gradient = QLinearGradient(0, 0, 8, 0)
        glow_gradient.setColorAt(
            0, QColor(self._color.red(), self._color.green(), self._color.blue(), 180)
        )
        glow_gradient.setColorAt(
            1, QColor(self._color.red(), self._color.green(), self._color.blue(), 0)
        )

        glow_path = QPainterPath()
        glow_path.addRoundedRect(0, 8, 6, rect.height() - 16, 3, 3)
        painter.fillPath(glow_path, glow_gradient)

        super().paintEvent(event)

    def _apply_theme(self) -> None:
        """Re-applies styles for theme switching."""
        self.lbl_label.setStyleSheet(f"""
            font-size: 10px;
            color: {THEME.text_muted};
            background: transparent;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        """)
        self.lbl_value.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 700;
            color: {THEME.text_primary};
            background: transparent;
        """)
        self.icon_label.setStyleSheet(
            f"font-size: 20px; background: transparent; color: {THEME.text_primary};"
        )
        self.update()

    def set_value(self, value: str) -> None:
        self._value = value
        self.lbl_value.setText(value)

    def set_label(self, label: str) -> None:
        """Ändert das Label der Karte zur Laufzeit (z.B. für Modus-Wechsel)."""
        self._label = label
        self.lbl_label.setText(label)

    def set_icon(self, icon: str) -> None:
        """Ändert das Icon zur Laufzeit (Modus-Wechsel: ✦ -> 💎)."""
        self._icon = icon
        self.icon_label.setText(icon)


class _ColorListItem(QFrame):
    """Eine Zeile in der kompakten Farbübersicht.

    Layout: [Farbe-Quadrat] Symbol Nr Name ··· Stiche Verbrauch
    Klickbar — emittiert `clicked(index)` beim LeftButton-Press.
    """

    clicked = Signal(int)

    def __init__(
        self,
        index: int,
        entry,
        fabric_count: int,
        calc_thread_fn,
        parent=None,
        mode: str = "stitch",
    ) -> None:
        super().__init__(parent)
        self._index = index
        self._entry = entry
        self._fabric_count = fabric_count
        self._calc_thread = calc_thread_fn
        self._selected = False
        self._hovered = False
        # Modus beeinflusst Layout: im Diamond-Modus entfällt die Symbol-
        # Spalte und der "Stiche"-Suffix wird zu "Drills".
        self._mode = mode
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(26)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 8, 2)
        layout.setSpacing(6)

        thread = self._entry.thread
        skip = self._entry.skip_stitching

        # Farbe-Quadrat. Alle internen QLabels mit parent=self konstruieren,
        # sonst flackern sie beim Color-List-Rebuild kurz als Top-Level-
        # Phantome auf (besonders das Symbol-Label mit setFixedWidth=14
        # war der haupt-Übeltäter beim Mode-Switch und Pattern-Load).
        self.swatch = QLabel(self)
        self.swatch.setFixedSize(16, 16)
        c = thread.color
        self.swatch.setStyleSheet(
            f"background: rgb({c.r},{c.g},{c.b}); "
            f"border: 1px solid {THEME.border_light}; border-radius: 3px;"
        )
        layout.addWidget(self.swatch)

        # Symbol (in Thread-Farbe wenn dunkel, sonst angepasst).
        # Im Diamond-Modus entfällt die Symbol-Spalte — Drills haben
        # keine eingebürgerte Symbol-Konvention, dort identifiziert man
        # über die Drill-Nummer.
        self.lbl_symbol = QLabel(self._entry.symbol, self)
        self.lbl_symbol.setFixedWidth(14)
        self.lbl_symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_symbol.setStyleSheet(
            f"color: {THEME.text_primary}; font-size: 11px; "
            f"font-weight: 700; background: transparent;"
        )
        self.lbl_symbol.setVisible(self._mode != "diamond")
        layout.addWidget(self.lbl_symbol)

        # Nummer (monospace für alignment). Im Diamond-Modus prominenter
        # (größer, in Vordergrund-Textfarbe), weil sie dort der Haupt-
        # Identifikator ist.
        num = thread.catalog_number or "—"
        self.lbl_num = QLabel(num, self)
        if self._mode == "diamond":
            self.lbl_num.setFixedWidth(48)
            self.lbl_num.setStyleSheet(
                f"color: {THEME.text_primary}; font-size: 11px; font-weight: 600; "
                f"font-family: 'Consolas', 'Courier New', monospace; background: transparent;"
            )
        else:
            self.lbl_num.setFixedWidth(34)
            self.lbl_num.setStyleSheet(
                f"color: {THEME.text_muted}; font-size: 10px; "
                f"font-family: 'Consolas', 'Courier New', monospace; background: transparent;"
            )
        layout.addWidget(self.lbl_num)

        # Name (truncated)
        name = thread.name
        if len(name) > 16:
            name = name[:15] + "…"
        self.lbl_name = QLabel(name, self)
        self.lbl_name.setStyleSheet(
            f"color: {THEME.text_secondary}; font-size: 11px; "
            f"font-weight: 500; background: transparent;"
            f"{' text-decoration: line-through;' if skip else ''}"
        )
        self.lbl_name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.lbl_name, 1)

        # Stiche + Verbrauch right-aligned
        if self._entry.stitch_count > 0 and not skip:
            usage = self._calc_thread(self._entry.stitch_count, self._fabric_count)
            stats_text = f"{self._entry.stitch_count}  ·  {usage}"
            stats_color = THEME.text_disabled
        elif skip:
            stats_text = t("übersp.")
            stats_color = THEME.warning
        else:
            stats_text = "0"
            stats_color = THEME.text_disabled
        self.lbl_stats = QLabel(stats_text, self)
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_stats.setStyleSheet(
            f"color: {stats_color}; font-size: 10px; background: transparent;"
        )
        layout.addWidget(self.lbl_stats)

        unit = t("Drills:") if self._mode == "diamond" else t("Stiche:")
        symbol_line = "" if self._mode == "diamond" else f"{t('Symbol:')} {self._entry.symbol}<br>"
        self.setToolTip(
            f"<b>{thread.name}</b><br>"
            f"{thread.manufacturer or '—'} {thread.catalog_number or ''}<br>"
            f"{symbol_line}"
            f"{unit} {self._entry.stitch_count}"
            + (f"<br><i>{t('Wird nicht gestickt')}</i>" if skip else "")
        )

    def set_selected(self, sel: bool) -> None:
        if self._selected != sel:
            self._selected = sel
            self.update()

    def update_entry(self, entry, fabric_count: int, calc_thread_fn) -> None:
        """Updatet die Werte ohne das Widget neu zu erstellen.

        Wird bei jedem Stitch-Placed aufgerufen — Recreation würde das
        Phantom-Top-Level-Window-Problem triggern.
        """
        self._entry = entry
        self._fabric_count = fabric_count
        self._calc_thread = calc_thread_fn

        # Symbol kann sich ändern wenn User es geändert hat
        self.lbl_symbol.setText(entry.symbol)

        # Stiche + Verbrauch neu berechnen
        skip = entry.skip_stitching
        if entry.stitch_count > 0 and not skip:
            usage = calc_thread_fn(entry.stitch_count, fabric_count)
            stats_text = f"{entry.stitch_count}  ·  {usage}"
            stats_color = THEME.text_disabled
        elif skip:
            stats_text = t("übersp.")
            stats_color = THEME.warning
        else:
            stats_text = "0"
            stats_color = THEME.text_disabled
        self.lbl_stats.setText(stats_text)
        self.lbl_stats.setStyleSheet(
            f"color: {stats_color}; font-size: 10px; background: transparent;"
        )

        # Tooltip aktualisieren
        thread = entry.thread
        self.setToolTip(
            f"<b>{thread.name}</b><br>"
            f"{thread.manufacturer or '—'} {thread.catalog_number or ''}<br>"
            f"{t('Symbol:')} {entry.symbol}<br>"
            f"{t('Stiche:')} {entry.stitch_count}"
            + ("<br><i>Wird nicht gestickt</i>" if skip else "")
        )
        self.update()

    def paintEvent(self, event) -> None:
        # Eigener Hintergrund — Stylesheet auf Custom-Klassen ist in Qt
        # nicht zuverläßig; paintEvent gibt deterministische Kontrolle.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(0, 0, -1, -1)
        if self._selected:
            painter.setBrush(QColor(THEME.bg_lighter))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 4, 4)
            # Linker Akzent-Streifen
            accent = QColor(THEME.accent_primary)
            painter.setBrush(accent)
            painter.drawRect(rect.left(), rect.top() + 2, 3, rect.height() - 4)
        elif self._hovered:
            painter.setBrush(QColor(THEME.bg_light))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 4, 4)
        super().paintEvent(event)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._index)


class SectionHeader(QWidget):
    """Sektion-Header mit dezenter Linie."""

    def __init__(self, icon: str, title: str, color: str = None, parent=None) -> None:
        super().__init__(parent)
        self._color = color or THEME.accent_primary

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 12, 4, 6)
        layout.setSpacing(8)

        self._icon_label = QLabel(icon)
        self._icon_label.setStyleSheet(f"font-size: 14px; color: {self._color};")
        layout.addWidget(self._icon_label)

        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 700;
            color: {self._color};
            letter-spacing: 1.5px;
        """)
        layout.addWidget(self._title_label)

        layout.addStretch()

    def set_title(self, title: str) -> None:
        """Ändert den Sektion-Titel zur Laufzeit (z.B. für Modus-Wechsel)."""
        self._title_label.setText(title)

    def set_icon(self, icon: str) -> None:
        """Ändert das Section-Icon zur Laufzeit."""
        self._icon_label.setText(icon)
