"""
Undo/Redo-System mit Command-Pattern.

Dieses Modul implementiert ein vollständiges Undo/Redo-System für
alle Bearbeitungsoperationen im Pattern-Editor. Es verwendet das
Command-Pattern für saubere Kapselung und einfache Erweiterbarkeit.

Hauptkomponenten:
    - Command: Abstrakte Basisklasse für alle Operationen
    - UndoManager: Verwaltet die Undo/Redo-Stacks
    - Konkrete Commands: PlaceStitchCommand, RemoveStitchCommand, etc.

Example:
    >>> manager = UndoManager()
    >>> manager.set_pattern(pattern)
    >>> cmd = PlaceStitchCommand(pattern, x=10, y=10, color_index=0, layer_index=0)
    >>> manager.execute(cmd)
    >>> manager.undo()  # Stich wird entfernt
    >>> manager.redo()  # Stich wird wieder platziert
"""

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .backstitch_manager import Backstitch
    from .pattern import Pattern


class Command(ABC):
    """
    Abstrakte Basisklasse für alle Commands (Command-Pattern).

    Jeder Command kapselt eine atomare Operation, die ausgeführt
    und rückgängig gemacht werden kann. Commands sind unveränderlich
    nach der Erstellung.

    Subklassen müssen implementieren:
        - execute(): Führt die Operation aus
        - undo(): Macht die Operation rückgängig
        - description: Lesbare Beschreibung für die UI
    """

    @abstractmethod
    def execute(self) -> None:
        """
        Führt den Command aus.

        Diese Methode wird beim ersten Ausführen und bei Redo aufgerufen.
        Implementierungen sollten den vorherigen Zustand speichern,
        um undo() zu ermöglichen.
        """
        pass

    @abstractmethod
    def undo(self) -> None:
        """
        Macht den Command rückgängig.

        Stellt den Zustand vor execute() wieder her.
        Muss idempotent sein (mehrfaches Aufrufen hat keine Nebenwirkungen).
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Gibt eine lesbare Beschreibung des Commands zurück.

        Wird in der UI für Undo/Redo-Menüs verwendet.

        Returns:
            Kurze Beschreibung wie "Stich bei (10, 20)"
        """
        pass


@dataclass
class StitchData:
    """
    Datenklasse für einen einzelnen Stich.

    Speichert alle Informationen, die zum Wiederherstellen
    eines Stichs benötigt werden.

    Attributes:
        x: X-Koordinate des Stichs
        y: Y-Koordinate des Stichs
        color_index: Index der Farbe in der Palette
        layer_index: Index des Layers im Stack
    """

    x: int
    y: int
    color_index: int
    layer_index: int


class PlaceStitchCommand(Command):
    """
    Command zum Platzieren eines einzelnen Stichs.

    Speichert den vorherigen Stich (falls vorhanden) für Undo.
    Aktualisiert automatisch die Stichzählung in der Palette.

    Attributes:
        _pattern: Referenz auf das Pattern
        _x, _y: Koordinaten des Stichs
        _color_index: Index der neuen Farbe
        _layer_index: Index des Ziel-Layers

    Example:
        >>> cmd = PlaceStitchCommand(pattern, 10, 20, color_index=0, layer_index=0)
        >>> cmd.execute()  # Stich wird platziert
        >>> cmd.undo()     # Vorheriger Zustand wird wiederhergestellt
    """

    def __init__(
        self,
        pattern: "Pattern",
        x: int,
        y: int,
        color_index: int,
        layer_index: int,
        stitch_type: int = 0,
    ) -> None:
        """
        Erstellt einen neuen PlaceStitchCommand.

        Args:
            pattern: Das zu bearbeitende Pattern
            x: X-Koordinate des Stichs
            y: Y-Koordinate des Stichs
            color_index: Index der Farbe in color_entries
            layer_index: Index des Layers im layer_stack
            stitch_type: Stichtyp (0=FULL, 1=HALF_TL_BR, etc.)
        """
        self._pattern = pattern
        self._x = x
        self._y = y
        self._color_index = color_index
        self._layer_index = layer_index
        self._stitch_type = stitch_type
        self._old_color_index: int | None = None
        self._old_stitch_type: int = 0
        self._had_stitch = False

    def execute(self) -> None:
        """Platziert den Stich und speichert den vorherigen Zustand."""
        layer = self._pattern.layer_stack[self._layer_index]
        old_stitch = layer.get_stitch(self._x, self._y)

        if old_stitch is not None:
            self._had_stitch = True
            self._old_color_index = old_stitch
            self._old_stitch_type = layer.get_stitch_type(self._x, self._y)
            # Alte Stichzahl reduzieren
            if 0 <= old_stitch < len(self._pattern.color_entries):
                self._pattern.color_entries[old_stitch].stitch_count -= 1

        layer.set_stitch(self._x, self._y, self._color_index, stitch_type=self._stitch_type)

        # Neue Stichzahl erhöhen
        if 0 <= self._color_index < len(self._pattern.color_entries):
            self._pattern.color_entries[self._color_index].stitch_count += 1

    def undo(self) -> None:
        """Entfernt den Stich und stellt den vorherigen Zustand wieder her."""
        layer = self._pattern.layer_stack[self._layer_index]

        # Aktuelle Stichzahl reduzieren
        if 0 <= self._color_index < len(self._pattern.color_entries):
            self._pattern.color_entries[self._color_index].stitch_count -= 1

        if self._had_stitch and self._old_color_index is not None:
            layer.set_stitch(
                self._x, self._y, self._old_color_index, stitch_type=self._old_stitch_type
            )
            # Alte Stichzahl wiederherstellen
            if 0 <= self._old_color_index < len(self._pattern.color_entries):
                self._pattern.color_entries[self._old_color_index].stitch_count += 1
        else:
            layer.remove_stitch(self._x, self._y)

    @property
    def description(self) -> str:
        """Gibt 'Stich bei (x, y)' zurück."""
        return f"Stich bei ({self._x}, {self._y})"


