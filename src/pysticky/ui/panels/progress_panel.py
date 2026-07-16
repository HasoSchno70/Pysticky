"""
Fortschritts-Panel - Zeigt den Stickfortschritt an.

Zeigt den Gesamtfortschritt und den Fortschritt pro Farbe.
Ermöglicht das Markieren ganzer Farben als erledigt und
das Zurücksetzen des gesamten Fortschritts.
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...core import Pattern
from ...core.i18n import t
from ..styles import THEME


class ProgressPanel(QWidget):
    """Panel als Stick-Companion: Sticken-Modus-Toggle, Fortschritt, pro-Farbe."""

    # Signals
    mark_color_completed = Signal(int)  # color_index
    reset_progress = Signal()
    toggle_stitch_mode_requested = Signal(bool)  # User klickt den Sticken-Modus-Toggle

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pattern: Pattern | None = None
        self._color_widgets: list[QWidget] = []
        # Debounce-Timer: bei schnellen Updates (Drag im Sticken-Modus) wird
        # nur die LETZTE Änderung in 80ms tatsächlich gerendert. Verhindert
        # das "flackernde Fenster"-Problem (vorher: bei jedem Mausevent wurden
        # alle Color-Rows neu erzeugt, frische QFrames flashten als
        # Top-Level-Windows auf).
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(80)
        self._update_timer.timeout.connect(self._do_update_progress)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # === Sticken-Modus Toggle (gross + auffällig) ===
        self.btn_stitch_mode = QPushButton("✓  " + t("Sticken-Modus starten"))
        self.btn_stitch_mode.setCheckable(True)
        self.btn_stitch_mode.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stitch_mode.setMinimumHeight(44)
        self.btn_stitch_mode.setToolTip(
            t("Konzentrierter Modus zum Sticken: Klick auf Zelle = abhaken.\nTastenkürzel: Ctrl+M")
        )
        self.btn_stitch_mode.toggled.connect(self.toggle_stitch_mode_requested.emit)
        self._apply_stitch_mode_btn_style(False)
        layout.addWidget(self.btn_stitch_mode)

        # === Header ===
        self._header = QLabel(t("FORTSCHRITT"))
        self._header.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 700;
            color: {THEME.text_muted};
            letter-spacing: 2px;
            padding-top: 4px;
        """)
        layout.addWidget(self._header)

        # === Gesamt-Fortschrittsbalken ===
        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 1000)  # 0.1% Auflösung
        self.overall_progress.setTextVisible(True)
        self.overall_progress.setFormat("%p%")
        self.overall_progress.setMinimumHeight(28)
        self.overall_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {THEME.bg_light};
                border: 1px solid {THEME.border_medium};
                border-radius: 6px;
                text-align: center;
                color: {THEME.text_primary};
                font-weight: 700;
                font-size: 13px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {THEME.success}, stop:1 {THEME.accent_primary});
                border-radius: 5px;
            }}
        """)
        layout.addWidget(self.overall_progress)

        # === Stich-Zähler ===
        self.lbl_counts = QLabel("0 / 0 " + t("Stiche"))
        self.lbl_counts.setStyleSheet(f"""
            font-size: 13px;
            font-weight: 600;
            color: {THEME.text_secondary};
            padding: 2px 0px;
        """)
        self.lbl_counts.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_counts)

        # === Trennlinie ===
        self._sep = QFrame()
        self._sep.setFrameShape(QFrame.Shape.HLine)
        self._sep.setStyleSheet(f"background-color: {THEME.border_medium};")
        self._sep.setMaximumHeight(1)
        layout.addWidget(self._sep)

        # === Pro-Farbe Header ===
        self._color_header = QLabel(t("PRO FARBE"))
        self._color_header.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 700;
            color: {THEME.text_muted};
            letter-spacing: 2px;
            padding-top: 4px;
        """)
        layout.addWidget(self._color_header)

        # === Scrollbarer Farb-Bereich ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)

        self._scroll_content = QWidget()
        self._per_color_layout = QVBoxLayout(self._scroll_content)
        self._per_color_layout.setContentsMargins(0, 0, 0, 0)
        self._per_color_layout.setSpacing(6)
        self._per_color_layout.addStretch()

        scroll.setWidget(self._scroll_content)
        layout.addWidget(scroll, 1)

        # === Zurücksetzen-Button ===
        self.btn_reset = QPushButton(t("Fortschritt zurücksetzen"))
        self.btn_reset.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME.bg_light};
                color: {THEME.error};
                border: 1px solid {THEME.border_medium};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {THEME.bg_lighter};
                border-color: {THEME.error};
            }}
        """)
        self.btn_reset.clicked.connect(self.reset_progress.emit)
        layout.addWidget(self.btn_reset)

        self.setMinimumWidth(240)
        self.setMaximumWidth(380)

    def _apply_theme(self) -> None:
        """Re-applies all stylesheets for theme switching."""
        self._header.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 700;
            color: {THEME.text_muted};
            letter-spacing: 2px;
            padding-bottom: 4px;
        """)
        self.overall_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {THEME.bg_light};
                border: 1px solid {THEME.border_medium};
                border-radius: 6px;
                text-align: center;
                color: {THEME.text_primary};
                font-weight: 700;
                font-size: 13px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {THEME.success}, stop:1 {THEME.accent_primary});
                border-radius: 5px;
            }}
        """)
        self.lbl_counts.setStyleSheet(f"""
            font-size: 13px;
            font-weight: 600;
            color: {THEME.text_secondary};
            padding: 2px 0px;
        """)
        self._sep.setStyleSheet(f"background-color: {THEME.border_medium};")
        self._color_header.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 700;
            color: {THEME.text_muted};
            letter-spacing: 2px;
            padding-top: 4px;
        """)
        self.btn_reset.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME.bg_light};
                color: {THEME.error};
                border: 1px solid {THEME.border_medium};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {THEME.bg_lighter};
                border-color: {THEME.error};
            }}
        """)
        # Re-render per-color rows
        if self._pattern:
            self.update_progress(self._pattern)

    def update_progress(self, pattern: Pattern) -> None:
        """Aktualisiert die Fortschrittsanzeige (debounced).

        Bei rapider Aufrufung (z.B. Mausdrag im Sticken-Modus) wird nur die
        letzte Änderung pro 80ms tatsächlich gerendert.
        """
        self._pattern = pattern
        # Sofortige (billige) Updates: nur Zähler + Balken — kein Widget-Rebuild.
        # Der teure Pro-Farben-Rebuild läuft debounced.
        stats = pattern.get_progress_statistics()
        percent = stats["progress_percent"]
        self.overall_progress.setValue(int(percent * 10))
        completed = stats["completed_stitches"]
        total = stats["total_stitches"]
        self.lbl_counts.setText(f"{completed:,} / {total:,} Stiche".replace(",", "."))
        # Pro-Farben-Rebuild verzögert anstossen
        if not self._update_timer.isActive():
            self._update_timer.start()

    def _do_update_progress(self) -> None:
        """Eigentliches Pro-Farben-Update — läuft via Debounce-Timer."""
        if not self._pattern:
            return
        stats = self._pattern.get_progress_statistics()
        self._update_per_color(stats["per_color"])

    def _update_per_color(self, per_color: list[dict]) -> None:
        """Aktualisiert die Pro-Farbe-Anzeige."""
        # Alte Widgets entfernen
        for widget in self._color_widgets:
            widget.setParent(None)
            widget.deleteLater()
        self._color_widgets.clear()

        # Stretch am Ende entfernen
        while self._per_color_layout.count() > 0:
            item = self._per_color_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Nur Farben mit Stichen anzeigen
        for color_data in per_color:
            if color_data["total"] == 0:
                continue

            widget = self._create_color_row(color_data)
            self._per_color_layout.addWidget(widget)
            self._color_widgets.append(widget)

        self._per_color_layout.addStretch()

    def _create_color_row(self, color_data: dict) -> QWidget:
        """Erstellt eine Zeile für eine Farbe.

        Wichtig: alle Sub-Widgets bekommen `row` als Parent, sonst flashen
        sie ggf. für einen Frame als Top-Level-Windows auf (Win-Qt-Quirk).
        """
        row = QFrame(self._scroll_content)
        row.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME.bg_medium};
                border: 1px solid {THEME.border_dark};
                border-radius: 6px;
                padding: 6px;
            }}
        """)

        layout = QVBoxLayout(row)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Obere Zeile: Farbfeld + Name + Prozent
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Farbfeld
        swatch = QFrame(row)
        swatch.setFixedSize(18, 18)
        hex_color = color_data["color_hex"]
        swatch.setStyleSheet(f"""
            QFrame {{
                background-color: {hex_color};
                border: 1px solid {THEME.border_light};
                border-radius: 3px;
            }}
        """)
        top_row.addWidget(swatch)

        # Symbol
        symbol_label = QLabel(color_data["symbol"], row)
        symbol_label.setStyleSheet(f"""
            font-size: 12px;
            color: {THEME.text_secondary};
            background: transparent;
            font-weight: 600;
        """)
        symbol_label.setFixedWidth(16)
        top_row.addWidget(symbol_label)

        # Name
        name_label = QLabel(color_data["thread_name"], row)
        name_label.setStyleSheet(f"""
            font-size: 11px;
            color: {THEME.text_primary};
            background: transparent;
        """)
        name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top_row.addWidget(name_label)

        # Prozent
        percent = color_data["percent"]
        percent_label = QLabel(f"{percent:.0f}%", row)
        percent_color = THEME.success if percent >= 100 else THEME.text_secondary
        percent_label.setStyleSheet(f"""
            font-size: 12px;
            font-weight: 700;
            color: {percent_color};
            background: transparent;
        """)
        top_row.addWidget(percent_label)

        layout.addLayout(top_row)

        # Fortschrittsbalken
        progress = QProgressBar(row)
        progress.setRange(0, 1000)
        progress.setValue(int(percent * 10))
        progress.setTextVisible(False)
        progress.setMaximumHeight(6)
        bar_color = THEME.success if percent >= 100 else THEME.accent_primary
        progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {THEME.bg_dark};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(progress)

        # Untere Zeile: Zähler + Button
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(4)

        count_label = QLabel(
            f"{color_data['completed']}/{color_data['total']}",
            row,
        )
        count_label.setStyleSheet(f"""
            font-size: 10px;
            color: {THEME.text_muted};
            background: transparent;
        """)
        bottom_row.addWidget(count_label)

        bottom_row.addStretch()

        # "Alle erledigt"-Button (nur wenn nicht schon 100%)
        if percent < 100:
            btn = QPushButton("✓ " + t("Alle erledigt"), row)
            btn.setToolTip(
                f"{t('Alle')} {color_data['total'] - color_data['completed']} {t('verbleibenden')} "
                f"{t('Stiche dieser Farbe als gestickt markieren.')}"
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            color_index = color_data["color_index"]
            btn.clicked.connect(
                lambda checked=False, ci=color_index: self.mark_color_completed.emit(ci)
            )
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {THEME.accent_primary};
                    color: {THEME.bg_dark};
                    border: 1px solid {THEME.accent_primary};
                    border-radius: 4px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background-color: {THEME.success};
                    border-color: {THEME.success};
                }}
                QPushButton:pressed {{
                    background-color: {THEME.bg_dark};
                    color: {THEME.accent_primary};
                }}
            """)
            btn.setMaximumHeight(24)
            bottom_row.addWidget(btn)

        layout.addLayout(bottom_row)

        return row

    def clear_progress(self) -> None:
        """Setzt die Anzeige zurück."""
        self.overall_progress.setValue(0)
        self.lbl_counts.setText("0 / 0 Stiche")
        for widget in self._color_widgets:
            widget.setParent(None)
            widget.deleteLater()
        self._color_widgets.clear()

    def set_stitch_mode_active(self, active: bool) -> None:
        """Synchronisiert den Toggle-Button mit dem MainWindow-State."""
        if self.btn_stitch_mode.isChecked() != active:
            self.btn_stitch_mode.blockSignals(True)
            self.btn_stitch_mode.setChecked(active)
            self.btn_stitch_mode.blockSignals(False)
        self._apply_stitch_mode_btn_style(active)

    def _apply_stitch_mode_btn_style(self, active: bool) -> None:
        """Toggle-Button-Look: prominent grün wenn an, neutral wenn aus."""
        if active:
            self.btn_stitch_mode.setText("◼  " + t("Sticken-Modus beenden"))
            self.btn_stitch_mode.setStyleSheet(f"""
                QPushButton {{
                    background: {THEME.success};
                    color: {THEME.bg_dark};
                    border: 2px solid {THEME.success};
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 700;
                    padding: 6px 12px;
                }}
                QPushButton:hover {{
                    background: {THEME.accent_primary};
                    border-color: {THEME.accent_primary};
                }}
            """)
        else:
            self.btn_stitch_mode.setText("✓  " + t("Sticken-Modus starten"))
            self.btn_stitch_mode.setStyleSheet(f"""
                QPushButton {{
                    background: {THEME.bg_medium};
                    color: {THEME.accent_primary};
                    border: 2px solid {THEME.accent_primary};
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 700;
                    padding: 6px 12px;
                }}
                QPushButton:hover {{
                    background: {THEME.accent_primary};
                    color: {THEME.bg_dark};
                }}
            """)
