"""
Custom-Tooltip: ersetzt Qt's natives QToolTip app-weit.

Hintergrund: Qt's eingebautes QToolTip rendert auf Windows fuer Widgets
innerhalb von QDockWidgets nachweislich mit schwarzem statt dem Theme-
Hintergrund — ein Qt/Windows-Rendering-Bug, der sich weder ueber QSS noch
QPalette, DWM-Backdrop/Immersive-Dark-Mode-APIs, WS_EX_LAYERED-Stripping
noch Deaktivieren der Tooltip-Fade-Animation beheben liess. Ein ganz
gewoehnlicher QWidget-Popup (statt Qt's interner QToolTip-Singleton-Klasse)
durchlaeuft denselben QSS-Rendering-Pfad wie jedes andere Widget in der App
und zeigt das Problem nicht.

`install_custom_tooltips()` haengt einen App-weiten Event-Filter ein, der
jedes QEvent.ToolTip abfaengt und stattdessen dieses Popup zeigt — bestehende
`setToolTip(...)`-Aufrufe im ganzen Code muessen dafuer NICHT angepasst
werden.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, Qt
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from ..styles import THEME


class _CustomTooltip(QWidget):
    """Singleton-Popup-Widget, das Qt's natives QToolTip ersetzt."""

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._label = QLabel(self)
        self._label.setWordWrap(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

        self._apply_theme()

    def _apply_theme(self) -> None:
        self.setStyleSheet(f"""
            _CustomTooltip {{
                background: {THEME.bg_light};
                border: 1px solid {THEME.accent_primary};
                border-radius: 4px;
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: {THEME.text_primary};
                font-size: 12px;
                padding: 4px 8px;
            }}
        """)

    def show_at(self, text: str, global_pos: QPoint, widget: QWidget | None = None) -> None:
        """Zeigt den Tooltip mit `text`.

        Vertikal wird bevorzugt unterhalb von `widget` positioniert (statt
        nur mit festem Cursor-Offset) — bei kleinen Widgets (z.B. einer
        ~30px hohen QSpinBox) reichte der reine Cursor-Offset sonst nicht
        aus, um das Widget selbst nicht zu verdecken, wenn der Cursor nahe
        am oberen Rand des Widgets steht.
        """
        if not text:
            self.hide()
            return

        self._label.setText(text)
        self.adjustSize()

        screen = QApplication.screenAt(global_pos) or QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else None

        x = global_pos.x() + 12
        if widget is not None:
            y = widget.mapToGlobal(QPoint(0, widget.height())).y() + 6
        else:
            y = global_pos.y() + 20
        if geo is not None:
            if x + self.width() > geo.right():
                x = geo.right() - self.width()
            if y + self.height() > geo.bottom():
                if widget is not None:
                    y = widget.mapToGlobal(QPoint(0, 0)).y() - self.height() - 4
                else:
                    y = global_pos.y() - self.height() - 4

        self.move(x, y)
        self.show()


_instance: "_CustomTooltip | None" = None


def _get_instance() -> _CustomTooltip:
    global _instance
    if _instance is None:
        _instance = _CustomTooltip()
    return _instance


def show_custom_tooltip(text: str, global_pos: QPoint, widget: QWidget | None = None) -> None:
    """Zeigt den Custom-Tooltip an — fuer manuelle Aufrufe (statt QToolTip.showText)."""
    _get_instance().show_at(text, global_pos, widget)


def hide_custom_tooltip() -> None:
    """Versteckt den Custom-Tooltip — fuer manuelle Aufrufe (statt QToolTip.hideText)."""
    if _instance is not None:
        _instance.hide()


def reapply_custom_tooltip_theme() -> None:
    """Wird von reapply_theme() nach einem Live-Theme-Wechsel aufgerufen."""
    if _instance is not None:
        _instance._apply_theme()


class _TooltipEventFilter(QObject):
    """Faengt QEvent.ToolTip app-weit ab und zeigt den Custom-Tooltip statt Qt's nativem."""

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        event_type = event.type()

        if event_type == QEvent.Type.ToolTip:
            if isinstance(obj, QWidget):
                text = obj.toolTip()
                if text:
                    show_custom_tooltip(text, event.globalPos(), obj)
                    return True
                hide_custom_tooltip()
            return False

        if event_type in (
            QEvent.Type.Leave,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.Wheel,
            QEvent.Type.WindowDeactivate,
            QEvent.Type.FocusOut,
        ):
            hide_custom_tooltip()

        return False


_filter_instance: "_TooltipEventFilter | None" = None


def install_custom_tooltips(app: QApplication) -> None:
    """Installiert den App-weiten Custom-Tooltip-Mechanismus (ersetzt QToolTip)."""
    global _filter_instance
    if _filter_instance is not None:
        return
    _filter_instance = _TooltipEventFilter()
    app.installEventFilter(_filter_instance)