class RemoveStitchCommand(Command):
    """
    Command zum Entfernen eines einzelnen Stichs.

    Speichert die vorherige Farbe für Undo.
    Aktualisiert automatisch die Stichzählung.

    Example:
        >>> cmd = RemoveStitchCommand(pattern, 10, 20, layer_index=0)
        >>> cmd.execute()  # Stich wird entfernt
        >>> cmd.undo()     # Stich wird wiederhergestellt
    """

    def __init__(self, pattern: "Pattern", x: int, y: int, layer_index: int) -> None:
        """
        Erstellt einen neuen RemoveStitchCommand.

        Args:
            pattern: Das zu bearbeitende Pattern
            x: X-Koordinate des Stichs
            y: Y-Koordinate des Stichs
            layer_index: Index des Layers im layer_stack
        """
        self._pattern = pattern
        self._x = x
        self._y = y
        self._layer_index = layer_index
        self._old_color_index: int | None = None

    def execute(self) -> None:
        """Entfernt den Stich und speichert die vorherige Farbe."""
        layer = self._pattern.layer_stack[self._layer_index]
        old_stitch = layer.get_stitch(self._x, self._y)

        if old_stitch is not None:
            self._old_color_index = old_stitch
            layer.remove_stitch(self._x, self._y)
            # Stichzahl reduzieren
            if 0 <= old_stitch < len(self._pattern.color_entries):
                self._pattern.color_entries[old_stitch].stitch_count -= 1

    def undo(self) -> None:
        """Stellt den entfernten Stich wieder her."""
        if self._old_color_index is not None:
            layer = self._pattern.layer_stack[self._layer_index]
            layer.set_stitch(self._x, self._y, self._old_color_index)
            # Stichzahl wiederherstellen
            if 0 <= self._old_color_index < len(self._pattern.color_entries):
                self._pattern.color_entries[self._old_color_index].stitch_count += 1

    @property
    def description(self) -> str:
        """Gibt 'Stich entfernt bei (x, y)' zurück."""
        return f"Stich entfernt bei ({self._x}, {self._y})"


