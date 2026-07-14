"""
Werkzeugleiste für Zeichenwerkzeuge.

Verwendet eine gemeinsame Basisklasse für alle Button-Typen
und das zentrale Styling-System.
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import t
from ..styles import THEME
from ..tools.tool_enum import Tool


class BaseToolButton(QToolButton):
    """
    Basis-Klasse für alle Tool-Buttons.

    Enthält die gemeinsame Logik für Rendering und Styling.
    """

    # Standard-Größen
    DEFAULT_WIDTH = 78
    DEFAULT_HEIGHT = 66
    ICON_FONT_SIZE = 22
    LABEL_FONT_SIZE = 9

    def __init__(
        self, icon_char: str, label: str, tooltip: str = "", checkable: bool = True, parent=None
    ) -> None:
        super().__init__(parent)
        self._icon_char = icon_char
        self._label = label

        self.setCheckable(checkable)
        self.setFixedSize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip if tooltip else f"<b>{label}</b>")

        self._apply_base_style()

    def _apply_stylesheet(self) -> None:
        """Wendet den Basis-Style an (überschreibbar für Theme-Wechsel)."""
        self._apply_base_style()

    def _apply_base_style(self) -> None:
        """Wendet den Basis-Style an."""
        self.setStyleSheet(f"""
            QToolButton {{
                background: {THEME.bg_medium};
                border: 2px solid transparent;
                border-radius: 8px;
                color: {THEME.text_muted};
                padding: 4px;
            }}
            QToolButton:hover {{
                background: {THEME.bg_light};
                border-color: {THEME.border_light};
                color: {THEME.text_secondary};
            }}
            QToolButton:checked {{
                background: {THEME.bg_lighter};
                border-color: {THEME.accent_primary};
                color: {THEME.text_primary};
            }}
            QToolButton:pressed {{
                background: {THEME.bg_lighter};
            }}
        """)

    def set_icon_and_label(self, icon: str, label: str) -> None:
        """Ändert Icon und Label."""
        self._icon_char = icon
        self._label = label
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Icon zeichnen
        icon_font = QFont("Segoe UI Emoji", self.ICON_FONT_SIZE)
        painter.setFont(icon_font)
        painter.setPen(self._get_icon_color())

        icon_rect = self.rect().adjusted(0, 2, 0, -18)
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, self._icon_char)

        # Label zeichnen
        label_font = QFont("Segoe UI", self.LABEL_FONT_SIZE)
        label_font.setBold(self.isChecked())
        painter.setFont(label_font)
        painter.setPen(self._get_label_color())

        label_rect = self.rect().adjusted(0, 42, 0, -2)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, self._label)

    def _get_icon_color(self) -> QColor:
        """Gibt die Icon-Farbe basierend auf dem Zustand zurück."""
        if self.isChecked():
            return QColor(THEME.text_primary)
        return QColor(THEME.text_secondary)

    def _get_label_color(self) -> QColor:
        """Gibt die Label-Farbe basierend auf dem Zustand zurück."""
        if self.isChecked():
            return QColor(THEME.accent_primary)
        return QColor(THEME.text_muted)


class ToolButton(BaseToolButton):
    """Werkzeug-Button mit Tool-Enum."""

    def __init__(
        self, tool: Tool, icon_char: str, label: str, shortcut: str = "", parent=None
    ) -> None:
        tooltip = f"<b>{label}</b>"
        if shortcut:
            tooltip += f"<br><span style='color:{THEME.accent_primary};'>Taste: {shortcut}</span>"

        super().__init__(icon_char, label, tooltip, True, parent)
        self._tool = tool

        if shortcut:
            self.setShortcut(shortcut)

    @property
    def tool(self) -> Tool:
        return self._tool

    @tool.setter
    def tool(self, value: Tool) -> None:
        self._tool = value


class ToggleToolButton(ToolButton):
    """Werkzeug-Button der zwischen zwei Zuständen wechselt."""

    toggled_state = Signal(bool)

    def __init__(
        self,
        tool_outline: Tool,
        tool_filled: Tool,
        icon_outline: str,
        icon_filled: str,
        label_outline: str,
        label_filled: str,
        shortcut: str = "",
        parent=None,
    ) -> None:
        super().__init__(tool_outline, icon_outline, label_outline, shortcut, parent)

        self._tool_outline = tool_outline
        self._tool_filled = tool_filled
        self._icon_outline = icon_outline
        self._icon_filled = icon_filled
        self._label_outline = label_outline
        self._label_filled = label_filled
        self._is_filled = False

        self.setToolTip(
            f"<b>{label_outline}</b><br>"
            f"<span style='color:{THEME.accent_primary};'>Erneut klicken: {label_filled}</span>"
            + (
                f"<br><span style='color:{THEME.text_muted};'>Taste: {shortcut}</span>"
                if shortcut
                else ""
            )
        )

    def toggle_fill_state(self) -> None:
        """Wechselt zwischen Umriss und Gefüllt."""
        self._is_filled = not self._is_filled

        if self._is_filled:
            self._tool = self._tool_filled
            self._icon_char = self._icon_filled
            self._label = self._label_filled
        else:
            self._tool = self._tool_outline
            self._icon_char = self._icon_outline
            self._label = self._label_outline

        self.toggled_state.emit(self._is_filled)
        self.update()

    @property
    def is_filled(self) -> bool:
        return self._is_filled

    def reset_to_outline(self) -> None:
        """Setzt auf Umriss zurück."""
        self._is_filled = False
        self._tool = self._tool_outline
        self._icon_char = self._icon_outline
        self._label = self._label_outline
        self.update()


class ActionButton(BaseToolButton):
    """Button für einmalige Aktionen (nicht toggle-bar)."""

    def __init__(self, icon_char: str, label: str, tooltip: str = "", parent=None) -> None:
        super().__init__(icon_char, label, tooltip or label, False, parent)
        self._apply_stylesheet()

    def _apply_stylesheet(self) -> None:
        """Spezieller Style für Action-Buttons."""
        self.setStyleSheet(f"""
            QToolButton {{
                background: {THEME.bg_medium};
                border: 2px solid transparent;
                border-radius: 8px;
                color: {THEME.text_muted};
                padding: 4px;
            }}
            QToolButton:hover {{
                background: {THEME.bg_light};
                border-color: {THEME.accent_secondary};
                color: {THEME.accent_secondary};
            }}
            QToolButton:pressed {{
                background: {THEME.bg_lighter};
                border-color: {THEME.accent_secondary};
            }}
        """)

    def _get_label_color(self) -> QColor:
        """Action-Buttons haben immer die gleiche Label-Farbe."""
        return QColor(THEME.text_muted)


class SymmetryToggle(BaseToolButton):
    """Toggle-Button für Symmetrie-Optionen."""

    toggled_state = Signal(bool)

    ICON_FONT_SIZE = 16

    def __init__(self, icon_char: str, label: str, tooltip: str, parent=None) -> None:
        super().__init__(icon_char, label, tooltip, True, parent)
        self.setFixedSize(70, 50)
        self.toggled.connect(self.toggled_state.emit)
        self._apply_stylesheet()

    def _apply_stylesheet(self) -> None:
        """Style für Symmetrie-Toggle."""
        self.setStyleSheet(f"""
            QToolButton {{
                background: {THEME.bg_dark};
                border: 2px solid transparent;
                border-radius: 6px;
                color: {THEME.text_muted};
                padding: 2px;
            }}
            QToolButton:hover {{
                background: {THEME.bg_light};
                border-color: {THEME.border_light};
            }}
            QToolButton:checked {{
                background: {THEME.bg_lighter};
                border-color: {THEME.accent_blue};
                color: {THEME.accent_blue};
            }}
        """)

    def _get_icon_color(self) -> QColor:
        if self.isChecked():
            return QColor(THEME.accent_blue)
        return QColor(THEME.text_muted)

    def _get_label_color(self) -> QColor:
        if self.isChecked():
            return QColor(THEME.accent_blue)
        return QColor(THEME.text_disabled)


class ToolBar(QWidget):
    """Vertikale Werkzeugleiste.

    Bei niedrigen Fenstern reicht die Hoehe oft nicht fuer alle Werkzeuge —
    statt eines klassischen Scrollbalkens scrollt der Inhalt automatisch,
    sobald die Maus oben/unten in eine schmale Hover-Zone kommt (aehnlich
    Drag&Drop-Auto-Scroll). Kleine ▲/▼-Hinweise am Rand zeigen an, wenn in
    dieser Richtung noch mehr Werkzeuge folgen.
    """

    tool_changed = Signal(object)
    mirror_h_clicked = Signal()
    mirror_v_clicked = Signal()

    HOVER_ZONE_PX = 28
    SCROLL_STEP_PX = 6
    SCROLL_INTERVAL_MS = 16

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_tool: Tool = Tool.PENCIL
        self._buttons: dict[Tool, ToolButton] = {}
        self._toggle_buttons: list[ToggleToolButton] = []
        self._action_buttons: list[ActionButton] = []
        self._headers: list[QLabel] = []
        self._separators: list[QFrame] = []
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        # Pollt die Cursor-Position statt auf Mouse-Move-Events zu warten:
        # die Tool-Buttons fuellen fast die komplette Breite/Hoehe des
        # Scroll-Bereichs, ein Event-Filter auf dem Viewport wuerde also
        # kaum je feuern (Mouse-Move-Events gehen an das Button-Widget
        # unter dem Cursor, nicht an den Viewport dahinter).
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setInterval(self.SCROLL_INTERVAL_MS)
        self._scroll_timer.timeout.connect(self._poll_auto_scroll)
        self._scroll_timer.start()

        self._setup_ui()

    def _setup_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer_layout.addWidget(self._scroll_area)

        content = QWidget()
        self._scroll_area.setWidget(content)

        # ▲/▼-Scroll-Hinweise: eigene Overlay-Labels ueber dem Scroll-Bereich,
        # transparent fuer Maus-Events, damit die Hover-Auto-Scroll-Zone
        # darunter weiter funktioniert.
        self._scroll_hint_top = self._create_scroll_hint("▲")
        self._scroll_hint_bottom = self._create_scroll_hint("▼")
        bar = self._scroll_area.verticalScrollBar()
        bar.valueChanged.connect(self._update_scroll_hints)
        bar.rangeChanged.connect(self._update_scroll_hints)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 10, 6, 10)
        layout.setSpacing(4)

        # Header
        layout.addWidget(self._create_header(t("WERKZEUGE")))
        layout.addWidget(self._create_separator())

        # Zeichenwerkzeuge
        self._add_tool(layout, Tool.PENCIL, "✏️", t("Stift"), "P")
        self._add_tool(layout, Tool.ERASER, "🗑️", t("Radierer"), "E")
        self._add_tool(layout, Tool.FILL, "🪣", t("Füllen"), "F")
        self._add_tool(layout, Tool.PIPETTE, "💉", t("Pipette"), "I")

        layout.addWidget(self._create_separator())

        # Formwerkzeuge
        self._add_tool(layout, Tool.LINE, "📏", t("Linie"), "L")
        self._add_toggle(
            layout, Tool.RECT, Tool.RECT_FILLED, "□", "■", t("Rechteck"), t("Rechteck") + " ■", "R"
        )
        self._add_toggle(
            layout,
            Tool.ELLIPSE,
            Tool.ELLIPSE_FILLED,
            "⭕",
            "🔴",
            t("Ellipse"),
            t("Ellipse") + " ●",
            "O",
        )
        self._add_toggle(
            layout,
            Tool.POLYGON,
            Tool.POLYGON_FILLED,
            "⬡",
            "⬢",
            t("Polygon"),
            t("Polygon") + " ■",
            "G",
        )

        layout.addWidget(self._create_separator())

        # Spezialwerkzeuge
        self._add_tool(layout, Tool.TEXT, "🔤", t("Text"), "T")
        self._add_tool(layout, Tool.BACKSTITCH, "↙️", t("Rückstich"), "B")
        self._add_tool(layout, Tool.GRADIENT, "🌈", t("Verlauf"), "D")
        self._add_tool(layout, Tool.PROGRESS, "✅", t("Fortschritt"), "K")

        layout.addWidget(self._create_separator())

        # Auswahl/Navigation
        self._add_toggle(
            layout, Tool.SELECT, Tool.SELECT_LASSO, "⬚", "〰️", t("Rechteck"), t("Lasso"), "S"
        )
        self._add_tool(layout, Tool.MOVE, "✋", t("Bewegen"), "M")

        layout.addWidget(self._create_separator())

        # Transformations-Aktionen
        self._add_action(
            layout, "↔️", t("Spiegel H"), t("Horizontal spiegeln"), self.mirror_h_clicked
        )
        self._add_action(layout, "↕️", t("Spiegel V"), t("Vertikal spiegeln"), self.mirror_v_clicked)

        layout.addWidget(self._create_separator())
        layout.addStretch()

        # Standard-Auswahl
        self._buttons[Tool.PENCIL].setChecked(True)

        self.setFixedWidth(90)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.reapply_styles()
        self._position_scroll_hints()
        QTimer.singleShot(0, self._update_scroll_hints)

    def _create_scroll_hint(self, arrow: str) -> QLabel:
        """Erstellt ein ▲/▼-Overlay-Label (zeigt an, dass in dieser Richtung
        noch weitere Werkzeuge folgen)."""
        label = QLabel(arrow, self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedHeight(16)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        label.hide()
        return label

    def _position_scroll_hints(self) -> None:
        """Positioniert die Scroll-Hinweise am oberen/unteren Rand."""
        w = self.width()
        self._scroll_hint_top.setGeometry(0, 0, w, 16)
        self._scroll_hint_bottom.setGeometry(0, self.height() - 16, w, 16)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_scroll_hints()

    def _update_scroll_hints(self) -> None:
        """Zeigt/versteckt die ▲/▼-Hinweise je nach Scroll-Position."""
        bar = self._scroll_area.verticalScrollBar()
        self._scroll_hint_top.setVisible(bar.value() > bar.minimum())
        self._scroll_hint_bottom.setVisible(bar.value() < bar.maximum())

    def _poll_auto_scroll(self) -> None:
        """Scrollt automatisch, wenn der Cursor (global) ueber der oberen/
        unteren Hover-Zone des Viewports steht — per Polling statt Events,
        da die Tool-Buttons fast den ganzen Viewport ausfuellen und Mouse-
        Move-Events so direkt an die Buttons gehen, nicht an den Viewport.
        """
        bar = self._scroll_area.verticalScrollBar()
        if bar.maximum() == bar.minimum():
            return

        viewport = self._scroll_area.viewport()
        local_pos = viewport.mapFromGlobal(QCursor.pos())
        if not viewport.rect().contains(local_pos):
            return

        y = local_pos.y()
        if y < self.HOVER_ZONE_PX:
            bar.setValue(bar.value() - self.SCROLL_STEP_PX)
        elif y > viewport.height() - self.HOVER_ZONE_PX:
            bar.setValue(bar.value() + self.SCROLL_STEP_PX)

    def reapply_styles(self) -> None:
        """Setzt alle Stylesheets neu (für Theme-Wechsel)."""
        self.setStyleSheet(f"""
            ToolBar {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {THEME.bg_dark}, stop:1 {THEME.bg_medium});
                border-right: 1px solid {THEME.border_medium};
            }}
        """)
        self._scroll_area.setStyleSheet("background: transparent; border: none;")
        self._scroll_area.viewport().setStyleSheet("background: transparent;")
        self._scroll_area.widget().setStyleSheet("background: transparent;")
        hint_style = f"""
            color: {THEME.accent_primary};
            background: {THEME.bg_dark};
            font-size: 11px;
            font-weight: bold;
        """
        self._scroll_hint_top.setStyleSheet(hint_style)
        self._scroll_hint_bottom.setStyleSheet(hint_style)
        for btn in self._buttons.values():
            btn._apply_stylesheet()
        for btn in self._toggle_buttons:
            btn._apply_stylesheet()
        for btn in self._action_buttons:
            btn._apply_stylesheet()
        for lbl in self._headers:
            lbl.setStyleSheet(f"""
                font-size: 9px; font-weight: bold;
                color: {THEME.accent_primary};
                letter-spacing: 1px; padding: 4px;
            """)
        for sep in self._separators:
            sep.setStyleSheet(
                f"background: {THEME.border_medium}; max-height: 1px; margin: 6px 8px;"
            )
        self.update()

    def _create_header(self, text: str) -> QLabel:
        """Erstellt einen Section-Header."""
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"""
            font-size: 9px;
            font-weight: bold;
            color: {THEME.accent_primary};
            letter-spacing: 1px;
            padding: 4px;
        """)
        self._headers.append(label)
        return label

    def _create_separator(self) -> QFrame:
        """Erstellt eine horizontale Trennlinie."""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {THEME.border_medium}; max-height: 1px; margin: 6px 8px;")
        self._separators.append(sep)
        return sep

    def _add_tool(
        self, layout: QVBoxLayout, tool: Tool, icon: str, label: str, shortcut: str = ""
    ) -> None:
        """Fügt einen normalen Tool-Button hinzu."""
        btn = ToolButton(tool, icon, label, shortcut, self)
        btn.clicked.connect(lambda: self._on_tool_clicked(tool, btn))

        self._buttons[tool] = btn
        self._button_group.addButton(btn)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _add_toggle(
        self,
        layout: QVBoxLayout,
        tool_outline: Tool,
        tool_filled: Tool,
        icon_outline: str,
        icon_filled: str,
        label_outline: str,
        label_filled: str,
        shortcut: str = "",
    ) -> None:
        """Fügt einen Toggle-Button hinzu."""
        btn = ToggleToolButton(
            tool_outline,
            tool_filled,
            icon_outline,
            icon_filled,
            label_outline,
            label_filled,
            shortcut,
            self,
        )
        btn.clicked.connect(lambda: self._on_toggle_clicked(btn))

        self._buttons[tool_outline] = btn
        self._buttons[tool_filled] = btn
        self._toggle_buttons.append(btn)
        self._button_group.addButton(btn)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _add_action(
        self, layout: QVBoxLayout, icon: str, label: str, tooltip: str, signal: Signal
    ) -> None:
        """Fügt einen Action-Button hinzu."""
        btn = ActionButton(icon, label, tooltip)
        btn.clicked.connect(signal.emit)
        self._action_buttons.append(btn)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _on_tool_clicked(self, tool: Tool, btn: ToolButton) -> None:
        """Normales Werkzeug wurde ausgewählt."""
        if tool != self._current_tool:
            self._current_tool = tool
            self.tool_changed.emit(tool)

    def _on_toggle_clicked(self, btn: ToggleToolButton) -> None:
        """Toggle-Werkzeug wurde geklickt."""
        if btn.isChecked() and self._current_tool in (btn._tool_outline, btn._tool_filled):
            btn.toggle_fill_state()

        self._current_tool = btn.tool
        self.tool_changed.emit(btn.tool)

    @property
    def current_tool(self) -> Tool:
        return self._current_tool

    @current_tool.setter
    def current_tool(self, tool: Tool) -> None:
        if tool in self._buttons:
            self._buttons[tool].setChecked(True)
            self._current_tool = tool

    def select_tool(self, tool: Tool) -> None:
        """Wählt ein Werkzeug aus (mit Signal)."""
        if tool in self._buttons:
            btn = self._buttons[tool]
            btn.setChecked(True)

            if isinstance(btn, ToggleToolButton):
                self._on_toggle_clicked(btn)
            else:
                self._on_tool_clicked(tool, btn)
