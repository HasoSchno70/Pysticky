"""
Garn-Vorratsliste — speichert pro Hersteller-Farbe wieviele Stränge
der User aktuell besitzt. Genutzt vom Statistics-Dialog zur Berechnung
einer Einkaufsliste für ein konkretes Muster.

Persistenz: JSON-Datei im App-Daten-Verzeichnis.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from ..utils.logging import get_logger
from .constants import DEFAULT_STITCHES_PER_SKEIN

if TYPE_CHECKING:
    from .thread import Thread

logger = get_logger(__name__)


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


def _key(manufacturer: str | None, catalog_number: str | None, name: str | None = None) -> str:
    """Eindeutiger Inventory-Key. Leerstrings werden in 'unknown' übersetzt.

    Sonderfall (zurückgestellter Fund aus Runde 22, hier nachgeholt): fehlen
    manufacturer UND catalog_number BEIDE (z.B. eine per Bildimport ohne
    Palette-Metadaten importierte oder manuell per Farbwähler angelegte
    Custom-Farbe), kollidierten vorher ALLE derartigen Farben auf denselben
    Schlüssel "unknown::unknown" und teilten sich dadurch ungewollt einen
    gemeinsamen Lagerbestand. Ist in diesem Fall ein Farbname bekannt, wird
    er als drittes Schlüssel-Segment angehängt ("unknown::unknown::<name>"),
    um verschiedene "unbekannte" Farben auseinanderzuhalten.

    Rückwärtskompatibilität: Der alte zweiteilige Schlüssel "unknown::unknown"
    wird nur noch erzeugt, wenn zusätzlich auch kein Name vorliegt -- bereits
    gespeicherte alte Einträge mit diesem Schlüssel bleiben beim Laden
    unverändert gültig (siehe `_load()`, das keine Annahme über das Format
    des Keys trifft), sie werden schlicht nicht mehr neu erzeugt, sobald ein
    Aufrufer einen Namen mitgibt.
    """
    m = (manufacturer or "").strip()
    c = (catalog_number or "").strip()
    if not m and not c:
        n = (name or "").strip()
        if n:
            return f"unknown::unknown::{n}"
        return "unknown::unknown"
    return f"{m or 'unknown'}::{c or 'unknown'}"


def _shoppable_threads(thread: "Thread") -> list["Thread"]:
    """Liefert die tatsaechlich kaufbaren Garne fuer einen Einkaufslisten-Eintrag.

    Fuer einen normalen Thread ist das nur er selbst. Fuer einen Tweed-Blend
    (`thread.is_blend`) waeren Hersteller/Katalognummer des Blends selbst
    eine synthetische Kombination (z.B. "DMC" / "310+745", siehe
    `Thread.blend()`) -- kein Geschaeft verkauft ein Garn mit dieser
    Katalognummer, und ein bereits vorhandener Vorrat der beiden ECHTEN
    Komponenten-Garne (DMC 310, DMC 745) wuerde nie gefunden, weil er unter
    deren eigenen Schluesseln liegt. Ohne diese Aufloesung erschien fuer
    jeden Blend ein Phantom-Eintrag, der nie mit echtem Vorrat abgeglichen
    werden konnte (immer on_hand=0), waehrend die beiden echten Garne in
    der Liste komplett fehlten. Jede Blend-Komponente braucht fuer JEDEN
    Stich einen eigenen vollen Strang (beide Faeden laufen gemeinsam durch
    dieselbe Nadel) -- die Stichzahl wird daher pro Komponente in voller
    Hoehe gezaehlt, nicht aufgeteilt.
    """
    if thread.is_blend and thread.blend_components:
        return list(thread.blend_components)
    return [thread]


def split_key(key: str) -> tuple[str, str, str]:
    """Zerlegt einen Inventory-Key zurück in (manufacturer, catalog_number, name).

    Inverse zu `_key()`. `name` ist nur beim "unknown::unknown::<name>"-
    Sonderfall nicht-leer -- bei allen anderen Schlüsseln (inklusive alter,
    zweiteiliger Legacy-Schlüssel) ist es "".
    """
    parts = key.split("::", 2)
    mfr = parts[0] if len(parts) > 0 else ""
    num = parts[1] if len(parts) > 1 else ""
    name = parts[2] if len(parts) > 2 else ""
    return mfr, num, name


class Inventory:
    """Verwaltet die Garn-Vorratsliste.

    Die Daten werden flach als Dict gehalten: {key: strands_on_hand}.
    Bei Änderungen muss `save()` explizit aufgerufen werden — Hot-Reload
    bei jedem Set wäre bei vielen Änderungen ineffizient.
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
        except (OSError, json.JSONDecodeError, ValueError):
            # ValueError deckt u.a. UnicodeDecodeError ab (Datei mit
            # ungueltiger Kodierung, z.B. durch einen abgebrochenen Schreib-
            # vorgang) -- ohne das crashte das Laden der Inventory statt
            # sauber auf eine leere Vorratsliste zurueckzufallen.
            self._data = {}
            return
        if isinstance(raw, dict):
            stock = raw.get("stock", raw)  # Backward-compat: flat oder wrapped
            if isinstance(stock, dict):
                data: dict[str, int] = {}
                for k, v in stock.items():
                    if v is None:
                        continue
                    try:
                        data[str(k)] = int(v)
                    except (TypeError, ValueError):
                        # Einzelner kaputter Wert (z.B. hand-editierte Datei
                        # mit "abc" statt einer Zahl) ueberspringen statt die
                        # ganze Vorratsliste an einem Eintrag scheitern zu
                        # lassen -- vorher liess ein ungueltiger Wert den
                        # Statistik-Dialog/Einkaufsliste-Tab komplett crashen.
                        continue
                self._data = data

    def save(self) -> None:
        """Schreibt die Inventory zurück auf die Platte."""
        payload = {
            "version": 1,
            "stock": dict(sorted(self._data.items())),
        }
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except OSError:
            logger.warning("Garn-Vorrat konnte nicht gespeichert werden: %s", self._path)

    # === Accessors ===

    def get(
        self,
        manufacturer: str | None,
        catalog_number: str | None,
        name: str | None = None,
    ) -> int:
        """Liefert die Strang-Anzahl, 0 wenn nicht hinterlegt.

        `name` ist optional und wird nur als Schlüssel-Fallback genutzt,
        wenn manufacturer UND catalog_number beide leer sind (siehe
        `_key()`) -- für Farben mit bekanntem Hersteller/Katalognummer
        ändert sich dadurch nichts.
        """
        return self._data.get(_key(manufacturer, catalog_number, name), 0)

    def set(
        self,
        manufacturer: str | None,
        catalog_number: str | None,
        strands: int,
        name: str | None = None,
    ) -> None:
        """Setzt die Strang-Anzahl. 0 = Eintrag entfernen.

        `name`: siehe `get()`.
        """
        k = _key(manufacturer, catalog_number, name)
        if strands <= 0:
            self._data.pop(k, None)
        else:
            self._data[k] = int(strands)

    def items(self) -> Iterable[tuple[str, int]]:
        """Iteriert (key, strands) über alle Einträge."""
        return list(self._data.items())

    def clear(self) -> None:
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