class BatchStitchCommand(Command):
    """
    Command für mehrere Stiche auf einmal.

    Wird verwendet für zusammenhängende Operationen wie:
    - Linien zeichnen
    - Rechtecke füllen
    - Drag-Operationen

    Alle Sub-Commands werden als eine atomare Operation behandelt,
    d.h. Undo macht alle auf einmal rückgängig.

    Example:
        >>> batch = BatchStitchCommand(pattern, "Linie zeichnen")
        >>> batch.add_command(PlaceStitchCommand(pattern, 0, 0, 0, 0))
        >>> batch.add_command(PlaceStitchCommand(pattern, 1, 1, 0, 0))
        >>> batch.execute()  # Beide Stiche werden platziert
        >>> batch.undo()     # Beide Stiche werden entfernt
    """

    def __init__(self, pattern: "Pattern", description_text: str = "Mehrere Stiche") -> None:
        """
        Erstellt einen neuen BatchStitchCommand.

        Args:
            pattern: Das zu bearbeitende Pattern
            description_text: Beschreibung für die UI (z.B. "Linie zeichnen")
        """
        self._pattern = pattern
        self._description_text = description_text
        self._commands: list[Command] = []

    def add_command(self, command: Command) -> None:
        """
        Fügt einen Sub-Command zur Batch hinzu.

        Hinweis: Der Command wird NICHT automatisch ausgeführt.
        Verwende add_to_batch() des UndoManagers für sofortige Ausführung.

        Args:
            command: Der hinzuzufügende Command
        """
        self._commands.append(command)

    def execute(self) -> None:
        """Führt alle Sub-Commands in Reihenfolge aus."""
        for cmd in self._commands:
            cmd.execute()

    def undo(self) -> None:
        """Macht alle Sub-Commands in umgekehrter Reihenfolge rückgängig."""
        for cmd in reversed(self._commands):
            cmd.undo()

    @property
    def description(self) -> str:
        """Gibt 'Beschreibung (n)' zurück, wobei n die Anzahl der Commands ist."""
        return f"{self._description_text} ({len(self._commands)})"

    @property
    def is_empty(self) -> bool:
        """
        Prüft ob die Batch leer ist.

        Returns:
            True wenn keine Sub-Commands vorhanden sind
        """
        return len(self._commands) == 0


class AddBackstitchCommand(Command):
    """
    Command zum Hinzufügen eines Rückstichs (Backstitch).

    Rückstiche sind Linien, die über das Muster gelegt werden,
    typischerweise für Konturen und Details.

    Example:
        >>> cmd = AddBackstitchCommand(pattern, 0, 0, 4, 4, color_index=0)
        >>> cmd.execute()  # Diagonaler Rückstich wird hinzugefügt
    """

    def __init__(
        self, pattern: "Pattern", x1: int, y1: int, x2: int, y2: int, color_index: int
    ) -> None:
        """
        Erstellt einen neuen AddBackstitchCommand.

        Koordinaten sind in halben Stichen (0 = Ecke, 1 = Mitte, 2 = nächste Ecke).

        Args:
            pattern: Das zu bearbeitende Pattern
            x1, y1: Startkoordinaten in halben Stichen
            x2, y2: Endkoordinaten in halben Stichen
            color_index: Index der Farbe für den Rückstich
        """
        self._pattern = pattern
        self._x1 = x1
        self._y1 = y1
        self._x2 = x2
        self._y2 = y2
        self._color_index = color_index
        self._backstitch: "Backstitch | None" = None

    def execute(self) -> None:
        """Fügt den Rückstich zum Pattern hinzu."""
        self._backstitch = self._pattern.add_backstitch(
            self._x1, self._y1, self._x2, self._y2, self._color_index
        )

    def undo(self) -> None:
        """Entfernt den hinzugefügten Rückstich."""
        if self._backstitch:
            self._pattern.remove_backstitch(self._backstitch)

    @property
    def description(self) -> str:
        """Gibt 'Rückstich (x1,y1)->(x2,y2)' zurück."""
        return f"Rückstich ({self._x1},{self._y1})->({self._x2},{self._y2})"


class RemoveBackstitchCommand(Command):
    """
    Command zum Entfernen eines Rückstichs.

    Speichert den Rückstich für Undo.

    Example:
        >>> cmd = RemoveBackstitchCommand(pattern, backstitch)
        >>> cmd.execute()  # Rückstich wird entfernt
        >>> cmd.undo()     # Rückstich wird wiederhergestellt
    """

    def __init__(self, pattern: "Pattern", backstitch: "Backstitch") -> None:
        """
        Erstellt einen neuen RemoveBackstitchCommand.

        Args:
            pattern: Das zu bearbeitende Pattern
            backstitch: Der zu entfernende Backstitch
        """
        self._pattern = pattern
        self._backstitch = backstitch

    def execute(self) -> None:
        """Entfernt den Rückstich aus dem Pattern."""
        self._pattern.remove_backstitch(self._backstitch)

    def undo(self) -> None:
        """Fügt den entfernten Rückstich wieder hinzu."""
        self._pattern.restore_backstitch(self._backstitch)

    @property
    def description(self) -> str:
        """Gibt 'Rückstich entfernt (x1,y1)->(x2,y2)' zurück."""
        bs = self._backstitch
        return f"Rückstich entfernt ({bs.x1},{bs.y1})->({bs.x2},{bs.y2})"


