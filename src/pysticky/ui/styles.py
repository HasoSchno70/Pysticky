"""
Zentrales Styling-System für PySticky.

Enthält alle Farben, Stylesheets und Theme-Definitionen.
"""

from dataclasses import dataclass

from PySide6.QtGui import QColor


@dataclass(frozen=True)
class ThemeColors:
    """Farbdefinitionen für ein Theme."""

    # Hintergrundfarben
    bg_dark: str = "#1a1a2e"
    bg_medium: str = "#1f1f3a"
    bg_light: str = "#2a2a4a"
    bg_lighter: str = "#3a3a5a"

    # Akzentfarben
    accent_primary: str = "#6ec6a0"  # Grün (Haupt-Akzent)
    accent_secondary: str = "#e6a040"  # Orange (Sekundär)
    accent_blue: str = "#6080c0"  # Blau
    accent_purple: str = "#8a6ec6"  # Lila

    # Textfarben
    text_primary: str = "#ffffff"
    text_secondary: str = "#c0c0e0"
    text_muted: str = "#8a8aa0"
    text_disabled: str = "#606080"

    # Rahmen
    border_dark: str = "#2a2a4a"
    border_medium: str = "#3a3a5a"
    border_light: str = "#4a4a6a"
    border_accent: str = "#6ec6a0"

    # Status-Farben
    success: str = "#4ade80"
    warning: str = "#fbbf24"
    error: str = "#f87171"
    info: str = "#60a5fa"


# Vordefinierte Themes
DARK_THEME = ThemeColors()

LIGHT_THEME = ThemeColors(
    # Hintergrundfarben — leicht warm-tonig statt rein weiss, klare Hierarchie
    bg_dark="#fbfbfd",  # Haupt-Hintergrund (Canvas-Container, Inputs)
    bg_medium="#ecedf3",  # Sekundär (Statusbar, Tabs unselected)
    bg_light="#dde0eb",  # Panel-Header, Hover
    bg_lighter="#c8cee0",  # Selektion / Tabbar-Track
    # Akzentfarben — kräftiger für hellen Hintergrund
    accent_primary="#2e9e6e",
    accent_secondary="#c07820",
    accent_blue="#4060a0",
    accent_purple="#6a4ea0",
    # Textfarben
    text_primary="#1a1a2e",
    text_secondary="#3a3a60",
    text_muted="#6a6a8a",
    text_disabled="#a0a0b0",
    # Rahmen — deutlicher als vorher, damit Container sichtbar werden
    border_dark="#b8bccf",
    border_medium="#9aa1bd",
    border_light="#7a83a8",
    border_accent="#2e9e6e",
    # Status-Farben
    success="#22a060",
    warning="#d09010",
    error="#d04040",
    info="#3080d0",
)


# Globale Theme-Instanz (kann zur Laufzeit gewechselt werden)
THEME = DARK_THEME

_current_theme_name: str = "dark"


def set_theme(name: str) -> None:
    """
    Wechselt das aktive Theme.

    Aktualisiert die THEME-Variable in diesem Modul UND in allen
    bereits geladenen Modulen, die THEME importiert haben.

    Args:
        name: "dark" oder "light"
    """
    import sys

    global THEME, _current_theme_name
    if name == "light":
        new_theme = LIGHT_THEME
        _current_theme_name = "light"
    else:
        new_theme = DARK_THEME
        _current_theme_name = "dark"

    THEME = new_theme

    # Alle Module patchen die 'THEME' aus diesem Modul importiert haben
    this_module = sys.modules[__name__]
    for mod in list(sys.modules.values()):
        if mod is None or mod is this_module:
            continue
        try:
            if getattr(mod, "THEME", None) is not new_theme:
                if hasattr(mod, "THEME") and isinstance(getattr(mod, "THEME", None), ThemeColors):
                    mod.THEME = new_theme
        except Exception:  # intentional catch-all: frozen/special modules may raise
            pass


