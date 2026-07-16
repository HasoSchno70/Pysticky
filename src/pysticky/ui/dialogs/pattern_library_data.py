"""
Datenklassen für die Muster-Bibliothek.

Enthält die Datenstrukturen LibraryEntry und LibraryData
für die Verwaltung von Kreuzstich-Mustern in der Bibliothek.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class LibraryEntry:
    """Ein Eintrag in der Muster-Bibliothek."""

    filepath: str
    name: str
    width: int
    height: int
    color_count: int
    stitch_count: int
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
            lib.entries.append(LibraryEntry(**e))
        return lib
