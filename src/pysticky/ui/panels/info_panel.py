"""
Info-Panel zur Anzeige von Muster-Informationen - Dunkles Design mit Gradient-Kacheln.
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
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...core import Pattern
from ...core.constants import COMMON_FABRIC_COUNTS
from ...core.i18n import t
from ..styles import THEME, Styles


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
            f"background: rgb({c.r},{c.g},{c.b}); border: 1px solid {THEME.border_light}; border-radius: 3px;"
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
            f"color: {THEME.text_primary}; font-size: 11px; font-weight: 700; background: transparent;"
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


class InfoPanel(QWidget):
    """Panel zur Anzeige von Muster-Statistiken - Dunkles Design."""

    fabric_count_changed = Signal(int)
    color_clicked = Signal(int)  # Farb-Index in der Pattern-Palette
    FABRIC_COUNTS = COMMON_FABRIC_COUNTS

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pattern: Pattern | None = None
        self._color_items: list[_ColorListItem] = []
        self._selected_color_index: int | None = None
        # Modus: "stitch" (Kreuzstich) oder "diamond" (Diamond Painting).
        # Beeinflusst Labels (Stiche/Drills, Stickzeit/Klebezeit, ...) und
        # Berechnungen (Zeit pro Einheit, Garnbedarf vs. Drill-Anzahl).
        self._mode: str = "stitch"
        self._setup_ui()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(THEME.bg_medium))
        gradient.setColorAt(0.5, QColor(THEME.bg_dark))
        gradient.setColorAt(1, QColor(THEME.bg_dark))
        painter.fillRect(self.rect(), gradient)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # === Stoff-Auswahl (im DP-Modus: Drill-Größe) ===
        self._section_fabric = SectionHeader("🧵", t("STOFFZÄHLUNG"), THEME.accent_primary)
        layout.addWidget(self._section_fabric)

        self.combo_fabric = QComboBox()
        self.combo_fabric.setStyleSheet(Styles.combo_box())
        for count in self.FABRIC_COUNTS:
            self.combo_fabric.addItem(f"{count} ct Aida", count)
        self.combo_fabric.setCurrentIndex(1)
        self.combo_fabric.currentIndexChanged.connect(self._on_fabric_changed)
        layout.addWidget(self.combo_fabric)

        layout.addSpacing(6)

        # === Statistik-Karten ===
        self.card_stitches = StatCard("✦", t("Stiche"), THEME.accent_primary)
        layout.addWidget(self.card_stitches)

        self.card_colors = StatCard("🎨", t("Farben"), THEME.accent_secondary)
        layout.addWidget(self.card_colors)

        self.card_size = StatCard("📐", t("Größe"), THEME.info)
        layout.addWidget(self.card_size)

        self.card_cm = StatCard("📏", t("Maße"), THEME.accent_purple)
        layout.addWidget(self.card_cm)

        self.card_layers = StatCard("📑", t("Ebenen"), THEME.error)
        layout.addWidget(self.card_layers)

        self.card_time = StatCard("⏱", t("Stickzeit"), "#40c8b0")
        layout.addWidget(self.card_time)

        self.card_thread = StatCard("🧵", t("Garnbedarf"), "#c878a8")
        layout.addWidget(self.card_thread)

        self.card_progress = StatCard("✅", t("Fortschritt"), "#40c870")
        layout.addWidget(self.card_progress)

        self.card_difficulty = StatCard("🎯", t("Schwierigkeit"), THEME.warning)
        self.card_difficulty.setToolTip(
            t("Heuristik aus Farbanzahl, Spezial-Stichen, Backstitches und Größe.")
        )
        layout.addWidget(self.card_difficulty)

        # === Quell-Info — eine kompakte Zeile, Detail im Tooltip ===
        # Vorher: 3 Zeilen + Padding (~80 px). Jetzt: 1 Zeile (~28 px).
        # Die volle Info erscheint als HTML-Tooltip beim Hover.
        self.source_frame = QFrame()
        self.source_frame.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_light};
                border: 1px solid {THEME.border_medium};
                border-left: 4px solid {THEME.accent_secondary};
                border-radius: 8px;
            }}
        """)
        source_layout = QHBoxLayout(self.source_frame)
        source_layout.setContentsMargins(10, 6, 10, 6)
        source_layout.setSpacing(8)

        source_icon = QLabel("🖼️")
        source_icon.setStyleSheet("font-size: 13px; background: transparent;")
        source_layout.addWidget(source_icon)

        self.lbl_source_file = QLabel("")
        self.lbl_source_file.setStyleSheet(
            f"font-size: 11px; color: {THEME.text_secondary}; background: transparent;"
        )
        # Eliding via Qt-FontMetrics: zu langer Name wird in der Mitte gekürzt
        self.lbl_source_file.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        source_layout.addWidget(self.lbl_source_file, 1)

        # Status-Indikator (Datei OK / fehlt) als kleines Badge rechts
        self.lbl_source_status = QLabel("")
        self.lbl_source_status.setStyleSheet("font-size: 10px; background: transparent;")
        source_layout.addWidget(self.lbl_source_status)

        # Legacy-Referenz für das Palette-Label (wird in update genutzt) —
        # versteckt, wir packen die Info in den Tooltip.
        self.lbl_source_palette = QLabel("")
        self.lbl_source_palette.setVisible(False)

        self.source_frame.setVisible(False)
        layout.addWidget(self.source_frame)

        # === Farbübersicht ===
        layout.addWidget(SectionHeader("📋", t("FARBÜBERSICHT"), THEME.info))

        self.colors_frame = QFrame()
        self.colors_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {THEME.bg_light}, stop:1 {THEME.bg_dark});
                border: 1px solid {THEME.border_medium};
                border-radius: 12px;
            }}
        """)
        colors_layout = QVBoxLayout(self.colors_frame)
        colors_layout.setContentsMargins(12, 12, 12, 12)
        colors_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(150)
        # Kein setMaximumHeight — Frame darf auf verfügbaren Platz wachsen
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            {Styles.scrollbar()}
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.colors_list_layout = QVBoxLayout(scroll_content)
        self.colors_list_layout.setContentsMargins(2, 2, 2, 2)
        self.colors_list_layout.setSpacing(1)
        # Stretch am Ende — Items werden vor diesem stretch eingefügt,
        # damit sie oben anliegen statt vertikal verteilt zu werden
        self.colors_list_layout.addStretch()

        self._scroll_content = scroll_content  # für _update_colors_list

        scroll.setWidget(scroll_content)
        colors_layout.addWidget(scroll)

        # stretch=1 sorgt dafür dass die Farbübersicht den restlichen Platz
        # bis zum Panel-Boden ausfüllt (statt von einem addStretch hochgedrückt
        # zu werden).
        layout.addWidget(self.colors_frame, 1)

        self.setMinimumWidth(250)
        self.setMaximumWidth(340)

    def _apply_theme(self) -> None:
        """Re-applies all stylesheets for theme switching."""
        self.combo_fabric.setStyleSheet(Styles.combo_box())
        self.source_frame.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_light};
                border: 1px solid {THEME.border_medium};
                border-left: 4px solid {THEME.accent_secondary};
                border-radius: 8px;
            }}
        """)
        # _update_source_info setzt die Datei-Label-Farbe je nach Status —
        # hier nur den Default für den noch-nicht-aktualisierten Fall.
        self.lbl_source_file.setStyleSheet(
            f"font-size: 11px; color: {THEME.text_secondary}; background: transparent;"
        )
        self.colors_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {THEME.bg_light}, stop:1 {THEME.bg_dark});
                border: 1px solid {THEME.border_medium};
                border-radius: 12px;
            }}
        """)
        # (lbl_colors_list existiert nicht mehr — Farbliste ist jetzt
        # eine Liste von _ColorListItem-Widgets, die sich selbst stylen)
        # Update StatCard labels
        for card in [
            self.card_stitches,
            self.card_colors,
            self.card_size,
            self.card_cm,
            self.card_layers,
            self.card_time,
            self.card_thread,
            self.card_progress,
            self.card_difficulty,
        ]:
            card._apply_theme()
        # Re-render color list with new theme colors
        if self._pattern:
            self._update_colors_list(self._pattern)
        self.update()

    def update_info(self, pattern: Pattern) -> None:
        self._pattern = pattern
        stats = pattern.get_statistics()

        # Zeige Stiche die gestickt werden (ohne übersprungene)
        stitches_to_do = stats["stitches_to_do"]
        if stats["skipped_stitches"] > 0:
            stitches_str = f"{stitches_to_do:,}".replace(",", ".")
            # Zeige übersprungene Stiche in Klammern
            self.card_stitches.set_value(f"{stitches_str} (+{stats['skipped_stitches']} überspr.)")
        else:
            stitches_str = f"{stats['total_stitches']:,}".replace(",", ".")
            self.card_stitches.set_value(stitches_str)

        # Farben: zeige auch übersprungene
        if stats["skipped_colors"] > 0:
            self.card_colors.set_value(
                f"{stats['used_colors']} / {stats['color_count']} ({stats['skipped_colors']} überspr.)"
            )
        else:
            self.card_colors.set_value(f"{stats['used_colors']} / {stats['color_count']}")

        self.card_size.set_value(f"{stats['width']} × {stats['height']}")
        self.card_cm.set_value(f"{stats['width_cm']:.1f} × {stats['height_cm']:.1f} cm")
        self.card_layers.set_value(f"{stats['layer_count']}")

        # Zeit nur für Stiche die gestickt werden
        time_str = self._calculate_stitch_time(stitches_to_do)
        self.card_time.set_value(time_str)

        thread_str = self._calculate_thread_usage(pattern)
        self.card_thread.set_value(thread_str)

        # Fortschritt
        progress_stats = pattern.get_progress_statistics()
        percent = progress_stats["progress_percent"]
        completed = progress_stats["completed_stitches"]
        total = progress_stats["total_stitches"]
        if total > 0:
            self.card_progress.set_value(f"{percent:.1f}% ({completed}/{total})")
        else:
            self.card_progress.set_value("0%")

        # Schwierigkeit (mit Score-Tooltip)
        from ...core.difficulty import compute_difficulty

        diff = compute_difficulty(pattern)
        self.card_difficulty.set_value(diff["level"])
        f = diff["factors"]
        d = diff["details"]
        self.card_difficulty.setToolTip(
            f"{t('Score')} {diff['score']}/12  —  "
            f"{t('Farben')} {f['colors']}/3, {t('Größe')} {f['size']}/3, "
            f"{t('Sonderstiche')} {f['special']}/3, {t('Backstitches')} {f['backstitches']}/3\n"
            f"({d['used_colors']} {t('Farben')}, {d['stitches_to_do']:,} {t('Stiche')}, "
            f"{d['special_ratio'] * 100:.1f}% {t('Sonder')}, {d['backstitches']} {t('Linien')})"
        )

        self._update_source_info(pattern)
        self._update_colors_list(pattern)

    def _calculate_stitch_time(self, stitches_to_do: int) -> str:
        """Berechnet die Arbeitszeit (Sticken oder Diamond Painting).

        Modus-abhängig:
        - Sticken: ~20s pro Kreuzstich (3 Stiche/min, mit Fadenwechsel)
        - Diamond: ~3s pro Drill (20 Drills/min, Hand-Tool-Tempo)
        """
        if stitches_to_do == 0:
            return "0 " + t("Min")

        seconds_per_unit = 3.0 if self._mode == "diamond" else 20.0
        total_seconds = stitches_to_do * seconds_per_unit
        total_minutes = total_seconds / 60
        hours = int(total_minutes // 60)
        minutes = int(total_minutes % 60)

        if hours >= 100:
            return f"~{hours} {t('Std')}"
        elif hours > 0:
            return f"~{hours}h {minutes}m"
        elif minutes > 0:
            return f"~{minutes} {t('Min')}"
        else:
            return "< 1 " + t("Min")

    def _calculate_thread_usage(self, pattern: Pattern) -> str:
        """Berechnet Garn-/Drill-Bedarf.

        Modus-abhängig:
        - Sticken: Garn-Bedarf in Metern (5 cm Garn pro Stich bei 14ct).
        - Diamond: Drill-Gesamtanzahl (alle DP-Drills + Reserve 10%).
        """
        total_stitches = sum(e.stitch_count for e in pattern.color_entries if not e.skip_stitching)

        if total_stitches == 0:
            return "0"

        if self._mode == "diamond":
            # 10% Reserve für verlorene/abgesprungene Drills
            total_drills = int(total_stitches * 1.10)
            return f"~{total_drills:,}".replace(",", ".") + " " + t("Drills")

        base_cm = 5.0 * (14 / pattern.fabric_count)
        total_cm = total_stitches * base_cm
        total_m = total_cm / 100
        total_m *= 1.15  # 15% Sicherheitszuschlag

        if total_m >= 100:
            return f"~{total_m:.0f} m"
        elif total_m >= 10:
            return f"~{total_m:.1f} m"
        else:
            return f"~{total_m:.2f} m"

    def _calculate_thread_per_color(self, stitch_count: int, fabric_count: int) -> str:
        if stitch_count == 0:
            return ""

        base_cm = 5.0 * (14 / fabric_count)
        total_cm = stitch_count * base_cm * 1.15
        total_m = total_cm / 100

        if total_m >= 10:
            return f"{total_m:.1f}m"
        elif total_m >= 1:
            return f"{total_m:.1f}m"
        else:
            return f"{total_cm:.0f}cm"

    def _update_source_info(self, pattern: Pattern) -> None:
        from pathlib import Path

        if not pattern.source_image_path:
            self.source_frame.setVisible(False)
            return

        self.source_frame.setVisible(True)
        source_path = Path(pattern.source_image_path)
        filename = source_path.name
        exists = source_path.exists()
        palette = pattern.source_palette_name or "—"

        # Eliding für den Dateinamen — bei langen Namen Mitte kürzen
        from PySide6.QtGui import QFontMetrics

        fm = QFontMetrics(self.lbl_source_file.font())
        elided = fm.elidedText(filename, Qt.TextElideMode.ElideMiddle, 200)
        self.lbl_source_file.setText(elided)
        self.lbl_source_file.setStyleSheet(
            f"font-size: 11px; "
            f"color: {THEME.text_secondary if exists else THEME.error}; "
            f"background: transparent;"
        )

        # Status-Badge: ✓ wenn Datei vorhanden, ⚠ wenn fehlt
        if exists:
            self.lbl_source_status.setText("✓")
            self.lbl_source_status.setStyleSheet(
                f"font-size: 11px; color: {THEME.accent_primary}; "
                f"font-weight: 700; background: transparent;"
            )
        else:
            self.lbl_source_status.setText("⚠")
            self.lbl_source_status.setStyleSheet(
                f"font-size: 12px; color: {THEME.warning}; "
                f"font-weight: 700; background: transparent;"
            )

        # Voller Tooltip mit Details
        status_line = (
            "✓ " + t("Datei vorhanden")
            if exists
            else f"<span style='color:#f87171'>⚠ {t('Datei nicht gefunden')}</span>"
        )
        self.source_frame.setToolTip(
            f"<b>{t('Importiert von:')}</b><br>"
            f"<code>{pattern.source_image_path}</code><br>"
            f"{status_line}<br>"
            f"<b>{t('Palette:')}</b> {palette}"
        )

    def _update_colors_list(self, pattern: Pattern) -> None:
        """Baut die kompakte Farbliste auf — incremental wenn möglich.

        WICHTIG: Bei jedem Stitch-Placed wird update_info() gerufen → diese
        Methode auch. Wenn wir hier alle Items neu erstellen, blinkt jedes
        Widget kurz top-level auf (Default-Title 'PySticky' im Window-Manager
        sichtbar als Phantom-Fenster). Deshalb: incremental updaten wenn die
        Farb-Anzahl + Identität gleich bleibt; nur bei echter Strukturänderung
        komplett neu bauen.
        """
        entries = pattern.color_entries

        # Schnell-Pfad: gleiche Anzahl Items wie Farben + alle sind ColorListItems
        # UND alle haben den aktuellen Modus (sonst müssen Symbol-Spalten
        # neu gerendert werden -> Rebuild nötig).
        same_structure = (
            len(self._color_items) == len(entries)
            and all(isinstance(it, _ColorListItem) for it in self._color_items)
            and all(getattr(it, "_mode", "stitch") == self._mode for it in self._color_items)
        )

        if same_structure and entries:
            # Nur Werte aktualisieren — keine Widget-Erzeugung, kein Phantom
            for i, (item, entry) in enumerate(zip(self._color_items, entries)):
                if isinstance(item, _ColorListItem):
                    item.update_entry(
                        entry,
                        pattern.fabric_count,
                        self._calculate_thread_per_color,
                    )
            return

        # Strukturänderung (Farbe hinzu/weg, Pattern-Wechsel): komplett neu.
        # Hier wird nur ausgeführt wenn sich die Farb-Anzahl wirklich ändert,
        # nicht bei normalen Stitch-Placeds.
        #
        # WICHTIG: setUpdatesEnabled(False) auf den Scroll-Content wrappen,
        # damit Qt während des Rebuilds keine frisch-konstruierten
        # ColorListItems als Top-Level-Fenster flickert. Das war die
        # Quelle des "leeres Fenster poppt kurz auf"-Phantoms.
        scroll_content = self._scroll_content
        scroll_content.setUpdatesEnabled(False)
        try:
            for item in self._color_items:
                # WICHTIG: kein setParent(None) — das macht das Widget top-level
                # und triggert das Phantom-Window. Stattdessen hide + remove + delete.
                self.colors_list_layout.removeWidget(item)
                item.hide()
                item.deleteLater()
            self._color_items.clear()

            if not entries:
                placeholder = QLabel(t("Keine Farben"))
                placeholder.setStyleSheet(
                    f"color: {THEME.text_disabled}; font-style: italic; padding: 8px; background: transparent;"
                )
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.colors_list_layout.insertWidget(0, placeholder)
                self._color_items.append(placeholder)
                return

            insert_pos = self.colors_list_layout.count() - 1  # vor stretch
            for i, entry in enumerate(entries):
                item = _ColorListItem(
                    index=i,
                    entry=entry,
                    fabric_count=pattern.fabric_count,
                    calc_thread_fn=self._calculate_thread_per_color,
                    parent=self._scroll_content,
                    mode=self._mode,
                )
                item.clicked.connect(self.color_clicked.emit)
                if i == self._selected_color_index:
                    item.set_selected(True)
                self.colors_list_layout.insertWidget(insert_pos, item)
                insert_pos += 1
                self._color_items.append(item)
        finally:
            scroll_content.setUpdatesEnabled(True)

    def set_selected_color(self, index: int) -> None:
        """Markiert die aktive Farbe in der Übersicht (synchron mit ColorBar)
        und scrollt sie sichtbar."""
        self._selected_color_index = index
        target_item = None
        for i, item in enumerate(self._color_items):
            if isinstance(item, _ColorListItem):
                is_target = i == index
                item.set_selected(is_target)
                if is_target:
                    target_item = item
        # Scroll-Area-Parent finden und Item sichtbar scrollen
        if target_item is not None:
            scroll = target_item.parentWidget()
            while scroll is not None and not isinstance(scroll, QScrollArea):
                scroll = scroll.parentWidget()
            if scroll is not None:
                scroll.ensureWidgetVisible(target_item, 0, 30)

    def set_mode(self, mode: str) -> None:
        """Schaltet das Panel zwischen Kreuzstich- und Diamond-Painting-Modus.

        Ändert Labels (Stiche/Drills, Stickzeit/Klebezeit, Stoff/Drill-Raster),
        Combobox-Inhalte (Aida-Counts vs. Drill-Größen) und die zugrunde-
        liegenden Zeit-/Verbrauchs-Berechnungen.

        Args:
            mode: "stitch" oder "diamond". Unbekannte Werte werden ignoriert.
        """
        if mode not in ("stitch", "diamond"):
            return
        if mode == self._mode:
            # Bereits im richtigen Modus — keine UI-Aktion nötig (vermeidet
            # Flackern beim wiederholten _apply_pattern_mode-Call).
            return
        self._mode = mode

        is_dp = mode == "diamond"

        # Section-Header
        if is_dp:
            self._section_fabric.set_icon("💎")
            self._section_fabric.set_title(t("DRILL-RASTER"))
        else:
            self._section_fabric.set_icon("🧵")
            self._section_fabric.set_title(t("STOFFZÄHLUNG"))

        # Stat-Cards: Icons + Labels umstellen
        if is_dp:
            self.card_stitches.set_icon("💎")
            self.card_stitches.set_label(t("Drills"))
            self.card_time.set_label(t("Klebezeit"))
            self.card_thread.set_icon("📦")
            self.card_thread.set_label(t("Drill-Bedarf"))
            # Fortschritt im DP-Modus weg — kein klassischer
            # "Stich-abhaken"-Workflow vorhanden.
            self.card_progress.setVisible(False)
        else:
            self.card_stitches.set_icon("✦")
            self.card_stitches.set_label(t("Stiche"))
            self.card_time.set_label(t("Stickzeit"))
            self.card_thread.set_icon("🧵")
            self.card_thread.set_label(t("Garnbedarf"))
            self.card_progress.setVisible(True)

        # Fabric-Combo neu befüllen — die Inhalte sind modus-spezifisch.
        # Im DP-Modus: Drill-Größen (Standard 2.5mm Square, plus Round-Drill-
        # und seltener Mini-Drill-Raster). Im Stitch-Modus: Aida-Counts.
        self.combo_fabric.blockSignals(True)
        self.combo_fabric.clear()
        if is_dp:
            # Drill-Pitch-Werte als Aida-equivalente Zählung ablegen, damit
            # die existierende Garn-Verbrauchs-Logik durchläuft ohne Spezial-
            # Behandlung. Äquivalenz: 2.5mm-Drill ≈ 10ct, 2.8mm ≈ 9ct.
            self.combo_fabric.addItem(t("2.5 mm Square (Standard)"), 10)
            self.combo_fabric.addItem(t("2.8 mm Round"), 9)
            self.combo_fabric.addItem(t("3.0 mm Round"), 8)
        else:
            for count in self.FABRIC_COUNTS:
                self.combo_fabric.addItem(f"{count} ct Aida", count)
        # Auf passenden Default-Index gehen (im DP-Mode: erstes Item).
        if self._pattern is not None:
            for i in range(self.combo_fabric.count()):
                if self.combo_fabric.itemData(i) == self._pattern.fabric_count:
                    self.combo_fabric.setCurrentIndex(i)
                    break
            else:
                self.combo_fabric.setCurrentIndex(0)
        else:
            self.combo_fabric.setCurrentIndex(0)
        self.combo_fabric.blockSignals(False)

    def _on_fabric_changed(self, index: int) -> None:
        count = self.combo_fabric.currentData()
        if self._pattern:
            self._pattern.fabric_count = count
            self.update_info(self._pattern)
        self.fabric_count_changed.emit(count)

    def clear_info(self) -> None:
        self.card_stitches.set_value("0")
        self.card_colors.set_value("0")
        self.card_size.set_value("0 × 0")
        self.card_cm.set_value("0 × 0 cm")
        self.card_layers.set_value("0")
        self.card_time.set_value("0 Min")
        self.card_thread.set_value("0" if self._mode == "diamond" else "0 m")
        self.card_progress.set_value("0%")
        self.card_difficulty.set_value("-")
        self.card_difficulty.setToolTip("")
        self.source_frame.setVisible(False)
        # Farbitems entsorgen
        for item in self._color_items:
            item.setParent(None)
            item.deleteLater()
        self._color_items.clear()
        self._selected_color_index = None
