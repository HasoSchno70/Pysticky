"""
Kreuzstich-Muster Klassen.

Dieses Modul enthält die Hauptklasse Pattern, die ein vollständiges
Kreuzstich-Muster repräsentiert, sowie ColorEntry für die Farbverwaltung.

Ein Pattern besteht aus:
    - Mehreren Layern (wie in Bildbearbeitungsprogrammen)
    - Einer Farbpalette mit Symbolen
    - Optionalen Rückstichen (Backstitches) für Konturen
    - Metadaten (Größe, Stoffzählung, etc.)

Example:
    >>> from pysticky.core import Pattern, Thread
    >>> pattern = Pattern(name="Blume", width=100, height=100)
    >>> pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
    >>> pattern.set_stitch(10, 10, color_index=0)
    >>> pattern.get_statistics()
    {'name': 'Blume', 'width': 100, ...}
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator, Optional

import numpy as np

if TYPE_CHECKING:
    from .layer import Layer
from pathlib import Path

from .backstitch_manager import Backstitch, BackstitchManager
from .constants import DEFAULT_FABRIC_COUNT, DEFAULT_PATTERN_HEIGHT, DEFAULT_PATTERN_WIDTH
from .layer import NO_STITCH, Layer, LayerStack
from .thread import Thread


def load_symbols() -> list[str]:
    """
    Lädt die verfügbaren Symbole für die Farbdarstellung.

    Symbole werden aus resources/symbols.txt geladen.
    Falls die Datei nicht existiert, werden Fallback-Symbole verwendet.

    Returns:
        Liste von Unicode-Symbolen für die Pattern-Darstellung
    """
    symbols_path = Path(__file__).parent.parent / "resources" / "symbols.txt"
    if symbols_path.exists():
        with open(symbols_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    # Fallback-Symbole
    return [
        "●",
        "○",
        "■",
        "□",
        "▲",
        "△",
        "◆",
        "◇",
        "★",
        "☆",
        "+",
        "×",
        "/",
        "\\",
        "~",
        "@",
        "&",
        "%",
    ]


# Globale Symbol-Liste
SYMBOLS = load_symbols()


@dataclass
class ColorEntry:
    """
    Repräsentiert eine Farbe im Muster mit zugehörigem Symbol.

    Jede Farbe in der Palette hat ein eindeutiges Symbol für die
    Schwarz-Weiß-Darstellung und Anleitung.

    Attributes:
        thread: Das Garn/die Farbe (Thread-Objekt)
        symbol: Das Symbol für diese Farbe im Muster (z.B. "●", "X")
        stitch_count: Anzahl der Stiche mit dieser Farbe (automatisch gezählt)
        skip_stitching: Wenn True, wird diese Farbe nicht gestickt
                       (z.B. wenn sie der Stofffarbe entspricht)

    Example:
        >>> entry = ColorEntry(
        ...     thread=Thread.from_hex("Rot", "#FF0000"),
        ...     symbol="●",
        ...     stitch_count=100
        ... )
        >>> entry.skip_stitching = True  # Farbe entspricht Stoff
    """

    thread: Thread
    symbol: str
    stitch_count: int = 0
    skip_stitching: bool = False
    strands: int = 2
    is_bead: bool = False  # True wenn die Farbe aus einer Bead-Palette stammt
    # — Stiche dieser Farbe werden automatisch als BEAD
    # platziert und in der Legende separat aufgefuehrt.
    is_diamond: bool = False  # True wenn die Farbe aus einer Diamond-Painting-
    # Palette stammt — Stiche werden als DIAMOND
    # platziert, in der DP-Ansicht als facettierter
    # Drill dargestellt und in der Legende mit Drill-
    # Codes (statt Garn-Strang-Bedarf) gefuehrt.

    def __repr__(self) -> str:
        skip = " [SKIP]" if self.skip_stitching else ""
        return f"ColorEntry({self.symbol}, '{self.thread.name}', {self.stitch_count}{skip})"


# Backstitch ist jetzt in backstitch_manager.py definiert


@dataclass
class Pattern:
    """
    Repräsentiert ein vollständiges Kreuzstich-Muster.

    Das Muster besteht aus mehreren Layern (wie in Photoshop),
    die übereinander gerendert werden. Jedes Layer hat ein eigenes
    numpy-basiertes Grid für effiziente Speicherung.

    Attributes:
        name: Name des Musters (für Anzeige und Dateiname)
        width: Breite in Stichen
        height: Höhe in Stichen
        layer_stack: Stack aller Layer (von unten nach oben)
        color_entries: Liste der verwendeten Farben mit Symbolen
        backstitch_manager: Verwaltet alle Rückstiche
        fabric_count: Stoffzählung (Stiche pro Inch, z.B. 14, 16, 18)
        metadata: Zusätzliche Metadaten (frei verwendbar)
        source_image_path: Pfad zum Originalbild (falls aus Bild importiert)
        source_image_crop: Ausschnitt des Originalbilds (x1, y1, x2, y2) normalisiert
        source_palette_name: Name der verwendeten Palette beim Import

    Example:
        >>> pattern = Pattern(name="Blume", width=100, height=100, fabric_count=16)
        >>> pattern.add_color(Thread.from_hex("Rot", "#FF0000"))
        >>> pattern.set_stitch(50, 50, color_index=0)
        >>> print(pattern.total_stitches)
        1
    """

    name: str = "Neues Muster"
    width: int = DEFAULT_PATTERN_WIDTH
    height: int = DEFAULT_PATTERN_HEIGHT
    # layer_stack/backstitch_manager werden, wenn nicht uebergeben, in
    # __post_init__ aus width/height erzeugt. Sie sind danach IMMER gesetzt;
    # der None-Default ist nur ein Init-Sentinel. Typ daher non-Optional
    # (das `type: ignore` betrifft nur den Sentinel-Default), damit die
    # vielen Zugriffe nicht ueberall ein None-Narrowing brauchen.
    layer_stack: LayerStack = None  # type: ignore[assignment]
    color_entries: list[ColorEntry] = field(default_factory=list)
    backstitch_manager: BackstitchManager = None  # type: ignore[assignment]
    fabric_count: int = DEFAULT_FABRIC_COUNT
    metadata: dict = field(default_factory=dict)
    # Für Palettenwechsel: Originalbild-Infos speichern
    source_image_path: Optional[str] = None
    source_image_crop: tuple[float, float, float, float] = (0, 0, 1, 1)
    source_palette_name: Optional[str] = None
    # Pattern-Modus: "stitch" (Kreuzstich) oder "diamond" (Diamond Painting).
    # Bestimmt die Default-View-Optik und welche Werkzeuge / Labels / Zeit-
    # Berechnungen die UI anzeigt. Wird in .pxs persistiert, sodass jedes
    # Muster nach dem Laden im richtigen Modus auftaucht.
    mode: str = "stitch"

    def __post_init__(self) -> None:
        """Initialisiert Defaults, die von width/height abhaengen."""
        if self.layer_stack is None:
            self.layer_stack = LayerStack(self.width, self.height)
        if self.backstitch_manager is None:
            self.backstitch_manager = BackstitchManager()
        if not self.color_entries:
            # Standard-Startfarbe — entfaellt z.B. beim Laden aus Datei,
            # wo color_entries direkt aus dem Konstruktor uebergeben wird.
            self.add_color(
                Thread.from_hex("Schwarz", "#000000", manufacturer="DMC", catalog_number="310")
            )

    @property
    def active_layer(self) -> Optional[Layer]:
        """Das aktuell aktive Layer."""
        return self.layer_stack.active_layer

    def resize(self, new_width: int, new_height: int) -> None:
        """
        Ändert die Größe des Musters und aller Layer.

        Args:
            new_width: Neue Breite (min. 1)
            new_height: Neue Höhe (min. 1)

        Raises:
            ValueError: Wenn Breite oder Höhe < 1
        """
        if new_width < 1 or new_height < 1:
            raise ValueError(f"Ungültige Größe: {new_width}x{new_height} (min. 1x1)")

        self.width = new_width
        self.height = new_height
        self.layer_stack.resize(new_width, new_height)

    def get_stitch(self, x: int, y: int) -> Optional[int]:
        """
        Gibt den sichtbaren Farbindex an Position (x, y) zurück.

        Berücksichtigt alle sichtbaren Layer.
        """
        return self.layer_stack.get_composite_stitch(x, y)

    def get_stitch_on_active_layer(self, x: int, y: int) -> Optional[int]:
        """Gibt den Farbindex auf dem aktiven Layer zurück."""
        layer = self.active_layer
        if layer:
            return layer.get_stitch(x, y)
        return None

    def set_stitch(self, x: int, y: int, color_index: Optional[int], stitch_type: int = 0) -> bool:
        """
        Setzt einen Stich auf dem aktiven Layer.

        Args:
            x: X-Koordinate des Stichs
            y: Y-Koordinate des Stichs
            color_index: Index der Farbe in color_entries, oder None zum Löschen
            stitch_type: Stichtyp (0=FULL, 1=HALF_TL_BR, etc.)

        Returns:
            True wenn erfolgreich, False bei ungültigem Index oder gesperrtem Layer
        """
        # Validierung des Farbindex
        if color_index is not None and not (0 <= color_index < len(self.color_entries)):
            return False

        layer = self.active_layer
        if not layer:
            return False

        old_index = layer.get_stitch(x, y)

        # Alte Farbe Stichzahl reduzieren
        if old_index is not None and 0 <= old_index < len(self.color_entries):
            self.color_entries[old_index].stitch_count -= 1

        # Bead- und Diamond-Farben werden immer als BEAD- bzw. DIAMOND-Stitch-
        # Type platziert, unabhaengig vom uebergebenen stitch_type. So muss
        # kein Tool explizit wissen, was eine Bead/Drill-Farbe ist — die
        # Farbe entscheidet.
        if color_index is not None and stitch_type == 0:
            from .stitch import StitchType

            entry = self.color_entries[color_index]
            if entry.is_bead:
                stitch_type = StitchType.BEAD.value
            elif entry.is_diamond:
                stitch_type = StitchType.DIAMOND.value

        # Neuen Stich setzen
        success = layer.set_stitch(x, y, color_index, stitch_type=stitch_type)

        # Neue Farbe Stichzahl erhöhen
        if success and color_index is not None and 0 <= color_index < len(self.color_entries):
            self.color_entries[color_index].stitch_count += 1

        return success

    def remove_stitch(self, x: int, y: int) -> bool:
        """Entfernt einen Stich auf dem aktiven Layer."""
        return self.set_stitch(x, y, None)

    def convert_to_mode(self, target_mode: str) -> bool:
        """Konvertiert die Pattern-Farben auf eine Default-Palette des Ziel-Modus.

        Beim Wechsel von Sticken zu Diamond Painting (und umgekehrt) ergeben
        die Original-Garn-/Drill-Codes im neuen Modus keinen Sinn. Diese
        Methode mapped jede Farbe via CIE-Lab-Distanz auf den naechsten
        Code in der Default-Palette des Ziel-Modus:

        - `target_mode == "diamond"` → "DMC Diamond Painting"
        - `target_mode == "stitch"`  → "DMC"

        **Reversibilitaet**: Vor jeder Konvertierung wird der aktuelle
        Thread-Stand pro Color-Entry als Snapshot in
        ``self.metadata["mode_backups"][<aktueller_mode>]`` abgelegt. Beim
        Zurueckwechseln (oder einer spaeteren Konvertierung in denselben
        Modus) wird der Snapshot bevorzugt — so trifft man nach
        Stick→Diamond→Stick wieder genau die Originalfarben, statt eines
        durch zweimaliges Nearest-Match leicht abgedrifteten Approximanten.

        **Bead- und Diamond-Farben** (``is_bead`` / ``is_diamond`` direkt
        ueber Palette gesetzt) werden uebersprungen. Beads sind in beiden
        Modi sinnvoll als Akzent; eine bereits aus DMC-DP stammende
        Diamond-Farbe muss nicht erneut gemapped werden.

        Args:
            target_mode: "stitch" oder "diamond".

        Returns:
            True wenn die Farben (oder der Mode) sich geaendert haben.
        """
        if target_mode not in ("stitch", "diamond"):
            return False
        if target_mode == self.mode:
            return False

        # Fabric-Count an Default des Ziel-Modus angleichen, wenn der
        # aktuelle Wert ein typischer Aida-Stick-Count ist. So passt das
        # Drill-Raster-Label (2.5 mm Square Standard = 10 ct equivalent)
        # automatisch beim Wechsel zu DP. Wenn der User vorher etwas
        # untypisches gewaehlt hat, lassen wir es unangetastet.
        TYPICAL_AIDA = {11, 14, 16, 18, 20, 22, 25}
        TYPICAL_DP = {8, 9, 10}
        if target_mode == "diamond" and self.fabric_count in TYPICAL_AIDA:
            self._stitch_fabric_count = self.fabric_count
            self.fabric_count = 10
        elif target_mode == "stitch" and self.fabric_count in TYPICAL_DP:
            self.fabric_count = getattr(self, "_stitch_fabric_count", 14)

        # Lokale Imports: vermeiden Circular-Import-Probleme im Pattern-Modul.
        from .thread import Thread
        from .thread_cross_ref import find_equivalent

        current_mode = self.mode
        changed = False

        if self.color_entries:
            backups = self.metadata.setdefault("mode_backups", {})

            # Aktuellen Stand fuer spaeteren Rueckweg merken.
            backups[current_mode] = [
                None
                if e.is_bead
                else {
                    "name": e.thread.name,
                    "color": e.thread.color.to_hex(),
                    "manufacturer": e.thread.manufacturer or "",
                    "catalog_number": e.thread.catalog_number or "",
                    "is_diamond": e.is_diamond,
                }
                for e in self.color_entries
            ]

            target_backup = backups.get(target_mode)
            use_backup = isinstance(target_backup, list) and len(target_backup) == len(
                self.color_entries
            )

            if use_backup:
                for entry, snapshot in zip(self.color_entries, target_backup):
                    if entry.is_bead or snapshot is None:
                        continue
                    entry.thread = Thread.from_hex(
                        name=snapshot["name"],
                        hex_color=snapshot["color"],
                        manufacturer=snapshot.get("manufacturer", "") or None,
                        catalog_number=snapshot.get("catalog_number", "") or None,
                    )
                    entry.is_diamond = bool(snapshot.get("is_diamond", False))
                    changed = True
            else:
                default_palette = "DMC Diamond Painting" if target_mode == "diamond" else "DMC"
                for entry in self.color_entries:
                    if entry.is_bead:
                        continue
                    # Wenn schon im Ziel-Format (z.B. is_diamond+target=diamond),
                    # nicht neu mappen — vermeidet leichte Drift bei Round-Trips.
                    already_target = (target_mode == "diamond" and entry.is_diamond) or (
                        target_mode == "stitch" and not entry.is_diamond
                    )
                    match = find_equivalent(entry.thread, default_palette)
                    if match is None:
                        continue
                    if already_target and match is entry.thread:
                        continue
                    entry.thread = match
                    entry.is_diamond = target_mode == "diamond"
                    changed = True

        self.mode = target_mode
        return changed or current_mode != target_mode

    def add_color(self, thread: Thread, is_bead: bool = False, is_diamond: bool = False) -> int:
        """
        Fügt eine neue Farbe zur Palette hinzu.

        Weist automatisch das nächste freie Symbol zu.

        Args:
            thread: Das hinzuzufügende Garn (Thread-Objekt)
            is_bead: True wenn die Farbe aus einer Bead-Palette stammt.
                     Stiche dieser Farbe werden automatisch als BEAD platziert.
            is_diamond: True wenn die Farbe aus einer Diamond-Painting-Palette
                        stammt. Stiche werden automatisch als DIAMOND platziert.

        Returns:
            Index der neuen Farbe in color_entries

        Example:
            >>> idx = pattern.add_color(Thread.from_hex("Blau", "#0000FF"))
            >>> pattern.set_stitch(10, 10, color_index=idx)
        """
        # Nächstes freies Symbol finden
        used_symbols = {entry.symbol for entry in self.color_entries}
        symbol = "?"
        for s in SYMBOLS:
            if s not in used_symbols:
                symbol = s
                break

        entry = ColorEntry(
            thread=thread,
            symbol=symbol,
            stitch_count=0,
            is_bead=is_bead,
            is_diamond=is_diamond,
        )
        self.color_entries.append(entry)
        return len(self.color_entries) - 1

    def remove_color(self, index: int) -> None:
        """
        Entfernt eine Farbe und alle zugehörigen Stiche aus allen Layern.

        Alle Stiche mit diesem Farbindex werden gelöscht.
        Höhere Farbindizes werden um 1 reduziert.

        Args:
            index: Index der zu entfernenden Farbe

        Note:
            Diese Operation kann nicht rückgängig gemacht werden
            außer durch UndoManager.
        """
        if not (0 <= index < len(self.color_entries)):
            return

        # Alle Stiche dieser Farbe in allen Layern entfernen und Indizes anpassen
        for layer in self.layer_stack:
            # Farbe löschen (durch NO_STITCH ersetzen)
            layer.replace_color(index, NO_STITCH)
            # Alle höheren Indizes um 1 reduzieren
            layer.shift_color_indices(index + 1, -1)

        del self.color_entries[index]

    def get_color_entry(self, index: int) -> Optional[ColorEntry]:
        """Gibt eine Farbe nach Index zurück."""
        if 0 <= index < len(self.color_entries):
            return self.color_entries[index]
        return None

    def set_symbol(self, color_index: int, symbol: str) -> None:
        """Ändert das Symbol einer Farbe."""
        if 0 <= color_index < len(self.color_entries):
            self.color_entries[color_index].symbol = symbol

    @property
    def color_count(self) -> int:
        """Anzahl der verwendeten Farben."""
        return len(self.color_entries)

    @property
    def total_stitches(self) -> int:
        """Gesamtanzahl der Stiche über alle Layer."""
        total = 0
        for layer in self.layer_stack:
            total += layer.count_stitches()
        return total

    @property
    def used_colors(self) -> list[ColorEntry]:
        """Liste der tatsächlich verwendeten Farben (mit Stichen)."""
        return [entry for entry in self.color_entries if entry.stitch_count > 0]

    @property
    def size_inches(self) -> tuple[float, float]:
        """Größe in Inch basierend auf fabric_count."""
        return (self.width / self.fabric_count, self.height / self.fabric_count)

    @property
    def size_cm(self) -> tuple[float, float]:
        """Größe in Zentimeter."""
        w_inch, h_inch = self.size_inches
        return (w_inch * 2.54, h_inch * 2.54)

    def recalculate_stitch_counts(self) -> None:
        """Berechnet alle Stichzahlen neu (über alle Layer).

        Verwendet numpy für effiziente Zählung.
        """
        # Zurücksetzen
        for entry in self.color_entries:
            entry.stitch_count = 0

        # Über alle Layer zählen mit numpy (sehr effizient)
        num_colors = len(self.color_entries)
        for layer in self.layer_stack:
            color_counts = layer.get_color_counts()
            for idx, count in color_counts.items():
                if 0 <= idx < num_colors:
                    self.color_entries[idx].stitch_count += count

    def get_bounds(self) -> tuple[int, int, int, int]:
        """
        Ermittelt die Bounding-Box des Musters (nur gefüllte Bereiche).

        Verwendet numpy für effiziente Berechnung.

        Returns:
            (min_x, min_y, max_x, max_y) oder (0, 0, 0, 0) wenn leer
        """
        # Composite Grid erstellen
        composite = self.layer_stack.get_composite_grid()

        # Positionen aller Stiche finden
        positions = np.argwhere(composite != NO_STITCH)

        if len(positions) == 0:
            return (0, 0, 0, 0)

        min_y = int(positions[:, 0].min())
        max_y = int(positions[:, 0].max())
        min_x = int(positions[:, 1].min())
        max_x = int(positions[:, 1].max())

        return (min_x, min_y, max_x, max_y)

    def get_statistics(self) -> dict:
        """
        Gibt umfassende Statistiken über das Muster zurück.

        Enthält Informationen über Größe, Stichzahlen, Farben
        und berücksichtigt skip_stitching für realistische Schätzungen.

        Returns:
            Dictionary mit folgenden Schlüsseln:
            - name: Name des Musters
            - width, height: Größe in Stichen
            - width_cm, height_cm: Größe in Zentimetern
            - fabric_count: Stoffzählung
            - total_stitches: Gesamtzahl aller Stiche
            - stitches_to_do: Stiche ohne skip_stitching Farben
            - skipped_stitches: Stiche mit skip_stitching Farben
            - color_count: Anzahl Farben in der Palette
            - used_colors: Anzahl tatsächlich verwendeter Farben
            - skipped_colors: Anzahl übersprungener Farben
            - layer_count: Anzahl Layer

        Example:
            >>> stats = pattern.get_statistics()
            >>> print(f"{stats['width_cm']} x {stats['height_cm']} cm")
        """
        w_cm, h_cm = self.size_cm

        # Zähle Stiche ohne übersprungene Farben
        stitches_to_do = 0
        skipped_stitches = 0
        for entry in self.color_entries:
            if entry.skip_stitching:
                skipped_stitches += entry.stitch_count
            else:
                stitches_to_do += entry.stitch_count

        # Zähle übersprungene Farben
        skipped_colors = sum(
            1 for e in self.color_entries if e.skip_stitching and e.stitch_count > 0
        )

        # Perlen separat zaehlen (Stitch-Type 10) — werden in Stueck verkauft,
        # nicht in Garnstraengen.
        bead_count = self._count_beads()

        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "width_cm": round(w_cm, 1),
            "height_cm": round(h_cm, 1),
            "fabric_count": self.fabric_count,
            "total_stitches": self.total_stitches,
            "stitches_to_do": stitches_to_do,
            "skipped_stitches": skipped_stitches,
            "color_count": self.color_count,
            "used_colors": len(self.used_colors),
            "skipped_colors": skipped_colors,
            "layer_count": len(self.layer_stack),
            "bead_count": bead_count,
        }

    def _count_beads(self) -> int:
        """Zaehlt alle sichtbaren Perlen (Stitch-Type 10) ueber alle Layer."""
        count = 0
        for layer in self.layer_stack:
            if not layer.visible or layer.grid is None or layer.stitch_type_grid is None:
                continue
            mask = (layer.grid != NO_STITCH) & (layer.stitch_type_grid == 10)
            count += int(mask.sum())
        return count

    def iterate_composite_stitches(self) -> Iterator[tuple[int, int, int]]:
        """
        Iteriert über alle sichtbaren Stiche: (x, y, color_index).

        Verwendet get_composite_grid() + numpy.argwhere() statt
        pro-Pixel Python-Loops für deutlich bessere Performance.
        """
        composite = self.layer_stack.get_composite_grid()
        positions = np.argwhere(composite != NO_STITCH)
        for y, x in positions:
            yield (int(x), int(y), int(composite[y, x]))

    def iter_stitches(self) -> Iterator[tuple[int, int, int, "Layer"]]:
        """Iteriert über alle gesetzten Stiche aller Layer.

        Im Gegensatz zu iterate_composite_stitches() liefert diese Methode
        auch die Layer-Referenz und iteriert über *alle* Layer, nicht nur
        das sichtbare Composite.

        Yields:
            (x, y, color_idx, layer) für jeden gesetzten Stich.
        """
        for layer in self.layer_stack:
            positions = np.argwhere(layer.grid != NO_STITCH)
            for y, x in positions:
                yield (int(x), int(y), int(layer.grid[y, x]), layer)

    def fill_rectangle(self, x1: int, y1: int, x2: int, y2: int, color_index: int) -> None:
        """
        Füllt ein Rechteck auf dem aktiven Layer.

        Verwendet numpy-Slicing für direkte Grid-Manipulation
        statt pro-Pixel set_stitch()-Aufrufe.
        """
        if color_index is not None and not (0 <= color_index < len(self.color_entries)):
            return

        layer = self.active_layer
        if not layer:
            return

        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)

        # Bounds clamping
        min_x = max(0, min_x)
        min_y = max(0, min_y)
        max_x = min(self.width - 1, max_x)
        max_y = min(self.height - 1, max_y)

        if min_x > max_x or min_y > max_y:
            return

        # Alte Stichzahlen im Bereich abziehen
        old_region = layer.grid[min_y : max_y + 1, min_x : max_x + 1].copy()
        for idx_val in np.unique(old_region):
            if idx_val != NO_STITCH and 0 <= idx_val < len(self.color_entries):
                count = int(np.count_nonzero(old_region == idx_val))
                self.color_entries[idx_val].stitch_count -= count

        # Numpy-Slicing für schnelles Füllen
        layer.grid[min_y : max_y + 1, min_x : max_x + 1] = color_index

        # Neue Stichzahlen addieren
        if color_index is not None and 0 <= color_index < len(self.color_entries):
            area = (max_x - min_x + 1) * (max_y - min_y + 1)
            self.color_entries[color_index].stitch_count += area

    def flatten_layers(self) -> None:
        """Vereint alle Layer zu einem."""
        flat_layer = self.layer_stack.flatten()
        self.layer_stack = LayerStack(self.width, self.height)
        self.layer_stack.replace_all_layers([flat_layer], active_index=0)

    def crop(self, x: int, y: int, width: int, height: int) -> bool:
        """
        Schneidet das Muster auf einen Bereich zu.

        Args:
            x: Linke obere Ecke X
            y: Linke obere Ecke Y
            width: Neue Breite
            height: Neue Höhe

        Returns:
            True wenn erfolgreich
        """
        if width < 1 or height < 1:
            return False
        if x < 0 or y < 0:
            return False
        if x + width > self.width or y + height > self.height:
            return False

        # Alle Layer zuschneiden (numpy-effizient)
        for layer in self.layer_stack:
            layer.crop(x, y, width, height)

        self.width = width
        self.height = height
        self.layer_stack.width = width
        self.layer_stack.height = height

        return True

    def auto_crop(self) -> tuple[int, int, int, int] | None:
        """
        Schneidet leere Ränder automatisch ab.

        Returns:
            (entfernt_links, entfernt_oben, entfernt_rechts, entfernt_unten)
            oder None wenn nichts zu schneiden
        """
        min_x, min_y, max_x, max_y = self.get_bounds()

        # Prüfen ob überhaupt was zu schneiden ist
        if max_x < 0:
            return None  # Leeres Muster

        new_width = max_x - min_x + 1
        new_height = max_y - min_y + 1

        # Prüfen ob sich was ändert
        if min_x == 0 and min_y == 0 and new_width == self.width and new_height == self.height:
            return None  # Nichts zu schneiden

        # Entfernte Ränder berechnen
        removed_left = min_x
        removed_top = min_y
        removed_right = self.width - max_x - 1
        removed_bottom = self.height - max_y - 1

        # Zuschneiden
        self.crop(min_x, min_y, new_width, new_height)

        return (removed_left, removed_top, removed_right, removed_bottom)

    def rotate_90_cw(self) -> None:
        """Dreht das gesamte Muster 90° im Uhrzeigersinn."""
        for layer in self.layer_stack:
            layer.rotate_90_cw()

        # Breite und Höhe tauschen
        self.width, self.height = self.height, self.width
        self.layer_stack.width = self.width
        self.layer_stack.height = self.height

    def rotate_90_ccw(self) -> None:
        """Dreht das gesamte Muster 90° gegen den Uhrzeigersinn."""
        for layer in self.layer_stack:
            layer.rotate_90_ccw()

        # Breite und Höhe tauschen
        self.width, self.height = self.height, self.width
        self.layer_stack.width = self.width
        self.layer_stack.height = self.height

    def rotate_180(self) -> None:
        """Dreht das gesamte Muster um 180°."""
        for layer in self.layer_stack:
            layer.rotate_180()

    def flip_horizontal(self) -> None:
        """Spiegelt das gesamte Muster horizontal."""
        for layer in self.layer_stack:
            layer.flip_horizontal()

    def flip_vertical(self) -> None:
        """Spiegelt das gesamte Muster vertikal."""
        for layer in self.layer_stack:
            layer.flip_vertical()

    # === Rückstich-Methoden (delegieren an BackstitchManager) ===

    @property
    def backstitches(self) -> list[Backstitch]:
        """Kompatibilitäts-Property für direkten Zugriff auf die Backstitch-Liste."""
        return self.backstitch_manager.backstitches

    def add_backstitch(self, x1: int, y1: int, x2: int, y2: int, color_index: int) -> Backstitch:
        """
        Fügt einen Rückstich hinzu.

        Koordinaten sind in halben Stichen (0 = Ecke, 1 = Mitte, 2 = nächste Ecke).

        Returns:
            Der erstellte Backstitch
        """
        return self.backstitch_manager.add(x1, y1, x2, y2, color_index)

    def remove_backstitch(self, backstitch: Backstitch) -> bool:
        """
        Entfernt einen Rückstich.

        Returns:
            True wenn gefunden und entfernt
        """
        return self.backstitch_manager.remove(backstitch)

    def remove_backstitch_at(self, x: int, y: int, tolerance: int = 1) -> Backstitch | None:
        """
        Entfernt einen Rückstich an einer Position.

        Args:
            x, y: Position in halben Stichen
            tolerance: Toleranz in halben Stichen

        Returns:
            Der entfernte Backstitch oder None
        """
        return self.backstitch_manager.remove_at(x, y, tolerance)

    def _point_on_line(
        self, px: int, py: int, x1: int, y1: int, x2: int, y2: int, tol: int
    ) -> bool:
        """
        Prüft ob ein Punkt auf einer Linie liegt (mit Toleranz).

        .. deprecated::
            Verwende stattdessen backstitch_manager.find_at() für die Suche
            nach Backstitches an einer Position.
        """
        return self.backstitch_manager._point_on_line(px, py, x1, y1, x2, y2, tol)

    def get_backstitches_in_area(self, x1: int, y1: int, x2: int, y2: int) -> list[Backstitch]:
        """
        Gibt alle Rückstiche zurück, die einen Bereich berühren.

        Koordinaten in halben Stichen.
        """
        return self.backstitch_manager.get_in_area(x1, y1, x2, y2)

    # === Fortschritts-Tracking ===

    def get_progress_statistics(self) -> dict:
        """
        Gibt Fortschritts-Statistiken zurück.

        Returns:
            Dictionary mit:
            - total_stitches: Gesamtanzahl Stiche
            - completed_stitches: Erledigte Stiche
            - progress_percent: Fortschritt in Prozent (0.0 - 100.0)
            - per_color: Liste mit Pro-Farbe-Statistiken
        """
        # Aggregiere über alle Layer
        total_per_color: dict[int, int] = {}
        completed_per_color: dict[int, int] = {}

        for layer in self.layer_stack:
            for idx, count in layer.get_color_counts().items():
                total_per_color[idx] = total_per_color.get(idx, 0) + count
            for idx, count in layer.get_completed_color_counts().items():
                completed_per_color[idx] = completed_per_color.get(idx, 0) + count

        total = sum(total_per_color.values())
        completed = sum(completed_per_color.values())
        percent = (completed / total * 100.0) if total > 0 else 0.0

        per_color = []
        for i, entry in enumerate(self.color_entries):
            color_total = total_per_color.get(i, 0)
            color_completed = completed_per_color.get(i, 0)
            color_percent = (color_completed / color_total * 100.0) if color_total > 0 else 0.0
            per_color.append(
                {
                    "color_index": i,
                    "thread_name": entry.thread.name,
                    "symbol": entry.symbol,
                    "color_hex": entry.thread.color.to_hex(),
                    "total": color_total,
                    "completed": color_completed,
                    "percent": round(color_percent, 1),
                    "skip_stitching": entry.skip_stitching,
                }
            )

        return {
            "total_stitches": total,
            "completed_stitches": completed,
            "progress_percent": round(percent, 1),
            "per_color": per_color,
        }

    def mark_stitch_completed(self, x: int, y: int, layer_index: int) -> bool:
        """Markiert einen Stich auf einem bestimmten Layer als erledigt."""
        if 0 <= layer_index < len(self.layer_stack):
            return self.layer_stack[layer_index].mark_completed(x, y)
        return False

    def unmark_stitch_completed(self, x: int, y: int, layer_index: int) -> bool:
        """Entfernt die Erledigt-Markierung eines Stichs."""
        if 0 <= layer_index < len(self.layer_stack):
            return self.layer_stack[layer_index].unmark_completed(x, y)
        return False

    def mark_color_completed(self, color_index: int) -> int:
        """
        Markiert alle Stiche einer Farbe als erledigt (über alle Layer).

        Returns:
            Anzahl der neu markierten Stiche
        """
        count = 0
        for layer in self.layer_stack:
            mask = (layer.grid == color_index) & ~layer.completion_grid
            count += int(np.count_nonzero(mask))
            layer.completion_grid[mask] = True
        return count

    def reset_progress(self) -> None:
        """Setzt den gesamten Fortschritt aller Layer zurück."""
        for layer in self.layer_stack:
            layer.reset_completion()

    def __repr__(self) -> str:
        return (
            f"Pattern('{self.name}', {self.width}x{self.height}, "
            f"{len(self.layer_stack)} layers, {self.color_count} colors)"
        )
