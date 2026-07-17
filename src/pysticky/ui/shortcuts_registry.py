"""
Zentrale Registrierung anpassbarer Tastenkürzel.

Bislang gab es zwei komplett getrennte Listen: die echten `setShortcut()`-
Aufrufe an den QAction-/ToolButton-Erstellungsstellen (mw_actions_mixin.py,
tool_bar.py) und eine zweite, hart-codierte `DEFAULT_SHORTCUTS`-Liste im
Tastenkürzel-Settings-Tab, die nirgends gelesen wurde — "Bearbeiten" in den
Einstellungen hatte dadurch buchstäblich keine Wirkung.

Diese Registry vermeidet genau die Zwei-Listen-Falle: der Default-Wert
wird beim Registrieren direkt vom lebenden QAction/ToolButton abgelesen
(nicht hier erneut hart-codiert), einzige Quelle der Wahrheit bleiben die
echten setShortcut()-Aufrufe. Nur *welche* Aktionen überhaupt anpassbar
sind (die ID-zu-Label-Zuordnung) muss gepflegt werden — dort ist eine
vergessene neue Aktion nur eine Auslassung, kein falscher Wert.
"""

from __future__ import annotations

from typing import Protocol

from PySide6.QtCore import QSettings
from PySide6.QtGui import QKeySequence


class _ShortcutTarget(Protocol):
    """Gemeinsame Schnittstelle von QAction und QAbstractButton (ToolButton)."""

    def shortcut(self) -> QKeySequence: ...
    def setShortcut(self, shortcut: QKeySequence | str) -> None: ...


class ShortcutRegistry:
    """Sammelt anpassbare Tastenkürzel-Ziele und wendet Overrides an."""

    def __init__(self) -> None:
        self._targets: dict[str, _ShortcutTarget] = {}
        self._labels: dict[str, str] = {}
        self._defaults: dict[str, str] = {}

    def register(self, shortcut_id: str, target: _ShortcutTarget, label: str) -> None:
        """Registriert ein Ziel; merkt sich dessen AKTUELLEN Shortcut als Default."""
        self._targets[shortcut_id] = target
        self._labels[shortcut_id] = label
        self._defaults[shortcut_id] = target.shortcut().toString()

    def ids(self) -> list[str]:
        """IDs in Registrierungs-Reihenfolge (== Anzeige-Reihenfolge im Tab)."""
        return list(self._targets.keys())

    def label(self, shortcut_id: str) -> str:
        return self._labels.get(shortcut_id, shortcut_id)

    def default(self, shortcut_id: str) -> str:
        return self._defaults.get(shortcut_id, "")

    def current(self, shortcut_id: str) -> str:
        target = self._targets.get(shortcut_id)
        return target.shortcut().toString() if target else ""

    def all_current(self) -> dict[str, str]:
        return {sid: self.current(sid) for sid in self._targets}

    def set_shortcut(self, shortcut_id: str, key_sequence: str) -> None:
        """Setzt den Shortcut sofort auf dem lebenden Ziel."""
        target = self._targets.get(shortcut_id)
        if target is not None:
            target.setShortcut(QKeySequence(key_sequence))

    def reset_all(self) -> None:
        """Setzt alle Ziele auf ihren beim Start abgelesenen Default zurück."""
        for shortcut_id, default in self._defaults.items():
            self.set_shortcut(shortcut_id, default)

    def find_conflict(self, key_sequence: str, exclude_id: str | None = None) -> str | None:
        """Gibt die ID eines ANDEREN Ziels zurück, das bereits denselben
        Shortcut nutzt (oder None). Für die Duplikat-Warnung beim Editieren
        -- genau die Bug-Klasse, die schon zweimal manuell gefunden wurde
        (Ctrl+Shift+I, Ctrl+H), soll hier gar nicht erst neu entstehen können.
        """
        if not key_sequence:
            return None
        normalized = QKeySequence(key_sequence).toString()
        for shortcut_id in self._targets:
            if shortcut_id == exclude_id:
                continue
            if self.current(shortcut_id) == normalized:
                return shortcut_id
        return None


def apply_saved_overrides(registry: ShortcutRegistry, settings: QSettings) -> None:
    """Wendet in QSettings gespeicherte Custom-Shortcuts auf die Registry an.

    Wird sowohl beim Programmstart als auch nach jedem Speichern im
    Settings-Dialog aufgerufen (live, ohne Neustart).
    """
    # QSettings.value() kennt kein type=dict (nur die in der Fehlermeldung
    # gelisteten primitiven/Qt-Typen) -- daher ohne type= lesen und selbst
    # gegen alles Unerwartete (leerer String, falscher Typ nach manueller
    # QSettings-Manipulation) absichern.
    overrides = settings.value("shortcuts", {})
    if not isinstance(overrides, dict):
        return
    for shortcut_id, key_sequence in overrides.items():
        if key_sequence:
            registry.set_shortcut(shortcut_id, key_sequence)
