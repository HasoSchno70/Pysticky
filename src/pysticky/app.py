"""
Hauptanwendungs-Klasse mit Initialisierung und Styling.
"""

import sys
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from .config import APP_NAME, ORG_NAME
from .ui import MainWindow
from .ui.styles import apply_theme_to_app, set_theme
from .ui.wheel_guard import install_wheel_guard
from .ui.widgets.custom_tooltip import install_custom_tooltips
from .utils import get_logger, setup_logging

logger = get_logger(__name__)


class PySticky:
    """
    Hauptanwendungs-Klasse.

    Verantwortlich für:
    - Initialisierung der Qt-Anwendung
    - Laden von Stylesheets
    - Fenster-Management
    """

    # Version und Namen aus config.py (Single Source of Truth)
    APP_NAME_CONST = APP_NAME
    ORG_NAME_CONST = ORG_NAME

    def __init__(self, args: Optional[list[str]] = None) -> None:
        self.args = args or sys.argv
        self.app: Optional[QApplication] = None
        self.main_window: Optional[MainWindow] = None

    def init(self) -> bool:
        """
        Initialisiert die Anwendung.

        Returns:
            True bei Erfolg, False bei Fehler
        """
        logger.info("Initialisiere PySticky...")

        setup_logging(file_logging=False)

        self.app = QApplication(self.args)
        self.app.setApplicationName(self.APP_NAME_CONST)
        self.app.setOrganizationName(self.ORG_NAME_CONST)

        # "Fusion" statt des nativen Plattform-Stils: der native Windows-
        # Stil ("windowsvista") rendert Tooltips und manche QPushButtons
        # teils ueber die OS-Theme-Engine statt ueber unsere QSS/Palette —
        # das fuehrt zu falschen Farben (z.B. schwarzer Tooltip-Text auf
        # dunklem Grund) bzw. unsichtbaren Button-Glyphen, wenn OS- und
        # App-Theme voneinander abweichen. Fusion respektiert QSS/Palette
        # vollstaendig und macht das Theming plattformunabhaengig konsistent.
        self.app.setStyle("Fusion")

        self.app.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        # Plattform-abhängigen Standard-Font verwenden
        import platform

        if platform.system() == "Windows":
            font = QFont("Segoe UI", 10)
        elif platform.system() == "Darwin":
            font = QFont("SF Pro Text", 13)
        else:
            font = QFont("Noto Sans", 10)
        self.app.setFont(font)

        # Gespeichertes Theme laden
        from PySide6.QtCore import QSettings

        settings = QSettings(self.ORG_NAME_CONST, self.APP_NAME_CONST)
        theme_name = settings.value("theme", "dark", type=str)
        set_theme(theme_name)

        # Sprache initialisieren — VOR dem MainWindow-Build, damit
        # die Menue-Strings beim Erzeugen schon uebersetzt werden.
        self._init_language(settings)

        # Zentrales Theme-System anwenden
        apply_theme_to_app(self.app)

        # Zusätzliches QSS laden (falls vorhanden)
        self._load_stylesheet()

        # Wheel-Guard: verhindert versehentliche Wert-Aenderungen in
        # SpinBoxes/ComboBoxes/Slidern beim Scrollen ueber sie.
        install_wheel_guard(self.app)

        # Custom-Tooltip statt Qt's nativem QToolTip: Qt rendert Tooltips
        # fuer Widgets innerhalb von QDockWidgets auf Windows nachweislich
        # mit schwarzem statt Theme-Hintergrund (siehe custom_tooltip.py).
        install_custom_tooltips(self.app)

        self.main_window = MainWindow()

        logger.info("Initialisierung abgeschlossen")
        return True

    def _init_language(self, settings) -> None:
        """Setzt die UI-Sprache aus dem Setting (oder Auto = System-Locale).

        "auto" -> deutsch wenn QLocale-LanguageName mit "German" beginnt,
        sonst englisch. Andernfalls wird der explizite Sprachcode genutzt.
        """
        from .core.i18n import (
            available_languages,
            get_translation_manager,
            set_language,
        )

        raw_lang = settings.value("ui_language", "auto", type=str)
        lang = raw_lang
        if lang == "auto":
            from PySide6.QtCore import QLocale

            sys_lang = QLocale.system().name().lower()  # z.B. "de_de", "en_us"
            lang = "de" if sys_lang.startswith("de") else "en"

        mgr = get_translation_manager()
        available = available_languages()
        logger.info(
            f"UI-Sprache: setting={raw_lang!r}, resolved={lang!r}, "
            f"i18n-dir={mgr._i18n_dir}, available={available}"
        )

        if lang in available:
            set_language(lang)
            logger.info(f"UI-Sprache aktiv: {lang}")
        else:
            logger.warning(
                f"Sprache '{lang}' nicht verfuegbar (gefunden: {available}, "
                f"i18n-dir: {mgr._i18n_dir}) — bleibe bei Default (de)"
            )

    def _load_stylesheet(self) -> None:
        """Lädt das zusätzliche QSS-Stylesheet (nur für Dark-Theme)."""
        from .ui.styles import _append_dark_qss, get_current_theme_name

        if get_current_theme_name() != "dark":
            logger.debug("Light-Theme aktiv – dark.qss wird nicht geladen")
            return

        if self.app:
            _append_dark_qss(self.app)
            logger.debug("dark.qss geladen")

    def run(self) -> int:
        """
        Startet die Anwendung.

        Returns:
            Exit-Code der Anwendung
        """
        if not self.app or not self.main_window:
            if not self.init():
                return 1

        # Kein Auto-Demo mehr — der User laedt das Demo-Muster auf Wunsch
        # ueber den Welcome-Screen oder Datei → Demo-Muster oeffnen.
        # Das Welcome-Widget erscheint regulaer ueber _perform_start_action.

        self.main_window.show()

        logger.info("PySticky gestartet")

        return self.app.exec()

    def _create_demo_pattern(self) -> None:
        """Erstellt ein Demo-Muster mit Anchor-Farben zum Testen.

        Wird von der Demo-Open-Aktion in MainWindow aufgerufen — nicht
        mehr beim Start. Setzt das Pattern direkt im MainWindow.
        """
        from .core import Pattern, get_palette_manager

        pm = get_palette_manager()
        pm.load_all()
        anchor = pm.get_palette("Anchor")

        if not anchor:
            logger.warning("Anchor-Palette nicht gefunden!")
            return

        pattern = Pattern(name="Demo Kreuzstich", width=40, height=40)
        pattern.color_entries.clear()

        anchor_colors = [
            ("403", "Schwarz"),
            ("47", "Rot"),
            ("309", "Gelb"),
            ("228", "Grün"),
            ("134", "Blau"),
            ("1", "Weiß"),
        ]

        for num, expected_name in anchor_colors:
            thread = anchor.find_by_number(num)
            if thread:
                pattern.add_color(thread)
                logger.debug(f"Anchor {num}: {thread.name}")
            else:
                logger.warning(f"Anchor-Farbe {num} ({expected_name}) nicht gefunden")

        if len(pattern.color_entries) < 5:
            logger.warning("Nicht genug Farben gefunden")
            return

        pattern.layer_stack[0].name = "Rahmen"

        for x in range(5, 35):
            pattern.set_stitch(x, 5, 4)
            pattern.set_stitch(x, 34, 4)
        for y in range(5, 35):
            pattern.set_stitch(5, y, 4)
            pattern.set_stitch(34, y, 4)

        for i in range(3):
            pattern.set_stitch(6 + i, 6 + i, 2)
            pattern.set_stitch(33 - i, 6 + i, 2)
            pattern.set_stitch(6 + i, 33 - i, 2)
            pattern.set_stitch(33 - i, 33 - i, 2)

        pattern.layer_stack.add_layer("Herz")

        heart = [
            "  ##  ##  ",
            " ######## ",
            "##########",
            "##########",
            " ######## ",
            "  ######  ",
            "   ####   ",
            "    ##    ",
        ]

        start_x = 15
        start_y = 12

        for dy, row in enumerate(heart):
            for dx, char in enumerate(row):
                if char == "#":
                    pattern.set_stitch(start_x + dx, start_y + dy, 1)

        pattern.layer_stack.add_layer("Details")

        stars = [(8, 10), (31, 10), (8, 30), (31, 30), (20, 25)]
        for sx, sy in stars:
            pattern.set_stitch(sx, sy, 2)

        pattern.layer_stack.active_index = 0
        pattern.recalculate_stitch_counts()

        if self.main_window:
            self.main_window.set_pattern(pattern)
