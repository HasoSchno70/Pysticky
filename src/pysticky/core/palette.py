"""
Paletten-Manager für Garn-Farbpaletten verschiedener Hersteller.

Thread-sicherer Singleton für den globalen Zugriff auf Paletten.
"""

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from ..utils.logging import get_logger
from .color_math import delta_e2000, rgb_to_lab
from .thread import Thread, ThreadColor

logger = get_logger(__name__)


@dataclass
class ThreadPalette:
    """
    Repräsentiert eine Garn-Farbpalette eines Herstellers.

    Attributes:
        name: Name der Palette (z.B. "DMC", "Madeira")
        manufacturer: Hersteller
        threads: Liste der verfügbaren Garne
        is_beads: True wenn dies eine Bead-Palette ist (Mill Hill, Toho, ...).
                  Farben aus Bead-Paletten werden im Pattern als BEAD-Stitch-Type
                  platziert, mit eigener Visualisierung und eigener Legende.
        is_diamond: True wenn dies eine Diamond-Painting-Palette ist (DMC DP,
                    Diamond Art Club, Diamond Dotz, ...). Farben werden im
                    Pattern als DIAMOND-Stitch-Type platziert und erscheinen
                    in der DP-Ansicht als facettierte Drills.
    """

    name: str
    manufacturer: str
    threads: list[Thread] = field(default_factory=list)
    is_beads: bool = False
    is_diamond: bool = False

    def __len__(self) -> int:
        return len(self.threads)

    def __iter__(self) -> Iterator[Thread]:
        return iter(self.threads)

    def __getitem__(self, index: int) -> Thread:
        return self.threads[index]

    def find_by_number(self, number: str) -> Thread | None:
        """Findet ein Garn nach Katalognummer."""
        for thread in self.threads:
            if thread.catalog_number == number:
                return thread
        return None

    def find_by_name(self, name: str) -> list[Thread]:
        """Findet Garne nach Name (Teilstring-Suche)."""
        name_lower = name.lower()
        return [t for t in self.threads if name_lower in t.name.lower()]

    def find_similar_color(self, color: ThreadColor, max_results: int = 5) -> list[Thread]:
        """
        Findet ähnliche Farben basierend auf perzeptueller CIE-Lab-Distanz.

        Nutzt CIEDE2000 statt RGB-Euklid — konsistent mit der
        Cross-Reference-Suche (thread_cross_ref.find_equivalent) und
        wahrnehmungsmäßig korrekter.

        Args:
            color: Zielfarbe
            max_results: Maximale Anzahl Ergebnisse

        Returns:
            Liste der ähnlichsten Garne, sortiert nach Ähnlichkeit
        """
        target_lab = rgb_to_lab(color.r, color.g, color.b)

        def color_distance(t: Thread) -> float:
            return delta_e2000(rgb_to_lab(t.color.r, t.color.g, t.color.b), target_lab)

        sorted_threads = sorted(self.threads, key=color_distance)
        return sorted_threads[:max_results]


