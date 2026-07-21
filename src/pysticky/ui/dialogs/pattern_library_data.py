"""
Datenklassen für die Muster-Bibliothek.

Enthält die Datenstrukturen LibraryEntry und LibraryData
für die Verwaltung von Kreuzstich-Mustern in der Bibliothek.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime

from ...utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LibraryEntry:
    """Ein Eintrag in der Muster-Bibliothek."""

    filepath: str
    name: str
    width: int
    height: int
    color_count: int
    stitch_count: int
    # Default 14 = DEFAULT_FABRIC_COUNT -- fuer Eintraege aus einer aelteren
    # library.json, die dieses Feld noch nicht kannte (physische-Groesse-
    # Anzeige in pattern_library_dialog.py nahm vorher IMMER 14ct an,
    # unabhaengig vom tatsaechlichen Stoff des Musters).
    fabric_count: int = 14
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    thumbnail_path: str | None = None
    added_date: str = ""
    last_opened: str = ""
    favorite: bool = False
    notes: str = ""

    def __post_init__(self):
        if not self.added_date:
            self.added_date = datetime.now().isoformat()


@dataclass
class LibraryData:
    """Gesamte Bibliotheks-Daten."""

    version: str = "1.0"
    entries: list[LibraryEntry] = field(default_factory=list)
    categories: list[str] = field(
        default_factory=lambda: [
            "Alle",
            "Favoriten",
            "Blumen",
            "Tiere",
            "Landschaften",
            "Alphabete",
            "Bordueren",
            "Weihnachten",
            "Ostern",
            "Sonstiges",
        ]
    )

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "entries": [asdict(e) for e in self.entries],
            "categories": self.categories,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LibraryData":
        lib = cls()
        lib.version = data.get("version", "1.0")
        lib.categories = data.get("categories", lib.categories)
        lib.entries = []
        for e in data.get("entries", []):
            # Ein einzelner fehlerhafter Eintrag (z.B. ein umbenanntes/
            # entferntes Feld aus einer aelteren library.json, oder eine
            # manuell kaputtbearbeitete Datei) darf nicht den kompletten
            # Bibliotheks-Load mitreissen -- gleiche Fehlerklasse wie
            # PaletteManager/Inventory: einzelne kaputte Eintraege
            # ueberspringen statt die ganze Liste (und den Dialog) crashen
            # zu lassen.
            try:
                lib.entries.append(LibraryEntry(**e))
            except TypeError as exc:
                logger.warning("Ungueltiger Bibliotheks-Eintrag uebersprungen: %s", exc)
        return lib
