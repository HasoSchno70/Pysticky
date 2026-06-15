# -*- coding: utf-8 -*-
"""
Utility-Modul für PySticky.

Enthält Hilfsfunktionen und -klassen.
"""

from .errors import (
    ErrorContext,
    confirm,
    handle_errors,
    safe_call,
    show_error,
    show_info,
    show_warning,
)
from .logging import (
    PyStickLogger,
    critical,
    debug,
    error,
    get_logger,
    info,
    setup_logging,
    warning,
)

__all__ = [
    # Logging
    "setup_logging",
    "get_logger",
    "PyStickLogger",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    # Error Handling
    "show_error",
    "show_warning",
    "show_info",
    "confirm",
    "handle_errors",
    "safe_call",
    "ErrorContext",
]
