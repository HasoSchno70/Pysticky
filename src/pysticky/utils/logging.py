# -*- coding: utf-8 -*-
"""
Logging-Konfiguration für PySticky.

Verwendung:
    from pysticky.utils.logging import get_logger

    logger = get_logger(__name__)
    logger.info("Muster geladen")
    logger.error("Fehler beim Speichern", exc_info=True)
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Standard Log-Format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Farben für Console-Output (ANSI)
COLORS = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[32m",  # Grün
    "WARNING": "\033[33m",  # Gelb
    "ERROR": "\033[31m",  # Rot
    "CRITICAL": "\033[35m",  # Magenta
    "RESET": "\033[0m",  # Reset
}


class ColoredFormatter(logging.Formatter):
    """Formatter mit farbiger Ausgabe für die Konsole."""

    def format(self, record: logging.LogRecord) -> str:
        # Farbe basierend auf Level
        color = COLORS.get(record.levelname, COLORS["RESET"])
        reset = COLORS["RESET"]

        # Original-Format
        original = super().format(record)

        # Levelname einfärben
        colored_level = f"{color}{record.levelname:8}{reset}"
        return original.replace(f"{record.levelname:8}", colored_level, 1)


class PyStickLogger:
    """
    Singleton Logger-Manager für PySticky.

    Features:
    - Farbige Konsolen-Ausgabe
    - Optional: Datei-Logging
    - Konfigurierbare Log-Level
    """

    _instance: "PyStickLogger | None" = None
    _initialized: bool = False

    def __new__(cls) -> "PyStickLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._initialized = True
        self._root_logger = logging.getLogger("pysticky")
        self._root_logger.setLevel(logging.DEBUG)
        self._file_handler: logging.FileHandler | None = None

        # Console Handler (immer aktiv)
        self._setup_console_handler()

    def _setup_console_handler(self) -> None:
        """Richtet den Console-Handler ein."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # Farbiger Formatter für Konsole
        formatter = ColoredFormatter(LOG_FORMAT, LOG_DATE_FORMAT)
        console_handler.setFormatter(formatter)

        self._root_logger.addHandler(console_handler)

    def enable_file_logging(self, log_dir: Path | None = None, level: int = logging.DEBUG) -> Path:
        """
        Aktiviert Datei-Logging.

        Args:
            log_dir: Verzeichnis für Log-Dateien (default: ~/.pysticky/logs)
            level: Log-Level für Datei

        Returns:
            Pfad zur Log-Datei
        """
        if log_dir is None:
            log_dir = Path.home() / ".pysticky" / "logs"

        log_dir.mkdir(parents=True, exist_ok=True)

        # Log-Dateiname mit Datum
        timestamp = datetime.now().strftime("%Y-%m-%d")
        log_file = log_dir / f"pysticky_{timestamp}.log"

        # Alten Handler entfernen falls vorhanden
        if self._file_handler:
            self._root_logger.removeHandler(self._file_handler)

        # Neuen Handler erstellen
        self._file_handler = logging.FileHandler(log_file, encoding="utf-8", mode="a")
        self._file_handler.setLevel(level)

        # Standard-Formatter (ohne Farben)
        formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
        self._file_handler.setFormatter(formatter)

        self._root_logger.addHandler(self._file_handler)
        self._root_logger.info(f"File logging enabled: {log_file}")

        return log_file

    def disable_file_logging(self) -> None:
        """Deaktiviert Datei-Logging."""
        if self._file_handler:
            self._root_logger.removeHandler(self._file_handler)
            self._file_handler.close()
            self._file_handler = None

    def set_level(self, level: int) -> None:
        """Setzt den globalen Log-Level."""
        self._root_logger.setLevel(level)

    def set_console_level(self, level: int) -> None:
        """Setzt den Log-Level nur für die Konsole."""
        for handler in self._root_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(level)


# Globale Instanz
_logger_manager: PyStickLogger | None = None


def setup_logging(
    console_level: int = logging.INFO, file_logging: bool = False, log_dir: Path | None = None
) -> PyStickLogger:
    """
    Initialisiert das Logging-System.

    Args:
        console_level: Log-Level für Konsole
        file_logging: Datei-Logging aktivieren?
        log_dir: Verzeichnis für Log-Dateien

    Returns:
        Logger-Manager Instanz
    """
    global _logger_manager

    if _logger_manager is None:
        _logger_manager = PyStickLogger()

    _logger_manager.set_console_level(console_level)

    if file_logging:
        _logger_manager.enable_file_logging(log_dir)

    return _logger_manager


def get_logger(name: str) -> logging.Logger:
    """
    Holt einen Logger für ein Modul.

    Args:
        name: Modul-Name (üblicherweise __name__)

    Returns:
        Konfigurierter Logger

    Beispiel:
        logger = get_logger(__name__)
        logger.info("Nachricht")
    """
    # Sicherstellen dass Basis-Logger existiert
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = PyStickLogger()

    # Child-Logger unter pysticky.*
    if name.startswith("pysticky"):
        return logging.getLogger(name)
    else:
        return logging.getLogger(f"pysticky.{name}")


# Convenience-Funktionen für schnelles Logging
def debug(msg: str, *args, **kwargs) -> None:
    """Log debug message."""
    get_logger("app").debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs) -> None:
    """Log info message."""
    get_logger("app").info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs) -> None:
    """Log warning message."""
    get_logger("app").warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs) -> None:
    """Log error message."""
    get_logger("app").error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs) -> None:
    """Log critical message."""
    get_logger("app").critical(msg, *args, **kwargs)