class ClearLayerCommand(Command):
    """
    Command zum Leeren einer kompletten Ebene.

    Speichert das gesamte Grid als numpy-Array für effizientes Undo.
    Aktualisiert alle betroffenen Stichzählungen.

    Example:
        >>> cmd = ClearLayerCommand(pattern, layer_index=0)
        >>> cmd.execute()  # Alle Stiche auf Layer 0 werden entfernt
        >>> cmd.undo()     # Alle Stiche werden wiederhergestellt
    """

    def __init__(self, pattern: "Pattern", layer_index: int) -> None:
        """
        Erstellt einen neuen ClearLayerCommand.

        Args:
            pattern: Das zu bearbeitende Pattern
            layer_index: Index des zu leerenden Layers
        """
        self._pattern = pattern
        self._layer_index = layer_index
        self._old_grid: np.ndarray | None = None
        self._old_completion_grid: np.ndarray | None = None

    def execute(self) -> None:
        """Leert das Layer und speichert den vorherigen Zustand."""
        layer = self._pattern.layer_stack[self._layer_index]

        # Grid und Completion als Kopie speichern (numpy-effizient)
        self._old_grid = layer.grid.copy()
        self._old_completion_grid = layer.completion_grid.copy()

        # Stichzahlen reduzieren
        color_counts = layer.get_color_counts()
        for color_index, count in color_counts.items():
            if 0 <= color_index < len(self._pattern.color_entries):
                self._pattern.color_entries[color_index].stitch_count -= count

        layer.clear()

    def undo(self) -> None:
        """Stellt das geleerte Layer wieder her."""
        layer = self._pattern.layer_stack[self._layer_index]

        if self._old_grid is not None:
            # Grid wiederherstellen (numpy-effizient)
            layer.grid = self._old_grid.copy()

            # Stichzahlen wiederherstellen
            color_counts = layer.get_color_counts()
            for color_index, count in color_counts.items():
                if 0 <= color_index < len(self._pattern.color_entries):
                    self._pattern.color_entries[color_index].stitch_count += count

        if self._old_completion_grid is not None:
            layer.completion_grid = self._old_completion_grid.copy()

    @property
    def description(self) -> str:
        """Gibt 'Ebene 'Name' geleert' zurück."""
        layer = self._pattern.layer_stack[self._layer_index]
        return f"Ebene '{layer.name}' geleert"


class MarkStitchCompletedCommand(Command):
    """
    Command zum Markieren eines Stichs als erledigt.

    Speichert den vorherigen Zustand für Undo.

    Example:
        >>> cmd = MarkStitchCompletedCommand(pattern, 10, 20, layer_index=0)
        >>> cmd.execute()  # Stich wird als erledigt markiert
        >>> cmd.undo()     # Markierung wird entfernt
    """

    def __init__(self, pattern: "Pattern", x: int, y: int, layer_index: int) -> None:
        self._pattern = pattern
        self._x = x
        self._y = y
        self._layer_index = layer_index
        self._was_completed = False

    def execute(self) -> None:
        """Markiert den Stich als erledigt."""
        layer = self._pattern.layer_stack[self._layer_index]
        self._was_completed = layer.is_completed(self._x, self._y)
        layer.mark_completed(self._x, self._y)

    def undo(self) -> None:
        """Stellt den vorherigen Zustand wieder her."""
        if not self._was_completed:
            layer = self._pattern.layer_stack[self._layer_index]
            layer.unmark_completed(self._x, self._y)

    @property
    def description(self) -> str:
        return f"Stich erledigt bei ({self._x}, {self._y})"


