"""
Projekt-Liste — verwaltet eine Liste von .pxs-Dateipfaden, die der User als
"aktive Projekte" markiert hat. Wird genutzt, um eine kombinierte
Einkaufsliste über mehrere Muster hinweg zu berechnen (core.inventory).

Persistenz: JSON-Datei im App-Daten-Verzeichnis (wie core.inventory).
"""

from __future__ import annotations

import json
from pathlib import Path

from ..utils.logging import get_logger

logger = get_logger(__name__)


def get_project_list_path() -> Path:
    """Pfad zur globalen Projekt-Listen-JSON-Datei (plattform-konform)."""
    try:
        from PySide6.QtCore import QStandardPaths

        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        if base:
            root = Path(base)
        else:
            root = Path.home() / ".pysticky"
    except Exception:  # noqa: BLE001 - Qt darf in Test-Env fehlen
        root = Path.home() / ".pysticky"
    root.mkdir(parents=True, exist_ok=True)
    return root / "projects.json"


class ProjectList:
    """Verwaltet die Liste registrierter Projekt-Dateien (.pxs-Pfade).

    Reine Pfad-Liste ohne Duplikate; Reihenfolge = Einfüge-Reihenfolge.
    Bei Änderungen muss `save()` explizit aufgerufen werden.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or get_project_list_path()
        self._paths: list[str] = []
        self._load()

    @property
    def path(self) -> Path:
        return self._path

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._paths = []
            return
        if isinstance(raw, dict):
            projects = raw.get("projects", [])
            if isinstance(projects, list):
                self._paths = [str(p) for p in projects]

    def save(self) -> None:
        """Schreibt die Projekt-Liste zurück auf die Platte."""
        payload = {"version": 1, "projects": self._paths}
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except OSError:
            logger.warning("Projektliste konnte nicht gespeichert werden: %s", self._path)

    def add(self, path: str | Path) -> bool:
        """Fügt einen Pfad hinzu. Gibt False zurück, wenn schon vorhanden.

        Normalisiert per resolve() (wie misc_handlers.py::_add_recent_file
        das schon für die Zuletzt-geöffnet-Liste tut) -- sonst würde
        derselbe Pfad relativ vs. absolut, oder mit "../"-Segmenten, als
        zwei unterschiedliche Einträge geführt.
        """
        p = str(Path(path).resolve())
        if p in self._paths:
            return False
        self._paths.append(p)
        return True

    def remove(self, path: str | Path) -> None:
        """Entfernt einen Pfad, falls vorhanden."""
        p = str(Path(path).resolve())
        if p in self._paths:
            self._paths.remove(p)

    def items(self) -> list[str]:
        """Liste aller registrierten Pfade (Einfüge-Reihenfolge)."""
        return list(self._paths)

    def __len__(self) -> int:
        return len(self._paths)