def reapply_theme(app) -> None:
    """
    Wechselt das Theme live und stylt die gesamte App neu.

    Wird aufgerufen wenn der Benutzer das Theme in den
    Einstellungen ändert — ohne Neustart.
    """
    # Stylesheet komplett zurücksetzen, damit dark.qss nicht nachwirkt
    app.setStyleSheet("")
    apply_theme_to_app(app)

    # dark.qss nur für Dark-Theme laden
    if _current_theme_name == "dark":
        _append_dark_qss(app)

    # Alle Top-Level-Widgets neu stylen
    for widget in app.topLevelWidgets():
        _restyle_widget_tree(widget)

    # Custom-Tooltip-Popup (ersetzt Qt's natives QToolTip) neu einfärben
    from .widgets.custom_tooltip import reapply_custom_tooltip_theme

    reapply_custom_tooltip_theme()


def _append_dark_qss(app) -> None:
    """Lädt dark.qss und hängt es an das App-Stylesheet an."""
    from pathlib import Path

    style_path = Path(__file__).parent.parent / "resources" / "styles" / "dark.qss"
    if style_path.exists():
        try:
            with open(style_path, "r", encoding="utf-8") as f:
                current = app.styleSheet()
                app.setStyleSheet(current + "\n" + f.read())
        except OSError:
            pass


def _restyle_widget_tree(widget) -> None:
    """Ruft _apply_theme() rekursiv auf allen Widgets auf."""
    from PySide6.QtWidgets import QWidget

    if hasattr(widget, "_apply_theme"):
        widget._apply_theme()
    for child in widget.findChildren(QWidget):
        if hasattr(child, "_apply_theme"):
            child._apply_theme()
    widget.update()


def get_current_theme_name() -> str:
    """Gibt den Namen des aktiven Themes zurück."""
    return _current_theme_name


def get_available_themes() -> list[str]:
    """Gibt die verfügbaren Theme-Namen zurück."""
    return ["dark", "light"]