class PaletteManager:
    """
    Manager für Garn-Farbpaletten.

    Lädt und verwaltet alle verfügbaren Paletten aus dem
    resources/palettes Verzeichnis.

    Thread-sicher durch Verwendung eines RLock für alle
    Schreib- und Leseoperationen auf die Paletten.
    """

    def __init__(self) -> None:
        self._palettes: dict[str, ThreadPalette] = {}
        self._palettes_dir: Path = Path(__file__).parent.parent / "resources" / "palettes"
        self._lock = threading.RLock()  # Reentrant lock für verschachtelte Aufrufe
        self._loaded = False

    @property
    def available_palettes(self) -> list[str]:
        """Liste der verfügbaren Paletten-Namen."""
        with self._lock:
            return list(self._palettes.keys())

    def load_all(self) -> None:
        """Lädt alle verfügbaren Paletten (thread-sicher)."""
        with self._lock:
            if self._loaded:
                return  # Bereits geladen

            if not self._palettes_dir.exists():
                logger.warning(f"Paletten-Verzeichnis nicht gefunden: {self._palettes_dir}")
                self._loaded = True
                return

            for json_file in self._palettes_dir.glob("*.json"):
                try:
                    self._load_palette_file(json_file)
                except (OSError, json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Fehler beim Laden von {json_file.name}: {e}")

            self._loaded = True

    def _load_palette_file(self, file_path: Path) -> None:
        """
        Lädt eine einzelne Paletten-Datei.

        Hinweis: Wird innerhalb von load_all() aufgerufen,
        das Lock wird dort bereits gehalten.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not data:
            return

        # Struktur validieren, BEVOR data[0]/first_entry.keys() darauf
        # zugreifen -- eine strukturell falsch geformte (aber syntaktisch
        # gueltige) JSON-Datei (z.B. ein Objekt statt einer Liste, oder eine
        # Liste mit Nicht-Dict-Eintraegen) wuerde sonst mit KeyError/
        # AttributeError/TypeError abstuerzen, was load_all()'s except-
        # Tuple nicht faengt -- und dabei das GESAMTE Laden weiterer
        # Palettendateien in derselben glob()-Schleife abbrechen, nicht nur
        # diese eine Datei (gleiche Fehlerklasse wie der pat_import.py-
        # Groessenlimit- und Inventory._load-Fund).
        if not isinstance(data, list) or not all(isinstance(entry, dict) for entry in data):
            raise ValueError(
                f"Erwartete Liste von Farb-Objekten in {file_path.name}, "
                f"bekam: {type(data).__name__}"
            )

        # Herstellernamen aus Dateinamen extrahieren
        filename = file_path.stem
        # "DMC_Farben" -> "DMC"
        # "Madeira_Stickgarn_Farben" -> "Madeira"
        # "Mill_Hill_Beads_Farben" -> "Mill Hill Beads" (is_beads=True)
        # "DMC_Diamond_Painting_Farben" -> "DMC Diamond Painting" (is_diamond=True)
        parts = filename.replace("_Farben", "").replace("_Stickgarn", "").replace("_Stick", "")
        manufacturer = parts.replace("_", " ").strip()
        # Bead-Erkennung: Manufacturer-Name enthält "Bead" (case-insensitive)
        is_beads = "bead" in manufacturer.lower()
        # Diamond-Painting-Erkennung: Manufacturer-Name enthält "Diamond"
        # (case-insensitive). Beads und Diamond schliessen sich aus —
        # ein Drill ist keine Perle.
        is_diamond = (not is_beads) and ("diamond" in manufacturer.lower())

        # Katalognummer-Feld finden (variiert je nach Hersteller)
        first_entry = data[0]
        number_field = None
        for key in first_entry.keys():
            if key.lower().endswith("number") or key == "Code":
                number_field = key
                break

        # Threads erstellen
        threads: list[Thread] = []
        for entry in data:
            # Ein einzelner fehlerhafter Eintrag (z.B. "Color": null oder
            # "R" als String statt Zahl -- beides syntaktisch gueltiges
            # JSON) darf nicht die GESAMTE Datei zum Absturz bringen --
            # ThreadColor.__post_init__ wirft dann TypeError, ".get()" auf
            # einem Nicht-Dict wirft AttributeError, beides ausserhalb von
            # load_all()'s except-Tuple. Stattdessen: diesen einen Eintrag
            # ueberspringen, Rest der Palette bleibt nutzbar.
            try:
                color_data = entry.get("Color", {})
                if not isinstance(color_data, dict):
                    raise ValueError(f"'Color' ist kein Objekt: {color_data!r}")

                thread = Thread(
                    name=entry.get("Name", "Unknown"),
                    color=ThreadColor(
                        r=color_data.get("R", 128),
                        g=color_data.get("G", 128),
                        b=color_data.get("B", 128),
                    ),
                    manufacturer=manufacturer,
                    catalog_number=str(entry.get(number_field, "")) if number_field else None,
                )
            except (AttributeError, TypeError, ValueError) as e:
                logger.warning(f"Ungültiger Farbeintrag in {file_path.name} übersprungen: {e}")
                continue
            threads.append(thread)

        # Palette erstellen und speichern
        palette = ThreadPalette(
            name=manufacturer,
            manufacturer=manufacturer,
            threads=threads,
            is_beads=is_beads,
            is_diamond=is_diamond,
        )
        self._palettes[manufacturer] = palette
        logger.debug(f"Palette geladen: {manufacturer} ({len(threads)} Farben)")

    def get_palette(self, name: str) -> ThreadPalette | None:
        """Gibt eine Palette nach Name zurück (thread-sicher)."""
        with self._lock:
            return self._palettes.get(name)

    def find_color_across_palettes(
        self, color: ThreadColor, max_per_palette: int = 3
    ) -> dict[str, list[Thread]]:
        """
        Findet ähnliche Farben in allen Paletten (thread-sicher).

        Args:
            color: Zielfarbe
            max_per_palette: Max. Ergebnisse pro Palette

        Returns:
            Dict mit Palette-Name -> Liste ähnlicher Threads
        """
        with self._lock:
            results: dict[str, list[Thread]] = {}

            for name, palette in self._palettes.items():
                similar = palette.find_similar_color(color, max_per_palette)
                if similar:
                    results[name] = similar

            return results

    def get_all_threads(self) -> list[Thread]:
        """Gibt alle Garne aus allen Paletten zurück (thread-sicher)."""
        with self._lock:
            all_threads: list[Thread] = []
            for palette in self._palettes.values():
                all_threads.extend(palette.threads)
            return all_threads

    def reload(self) -> None:
        """Lädt alle Paletten neu (thread-sicher)."""
        with self._lock:
            self._palettes.clear()
            self._loaded = False
        self.load_all()


# Thread-sichere Singleton-Implementierung
_palette_manager: PaletteManager | None = None
_singleton_lock = threading.Lock()


def get_palette_manager() -> PaletteManager:
    """
    Gibt den globalen Palette-Manager zurück (thread-sicher).

    Verwendet Double-Checked Locking Pattern für optimale
    Performance bei wiederholten Aufrufen.
    """
    global _palette_manager

    # Erster Check ohne Lock (schneller Pfad)
    if _palette_manager is not None:
        return _palette_manager

    # Lock für Thread-sichere Initialisierung
    with _singleton_lock:
        # Zweiter Check mit Lock (verhindert Race Condition)
        if _palette_manager is None:
            _palette_manager = PaletteManager()
            _palette_manager.load_all()

    return _palette_manager


def reset_palette_manager() -> None:
    """
    Setzt den globalen Palette-Manager zurück (für Tests).

    Thread-sicher.
    """
    global _palette_manager
    with _singleton_lock:
        _palette_manager = None
