# -*- coding: utf-8 -*-
"""
Utility-Modul für PySticky.

Enthält Hilfsfunktionen und -klassen.

Die Dialog-Helfer aus .errors (show_error, confirm, ...) werden LAZY
importiert (PEP 562): errors.py zieht PySide6 herein, und dieses Paket
soll auch aus Qt-freien Schichten (core/, io/) importierbar sein —
z.B. für get_logger und clamp.
"""

from typing import Any

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
from .numeric import clamp, clamp_int
from .os_open import open_path, reveal_in_file_manager

_ERROR_HELPERS = frozenset(
    (
        "ErrorContext",
        "confirm",
        "handle_errors",
        "safe_call",
        "show_error",
        "show_info",
        "show_warning",
    )
)


def __getattr__(name: str) -> Any:
    if name in _ERROR_HELPERS:
        from . import errors

        return getattr(errors, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Numerik
    "clamp",
    "clamp_int",
    # OS-übergreifendes Öffnen/Anzeigen von Dateien
    "open_path",
    "reveal_in_file_manager",
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