def compute_shopping_list(
    pattern,
    inventory: Inventory,
    stitches_per_skein: dict[int, int],
    waste_percent: float = 20.0,
) -> list[dict]:
    """Berechnet die Einkaufsliste für ein konkretes Pattern.

    Diamond-Painting-Muster (`pattern.mode == "diamond"`) kennen keine
    Strang-pro-Stoffzaehlung-Umrechnung -- ein Drill wird stueckweise
    verbraucht, nicht nach Aida-Zaehlung aus einem Garnstrang geschnitten.
    Fuer solche Muster wird "needed_skeins" daher NICHT durch
    `stitches_per_skein` geteilt, sondern zeigt die (mit Sicherheits-
    zuschlag versehene) absolute Drill-Anzahl. Es gibt in dieser App keine
    etablierte Verpackungsgroesse fuer DP-Nachschub (Beutel/Rollen sind
    herstellerabhaengig und nicht recherchierbar) -- die absolute Stueckzahl
    ist daher die einzige verlaesslich richtige Zahl (siehe
    dead-code-and-export-gaps.md).

    Args:
        pattern: das Pattern (mit color_entries)
        inventory: globale Vorratsliste
        stitches_per_skein: Mapping fabric_count -> Stiche pro Strang
            (wird fuer Diamond-Painting-Farben ignoriert, siehe oben)
        waste_percent: Verschnitt-/Sicherheits-Zuschlag in Prozent (Default
            20, wie statistics_tabs/thread_tab.py's Standard-Vorbelegung --
            dieselbe Formel wie dort (`ceil(exact_skeins * (1 +
            waste_percent/100))`), damit Garnverbrauch- und Einkaufsliste-
            Tab nicht mehr auf unterschiedliche "benoetigte Straenge"-Zahlen
            fuer dasselbe Muster kommen (siehe dead-code-and-export-gaps.md).
            Gilt fuer Diamond-Painting-Farben analog als Puffer fuer
            verlorene/beschaedigte Drills.

    Returns:
        Liste von Dicts pro Farbe: {
            "thread", "stitch_count", "needed_skeins", "on_hand", "to_buy",
            "is_diamond"
        }
    """
    from math import ceil

    is_diamond = getattr(pattern, "mode", "stitch") == "diamond"
    spk = (
        1
        if is_diamond
        else stitches_per_skein.get(pattern.fabric_count, DEFAULT_STITCHES_PER_SKEIN)
    )
    waste_factor = 1 + (waste_percent / 100)
    out: list[dict] = []
    for entry in pattern.color_entries:
        if entry.skip_stitching:
            continue
        thread = entry.thread
        count = entry.stitch_count
        if count <= 0:
            continue
        needed = ceil((count / spk) * waste_factor)
        # Tweed-Blends: gegen die ECHTEN Komponenten-Garne abgleichen statt
        # gegen den synthetischen Blend-Thread (siehe _shoppable_threads()).
        for real_thread in _shoppable_threads(thread):
            on_hand = inventory.get(
                real_thread.manufacturer, real_thread.catalog_number, real_thread.name
            )
            to_buy = max(0, needed - on_hand)
            out.append(
                {
                    "thread": real_thread,
                    "stitch_count": count,
                    "needed_skeins": needed,
                    "on_hand": on_hand,
                    "to_buy": to_buy,
                    "is_diamond": is_diamond,
                }
            )
    return out