class UnmarkStitchCompletedCommand(Command):
    """
    Command zum Entfernen der Erledigt-Markierung eines Stichs.

    Example:
        >>> cmd = UnmarkStitchCompletedCommand(pattern, 10, 20, layer_index=0)
        >>> cmd.execute()  # Markierung wird entfernt
        >>> cmd.undo()     # Markierung wird wiederhergestellt
    """

    def __init__(self, pattern: "Pattern", x: int, y: int, layer_index: int) -> None:
        self._pattern = pattern
        self._x = x
        self._y = y
        self._layer_index = layer_index
        self._was_completed = False

    def execute(self) -> None:
        """Entfernt die Erledigt-Markierung."""
        layer = self._pattern.layer_stack[self._layer_index]
        self._was_completed = layer.is_completed(self._x, self._y)
        layer.unmark_completed(self._x, self._y)

    def undo(self) -> None:
        """Stellt die Markierung wieder her, falls sie vorher gesetzt war."""
        if self._was_completed:
            layer = self._pattern.layer_stack[self._layer_index]
            layer.mark_completed(self._x, self._y)

    @property
    def description(self) -> str:
        return f"Stich nicht erledigt bei ({self._x}, {self._y})"


class MarkColorCompletedCommand(Command):
    """
    Command zum Markieren aller Stiche einer Farbe als erledigt.

    Speichert alle completion_grids für vollständiges Undo.

    Example:
        >>> cmd = MarkColorCompletedCommand(pattern, color_index=0)
        >>> cmd.execute()  # Alle Stiche von Farbe 0 werden als erledigt markiert
        >>> cmd.undo()     # Vorheriger Zustand wird wiederhergestellt
    """

    def __init__(self, pattern: "Pattern", color_index: int) -> None:
        self._pattern = pattern
        self._color_index = color_index
        self._old_grids: list[np.ndarray] = []

    def execute(self) -> None:
        """Markiert alle Stiche der Farbe als erledigt."""
        self._old_grids = []
        for layer in self._pattern.layer_stack:
            self._old_grids.append(layer.completion_grid.copy())
            mask = layer.grid == self._color_index
            layer.completion_grid[mask] = True

    def undo(self) -> None:
        """Stellt den vorherigen Zustand aller completion_grids wieder her."""
        for layer, old_grid in zip(self._pattern.layer_stack, self._old_grids):
            layer.completion_grid = old_grid.copy()

    @property
    def description(self) -> str:
        return f"Alle Stiche Farbe {self._color_index} erledigt"


