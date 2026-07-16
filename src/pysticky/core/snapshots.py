"""
Snapshot-System für .pxs-Pattern.

Speichert versionierte Kopien eines Patterns in einem App-Data-Verzeichnis.
Ergänzt das normale Autosave: das Autosave ist ein einziger Recovery-Punkt,
ein Snapshot ist Teil einer Versions-Timeline.

Verzeichnis-Layout:
    <appdata>/PySticky/snapshots/<pattern-key>/v_YYYY-MM-DD_HH-MM-SS.pxs
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

from ..utils.logging import get_logger

if TYPE_CHECKING:
    from .pattern import Pattern

logger = get_logger(__name__)


MAX_SNAPSHOTS_PER_PATTERN = 20
SNAPSHOT_INTERVAL_SECONDS = 30 * 60  # Default — 30 Minuten zwischen Snapshots

_FILENAME_FORMAT = "%Y-%m-%d_%H-%M-%S"


def get_configured_interval_seconds() -> int:
    """Liest das Snapshot-Intervall aus QSettings, sonst Default.

    QSettings-Schlüssel: `snapshot_interval_minutes` (int, in Minuten).
    Fällt bei fehlendem Qt (Test-Env) auf den Default-Wert zurück.
    """
    try:
        from PySide6.QtCore import QSettings

        settings = QSettings()
        minutes = cast(int, settings.value("snapshot_interval_minutes", 30, type=int))
        if minutes <= 0:
            return SNAPSHOT_INTERVAL_SECONDS
        return minutes * 60
    except Exception:  # noqa: BLE001 - Qt darf in Test-Env fehlen
        return SNAPSHOT_INTERVAL_SECONDS


def _safe_key(name: str) -> str:
    """Macht den Pattern-Namen dateinamen-safe (Slashes, Sonderzeichen raus)."""
    if not name:
        return "_unnamed"
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_")
    return cleaned or "_unnamed"


def get_snapshots_root() -> Path:
    """Liefert das Snapshot-Wurzel-Verzeichnis (plattform-konform).

    Auf Windows typisch: `%APPDATA%/PySticky/snapshots`
    Auf Linux/Mac: `~/.local/share/PySticky/snapshots` bzw. `~/Library/...`
    """
    try:
        from PySide6.QtCore import QStandardPaths

        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        if base:
            root = Path(base) / "snapshots"
        else:
            root = Path.home() / ".pysticky" / "snapshots"
    except Exception:  # noqa: BLE001 - Qt darf in Test-Env fehlen
        root = Path.home() / ".pysticky" / "snapshots"
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_pattern_dir(pattern_key: str) -> Path:
    """Liefert das Snapshot-Verzeichnis für einen Pattern-Key."""
    pdir = get_snapshots_root() / _safe_key(pattern_key)
    pdir.mkdir(parents=True, exist_ok=True)
    return pdir


def _snapshot_filename(when: datetime | None = None) -> str:
    when = when or datetime.now()
    return f"v_{when.strftime(_FILENAME_FORMAT)}.pxs"


def parse_snapshot_timestamp(path: Path) -> datetime | None:
    """Parst das Datum aus dem Snapshot-Dateinamen, None wenn nicht erkannt."""
    name = path.stem
    if not name.startswith("v_"):
        return None
    try:
        return datetime.strptime(name[2:], _FILENAME_FORMAT)
    except ValueError:
        return None


def list_snapshots(pattern_key: str) -> list[Path]:
    """Listet Snapshots eines Patterns, sortiert neueste zuerst."""
    pdir = get_pattern_dir(pattern_key)
    files: list[tuple[datetime, Path]] = []
    for p in pdir.glob("v_*.pxs"):
        ts = parse_snapshot_timestamp(p)
        if ts is not None:
            files.append((ts, p))
    files.sort(key=lambda t: t[0], reverse=True)
    return [p for _ts, p in files]


def create_snapshot(
    pattern: "Pattern",
    pattern_key: str,
    *,
    max_keep: int = MAX_SNAPSHOTS_PER_PATTERN,
) -> Path:
    """Erzeugt einen neuen Snapshot, räumt alte über `max_keep` auf.

    Returns:
        Pfad zur neu angelegten Snapshot-Datei.
    """
    from .file_io import save_pattern

    pdir = get_pattern_dir(pattern_key)
    filename = _snapshot_filename()
    target = pdir / filename
    # Falls innerhalb derselben Sekunde mehrere Snapshots — Suffix anhängen
    if target.exists():
        i = 1
        while target.exists():
            target = pdir / f"{filename[:-4]}_{i}.pxs"
            i += 1

    save_pattern(pattern, target)
    _cleanup_old_snapshots(pdir, max_keep=max_keep)
    return target


def _cleanup_old_snapshots(pdir: Path, max_keep: int) -> None:
    """Behält nur die `max_keep` neuesten Snapshots, löscht den Rest."""
    snapshots: list[tuple[datetime, Path]] = []
    for p in pdir.glob("v_*.pxs"):
        ts = parse_snapshot_timestamp(p)
        if ts is not None:
            snapshots.append((ts, p))
    if len(snapshots) <= max_keep:
        return
    snapshots.sort(key=lambda t: t[0], reverse=True)
    for _ts, old_path in snapshots[max_keep:]:
        try:
            old_path.unlink()
        except OSError:
            logger.warning("Alter Snapshot konnte nicht gelöscht werden: %s", old_path)


def should_snapshot(
    pattern_key: str,
    *,
    interval_seconds: int | None = None,
) -> bool:
    """True, wenn seit dem letzten Snapshot mehr als `interval_seconds` her sind.

    `interval_seconds=None` (Default) liest den User-Wert aus QSettings.
    """
    if interval_seconds is None:
        interval_seconds = get_configured_interval_seconds()
    snaps = list_snapshots(pattern_key)
    if not snaps:
        return True
    latest = parse_snapshot_timestamp(snaps[0])
    if latest is None:
        return True
    delta = datetime.now() - latest
    return delta.total_seconds() >= interval_seconds


def delete_snapshot(path: Path) -> bool:
    """Löscht einen einzelnen Snapshot. Returns True bei Erfolg."""
    try:
        path.unlink()
        return True
    except OSError:
        return False


def pattern_key_for(pattern: "Pattern", file_path: Path | None = None) -> str:
    """Liefert den Snapshot-Key für ein Pattern.

    Vorrang: aktueller Dateiname (stem) — sonst der Pattern-Name.
    So bleiben Snapshots stabil über Pattern-Umbenennungen.
    """
    if file_path is not None:
        return file_path.stem
    return pattern.name or "_unnamed"