def compute_shopping_list_multi(
    patterns: Iterable,
    inventory: Inventory,
    stitches_per_skein: dict[int, int],
    waste_percent: float = 20.0,
) -> list[dict]:
    """Berechnet die kombinierte Einkaufsliste über mehrere Muster hinweg.

    Summiert den Garnbedarf (in Strängen) pro Farbe über alle übergebenen
    Patterns, bevor der Vorrat EINMAL insgesamt abgezogen wird — so wird
    derselbe Vorrats-Strang nicht mehrfach (einmal pro Projekt) verrechnet.

    Jedes Pattern behaelt seine eigene Modus-Rechnung (siehe
    compute_shopping_list()): Diamond-Painting-Patterns liefern die
    absolute Drill-Stueckzahl statt einer Strang-Umrechnung, auch wenn sie
    hier zusammen mit Kreuzstich-Projekten aggregiert werden.

    Args:
        patterns: die zu aggregierenden Patterns (mit color_entries)
        inventory: globale Vorratsliste
        stitches_per_skein: Mapping fabric_count -> Stiche pro Strang
        waste_percent: Verschnitt-Zuschlag in Prozent (siehe
            compute_shopping_list() -- dieselbe Konvention)

    Returns:
        Liste von Dicts pro Farbe: {
            "thread", "needed_skeins", "on_hand", "to_buy", "is_diamond"
        }
        "is_diamond" ist True, wenn die Farbe (mindestens einmal) aus einem
        Diamond-Painting-Pattern stammt -- bei einer Farbe, die in einem
        Kreuzstich- UND einem DP-Projekt gleichzeitig registriert ist (der
        gleiche Hersteller/Katalognummer-Schluessel), gewinnt der zuerst
        gesehene Eintrag, analog zu `thread_by_key.setdefault()` unten.
    """
    from math import ceil

    waste_factor = 1 + (waste_percent / 100)
    needed_by_key: dict[str, int] = {}
    thread_by_key: dict[str, "Thread"] = {}
    is_diamond_by_key: dict[str, bool] = {}
    for pattern in patterns:
        is_diamond = getattr(pattern, "mode", "stitch") == "diamond"
        spk = (
            1
            if is_diamond
            else stitches_per_skein.get(pattern.fabric_count, DEFAULT_STITCHES_PER_SKEIN)
        )
        for entry in pattern.color_entries:
            if entry.skip_stitching:
                continue
            thread = entry.thread
            count = entry.stitch_count
            if count <= 0:
                continue
            needed = ceil((count / spk) * waste_factor)
            # Tweed-Blends: auf die ECHTEN Komponenten-Garne aufteilen statt
            # unter dem synthetischen Blend-Schluessel zu sammeln (siehe
            # _shoppable_threads()) -- sonst landet der Bedarf unter einem
            # Schluessel, den kein Vorrat je erreichen kann.
            for real_thread in _shoppable_threads(thread):
                key = _key(real_thread.manufacturer, real_thread.catalog_number, real_thread.name)
                needed_by_key[key] = needed_by_key.get(key, 0) + needed
                thread_by_key.setdefault(key, real_thread)
                is_diamond_by_key.setdefault(key, is_diamond)

    out: list[dict] = []
    for key in sorted(needed_by_key):
        thread = thread_by_key[key]
        needed = needed_by_key[key]
        on_hand = inventory.get(thread.manufacturer, thread.catalog_number, thread.name)
        to_buy = max(0, needed - on_hand)
        out.append(
            {
                "thread": thread,
                "needed_skeins": needed,
                "on_hand": on_hand,
                "to_buy": to_buy,
                "is_diamond": is_diamond_by_key[key],
            }
        )
    return out
