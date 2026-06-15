"""
Error-Handling Utilities für PySticky.

Zentrale Fehlerbehandlung und User-Feedback.
"""

import traceback
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from PySide6.QtWidgets import QMessageBox, QWidget

from .logging import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def show_error(
    parent: QWidget | None, title: str, message: str, details: str | None = None
) -> None:
    """
    Zeigt einen Fehler-Dialog an.

    Args:
        parent: Eltern-Widget für den Dialog
        title: Dialog-Titel
        message: Kurze Fehlerbeschreibung
        details: Detaillierte Informationen (optional)
    """
    dialog = QMessageBox(parent)
    dialog.setIcon(QMessageBox.Icon.Critical)
    dialog.setWindowTitle(title)
    dialog.setText(message)

    if details:
        dialog.setDetailedText(details)

    dialog.exec()


def show_warning(parent: QWidget | None, title: str, message: str) -> None:
    """Zeigt einen Warnungs-Dialog an."""
    QMessageBox.warning(parent, title, message)


def show_info(parent: QWidget | None, title: str, message: str) -> None:
    """Zeigt einen Info-Dialog an."""
    QMessageBox.information(parent, title, message)


def confirm(
    parent: QWidget | None,
    title: str,
    message: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Yes
    | QMessageBox.StandardButton.No,
    default: QMessageBox.StandardButton = QMessageBox.StandardButton.No,
) -> bool:
    """
    Zeigt einen Bestätigungs-Dialog an.

    Returns:
        True wenn mit Ja/OK bestätigt wurde
    """
    result = QMessageBox.question(parent, title, message, buttons, default)
    return result in (QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.Ok)


def handle_errors(
    error_title: str = "Fehler",
    error_message: str = "Ein unerwarteter Fehler ist aufgetreten.",
    reraise: bool = False,
    log_level: str = "error",
) -> Callable[[Callable[P, T]], Callable[P, T | None]]:
    """
    Decorator für automatisches Error-Handling mit Dialog.

    Args:
        error_title: Titel des Fehler-Dialogs
        error_message: Standard-Fehlermeldung
        reraise: Exception erneut werfen?
        log_level: Log-Level für die Fehlermeldung

    Example:
        @handle_errors("Speichern fehlgeschlagen", "Datei konnte nicht gespeichert werden.")
        def save_file(self, path: str) -> bool:
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T | None]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
            try:
                return func(*args, **kwargs)
            except Exception as e:  # intentional catch-all
                # Logging
                log_func = getattr(logger, log_level, logger.error)
                log_func(f"{error_title}: {e}", exc_info=True)

                # Dialog anzeigen
                parent = None
                if args and isinstance(args[0], QWidget):
                    parent = args[0]
                elif args and hasattr(args[0], "parent") and callable(args[0].parent):
                    parent = args[0].parent()

                details = f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}"
                show_error(parent, error_title, f"{error_message}\n\n{e}", details)

                if reraise:
                    raise

                return None

        return wrapper

    return decorator


def safe_call(
    func: Callable[P, T], *args: P.args, default: T | None = None, **kwargs: P.kwargs
) -> T | None:
    """
    Ruft eine Funktion auf und fängt alle Exceptions ab.

    Args:
        func: Die aufzurufende Funktion
        *args: Positionsargumente
        default: Rückgabewert bei Fehler
        **kwargs: Keyword-Argumente

    Returns:
        Rückgabewert der Funktion oder default bei Fehler
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:  # intentional catch-all
        logger.warning(f"safe_call fehlgeschlagen für {func.__name__}: {e}")
        return default


class ErrorContext:
    """
    Context-Manager für Fehlerbehandlung in Code-Blöcken.

    Example:
        with ErrorContext("Datei laden", parent=self):
            data = load_file(path)
            process(data)
    """

    def __init__(
        self,
        operation: str,
        parent: QWidget | None = None,
        show_dialog: bool = True,
        reraise: bool = False,
    ) -> None:
        self.operation = operation
        self.parent = parent
        self.show_dialog = show_dialog
        self.reraise = reraise
        self.error: Exception | None = None

    def __enter__(self) -> "ErrorContext":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_val is not None:
            self.error = exc_val
            logger.error(f"{self.operation} fehlgeschlagen: {exc_val}", exc_info=True)

            if self.show_dialog:
                show_error(
                    self.parent,
                    f"{self.operation} fehlgeschlagen",
                    str(exc_val),
                    traceback.format_exc(),
                )

            return not self.reraise
        return False

    @property
    def success(self) -> bool:
        """True wenn kein Fehler aufgetreten ist."""
        return self.error is None
