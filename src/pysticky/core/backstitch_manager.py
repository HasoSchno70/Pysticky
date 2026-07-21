"""
Backstitch-Manager für Rückstich-Verwaltung.

Rückstiche (Backstitches) sind Linien zwischen Eckpunkten/Mitten von Stichen,
die über den normalen Kreuzstichen gezeichnet werden für Konturen und Details.

Koordinatensystem (in halben Stichen):
    - Jeder Kreuzstich belegt einen 2x2 Bereich
    - (0,0), (2,0), (0,2), (2,2) = Ecken einer Zelle
    - (1,1) = Mitte einer Zelle
    - (1,0), (0,1), (2,1), (1,2) = Kantenmittelpunkte

Example:
    >>> manager = BackstitchManager()
    >>> bs = manager.add(0, 0, 4, 4, color_index=0)  # Diagonale über 2 Zellen
    >>> manager.count()
    1
    >>> manager.remove(bs)
    True
"""

from dataclasses import dataclass
from typing import Callable, Iterator


@dataclass
class Backstitch:
    """
    Repräsentiert einen Rückstich (Linie zwischen zwei Punkten).

    Koordinaten sind in halben Stichen, was feinere Platzierung erlaubt:
    - (0,0) = linke obere Ecke des ersten Stichs
    - (2,2) = rechte untere Ecke des ersten Stichs
    - (1,1) = Mitte des ersten Stichs

    Attributes:
        x1: X-Koordinate des Startpunkts (in halben Stichen)
        y1: Y-Koordinate des Startpunkts (in halben Stichen)
        x2: X-Koordinate des Endpunkts (in halben Stichen)
        y2: Y-Koordinate des Endpunkts (in halben Stichen)
        color_index: Index der Farbe in der Pattern-Palette

    Example:
        >>> bs = Backstitch(0, 0, 2, 2, color_index=0)  # Diagonal über eine Zelle
        >>> bs.to_dict()
        {'x1': 0, 'y1': 0, 'x2': 2, 'y2': 2, 'color_index': 0}
    """

    x1: int
    y1: int
    x2: int
    y2: int
    color_index: int

    def __repr__(self) -> str:
        """Gibt eine lesbare Repräsentation zurück."""
        return f"Backstitch(({self.x1},{self.y1})->({self.x2},{self.y2}), color={self.color_index})"

    def to_dict(self) -> dict:
        """
        Konvertiert zu Dictionary für Serialisierung.

        Returns:
            Dictionary mit x1, y1, x2, y2, color_index
        """
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "color_index": self.color_index,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Backstitch":
        """
        Erstellt einen Backstitch aus einem Dictionary.

        Args:
            data: Dictionary mit x1, y1, x2, y2, color_index

        Returns:
            Neue Backstitch-Instanz
        """
        return cls(
            x1=data["x1"],
            y1=data["y1"],
            x2=data["x2"],
            y2=data["y2"],
            color_index=data["color_index"],
        )


