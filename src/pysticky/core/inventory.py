"""
Garn-Vorratsliste — speichert pro Hersteller-Farbe wieviele Straenge
der User aktuell besitzt. Genutzt vom Statistics-Dialog zur Berechnung
einer Einkaufsliste fuer ein konkretes Muster.

Persistenz: JSON-Datei im App-Daten-Verzeichnis.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def get_inventory_path() -> Path:
    """Pfad zur globalen Inventory-JSON-Datei (plattform-konform)."""
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
    return root / "inventory.json"


def _key(manufacturer: str | None, catalog_number: str | None) -> str:
    """Eindeutiger Inventory-Key. Leerstrings werden in 'unknown' uebersetzt."""
    m = (manufacturer or "unknown").strip()
    c = (catalog_number or "unknown").strip()
    return f"{m}::{c}"


class Inventory:
    """Verwaltet die Garn-Vorratsliste.

    Die Daten werden flach als Dict gehalten: {key: strands_on_hand}.
    Bei Aenderungen muss `save()` explizit aufgerufen werden — Hot-Reload
    bei jedem Set waere bei vielen Aenderungen ineffizient.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or get_inventory_path()
        self._data: dict[str, int] = {}
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
            self._data = {}
            return
        if isinstance(raw, dict):
            stock = raw.get("stock", raw)  # Backward-compat: flat oder wrapped
            if isinstance(stock, dict):
                self._data = {str(k): int(v) for k, v in stock.items() if v is not None}

    def save(self) -> None:
        """Schreibt die Inventory zurueck auf die Platte."""
        payload = {
            "version": 1,
            "stock": dict(sorted(self._data.items())),
        }
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    # === Accessors ===

    def get(self, manufacturer: str | None, catalog_number: str | None) -> int:
        """Liefert die Strang-Anzahl, 0 wenn nicht hinterlegt."""
        return self._data.get(_key(manufacturer, catalog_number), 0)

    def set(self, manufacturer: str | None, catalog_number: str | None, strands: int) -> None:
        """Setzt die Strang-Anzahl. 0 = Eintrag entfernen."""
        k = _key(manufacturer, catalog_number)
        if strands <= 0:
            self._data.pop(k, None)
        else:
            self._data[k] = int(strands)

    def items(self) -> Iterable[tuple[str, int]]:
        """Iteriert (key, strands) ueber alle Eintraege."""
        return list(self._data.items())

    def clear(self) -> None:
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


def compute_shopping_list(
    pattern,
    inventory: Inventory,
    stitches_per_skein: dict[int, int],
) -> list[dict]:
    """Berechnet die Einkaufsliste fuer ein konkretes Pattern.

    Args:
        pattern: das Pattern (mit color_entries)
        inventory: globale Vorratsliste
        stitches_per_skein: Mapping fabric_count -> Stiche pro Strang

    Returns:
        Liste von Dicts pro Farbe: {
            "thread", "stitch_count", "needed_skeins", "on_hand", "to_buy"
        }
    """
    from math import ceil

    spk = stitches_per_skein.get(pattern.fabric_count, 1800)
    out: list[dict] = []
    for entry in pattern.color_entries:
        if entry.skip_stitching:
            continue
        thread = entry.thread
        count = entry.stitch_count
        if count <= 0:
            continue
        needed = ceil(count / spk)
        # Sicherheitszuschlag bei sehr vielen Stichen
        if count > 1000:
            needed += 1
        on_hand = inventory.get(thread.manufacturer, thread.catalog_number)
        to_buy = max(0, needed - on_hand)
        out.append(
            {
                "thread": thread,
                "stitch_count": count,
                "needed_skeins": needed,
                "on_hand": on_hand,
                "to_buy": to_buy,
            }
        )
    return out
