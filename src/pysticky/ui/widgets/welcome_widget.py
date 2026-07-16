"""
Welcome-Widget — wird im Canvas-Bereich angezeigt wenn kein Muster geladen
oder das Default-Pattern noch unangetastet ist. Bietet Quick-Start-Aktionen.
"""

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import t
from ..styles import THEME


class _ActionTile(QFrame):
    """Eine grosse klickbare Kachel mit Icon, Titel, Beschreibung."""

    clicked = Signal()

    def __init__(self, emoji: str, title: str, subtitle: str, accent: str, parent=None) -> None:
        super().__init__(parent)
        self._emoji = emoji
        self._title = title
        self._subtitle = subtitle
        self._accent = accent
        self._hovered = False
        self.setFixedSize(220, 120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_accent(self, accent: str) -> None:
        """Aktualisiert die Akzentfarbe (z.B. nach einem Live-Themewechsel)."""
        self._accent = accent
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
        rect = self.rect().adjusted(1, 1, -1, -1)

        accent = QColor(self._accent)
        tint = QColor(accent)
        tint.setAlpha(60 if self._hovered else 25)
        bg = QColor(THEME.bg_medium)

        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, bg)
        # Tint mit Akzentfarbe — sehr dezent
        tinted = QColor(
            min(255, bg.red() + (accent.red() - bg.red()) * tint.alpha() // 255),
            min(255, bg.green() + (accent.green() - bg.green()) * tint.alpha() // 255),
            min(255, bg.blue() + (accent.blue() - bg.blue()) * tint.alpha() // 255),
        )
        gradient.setColorAt(1, tinted)
        painter.setBrush(QBrush(gradient))
        border_color = accent if self._hovered else QColor(THEME.border_medium)
        painter.setPen(QPen(border_color, 2 if self._hovered else 1))
        painter.drawRoundedRect(rect, 12, 12)

        # Akzent-Streifen links
        stripe = rect.adjusted(0, 12, -rect.width() + 5, -12)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        painter.drawRoundedRect(stripe, 2, 2)

        # Emoji oben-links
        painter.setPen(QColor(THEME.text_primary))
        font = QFont("Segoe UI Emoji", 28)
        painter.setFont(font)
        painter.drawText(
            rect.adjusted(20, 8, 0, 0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            self._emoji,
        )

        # Titel
        title_font = QFont("Segoe UI", 13, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(accent if self._hovered else QColor(THEME.text_primary))
        painter.drawText(rect.adjusted(20, 58, -10, -42), Qt.AlignmentFlag.AlignLeft, self._title)

        # Untertitel
        subtitle_font = QFont("Segoe UI", 9)
        painter.setFont(subtitle_font)
        painter.setPen(QColor(THEME.text_muted))
        painter.drawText(
            rect.adjusted(20, 82, -14, -8),
            Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
            self._subtitle,
        )


class WelcomeWidget(QWidget):
    """Welcome-Screen mit Quick-Start-Aktionen.

    Emittiert Signale für:
    - new_clicked  — neues leeres Muster
    - open_clicked — Datei-Öffnen-Dialog
    - import_image_clicked — Bild importieren
    - open_recent  — bestimmten Recent-Pfad öffnen (str)
    """

    new_clicked = Signal()
    open_clicked = Signal()
    import_image_clicked = Signal()
    demo_clicked = Signal()
    open_recent = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._recent_files: list[str] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 40, 40, 40)
        outer.setSpacing(20)
        outer.addStretch(1)

        # Header-Karte
        self._header_label = QLabel("PySticky")
        self._header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._header_label.setStyleSheet(
            f"font-size: 36px; font-weight: 700; color: {THEME.accent_primary}; "
            f"letter-spacing: 2px; background: transparent;"
        )
        outer.addWidget(self._header_label)

        self._subtitle_label = QLabel(t("Kreuzstich-Muster Editor"))
        self._subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle_label.setStyleSheet(
            f"font-size: 13px; color: {THEME.text_muted}; "
            f"letter-spacing: 3px; background: transparent;"
        )
        outer.addWidget(self._subtitle_label)

        outer.addSpacing(20)

        # Action-Kacheln in zwei Reihen (responsive: bei wenig Platz wrappen)
        tiles_row = QHBoxLayout()
        tiles_row.setSpacing(16)
        tiles_row.addStretch(1)

        self._new_tile = _ActionTile(
            "📄",
            t("Neues Muster"),
            t("Leinwand mit Standardgröße erstellen."),
            THEME.accent_primary,
        )
        self._new_tile.clicked.connect(self.new_clicked.emit)
        tiles_row.addWidget(self._new_tile)

        self._open_tile = _ActionTile(
            "📂",
            t("Datei öffnen"),
            t("Bestehendes .pxs-Muster laden."),
            THEME.accent_secondary,
        )
        self._open_tile.clicked.connect(self.open_clicked.emit)
        tiles_row.addWidget(self._open_tile)

        self._import_tile = _ActionTile(
            "🖼",
            t("Aus Bild"),
            t("Foto / Grafik in ein Muster umwandeln."),
            THEME.info,
        )
        self._import_tile.clicked.connect(self.import_image_clicked.emit)
        tiles_row.addWidget(self._import_tile)

        self._demo_tile = _ActionTile(
            "🎨",
            t("Demo-Muster"),
            t("Beispiel zum Ausprobieren — Herz mit Rahmen."),
            THEME.accent_purple,
        )
        self._demo_tile.clicked.connect(self.demo_clicked.emit)
        tiles_row.addWidget(self._demo_tile)

        tiles_row.addStretch(1)
        outer.addLayout(tiles_row)

        outer.addSpacing(16)

        # Recent-Files-Liste
        self._recent_label = QLabel(t("Zuletzt geöffnet"))
        self._recent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._recent_label.setStyleSheet(
            f"font-size: 10px; color: {THEME.text_muted}; "
            f"letter-spacing: 2px; font-weight: 600; background: transparent;"
        )
        outer.addWidget(self._recent_label)

        self._recent_list = QListWidget()
        self._recent_list.setMaximumHeight(240)
        self._recent_list.setMinimumWidth(640)
        self._recent_list.setMaximumWidth(1100)
        # Pfad-Elision: lange Pfade werden in der Mitte mit "…" gekürzt
        self._recent_list.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self._recent_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._recent_list.setUniformItemSizes(True)
        self._recent_list.setStyleSheet(self._recent_list_stylesheet())
        self._recent_list.itemDoubleClicked.connect(self._on_recent_double_clicked)
        recent_row = QHBoxLayout()
        recent_row.addStretch(1)
        recent_row.addWidget(self._recent_list, 4)
        recent_row.addStretch(1)
        outer.addLayout(recent_row)

        self._empty_recent_label = QLabel(t("Noch keine Dateien geöffnet."))
        self._empty_recent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_recent_label.setStyleSheet(
            f"color: {THEME.text_disabled}; font-style: italic; background: transparent;"
        )
        outer.addWidget(self._empty_recent_label)

        outer.addStretch(2)

    @staticmethod
    def _recent_list_stylesheet() -> str:
        return f"""
            QListWidget {{
                background: {THEME.bg_medium};
                border: 1px solid {THEME.border_medium};
                border-radius: 8px;
                padding: 4px;
                color: {THEME.text_secondary};
            }}
            QListWidget::item {{
                padding: 6px 10px;
                border-radius: 4px;
            }}
            QListWidget::item:hover {{
                background: {THEME.bg_light};
            }}
            QListWidget::item:selected {{
                background: {THEME.accent_primary};
                color: {THEME.bg_dark};
            }}
        """

    def _apply_theme(self) -> None:
        """Aktualisiert alle gecachten THEME-Farben nach einem Live-Themewechsel."""
        self._header_label.setStyleSheet(
            f"font-size: 36px; font-weight: 700; color: {THEME.accent_primary}; "
            f"letter-spacing: 2px; background: transparent;"
        )
        self._subtitle_label.setStyleSheet(
            f"font-size: 13px; color: {THEME.text_muted}; "
            f"letter-spacing: 3px; background: transparent;"
        )
        self._recent_label.setStyleSheet(
            f"font-size: 10px; color: {THEME.text_muted}; "
            f"letter-spacing: 2px; font-weight: 600; background: transparent;"
        )
        self._recent_list.setStyleSheet(self._recent_list_stylesheet())
        self._empty_recent_label.setStyleSheet(
            f"color: {THEME.text_disabled}; font-style: italic; background: transparent;"
        )
        self._new_tile.set_accent(THEME.accent_primary)
        self._open_tile.set_accent(THEME.accent_secondary)
        self._import_tile.set_accent(THEME.info)
        self._demo_tile.set_accent(THEME.accent_purple)
        # Recent-Files-Items werden mit eigenen, inline gestylten Labels
        # gebaut (siehe set_recent_files) -- am einfachsten neu aufbauen,
        # statt jedes Item-Widget einzeln zu durchsuchen.
        self.set_recent_files(self._recent_files)
        self.update()

    def paintEvent(self, event) -> None:
        """Dezenter Hintergrund-Gradient — passt zur Canvas-Optik."""
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(THEME.bg_dark))
        gradient.setColorAt(1, QColor(THEME.bg_medium))
        painter.fillRect(self.rect(), gradient)

    def set_recent_files(self, files: list[str]) -> None:
        """Aktualisiert die Recent-Files-Liste.

        Jedes Eintrag besteht aus zwei Zeilen:
        - Dateiname in fett (gut lesbar)
        - Vollständiger Pfad in muted-Farbe (Elision via QListWidget)
        """
        self._recent_files = list(files)
        self._recent_list.clear()
        valid: list[str] = []
        for path in self._recent_files:
            p = Path(path)
            if not p.exists():
                continue
            valid.append(path)

            # parent=self verhindert Top-Level-Phantom beim ersten Show des
            # Welcome-Widgets. Container und Labels bekommen Parent direkt
            # mit, statt erst beim addWidget zu geparented zu werden.
            container = QWidget(self)
            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(2, 2, 2, 2)
            v_layout.setSpacing(1)

            name_label = QLabel(f"📄  {p.name}", container)
            name_label.setStyleSheet(
                f"font-size: 12px; font-weight: 600; color: {THEME.text_primary}; "
                f"background: transparent;"
            )
            v_layout.addWidget(name_label)

            # Pfad mittig mit "…" kürzen, damit selbst sehr lange Pfade
            # in eine Zeile passen. fontMetrics liefert die Pixel-Breite.
            from PySide6.QtGui import QFontMetrics

            path_str = str(p.parent)
            elide_width = min(self._recent_list.maximumWidth(), 1040) - 40
            metrics = QFontMetrics(self.font())
            elided = metrics.elidedText(path_str, Qt.TextElideMode.ElideMiddle, elide_width)
            path_label = QLabel(elided, container)
            path_label.setStyleSheet(
                f"font-size: 10px; color: {THEME.text_muted}; background: transparent;"
            )
            path_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            v_layout.addWidget(path_label)

            item = QListWidgetItem()
            # Größe pro Item: gross genug für 2 Zeilen
            item.setSizeHint(QSize(0, 44))
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            self._recent_list.addItem(item)
            self._recent_list.setItemWidget(item, container)

        has_recent = bool(valid)
        self._recent_list.setVisible(has_recent)
        self._empty_recent_label.setVisible(not has_recent)

    def _on_recent_double_clicked(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.open_recent.emit(path)
