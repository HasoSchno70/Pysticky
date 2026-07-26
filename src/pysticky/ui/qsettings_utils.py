# -*- coding: utf-8 -*-
"""
Typisierter Zugriff auf QSettings.

PySide6s `QSettings.value(key, default, type=X)` ist zur Laufzeit korrekt
(gibt wirklich einen Wert vom Typ X zurück), aber die Typ-Stubs deklarieren
den Rückgabewert unabhängig vom `type=`-Argument als `object` -- das erzeugt
in praktisch jedem Aufrufer einen mypy-Fehler ("incompatible type object").
`typed_setting()` kapselt den `cast()` an einer einzigen Stelle.
"""

from typing import TypeVar, cast

from PySide6.QtCore import QSettings

T = TypeVar("T")


def typed_setting(settings: QSettings, key: str, default: T, value_type: type[T]) -> T:
    """Liest einen QSettings-Wert mit korrektem, mypy-sichtbarem Rückgabetyp."""
    return cast(T, settings.value(key, default, type=value_type))