class UndoManager:
    """
    Verwaltet die Undo/Redo-Historie für ein Pattern.

    Verwendet zwei Stacks (implementiert als deque mit maxlen):
    - undo_stack: Ausgeführte Commands
    - redo_stack: Rückgängig gemachte Commands

    Unterstützt Batch-Operationen für zusammenhängende Aktionen.
    Die Historie ist automatisch auf max_history begrenzt.

    Attributes:
        max_history: Maximale Anzahl an Undo-Schritten (Standard: 100)

    Example:
        >>> manager = UndoManager(max_history=50)
        >>> manager.set_pattern(pattern)
        >>>
        >>> # Einzelne Operation
        >>> manager.execute(PlaceStitchCommand(pattern, 10, 10, 0, 0))
        >>>
        >>> # Batch-Operation (z.B. beim Zeichnen einer Linie)
        >>> manager.begin_batch("Linie zeichnen")
        >>> for x in range(10):
        ...     manager.add_to_batch(PlaceStitchCommand(pattern, x, x, 0, 0))
        >>> manager.end_batch()
        >>>
        >>> manager.undo()  # Macht die gesamte Linie rückgängig
    """

    def __init__(self, max_history: int = 100) -> None:
        """
        Erstellt einen neuen UndoManager.

        Args:
            max_history: Maximale Anzahl gespeicherter Undo-Schritte.
                        Ältere Einträge werden automatisch verworfen.
        """
        self._undo_stack: deque[Command] = deque(maxlen=max_history)
        self._redo_stack: deque[Command] = deque()
        self._max_history = max_history
        self._batch_command: BatchStitchCommand | None = None
        self._pattern: "Pattern | None" = None

    def set_pattern(self, pattern: "Pattern") -> None:
        """
        Setzt das aktuelle Pattern und löscht die Historie.

        Sollte aufgerufen werden, wenn ein neues Pattern geladen
        oder erstellt wird.

        Args:
            pattern: Das neue Pattern
        """
        self._pattern = pattern
        self.clear()

    def execute(self, command: Command) -> None:
        """
        Führt einen Command aus und speichert ihn im Undo-Stack.

        Löscht den Redo-Stack, da nach einer neuen Aktion
        kein Redo mehr möglich ist.

        Args:
            command: Der auszuführende Command
        """
        command.execute()
        self._undo_stack.append(command)
        self._redo_stack.clear()
        # Historie wird automatisch durch maxlen begrenzt

    def begin_batch(self, description: str = "Mehrere Stiche") -> None:
        """
        Beginnt eine Batch-Operation.

        Alle folgenden add_to_batch() Aufrufe werden zu einer
        atomaren Operation zusammengefasst.

        Args:
            description: Beschreibung für die UI

        Note:
            Muss mit end_batch() oder cancel_batch() beendet werden.
        """
        if self._pattern:
            self._batch_command = BatchStitchCommand(self._pattern, description)

    def add_to_batch(self, command: Command) -> None:
        """
        Fügt einen Command zur aktuellen Batch hinzu und führt ihn aus.

        Im Gegensatz zu BatchStitchCommand.add_command() wird der
        Command sofort ausgeführt.

        Args:
            command: Der hinzuzufügende und auszuführende Command

        Note:
            Hat keine Wirkung, wenn keine Batch aktiv ist.
        """
        if self._batch_command:
            command.execute()
            self._batch_command.add_command(command)

    def end_batch(self) -> None:
        """
        Beendet die Batch-Operation und speichert sie im Undo-Stack.

        Leere Batches werden ignoriert.
        Löscht den Redo-Stack.
        """
        if self._batch_command and not self._batch_command.is_empty:
            self._undo_stack.append(self._batch_command)
            self._redo_stack.clear()
            # Historie wird automatisch durch maxlen begrenzt

        self._batch_command = None

    def cancel_batch(self) -> None:
        """
        Bricht die Batch-Operation ab und macht alle Änderungen rückgängig.

        Nützlich wenn der Benutzer eine Aktion abbricht (z.B. Escape).
        """
        if self._batch_command:
            self._batch_command.undo()
            self._batch_command = None

    @property
    def in_batch(self) -> bool:
        """
        Prüft ob gerade eine Batch-Operation aktiv ist.

        Returns:
            True wenn begin_batch() aufgerufen wurde ohne end_batch()/cancel_batch()
        """
        return self._batch_command is not None

    def undo(self) -> bool:
        """
        Macht den letzten Command rückgängig.

        Der Command wird in den Redo-Stack verschoben.

        Returns:
            True wenn ein Command rückgängig gemacht wurde,
            False wenn der Undo-Stack leer ist
        """
        if not self._undo_stack:
            return False

        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        return True

    def redo(self) -> bool:
        """
        Wiederholt den zuletzt rückgängig gemachten Command.

        Der Command wird zurück in den Undo-Stack verschoben.

        Returns:
            True wenn ein Command wiederholt wurde,
            False wenn der Redo-Stack leer ist
        """
        if not self._redo_stack:
            return False

        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)
        return True

    def clear(self) -> None:
        """
        Löscht die gesamte Historie (Undo und Redo).

        Bricht auch eine eventuell aktive Batch-Operation ab
        (ohne Undo).
        """
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._batch_command = None

    @property
    def can_undo(self) -> bool:
        """
        Prüft ob Undo möglich ist.

        Returns:
            True wenn mindestens ein Command im Undo-Stack ist
        """
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        """
        Prüft ob Redo möglich ist.

        Returns:
            True wenn mindestens ein Command im Redo-Stack ist
        """
        return len(self._redo_stack) > 0

    @property
    def undo_description(self) -> str:
        """
        Gibt die Beschreibung des nächsten Undo-Commands zurück.

        Nützlich für Menü-Einträge wie "Rückgängig: Stich bei (10, 20)".

        Returns:
            Beschreibung des Commands oder leerer String
        """
        if self._undo_stack:
            return self._undo_stack[-1].description
        return ""

    @property
    def redo_description(self) -> str:
        """
        Gibt die Beschreibung des nächsten Redo-Commands zurück.

        Nützlich für Menü-Einträge wie "Wiederholen: Stich bei (10, 20)".

        Returns:
            Beschreibung des Commands oder leerer String
        """
        if self._redo_stack:
            return self._redo_stack[-1].description
        return ""

    @property
    def undo_count(self) -> int:
        """
        Gibt die Anzahl der Undo-Schritte zurück.

        Returns:
            Anzahl der Commands im Undo-Stack
        """
        return len(self._undo_stack)

    @property
    def redo_count(self) -> int:
        """
        Gibt die Anzahl der Redo-Schritte zurück.

        Returns:
            Anzahl der Commands im Redo-Stack
        """
        return len(self._redo_stack)