class BackstitchManager:
    """
    Verwaltet alle Rückstiche eines Musters.

    Bietet Methoden zum Hinzufügen, Entfernen und Suchen von Rückstichen.
    Unterstützt Serialisierung für Datei-I/O.

    Das Koordinatensystem verwendet halbe Stiche:
    - Ecken: (0,0), (2,0), (0,2), (2,2) einer Zelle
    - Mitte: (1,1)
    - Kanten-Mitten: (1,0), (0,1), (2,1), (1,2)

    Attributes:
        backstitches: Liste aller Rückstiche (read-only Property)

    Example:
        >>> manager = BackstitchManager()
        >>> bs = manager.add(0, 0, 4, 4, color_index=0)
        >>> manager.find_at(2, 2)  # Findet bs weil Punkt auf Linie
        Backstitch((0,0)->(4,4), color=0)
    """

    def __init__(self) -> None:
        """Initialisiert einen leeren BackstitchManager."""
        self._backstitches: list[Backstitch] = []

    @property
    def backstitches(self) -> list[Backstitch]:
        """
        Gibt die Liste aller Rückstiche zurück.

        Returns:
            Liste der Backstitch-Objekte (direkter Zugriff, keine Kopie)

        Warning:
            Direkte Manipulation der Liste kann zu Inkonsistenzen führen.
            Verwende add() und remove() stattdessen.
        """
        return self._backstitches

    def add(self, x1: int, y1: int, x2: int, y2: int, color_index: int) -> Backstitch:
        """
        Fügt einen neuen Rückstich hinzu.

        Args:
            x1: X-Koordinate des Startpunkts (in halben Stichen)
            y1: Y-Koordinate des Startpunkts (in halben Stichen)
            x2: X-Koordinate des Endpunkts (in halben Stichen)
            y2: Y-Koordinate des Endpunkts (in halben Stichen)
            color_index: Index der Farbe in der Pattern-Palette

        Returns:
            Der erstellte Backstitch

        Example:
            >>> bs = manager.add(0, 0, 2, 2, 0)  # Diagonale in Zelle (0,0)
        """
        backstitch = Backstitch(x1, y1, x2, y2, color_index)
        self._backstitches.append(backstitch)
        return backstitch

    def restore(self, backstitch: Backstitch) -> None:
        """
        Fügt einen bereits existierenden Backstitch wieder hinzu (Undo einer
        Entfernung). Anders als add() wird KEIN neues Objekt konstruiert --
        wichtig falls anderer Code (z.B. eine Selektion) noch die exakte
        Objektidentität des entfernten Backstitch referenziert.

        Args:
            backstitch: Der wiederherzustellende Backstitch
        """
        self._backstitches.append(backstitch)

    def transform(
        self, fn: Callable[[int, int, int, int], tuple[int, int, int, int] | None]
    ) -> None:
        """Wendet eine Koordinaten-Transformation auf alle Rückstiche an --
        für Pattern-weite Rotate/Flip/Crop/Resize-Operationen, die die
        Stich-Grids bereits transformieren, aber Rückstich-Koordinaten
        (absolute Pattern-Positionen in halben Stichen) sonst unangetastet
        lassen würden.

        Args:
            fn: Bekommt (x1, y1, x2, y2) eines Rückstichs und gibt entweder
                die neuen Koordinaten zurück, oder None um den Rückstich zu
                verwerfen (z.B. weil er nach einem Crop/Verkleinern
                außerhalb des neuen Bereichs liegt).
        """
        new_backstitches = []
        for bs in self._backstitches:
            result = fn(bs.x1, bs.y1, bs.x2, bs.y2)
            if result is None:
                continue
            x1, y1, x2, y2 = result
            new_backstitches.append(Backstitch(x1, y1, x2, y2, bs.color_index))
        self._backstitches = new_backstitches

    def remove(self, backstitch: Backstitch) -> bool:
        """
        Entfernt einen bestimmten Rückstich.

        Args:
            backstitch: Der zu entfernende Backstitch

        Returns:
            True wenn gefunden und entfernt, False wenn nicht gefunden

        Note:
            Vergleicht per Objekt-Identität, nicht per Wert. `Backstitch`
            ist ein normales (nicht-frozen) Dataclass mit wertbasiertem
            `__eq__` -- `in`/`list.remove()` haetten zwei Rueckstiche mit
            identischen Koordinaten+Farbe (z.B. zweimal dieselbe Linie
            gezeichnet) nicht unterscheiden koennen und potenziell die
            FALSCHE, aber wertgleiche Instanz geloescht. Beide Aufrufer
            (undo.py) uebergeben ohnehin immer die exakte Instanz, die sie
            selbst zuvor erhalten haben -- Identitaet ist hier die
            eigentlich gemeinte Semantik.
        """
        for i, existing in enumerate(self._backstitches):
            if existing is backstitch:
                del self._backstitches[i]
                return True
        return False

    def remove_at(self, x: int, y: int, tolerance: int = 1) -> Backstitch | None:
        """
        Entfernt einen Rückstich an einer bestimmten Position.

        Findet den ersten Rückstich, der durch den Punkt (x, y) verläuft
        (mit Toleranz), und entfernt ihn.

        Args:
            x: X-Koordinate (in halben Stichen)
            y: Y-Koordinate (in halben Stichen)
            tolerance: Maximaler Abstand zur Linie (Standard: 1)

        Returns:
            Der entfernte Backstitch oder None wenn keiner gefunden
        """
        for bs in self._backstitches:
            if self._point_on_line(x, y, bs.x1, bs.y1, bs.x2, bs.y2, tolerance):
                self._backstitches.remove(bs)
                return bs
        return None

    def find_at(self, x: int, y: int, tolerance: int = 2) -> Backstitch | None:
        """
        Findet einen Rückstich an einer Position ohne ihn zu entfernen.

        Nützlich für Hover-Effekte oder Auswahl.

        Args:
            x: X-Koordinate (in halben Stichen)
            y: Y-Koordinate (in halben Stichen)
            tolerance: Maximaler Abstand zur Linie (Standard: 2)

        Returns:
            Der erste gefundene Backstitch oder None
        """
        for bs in self._backstitches:
            if self._point_on_line(x, y, bs.x1, bs.y1, bs.x2, bs.y2, tolerance):
                return bs
        return None

    def get_in_area(self, x1: int, y1: int, x2: int, y2: int) -> list[Backstitch]:
        """
        Gibt alle Rückstiche zurück, die einen rechteckigen Bereich berühren.

        Ein Rückstich wird eingeschlossen wenn seine Bounding-Box
        den angegebenen Bereich überlappt.

        Args:
            x1: X-Koordinate der linken oberen Ecke (in halben Stichen)
            y1: Y-Koordinate der linken oberen Ecke
            x2: X-Koordinate der rechten unteren Ecke
            y2: Y-Koordinate der rechten unteren Ecke

        Returns:
            Liste aller Backstitches die den Bereich berühren
        """
        result = []
        for bs in self._backstitches:
            # Prüfen ob Linie den Bereich schneidet (Bounding-Box Überlappung)
            if (
                max(bs.x1, bs.x2) >= x1
                and min(bs.x1, bs.x2) <= x2
                and max(bs.y1, bs.y2) >= y1
                and min(bs.y1, bs.y2) <= y2
            ):
                result.append(bs)
        return result

    def get_by_color(self, color_index: int) -> list[Backstitch]:
        """
        Gibt alle Rückstiche einer bestimmten Farbe zurück.

        Args:
            color_index: Index der Farbe in der Palette

        Returns:
            Liste aller Backstitches mit dieser Farbe
        """
        return [bs for bs in self._backstitches if bs.color_index == color_index]

    def update_color_indices(self, removed_index: int) -> None:
        """
        Aktualisiert Farbindizes nach dem Entfernen einer Farbe aus der Palette.

        - Entfernt alle Backstitches mit dem gelöschten Farbindex
        - Dekrementiert alle höheren Farbindizes um 1

        Args:
            removed_index: Der Index der entfernten Farbe

        Example:
            >>> # Farbe 2 wurde entfernt
            >>> manager.update_color_indices(2)
            >>> # Backstitch mit color_index=3 hat jetzt color_index=2
        """
        # Backstitches mit diesem Index entfernen
        self._backstitches = [bs for bs in self._backstitches if bs.color_index != removed_index]

        # Höhere Indizes anpassen
        for bs in self._backstitches:
            if bs.color_index > removed_index:
                # Dataclass ist mutable, direkter Zugriff möglich
                object.__setattr__(bs, "color_index", bs.color_index - 1)

    def clear(self) -> None:
        """Entfernt alle Rückstiche."""
        self._backstitches.clear()

    def count(self) -> int:
        """
        Gibt die Anzahl der Rückstiche zurück.

        Returns:
            Anzahl der gespeicherten Backstitches
        """
        return len(self._backstitches)

    def _point_on_line(
        self, px: int, py: int, x1: int, y1: int, x2: int, y2: int, tol: int
    ) -> bool:
        """
        Prüft ob ein Punkt auf einer Linie liegt (mit Toleranz).

        Verwendet Projektion auf die Linie und Abstandsberechnung.

        Args:
            px, py: Zu prüfender Punkt
            x1, y1: Startpunkt der Linie
            x2, y2: Endpunkt der Linie
            tol: Maximaler Abstand zur Linie

        Returns:
            True wenn der Punkt innerhalb der Toleranz auf der Linie liegt
        """
        # Bounding-Box prüfen (schnelle Vorprüfung)
        if px < min(x1, x2) - tol or px > max(x1, x2) + tol:
            return False
        if py < min(y1, y2) - tol or py > max(y1, y2) + tol:
            return False

        # Linien-Richtungsvektor
        dx = x2 - x1
        dy = y2 - y1
        length_sq = dx * dx + dy * dy

        if length_sq == 0:
            # Linie ist ein Punkt (Start == Ende)
            return abs(px - x1) <= tol and abs(py - y1) <= tol

        # Projektion des Punktes auf die Linie (Parameter t in [0, 1])
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / length_sq))

        # Nächster Punkt auf der Linie
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy

        # Euklidischer Abstand
        dist = ((px - proj_x) ** 2 + (py - proj_y) ** 2) ** 0.5
        return dist <= tol

    def to_list(self) -> list[dict]:
        """
        Konvertiert alle Backstitches zu einer Liste von Dictionaries.

        Für Serialisierung/Export.

        Returns:
            Liste von Dictionaries, jedes mit x1, y1, x2, y2, color_index
        """
        return [bs.to_dict() for bs in self._backstitches]

    def from_list(self, data: list[dict]) -> None:
        """
        Lädt Backstitches aus einer Liste von Dictionaries.

        Ersetzt alle vorhandenen Backstitches.

        Args:
            data: Liste von Dictionaries aus to_list()
        """
        self._backstitches = [Backstitch.from_dict(d) for d in data]

    def __len__(self) -> int:
        """
        Gibt die Anzahl der Rückstiche zurück.

        Returns:
            Anzahl der gespeicherten Backstitches
        """
        return len(self._backstitches)

    def __iter__(self) -> Iterator[Backstitch]:
        """
        Iteriert über alle Rückstiche.

        Yields:
            Backstitch-Objekte in Einfügereihenfolge
        """
        return iter(self._backstitches)

    def __repr__(self) -> str:
        """Gibt eine lesbare Repräsentation zurück."""
        return f"BackstitchManager({len(self._backstitches)} backstitches)"
