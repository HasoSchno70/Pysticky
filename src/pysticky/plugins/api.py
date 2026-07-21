"""
Plugin-API: Datenklassen, Context-Protocol, Discovery, Run.

Kein Qt-Import auf Top-Level — die API selbst ist UI-frei und testbar.
Der `PluginContext` ist ein Protocol, das von der UI-Schicht implementiert
wird (z.B. `QtPluginContext`).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from ..utils.logging import get_logger

if TYPE_CHECKING:
    from ..core.pattern import Pattern

logger = get_logger(__name__)


class PluginError(Exception):
    """Fehler beim Laden oder Ausführen eines Plugins."""


@dataclass(frozen=True)
class PluginManifest:
    """Geparstes manifest.json eines Plugins."""

    id: str
    name: str
    version: str
    description: str
    entry_module: str = "plugin"
    entry_function: str = "run"

    @classmethod
    def from_dict(cls, data: dict) -> "PluginManifest":
        if not isinstance(data, dict):
            # manifest.json ist syntaktisch gueltiges JSON, aber die Wurzel
            # ist kein Objekt (z.B. null, eine Liste oder eine Zahl) -- ohne
            # diese Pruefung wirft `k not in data` ein TypeError, das
            # discover_plugins() nicht abfaengt und den gesamten Plugin-
            # Dialog fuer ALLE Plugins abstuerzen laesst, nicht nur das
            # kaputte.
            raise PluginError(
                f"Manifest muss ein JSON-Objekt sein, ist aber: {type(data).__name__}"
            )
        missing = [k for k in ("id", "name", "version") if k not in data]
        if missing:
            raise PluginError(f"Manifest fehlen Pflichtfelder: {missing}")
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            version=str(data["version"]),
            description=str(data.get("description", "")),
            entry_module=str(data.get("entry_module", "plugin")),
            entry_function=str(data.get("entry_function", "run")),
        )


@dataclass
class Plugin:
    """Ein entdecktes Plugin (noch nicht ausgeführt)."""

    manifest: PluginManifest
    directory: Path

    @property
    def id(self) -> str:
        return self.manifest.id

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def description(self) -> str:
        return self.manifest.description


class PluginContext(Protocol):
    """
    Protocol für den UI-Adapter, den Plugins bekommen.

    Die UI-Schicht (Qt) implementiert das. Headless-Tests können einen
    eigenen Mock-Context bauen.
    """

    def show_message(self, text: str) -> None: ...
    def show_error(self, text: str) -> None: ...
    def prompt_int(
        self,
        question: str,
        default: int = 0,
        minimum: int = 0,
        maximum: int = 1_000_000,
    ) -> int | None: ...
    def prompt_str(self, question: str, default: str = "") -> str | None: ...
    def progress(self, value: float, text: str = "") -> None: ...


# ---------- Discovery ----------


def _builtin_plugins_dir() -> Path:
    """Findet das builtin/-Plugin-Verzeichnis (Dev oder PyInstaller-Frozen)."""
    dev_path = Path(__file__).parent / "builtin"
    if dev_path.exists():
        return dev_path
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        frozen = Path(meipass) / "pysticky" / "plugins" / "builtin"
        if frozen.exists():
            return frozen
    return dev_path


def _user_plugins_dir() -> Path:
    return Path.home() / ".pysticky" / "plugins"


def discover_plugins(extra_dirs: list[Path] | None = None) -> list[Plugin]:
    """
    Findet alle Plugins in Built-in- und User-Verzeichnissen.

    Args:
        extra_dirs: Optionale zusätzliche Verzeichnisse zum Durchsuchen
                    (vor allem für Tests).

    Returns:
        Sortierte Liste der gefundenen Plugins. Bei Manifest-Fehlern
        wird das Plugin übersprungen (mit Warning-Log).
    """
    dirs = [_builtin_plugins_dir(), _user_plugins_dir()]
    if extra_dirs:
        dirs.extend(extra_dirs)

    plugins: list[Plugin] = []
    seen_ids: set[str] = set()

    for base in dirs:
        if not base.exists():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir():
                continue
            manifest_path = child / "manifest.json"
            if not manifest_path.exists():
                continue
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                manifest = PluginManifest.from_dict(data)
            except (OSError, json.JSONDecodeError, PluginError) as e:
                logger.warning(f"Plugin in {child} übersprungen: {e}")
                continue
            if manifest.id in seen_ids:
                logger.info(f"Plugin {manifest.id} bereits geladen, ueberspringe {child}")
                continue
            seen_ids.add(manifest.id)
            plugins.append(Plugin(manifest=manifest, directory=child))

    plugins.sort(key=lambda p: p.name.lower())
    return plugins


# ---------- Run ----------


def run_plugin(
    plugin: Plugin,
    pattern: "Pattern",
    ctx: PluginContext,
) -> Any:
    """
    Lädt das Entry-Modul, holt die Run-Function und ruft sie auf.

    Args:
        plugin:   Der zu startende Plugin.
        pattern:  Das aktuelle Muster (wird mutiert).
        ctx:      Der UI-Adapter.

    Returns:
        Der Rückgabewert der Plugin-Funktion (typischerweise None).

    Raises:
        PluginError: wenn das Modul oder die Funktion nicht ladbar/aufrufbar ist.
    """
    module_path = plugin.directory / f"{plugin.manifest.entry_module}.py"
    if not module_path.exists():
        raise PluginError(f"Entry-Modul nicht gefunden: {module_path}")

    spec = importlib.util.spec_from_file_location(
        f"pysticky_plugin_{plugin.id}",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise PluginError(f"Modul-Spec konnte nicht erzeugt werden: {module_path}")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise PluginError(f"Modul-Import fehlgeschlagen: {e}") from e

    fn = getattr(module, plugin.manifest.entry_function, None)
    if fn is None or not callable(fn):
        raise PluginError(
            f"Funktion '{plugin.manifest.entry_function}' nicht gefunden in {module_path}"
        )

    try:
        return fn(pattern, ctx)
    except Exception as e:
        raise PluginError(f"Plugin-Lauf fehlgeschlagen: {e}") from e
