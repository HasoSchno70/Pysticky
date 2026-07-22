"""
Hersteller-Cross-Reference für die Legende.

Sucht zu einem gegebenen Thread (z.B. DMC 310) die jeweils farblich
nächste Entsprechung in einer Ziel-Palette (Anchor, Madeira, ...).

Es gibt keine offiziellen 1:1-Mappings zwischen den Hersteller-Kataloge,
darum nutzen wir Delta-E (CIEDE2000 in Lab) — wahrnehmungsbasiert besser als
plain RGB. Der Algorithmus ist deterministisch und liefert pro Frage
denselben Match.

Performance: bei ~500 Threads pro Palette und ~50 Pattern-Farben ist das
50 * 500 = 25k Distance-Berechnungen — Millisekunden in numpy. Ergebnisse
werden gecached, damit wiederholte Aufrufe O(1) sind.
"""

from __future__ import annotations

from functools import lru_cache

from ..utils.logging import get_logger
from .color_math import nearest_index_by_lab
from .palette import get_palette_manager
from .thread import Thread

logger = get_logger(__name__)


def find_equivalent(
    thread: Thread,
    target_palette_name: str,
) -> Thread | None:
    """
    Findet zu einem Thread die naheste Entsprechung in einer Ziel-Palette.

    Args:
        thread: Quell-Thread (z.B. DMC 310).
        target_palette_name: Name der Ziel-Palette (z.B. "Anchor", "Madeira").

    Returns:
        Nähester Thread aus der Ziel-Palette, oder None wenn die Palette
        nicht existiert oder leer ist.

    Note:
        Wenn `thread` bereits aus der Ziel-Palette stammt (gleicher
        Manufacturer und gleiche Catalog-Number), wird er unverändert
        zurückgegeben.
    """
    if thread.manufacturer and thread.manufacturer.lower() == target_palette_name.lower():
        return thread

    return _cached_find(
        thread.color.r,
        thread.color.g,
        thread.color.b,
        target_palette_name,
    )


def find_equivalents(
    thread: Thread,
    target_palette_names: list[str],
) -> dict[str, Thread | None]:
    """
    Findet zu einem Thread die nahesten Entsprechungen in mehreren Paletten.

    Args:
        thread: Quell-Thread.
        target_palette_names: Liste von Ziel-Palette-Namen.

    Returns:
        Dict palette_name -> Thread (oder None wenn nicht gefunden ODER
        wenn die Aufloesung fuer GENAU diese Palette fehlschlaegt).

    Note:
        Jede Palette wird einzeln abgefangen -- ein fehlerhafter Thread/
        Farbeintrag in EINER Ziel-Palette darf nicht die Cross-Reference-
        Aufloesung fuer die anderen angefragten Paletten mitreissen (beide
        PDF- und HTML-Export rufen dies ungeschuetzt in einer Pro-Thread-
        Schleife auf -- ein einzelner kaputter Eintrag haette sonst den
        gesamten Export abgebrochen, nicht nur die eine Palette).
    """
    result: dict[str, Thread | None] = {}
    for name in target_palette_names:
        try:
            result[name] = find_equivalent(thread, name)
        except Exception as e:  # noqa: BLE001 - Palette-Daten koennen fehlerhaft sein
            logger.warning(f"Cross-Reference fuer Palette '{name}' fehlgeschlagen: {e}")
            result[name] = None
    return result


def clear_cache() -> None:
    """Leert den Lookup-Cache (z.B. nach Palette-Reload)."""
    _cached_find.cache_clear()


# ---------- Intern ----------


@lru_cache(maxsize=4096)
def _cached_find(
    r: int,
    g: int,
    b: int,
    target_palette_name: str,
) -> Thread | None:
    """Cached-Variante: arbeitet mit primitiven Typen, damit lru_cache greift."""
    pm = get_palette_manager()
    pm.load_all()
    palette = pm.get_palette(target_palette_name)
    if palette is None or not palette.threads:
        return None

    best_idx = nearest_index_by_lab(
        (r, g, b),
        [(t.color.r, t.color.g, t.color.b) for t in palette.threads],
    )
    return palette.threads[best_idx]
