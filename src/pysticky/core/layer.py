"""
Layer-System für Kreuzstich-Muster.

Ermöglicht das Arbeiten mit mehreren Ebenen, die übereinander
gelegt werden (wie in Photoshop/GIMP).

Verwendet numpy für effiziente Speicherung und schnelle Operationen.
"""

from dataclasses import dataclass, field
from typing import Iterator
from uuid import uuid4

import numpy as np

# Konstante für "kein Stich" (transparent)
NO_STITCH: int = -1


@dataclass
class Layer:
    """
    Eine einzelne Ebene im Muster.

    Jedes Layer hat sein eigenes Grid mit Farbindizes.
    Layer werden von unten nach oben gerendert.

    Attributes:
        id: Eindeutige ID
        name: Anzeigename
        width: Breite in Stichen
        height: Höhe in Stichen
        grid: numpy-Array mit Farbindizes (-1 = transparent/kein Stich)
        visible: Sichtbarkeit
        locked: Gesperrt (keine Bearbeitung)
        opacity: Deckkraft (0.0 - 1.0)
        note: Freie Notiz zur Ebene (z.B. "Schatten", "Vordergrund")
    """

    name: str
    width: int
    height: int
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    # None-Default ist nur Init-Sentinel; __post_init__ setzt die Grids immer.
    grid: np.ndarray = field(default=None)  # type: ignore[arg-type]
    completion_grid: np.ndarray = field(default=None)  # type: ignore[arg-type]
    stitch_type_grid: np.ndarray = field(default=None)  # type: ignore[arg-type]
    visible: bool = True
    locked: bool = False
    opacity: float = 1.0
    note: str = ""

    def __post_init__(self) -> None:
        """Initialisiert das Grid falls nicht vorhanden."""
        if self.grid is None:
            self.clear()
        if self.completion_grid is None:
            self.completion_grid = np.zeros((self.height, self.width), dtype=bool)
        if self.stitch_type_grid is None:
            self.stitch_type_grid = np.zeros((self.height, self.width), dtype=np.uint8)

    def clear(self) -> bool:
        """Leert das Layer (alle Zellen transparent).

        Returns:
            True wenn erfolgreich, False wenn gesperrt (Grid unveraendert) --
            gleiche Konvention wie set_stitch()/remove_stitch().
        """
        if self.locked:
            return False
        self.grid = np.full((self.height, self.width), NO_STITCH, dtype=np.int16)
        self.completion_grid = np.zeros((self.height, self.width), dtype=bool)
        self.stitch_type_grid = np.zeros((self.height, self.width), dtype=np.uint8)
        return True

    def resize(self, new_width: int, new_height: int) -> None:
        """Ändert die Größe des Layers (behält vorhandene Stiche)."""
        new_grid = np.full((new_height, new_width), NO_STITCH, dtype=np.int16)
        new_completion = np.zeros((new_height, new_width), dtype=bool)
        new_stitch_types = np.zeros((new_height, new_width), dtype=np.uint8)

        # Überlappenden Bereich kopieren
        copy_h = min(self.height, new_height)
        copy_w = min(self.width, new_width)
        new_grid[:copy_h, :copy_w] = self.grid[:copy_h, :copy_w]
        new_completion[:copy_h, :copy_w] = self.completion_grid[:copy_h, :copy_w]
        if self.stitch_type_grid is not None:
            new_stitch_types[:copy_h, :copy_w] = self.stitch_type_grid[:copy_h, :copy_w]

        self.width = new_width
        self.height = new_height
        self.grid = new_grid
        self.completion_grid = new_completion
        self.stitch_type_grid = new_stitch_types

    def get_stitch(self, x: int, y: int) -> int | None:
        """
        Gibt den Farbindex an Position (x, y) zurück.

        Returns:
            Farbindex (>= 0) oder None wenn kein Stich
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            value = self.grid[y, x]
            return None if value == NO_STITCH else int(value)
        return None

    def set_stitch(self, x: int, y: int, color_index: int | None, stitch_type: int = 0) -> bool:
        """
        Setzt einen Stich an Position (x, y).

        Args:
            x: X-Koordinate
            y: Y-Koordinate
            color_index: Farbindex (>= 0) oder None zum Löschen
            stitch_type: Stichtyp (0=FULL, 1=HALF_TL_BR, 2=HALF_TR_BL, etc.)

        Returns:
            True wenn erfolgreich, False wenn gesperrt oder außerhalb
        """
        if self.locked:
            return False
        if 0 <= x < self.width and 0 <= y < self.height:
            if color_index is None:
                self.grid[y, x] = NO_STITCH
                self.completion_grid[y, x] = False
                self.stitch_type_grid[y, x] = 0
            else:
                self.grid[y, x] = color_index
                self.stitch_type_grid[y, x] = stitch_type
            return True
        return False

    def remove_stitch(self, x: int, y: int) -> bool:
        """Entfernt einen Stich (setzt auf transparent)."""
        return self.set_stitch(x, y, None)

    def is_empty(self) -> bool:
        """Prüft ob das Layer leer ist (keine Stiche)."""
        return not np.any(self.grid != NO_STITCH)

    def count_stitches(self) -> int:
        """Zählt alle Stiche im Layer."""
        return int(np.count_nonzero(self.grid != NO_STITCH))

    def iterate_stitches(self) -> Iterator[tuple[int, int, int]]:
        """
        Iteriert über alle Stiche: (x, y, color_index).

        Yields:
            Tupel (x, y, color_index) für jeden gesetzten Stich
        """
        # np.argwhere gibt [(y, x), ...] für alle Nicht-NO_STITCH Werte
        positions = np.argwhere(self.grid != NO_STITCH)
        for y, x in positions:
            yield (int(x), int(y), int(self.grid[y, x]))

    def get_stitch_type(self, x: int, y: int) -> int:
        """Gibt den Stichtyp an Position (x, y) zurück (0=FULL)."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return int(self.stitch_type_grid[y, x])
        return 0

    def copy(self) -> "Layer":
        """Erstellt eine tiefe Kopie des Layers."""
        new_layer = Layer(
            name=f"{self.name} (Kopie)",
            width=self.width,
            height=self.height,
            visible=self.visible,
            locked=False,
            opacity=self.opacity,
            note=self.note,
        )
        new_layer.grid = self.grid.copy()
        new_layer.completion_grid = self.completion_grid.copy()
        new_layer.stitch_type_grid = self.stitch_type_grid.copy()
        return new_layer

    def rotate_90_cw(self) -> None:
        """Dreht das Layer 90° im Uhrzeigersinn."""
        from .stitch import ROTATE_CW_MAP

        self.grid = np.rot90(self.grid, k=-1)
        self.completion_grid = np.rot90(self.completion_grid, k=-1)
        self.stitch_type_grid = np.rot90(self.stitch_type_grid, k=-1)
        self._remap_stitch_types(ROTATE_CW_MAP)
        self.width, self.height = self.height, self.width

    def rotate_90_ccw(self) -> None:
        """Dreht das Layer 90° gegen den Uhrzeigersinn."""
        from .stitch import ROTATE_CCW_MAP

        self.grid = np.rot90(self.grid, k=1)
        self.completion_grid = np.rot90(self.completion_grid, k=1)
        self.stitch_type_grid = np.rot90(self.stitch_type_grid, k=1)
        self._remap_stitch_types(ROTATE_CCW_MAP)
        self.width, self.height = self.height, self.width

    def rotate_180(self) -> None:
        """Dreht das Layer um 180°."""
        self.grid = np.rot90(self.grid, k=2)
        self.completion_grid = np.rot90(self.completion_grid, k=2)
        self.stitch_type_grid = np.rot90(self.stitch_type_grid, k=2)
        # 180°-Drehung: Halbe Stiche bleiben gleich (/ bleibt /, \ bleibt \)

    def flip_horizontal(self) -> None:
        """Spiegelt das Layer horizontal (links-rechts)."""
        from .stitch import FLIP_H_MAP

        self.grid = np.flip(self.grid, axis=1)
        self.completion_grid = np.flip(self.completion_grid, axis=1)
        self.stitch_type_grid = np.flip(self.stitch_type_grid, axis=1)
        self._remap_stitch_types(FLIP_H_MAP)

    def flip_vertical(self) -> None:
        """Spiegelt das Layer vertikal (oben-unten)."""
        from .stitch import FLIP_V_MAP

        self.grid = np.flip(self.grid, axis=0)
        self.completion_grid = np.flip(self.completion_grid, axis=0)
        self.stitch_type_grid = np.flip(self.stitch_type_grid, axis=0)
        self._remap_stitch_types(FLIP_V_MAP)

    def _remap_stitch_types(self, mapping: dict[int, int]) -> None:
        """Wendet eine Stichtyp-Transformation auf das gesamte Grid an."""
        # Nur transformieren wenn es Nicht-FULL Stiche gibt
        if not np.any(self.stitch_type_grid != 0):
            return
        new_grid = self.stitch_type_grid.copy()
        for old_val, new_val in mapping.items():
            if old_val != new_val:
                new_grid[self.stitch_type_grid == old_val] = new_val
        self.stitch_type_grid = new_grid

    def get_color_counts(self) -> dict[int, int]:
        """
        Zählt wie oft jeder Farbindex vorkommt.

        Returns:
            Dict mit {color_index: count} für alle verwendeten Farben
        """
        # Nur positive Werte (echte Farben) zählen
        valid_mask = self.grid >= 0
        if not np.any(valid_mask):
            return {}

        values = self.grid[valid_mask].flatten()
        unique, counts = np.unique(values, return_counts=True)
        return {int(index): int(cnt) for index, cnt in zip(unique, counts)}

    def replace_color(self, old_index: int, new_index: int) -> int:
        """
        Ersetzt einen Farbindex durch einen anderen.

        Args:
            old_index: Zu ersetzender Farbindex
            new_index: Neuer Farbindex (oder -1 zum Löschen)

        Returns:
            Anzahl der ersetzten Stiche
        """
        mask = self.grid == old_index
        count = int(np.count_nonzero(mask))
        self.grid[mask] = new_index
        # Beim Löschen (NO_STITCH) auch Completion und Stichtyp zurücksetzen
        if new_index == NO_STITCH:
            self.completion_grid[mask] = False
            self.stitch_type_grid[mask] = 0
        return count

    def shift_color_indices(self, from_index: int, delta: int) -> None:
        """
        Verschiebt alle Farbindizes >= from_index um delta.

        Nützlich wenn eine Farbe entfernt wird (delta=-1).

        Args:
            from_index: Ab diesem Index verschieben
            delta: Verschiebung (typisch -1 beim Entfernen)
        """
        mask = self.grid >= from_index
        self.grid[mask] += delta

    def crop(self, x: int, y: int, width: int, height: int) -> bool:
        """
        Schneidet das Layer auf einen Bereich zu.

        Args:
            x: Linke obere Ecke X
            y: Linke obere Ecke Y
            width: Neue Breite
            height: Neue Höhe

        Returns:
            True wenn zugeschnitten wurde, False bei ungueltigem Bereich
            (Grid/width/height bleiben dann unveraendert).

        Note:
            Der einzige aktuelle Aufrufer (Pattern.crop()) validiert den
            Bereich bereits VOR dem Aufruf -- diese Pruefung hier ist
            Verteidigung in der Tiefe fuer die oeffentliche Layer-API: ohne
            sie wuerden width/height unbedingt auf die ANGEFORDERTEN Werte
            gesetzt, auch wenn numpy-Slicing bei einem zu grossen/negativen
            Bereich eine kleinere/verschobene Form zurueckgibt -- ein
            spaeterer get_stitch()/set_stitch() innerhalb der (falschen)
            deklarierten Groesse wuerde dann mit einem rohen IndexError
            abstuerzen statt sauber "out of bounds" zu melden.
        """
        if width < 1 or height < 1 or x < 0 or y < 0:
            return False
        if x + width > self.width or y + height > self.height:
            return False

        self.grid = self.grid[y : y + height, x : x + width].copy()
        self.completion_grid = self.completion_grid[y : y + height, x : x + width].copy()
        self.stitch_type_grid = self.stitch_type_grid[y : y + height, x : x + width].copy()
        self.width = width
        self.height = height
        return True

    # === Fortschritts-Tracking (Completion) ===

    def mark_completed(self, x: int, y: int) -> bool:
        """
        Markiert einen Stich als erledigt.

        Returns:
            True wenn erfolgreich (Stich vorhanden und in Bounds)
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            if self.grid[y, x] != NO_STITCH:
                self.completion_grid[y, x] = True
                return True
        return False

    def unmark_completed(self, x: int, y: int) -> bool:
        """
        Entfernt die Erledigt-Markierung eines Stichs.

        Returns:
            True wenn erfolgreich (in Bounds)
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            self.completion_grid[y, x] = False
            return True
        return False

    def is_completed(self, x: int, y: int) -> bool:
        """Prüft ob ein Stich als erledigt markiert ist."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return bool(self.completion_grid[y, x])
        return False

    def count_completed(self) -> int:
        """Zählt alle als erledigt markierten Stiche (nur wo auch ein Stich ist)."""
        return int(np.count_nonzero(self.completion_grid & (self.grid != NO_STITCH)))

    def get_completed_color_counts(self) -> dict[int, int]:
        """
        Zählt erledigte Stiche pro Farbe.

        Returns:
            Dict mit {color_index: completed_count}
        """
        mask = self.completion_grid & (self.grid >= 0)
        if not np.any(mask):
            return {}

        values = self.grid[mask].flatten()
        unique, counts = np.unique(values, return_counts=True)
        return {int(index): int(cnt) for index, cnt in zip(unique, counts)}

    def reset_completion(self) -> None:
        """Setzt den gesamten Fortschritt zurück."""
        self.completion_grid = np.zeros((self.height, self.width), dtype=bool)

    def __repr__(self) -> str:
        stitches = self.count_stitches()
        completed = self.count_completed()
        return f"Layer('{self.name}', {self.width}x{self.height}, {stitches} stitches, {completed} completed, visible={self.visible})"


class LayerStack:
    """
    Verwaltet einen Stapel von Layern.

    Layer werden von Index 0 (unten) bis n-1 (oben) gerendert.
    Das oberste sichtbare Layer "gewinnt" bei der Anzeige.
    """

    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height
        self._layers: list[Layer] = []
        self._active_index: int = -1

        # Standard-Layer erstellen
        self.add_layer("Hintergrund")

    @property
    def width(self) -> int:
        return self._width

    @width.setter
    def width(self, value: int) -> None:
        self._width = value

    @property
    def height(self) -> int:
        return self._height

    @height.setter
    def height(self, value: int) -> None:
        self._height = value

    @property
    def layers(self) -> list[Layer]:
        """Liste aller Layer (von unten nach oben)."""
        return self._layers

    @property
    def active_layer(self) -> Layer | None:
        """Das aktuell aktive Layer."""
        if 0 <= self._active_index < len(self._layers):
            return self._layers[self._active_index]
        return None

    @property
    def active_index(self) -> int:
        return self._active_index

    @active_index.setter
    def active_index(self, index: int) -> None:
        if 0 <= index < len(self._layers):
            self._active_index = index

    def __len__(self) -> int:
        return len(self._layers)

    def __getitem__(self, index: int) -> Layer:
        return self._layers[index]

    def __iter__(self) -> Iterator[Layer]:
        return iter(self._layers)

    def add_layer(self, name: str, index: int | None = None) -> Layer:
        """
        Fügt ein neues Layer hinzu.

        Args:
            name: Name des Layers
            index: Position (None = oben)

        Returns:
            Das neue Layer
        """
        layer = Layer(name=name, width=self._width, height=self._height)

        if index is None or index >= len(self._layers):
            self._layers.append(layer)
            self._active_index = len(self._layers) - 1
        else:
            self._layers.insert(index, layer)
            self._active_index = index

        return layer

    def remove_layer(self, index: int) -> Layer | None:
        """
        Entfernt ein Layer.

        Args:
            index: Index des zu entfernenden Layers

        Returns:
            Das entfernte Layer oder None
        """
        if len(self._layers) <= 1:
            return None  # Mindestens ein Layer behalten

        if 0 <= index < len(self._layers):
            layer = self._layers.pop(index)

            # Aktiven Index anpassen
            if self._active_index >= len(self._layers):
                self._active_index = len(self._layers) - 1
            elif self._active_index > index:
                self._active_index -= 1

            return layer
        return None

    def duplicate_layer(self, index: int) -> Layer | None:
        """Dupliziert ein Layer."""
        if 0 <= index < len(self._layers):
            copy = self._layers[index].copy()
            self._layers.insert(index + 1, copy)
            self._active_index = index + 1
            return copy
        return None

    def move_layer(self, from_index: int, to_index: int) -> bool:
        """
        Verschiebt ein Layer an eine neue Position.

        Returns:
            True bei Erfolg
        """
        if not (0 <= from_index < len(self._layers)):
            return False
        if not (0 <= to_index < len(self._layers)):
            return False
        if from_index == to_index:
            return True

        layer = self._layers.pop(from_index)
        self._layers.insert(to_index, layer)

        # Aktiven Index anpassen
        if self._active_index == from_index:
            self._active_index = to_index
        elif from_index < self._active_index <= to_index:
            self._active_index -= 1
        elif to_index <= self._active_index < from_index:
            self._active_index += 1

        return True

    def move_layer_up(self, index: int) -> bool:
        """Verschiebt ein Layer nach oben."""
        return self.move_layer(index, index + 1)

    def move_layer_down(self, index: int) -> bool:
        """Verschiebt ein Layer nach unten."""
        return self.move_layer(index, index - 1)

    def move_layer_to(self, from_index: int, to_index: int) -> bool:
        """
        Verschiebt ein Layer an eine absolute Position.

        Args:
            from_index: Quell-Index
            to_index: Ziel-Index

        Returns:
            True bei Erfolg
        """
        if not (0 <= from_index < len(self._layers)):
            return False
        if not (0 <= to_index < len(self._layers)):
            to_index = max(0, min(to_index, len(self._layers) - 1))
        if from_index == to_index:
            return True

        layer = self._layers.pop(from_index)
        self._layers.insert(to_index, layer)

        # Aktiven Index anpassen
        if self._active_index == from_index:
            self._active_index = to_index
        elif from_index < self._active_index <= to_index:
            self._active_index -= 1
        elif to_index <= self._active_index < from_index:
            self._active_index += 1

        return True

    def merge_layers(self, source_index: int, target_index: int) -> bool:
        """
        Vereint zwei Layer. Stiche vom Source-Layer werden auf das Target-Layer kopiert.
        Das Source-Layer wird anschließend entfernt.

        Args:
            source_index: Index des Layers, das aufgelöst wird
            target_index: Index des Layers, auf das kopiert wird

        Returns:
            True bei Erfolg
        """
        if source_index == target_index:
            return False
        if not (0 <= source_index < len(self._layers)):
            return False
        if not (0 <= target_index < len(self._layers)):
            return False
        if len(self._layers) <= 1:
            return False

        source = self._layers[source_index]
        target = self._layers[target_index]

        if target.locked:
            return False

        # Stiche vom Source auf Target kopieren (nur wo Source nicht leer ist)
        mask = source.grid != NO_STITCH
        target.grid[mask] = source.grid[mask]
        # Completion vom Source übernehmen (wo Source Stiche hat)
        target.completion_grid[mask] = source.completion_grid[mask]
        # Stich-Typ (Halb-/Viertelstich etc.) übernehmen -- ohne das würde
        # jede übernommene Zelle stillschweigend zu einem vollen Stich,
        # weil sie im Target-Grid an dieser Stelle vorher meist FULL (0)
        # oder leer war.
        target.stitch_type_grid[mask] = source.stitch_type_grid[mask]

        # Source-Layer entfernen
        self._layers.pop(source_index)

        # Aktiven Index anpassen
        if self._active_index == source_index:
            if target_index > source_index:
                self._active_index = target_index - 1
            else:
                self._active_index = target_index
        elif self._active_index > source_index:
            self._active_index -= 1

        return True

    def merge_down(self, index: int) -> bool:
        """
        Fügt ein Layer mit dem darunter liegenden zusammen.

        Returns:
            True bei Erfolg
        """
        if index <= 0 or index >= len(self._layers):
            return False

        upper = self._layers[index]
        lower = self._layers[index - 1]

        if lower.locked:
            return False

        # Oberes Layer auf unteres kopieren (nur wo oberes nicht transparent)
        mask = upper.grid != NO_STITCH
        lower.grid[mask] = upper.grid[mask]
        # Completion vom oberen Layer übernehmen
        lower.completion_grid[mask] = upper.completion_grid[mask]
        # Stich-Typ uebernehmen -- siehe merge_layers() fuer die Begruendung.
        lower.stitch_type_grid[mask] = upper.stitch_type_grid[mask]

        # Oberes Layer entfernen
        self._layers.pop(index)
        self._active_index = index - 1

        return True

    def flatten(self) -> Layer:
        """
        Vereint alle sichtbaren Layer zu einem.

        Returns:
            Das zusammengeführte Layer
        """
        result = Layer(name="Zusammengeführt", width=self._width, height=self._height)

        # Von unten nach oben durchgehen
        for layer in self._layers:
            if layer.visible:
                mask = layer.grid != NO_STITCH
                result.grid[mask] = layer.grid[mask]
                # Completion übernehmen (oberstes sichtbares Layer gewinnt)
                result.completion_grid[mask] = layer.completion_grid[mask]
                # Stich-Typ uebernehmen -- siehe merge_layers() fuer die
                # Begruendung (sonst wird jeder uebernommene Halb-/Viertel-
                # stich stillschweigend zu einem vollen Stich).
                result.stitch_type_grid[mask] = layer.stitch_type_grid[mask]

        return result

    def get_composite_stitch(self, x: int, y: int) -> int | None:
        """
        Gibt den sichtbaren Farbindex an Position (x, y) zurück.

        Berücksichtigt Layer-Sichtbarkeit und -Reihenfolge.
        Das oberste sichtbare, nicht-transparente Pixel gewinnt.
        """
        # Von oben nach unten durchgehen
        for layer in reversed(self._layers):
            if layer.visible:
                stitch = layer.get_stitch(x, y)
                if stitch is not None:
                    return stitch
        return None

    def get_composite_grid(self) -> np.ndarray:
        """
        Erstellt ein zusammengesetztes Grid aller sichtbaren Layer.

        Returns:
            numpy-Array mit dem kombinierten Ergebnis
        """
        result = np.full((self._height, self._width), NO_STITCH, dtype=np.int16)

        for layer in self._layers:
            if layer.visible:
                mask = layer.grid != NO_STITCH
                result[mask] = layer.grid[mask]

        return result

    def get_composite_completion_grid(self) -> np.ndarray:
        """
        Erstellt ein zusammengesetztes Completion-Grid aller sichtbaren Layer.

        Pro Zelle gilt die Completion-Markierung des obersten sichtbaren
        Layers, der dort einen Stich hat — analog zu `get_composite_grid`
        (nicht: ORen über alle Layer). Ein tiefer liegender, verdeckter
        Layer, der zufaellig an derselben Position denselben Stich als
        erledigt/nicht-erledigt markiert hat, darf die Sichtbarkeit des
        tatsaechlich angezeigten (obersten) Stichs nicht überschreiben.

        Returns:
            numpy-Array (bool) mit dem Completion-Status des sichtbaren
            Stichs pro Zelle (False bei Zellen ohne Stich).
        """
        result = np.zeros((self._height, self._width), dtype=bool)

        for layer in self._layers:
            if layer.visible:
                mask = layer.grid != NO_STITCH
                result[mask] = layer.completion_grid[mask]

        return result

    def get_composite_stitch_type_grid(self) -> np.ndarray:
        """
        Erstellt ein zusammengesetztes Stitch-Type-Grid aller sichtbaren Layer.

        Pro Zelle gewinnt der oberste sichtbare Layer, der dort einen Stich
        hat — analog zu `get_composite_grid`. Bei Zellen ohne Stich ist der
        Type 0 (FULL — semantisch egal, da nichts gezeichnet wird).

        Returns:
            numpy-Array (uint8) mit Stitch-Types (0 = FULL, 1-9 = Sondertypen)
        """
        result = np.zeros((self._height, self._width), dtype=np.uint8)

        for layer in self._layers:
            if layer.visible and layer.stitch_type_grid is not None:
                mask = layer.grid != NO_STITCH
                result[mask] = layer.stitch_type_grid[mask]

        return result

    def resize(self, new_width: int, new_height: int) -> None:
        """Ändert die Größe aller Layer."""
        self._width = new_width
        self._height = new_height
        for layer in self._layers:
            layer.resize(new_width, new_height)

    def get_layer_by_id(self, layer_id: str) -> Layer | None:
        """Findet ein Layer nach ID."""
        for layer in self._layers:
            if layer.id == layer_id:
                return layer
        return None

    def get_layer_index(self, layer: Layer) -> int:
        """Gibt den Index eines Layers zurück."""
        try:
            return self._layers.index(layer)
        except ValueError:
            return -1

    def replace_all_layers(self, layers: list[Layer], active_index: int = 0) -> None:
        """
        Ersetzt alle Layer durch eine neue Liste.

        Öffentliche API für file_io und flatten_layers, um direkten
        Zugriff auf _layers und _active_index zu vermeiden.

        Args:
            layers: Neue Layer-Liste (muss mindestens ein Layer enthalten)
            active_index: Index des aktiven Layers (wird geclampt)
        """
        if not layers:
            raise ValueError("LayerStack benötigt mindestens ein Layer")
        self._layers = list(layers)
        self._active_index = max(0, min(active_index, len(self._layers) - 1))

    def append_layer_object(self, layer: Layer) -> None:
        """
        Fügt ein existierendes Layer-Objekt zum Stack hinzu.

        Öffentliche API für file_io zum Laden von Layern,
        im Unterschied zu add_layer() das ein neues Layer erstellt.

        Args:
            layer: Das hinzuzufügende Layer
        """
        self._layers.append(layer)
        if self._active_index < 0:
            self._active_index = 0