class Styles:
    """Vordefinierte Stylesheet-Fragmente."""

    @staticmethod
    def button_primary() -> str:
        """Primärer Button-Style (grüner Akzent)."""
        darker = QColor(THEME.accent_primary).darker(130).name()
        lighter = QColor(THEME.accent_primary).lighter(130).name()
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {THEME.accent_primary}, stop:1 {darker});
                color: {THEME.bg_dark};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {lighter}, stop:1 {THEME.accent_primary});
            }}
            QPushButton:pressed {{
                background: {darker};
            }}
            QPushButton:disabled {{
                background: {THEME.bg_lighter};
                color: {THEME.text_disabled};
            }}
        """

    @staticmethod
    def button_secondary() -> str:
        """Sekundärer Button-Style (orangener Akzent)."""
        darker = QColor(THEME.accent_secondary).darker(130).name()
        lighter = QColor(THEME.accent_secondary).lighter(130).name()
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {THEME.accent_secondary}, stop:1 {darker});
                color: {THEME.bg_dark};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {lighter}, stop:1 {THEME.accent_secondary});
            }}
            QPushButton:disabled {{
                background: {THEME.bg_lighter};
                color: {THEME.text_disabled};
            }}
        """

    @staticmethod
    def input_field() -> str:
        """Standard-Input-Feld-Style."""
        return f"""
            QLineEdit, QSpinBox, QDoubleSpinBox {{
                background: {THEME.bg_dark};
                color: {THEME.text_primary};
                border: 2px solid {THEME.border_medium};
                border-radius: 6px;
                padding: 6px 10px;
            }}
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border-color: {THEME.accent_primary};
            }}
            QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
                border-color: {THEME.border_light};
            }}
        """

    @staticmethod
    def combo_box() -> str:
        """ComboBox-Style."""
        return f"""
            QComboBox {{
                background: {THEME.bg_dark};
                color: {THEME.text_primary};
                border: 2px solid {THEME.border_medium};
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: 600;
            }}
            QComboBox:hover {{
                border-color: {THEME.accent_primary};
                background: {THEME.bg_medium};
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
            QComboBox QAbstractItemView {{
                background: {THEME.bg_dark};
                color: {THEME.text_primary};
                border: 2px solid {THEME.accent_primary};
                border-radius: 6px;
                selection-background-color: {THEME.accent_primary};
                selection-color: {THEME.bg_dark};
            }}
        """

    @staticmethod
    def list_widget() -> str:
        """ListWidget-Style."""
        return f"""
            QListWidget {{
                background: {THEME.bg_dark};
                border: 1px solid {THEME.border_dark};
                border-radius: 6px;
                outline: none;
            }}
            QListWidget::item {{
                background: {THEME.bg_medium};
                border: 1px solid transparent;
                border-radius: 6px;
                margin: 2px 4px;
                padding: 4px;
            }}
            QListWidget::item:hover {{
                background: {THEME.bg_light};
                border-color: {THEME.border_light};
            }}
            QListWidget::item:selected {{
                background: {THEME.bg_lighter};
                border-color: {THEME.accent_primary};
            }}
        """

    @staticmethod
    def scrollbar() -> str:
        """Scrollbar-Style."""
        return f"""
            QScrollBar:vertical {{
                background: {THEME.bg_dark};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {THEME.border_light};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {THEME.accent_primary};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar:horizontal {{
                background: {THEME.bg_dark};
                height: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal {{
                background: {THEME.border_light};
                border-radius: 5px;
                min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {THEME.accent_primary};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
            }}
        """

    @staticmethod
    def frame_panel() -> str:
        """Panel/Frame-Style."""
        return f"""
            QFrame {{
                background: {THEME.bg_medium};
                border: 1px solid {THEME.border_medium};
                border-radius: 8px;
            }}
        """

    @staticmethod
    def frame_accent() -> str:
        """Akzent-Frame-Style (mit grünem Rahmen)."""
        return f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {THEME.bg_lighter}, stop:1 {THEME.bg_light});
                border: 1px solid {THEME.accent_primary};
                border-radius: 8px;
            }}
        """

    @staticmethod
    def toolbar() -> str:
        """Toolbar-Style."""
        return f"""
            QToolBar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {THEME.bg_light}, stop:1 {THEME.bg_medium});
                border-bottom: 1px solid {THEME.border_medium};
                spacing: 4px;
                padding: 4px;
            }}
        """

    @staticmethod
    def tool_button() -> str:
        """ToolButton-Style."""
        return f"""
            QToolButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px 8px;
                color: {THEME.text_secondary};
            }}
            QToolButton:hover {{
                background: {THEME.bg_lighter};
                border-color: {THEME.border_light};
            }}
            QToolButton:pressed {{
                background: {THEME.border_light};
            }}
            QToolButton:checked {{
                background: {THEME.bg_lighter};
                border-color: {THEME.accent_primary};
                color: {THEME.text_primary};
            }}
            QToolButton:disabled {{
                color: {THEME.text_disabled};
            }}
        """

    @staticmethod
    def section_header() -> str:
        """Section-Header-Style."""
        return f"""
            font-size: 10px;
            font-weight: 700;
            color: {THEME.accent_primary};
            letter-spacing: 1px;
            padding: 4px;
        """

    @staticmethod
    def label_muted() -> str:
        """Abgedunkelte Label-Style."""
        return f"color: {THEME.text_muted};"

    @staticmethod
    def dock_widget() -> str:
        """DockWidget-Style."""
        return f"""
            QDockWidget {{
                titlebar-close-icon: url(none);
                titlebar-normal-icon: url(none);
            }}
            QDockWidget::title {{
                background: {THEME.bg_light};
                color: {THEME.text_primary};
                padding: 6px;
                font-weight: bold;
            }}
        """


def get_qcolor(hex_color: str) -> QColor:
    """Konvertiert einen Hex-Farbwert in QColor."""
    return QColor(hex_color)


def apply_theme_to_app(app) -> None:
    """Wendet das Theme auf die gesamte Anwendung an."""
    # Windows 11 lässt native Popups (Context-Menüs, Datei-Dialoge) je
    # nach OS-weitem Dark/Light-Modus einfärben — unabhängig von unserer
    # eigenen QSS/Palette, sobald das App-Theme vom System-Theme abweicht.
    # Qt 6.5+ erlaubt, das explizit zu fixieren, statt dem OS zu folgen.
    # (Tooltips selbst laufen seit custom_tooltip.py nicht mehr über Qt's
    # natives QToolTip, das auf Windows für Dock-Widget-Inhalte nachweislich
    # falsch rendert — siehe dort.)
    from PySide6.QtCore import Qt as _Qt
    from PySide6.QtGui import QGuiApplication

    scheme = _Qt.ColorScheme.Dark if _current_theme_name == "dark" else _Qt.ColorScheme.Light
    QGuiApplication.styleHints().setColorScheme(scheme)

    app.setStyleSheet(f"""
        QMainWindow {{
            background: {THEME.bg_dark};
        }}
        QWidget {{
            font-family: 'Segoe UI', 'Arial', sans-serif;
            color: {THEME.text_primary};
        }}
        QDialog {{
            background: {THEME.bg_dark};
            color: {THEME.text_primary};
        }}
        QToolTip {{
            background: {THEME.bg_light};
            color: {THEME.text_primary};
            border: 1px solid {THEME.accent_primary};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QStatusBar {{
            background: {THEME.bg_light};
            color: {THEME.text_secondary};
            border-top: 2px solid {THEME.accent_primary};
        }}
        QStatusBar::item {{
            border: none;
        }}
        QStatusBar QLabel {{
            color: {THEME.text_secondary};
            padding: 2px 6px;
        }}
        /* === MenuBar === */
        QMenuBar {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {THEME.bg_light}, stop:1 {THEME.bg_medium});
            color: {THEME.text_primary};
            border-bottom: 2px solid {THEME.accent_primary};
            padding: 2px 4px;
            spacing: 2px;
            font-weight: 600;
        }}
        QMenuBar::item {{
            background: transparent;
            color: {THEME.text_primary};
            padding: 6px 14px;
            border-radius: 4px;
            margin: 1px 2px;
        }}
        QMenuBar::item:selected {{
            background: {THEME.accent_primary};
            color: {THEME.bg_dark};
        }}
        QMenuBar::item:pressed {{
            background: {THEME.accent_primary};
            color: {THEME.bg_dark};
        }}
        /* === Menu === */
        QMenu {{
            background: {THEME.bg_medium};
            color: {THEME.text_primary};
            border: 1px solid {THEME.accent_primary};
            border-radius: 6px;
            padding: 6px 4px;
        }}
        QMenu::item {{
            background: transparent;
            padding: 6px 24px 6px 28px;
            border-radius: 4px;
            margin: 1px 4px;
        }}
        QMenu::item:selected {{
            background: {THEME.accent_primary};
            color: {THEME.bg_dark};
        }}
        QMenu::item:disabled {{
            color: {THEME.text_disabled};
        }}
        QMenu::separator {{
            height: 1px;
            background: {THEME.border_medium};
            margin: 4px 12px;
        }}
        QMenu::icon {{
            padding-left: 6px;
        }}
        QMenu::indicator {{
            width: 14px;
            height: 14px;
            margin-left: 6px;
        }}
        QDockWidget {{
            color: {THEME.text_primary};
        }}
        QDockWidget::title {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {THEME.bg_light}, stop:1 {THEME.bg_lighter});
            color: {THEME.accent_primary};
            padding: 6px;
            font-weight: bold;
            border-left: 3px solid {THEME.accent_primary};
        }}
        QTabWidget::pane {{
            border: 1px solid {THEME.border_medium};
            background: {THEME.bg_medium};
        }}
        QTabBar::tab {{
            background: {THEME.bg_lighter};
            color: {THEME.text_secondary};
            border: 1px solid {THEME.border_medium};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 6px 12px;
            margin-right: 2px;
            font-weight: 600;
        }}
        QTabBar::tab:selected {{
            background: {THEME.bg_dark};
            color: {THEME.accent_primary};
            border: 2px solid {THEME.accent_primary};
            border-bottom: none;
            padding: 5px 11px;
        }}
        QTabBar::tab:hover:!selected {{
            background: {THEME.bg_light};
            color: {THEME.text_primary};
        }}
        /* Dock-Tabs am unteren Rand brauchen invertierte Radii und einen
           sichtbaren Akzent — sonst kleben sie auf dem hellen Statusbar-
           Hintergrund. */
        QTabBar[documentMode="false"]::tab:bottom {{
            border-top: none;
            border-bottom: 1px solid {THEME.border_medium};
            border-bottom-left-radius: 4px;
            border-bottom-right-radius: 4px;
            border-top-left-radius: 0;
            border-top-right-radius: 0;
        }}
        QTabBar[documentMode="false"]::tab:bottom:selected {{
            border-bottom: 2px solid {THEME.accent_primary};
            border-top: none;
        }}
        /* === GroupBox === */
        QGroupBox {{
            background: {THEME.bg_medium};
            color: {THEME.accent_primary};
            border: 1px solid {THEME.border_medium};
            border-left: 3px solid {THEME.accent_primary};
            border-radius: 6px;
            margin-top: 14px;
            padding: 14px 10px 10px 10px;
            font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            padding: 0 6px;
            background: {THEME.bg_dark};
            border-radius: 3px;
            color: {THEME.accent_primary};
        }}

        /* === Push-Buttons (Default Look für alle Dialoge) === */
        QPushButton {{
            background: {THEME.bg_lighter};
            color: {THEME.text_primary};
            border: 1px solid {THEME.border_medium};
            border-radius: 5px;
            padding: 6px 16px;
            font-weight: 600;
            min-height: 22px;
        }}
        QPushButton:hover {{
            background: {THEME.bg_light};
            border-color: {THEME.accent_primary};
            color: {THEME.accent_primary};
        }}
        QPushButton:pressed {{
            background: {THEME.accent_primary};
            color: {THEME.bg_dark};
        }}
        QPushButton:default {{
            background: {THEME.accent_primary};
            color: {THEME.bg_dark};
            border: 1px solid {THEME.accent_primary};
        }}
        QPushButton:default:hover {{
            background: {THEME.success};
            border-color: {THEME.success};
            color: {THEME.bg_dark};
        }}
        QPushButton:disabled {{
            background: {THEME.bg_medium};
            color: {THEME.text_disabled};
            border-color: {THEME.border_dark};
        }}

        /* === Eingabe-Felder === */
        QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit {{
            background: {THEME.bg_medium};
            color: {THEME.text_primary};
            border: 1px solid {THEME.border_medium};
            border-radius: 4px;
            padding: 5px 8px;
            selection-background-color: {THEME.accent_primary};
            selection-color: {THEME.bg_dark};
        }}
        QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover,
        QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover, QTimeEdit:hover {{
            border-color: {THEME.border_light};
        }}
        QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
        QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {{
            border: 2px solid {THEME.accent_primary};
            padding: 4px 7px;  /* kompensiert dickere Border */
        }}
        QLineEdit:disabled, QPlainTextEdit:disabled,
        QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled {{
            background: {THEME.bg_dark};
            color: {THEME.text_disabled};
        }}

        /* === ComboBox === */
        QComboBox {{
            background: {THEME.bg_medium};
            color: {THEME.text_primary};
            border: 1px solid {THEME.border_medium};
            border-radius: 4px;
            padding: 5px 8px;
            min-height: 18px;
        }}
        QComboBox:hover {{
            border-color: {THEME.accent_primary};
        }}
        QComboBox:focus {{
            border: 2px solid {THEME.accent_primary};
            padding: 4px 7px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 22px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {THEME.accent_primary};
            margin-right: 6px;
        }}
        QComboBox QAbstractItemView {{
            background: {THEME.bg_medium};
            color: {THEME.text_primary};
            border: 1px solid {THEME.accent_primary};
            border-radius: 4px;
            outline: none;
            selection-background-color: {THEME.accent_primary};
            selection-color: {THEME.bg_dark};
            padding: 4px;
        }}

        /* === CheckBox + RadioButton === */
        QCheckBox, QRadioButton {{
            color: {THEME.text_primary};
            spacing: 8px;
            padding: 2px;
        }}
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {THEME.border_light};
            background: {THEME.bg_medium};
        }}
        QCheckBox::indicator {{
            border-radius: 3px;
        }}
        QRadioButton::indicator {{
            border-radius: 8px;
        }}
        QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
            border-color: {THEME.accent_primary};
        }}
        QCheckBox::indicator:checked {{
            background: {THEME.accent_primary};
            border-color: {THEME.accent_primary};
            image: none;
        }}
        QRadioButton::indicator:checked {{
            background: {THEME.accent_primary};
            border: 4px solid {THEME.bg_medium};
            outline: 1px solid {THEME.accent_primary};
        }}

        /* === Slider === */
        QSlider::groove:horizontal {{
            background: {THEME.bg_lighter};
            height: 6px;
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {THEME.accent_primary};
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }}
        QSlider::sub-page:horizontal {{
            background: {THEME.accent_primary};
            border-radius: 3px;
        }}

        /* === DialogButtonBox === */
        QDialogButtonBox QPushButton {{
            min-width: 80px;
        }}
        {Styles.scrollbar()}
    """)
