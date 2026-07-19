"""
Stickpfad-Optimierung für Kreuzstich-Muster.

Berechnet die optimale Reihenfolge der Stiche pro Farbe,
um den Garnverlauf auf der Rückseite zu minimieren.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

from .constants import DEFAULT_FABRIC_COUNT

if TYPE_CHECKING:
    from .pattern import Pattern


class OptimizationStrategy(Enum):
    """Verfügbare Optimierungsstrategien."""

    ROW_BY_ROW = "row_by_row"  # Zeilenweise, abwechselnd links↔rechts
    NEAREST_NEIGHBOR = "nearest"  # Immer zum nächstgelegenen Stich
    DANISH_METHOD = "danish"  # Erst alle /// dann zurück alle \\\
    COLUMN_BY_COLUMN = "column"  # Spaltenweise, abwechselnd oben↔unten
    DIAGONAL = "diagonal"  # Diagonal von Ecke zu Ecke


@dataclass
class StitchStep:
    """
    Ein einzelner Schritt im Stickpfad.

    Attributes:
        x, y: Position des Stichs
        color_index: Farbindex
        step_number: Schrittnummer (1-basiert)
        distance_from_prev: Entfernung zum vorherigen Stich
        is_jump: True wenn Sprung > 3 Stiche (Faden evtl. abschneiden)
    """

    x: int
    y: int
    color_index: int
    step_number: int = 0
    distance_from_prev: float = 0.0
    is_jump: bool = False


@dataclass
class ColorPath:
    """
    Optimierter Pfad für eine Farbe.

    Attributes:
        color_index: Farbindex
        steps: Liste der Stiche in optimierter Reihenfolge
        total_distance: Gesamte Garnlänge auf der Rückseite
        jump_count: Anzahl der Sprünge (lange Strecken)
        stitch_count: Anzahl der Stiche
    """

    color_index: int
    steps: list[StitchStep] = field(default_factory=list)
    total_distance: float = 0.0
    jump_count: int = 0
    stitch_count: int = 0


@dataclass
class OptimizationResult:
    """
    Ergebnis der Stickpfad-Optimierung.

    Attributes:
        color_paths: Pfade pro Farbe
        strategy: Verwendete Strategie
        total_stitches: Gesamtanzahl Stiche
        total_distance: Gesamte Rückseitenlänge
        total_jumps: Gesamtanzahl Sprünge
        estimated_thread_length: Geschätzte Garnlänge in cm
    """

    color_paths: list[ColorPath] = field(default_factory=list)
    strategy: OptimizationStrategy = OptimizationStrategy.ROW_BY_ROW
    total_stitches: int = 0
    total_distance: float = 0.0
    total_jumps: int = 0
    estimated_thread_length: float = 0.0  # in cm


# Typ für Progress-Callback: (current, total, message)
ProgressCallback = Callable[[int, int, str], None]


class StitchPathOptimizer:
    """
    Optimiert die Stich-Reihenfolge für minimalen Garnverbrauch.

    Unterstützt verschiedene Strategien:
    - ROW_BY_ROW: Zeilenweise, Schlangenlinien-Muster
    - NEAREST_NEIGHBOR: Greedy - immer zum nächsten Stich
    - DANISH_METHOD: Erst alle Halbkreuze, dann zurück
    - COLUMN_BY_COLUMN: Spaltenweise
    - DIAGONAL: Diagonal
    """

    # Schwellwert für "Sprung" (in Stichen)
    JUMP_THRESHOLD: int = 4

    # Geschätzte Garnlänge pro Kreuzstich in cm (bei 14 count Aida)
    THREAD_PER_STITCH_CM: float = 2.5

    def __init__(
        self,
        pattern: "Pattern",
        progress_callback: ProgressCallback | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> None:
        """
        Initialisiert den Optimizer.

        Args:
            pattern: Das zu optimierende Muster
            progress_callback: Callback für Fortschrittsanzeige (current, total, message)
            cancel_check: Funktion die True zurückgibt wenn abgebrochen werden soll
        """
        self._pattern = pattern
        self._progress_callback = progress_callback
        self._cancel_check = cancel_check
        self._cancelled = False

    def _report_progress(self, current: int, total: int, message: str) -> None:
        """Meldet den Fortschritt über den Callback."""
        if self._progress_callback:
            self._progress_callback(current, total, message)

    def _check_cancelled(self) -> bool:
        """Prüft ob die Optimierung abgebrochen werden soll."""
        if self._cancel_check and self._cancel_check():
            self._cancelled = True
            return True
        return self._cancelled

    def optimize(
        self,
        strategy: OptimizationStrategy = OptimizationStrategy.ROW_BY_ROW,
        fabric_count: int = 14,
    ) -> OptimizationResult | None:
        """
        Führt die Optimierung durch.

        Args:
            strategy: Zu verwendende Strategie
            fabric_count: Stoffzählung (Stiche pro Zoll) für Längenberechnung

        Returns:
            OptimizationResult mit allen Pfaden, oder None wenn abgebrochen
        """
        self._cancelled = False
        result = OptimizationResult(strategy=strategy)

        # Phase 1: Stiche nach Farbe gruppieren
        self._report_progress(0, 100, "Sammle Stiche...")
        color_stitches = self._group_by_color()

        if self._check_cancelled():
            return None

        total_colors = len(color_stitches)
        if total_colors == 0:
            return result

        # Phase 2: Jeden Farbpfad optimieren
        for i, (color_index, positions) in enumerate(color_stitches.items()):
            if self._check_cancelled():
                return None

            if not positions:
                continue

            # Fortschritt pro Farbe
            progress = int(10 + (i / total_colors) * 85)
            entry = self._pattern.get_color_entry(color_index)
            color_name = entry.thread.name if entry else f"Farbe {color_index}"
            self._report_progress(
                progress, 100, f"Optimiere {color_name} ({len(positions)} Stiche)..."
            )

            color_path = self._optimize_color(color_index, positions, strategy)

            if self._check_cancelled():
                return None

            result.color_paths.append(color_path)
            result.total_stitches += color_path.stitch_count
            result.total_distance += color_path.total_distance
            result.total_jumps += color_path.jump_count

        # Phase 3: Garnlänge berechnen
        self._report_progress(95, 100, "Berechne Garnverbrauch...")

        count_factor = DEFAULT_FABRIC_COUNT / fabric_count
        result.estimated_thread_length = (
            result.total_stitches * self.THREAD_PER_STITCH_CM * count_factor
            + result.total_distance * 0.5 * count_factor
        )

        self._report_progress(100, 100, "Fertig!")
        return result

    def _group_by_color(self) -> dict[int, list[tuple[int, int]]]:
        """
        Gruppiert alle Stiche nach Farbindex.

        Returns:
            Dict mit Farbindex -> Liste von (x, y) Positionen
        """
        color_stitches: dict[int, list[tuple[int, int]]] = {}

        for layer in self._pattern.layer_stack:
            if not layer.visible:
                continue

            for x, y, color_idx in layer.iterate_stitches():
                if color_idx not in color_stitches:
                    color_stitches[color_idx] = []
                color_stitches[color_idx].append((x, y))

        return color_stitches

    def _optimize_color(
        self, color_index: int, positions: list[tuple[int, int]], strategy: OptimizationStrategy
    ) -> ColorPath:
        """
        Optimiert den Pfad für eine Farbe.
        """
        if strategy == OptimizationStrategy.ROW_BY_ROW:
            ordered = self._optimize_row_by_row(positions)
        elif strategy == OptimizationStrategy.NEAREST_NEIGHBOR:
            ordered = self._optimize_nearest_neighbor_fast(positions)
        elif strategy == OptimizationStrategy.DANISH_METHOD:
            ordered = self._optimize_danish(positions)
        elif strategy == OptimizationStrategy.COLUMN_BY_COLUMN:
            ordered = self._optimize_column_by_column(positions)
        elif strategy == OptimizationStrategy.DIAGONAL:
            ordered = self._optimize_diagonal(positions)
        else:
            ordered = positions

        # ColorPath erstellen
        path = ColorPath(color_index=color_index, stitch_count=len(ordered))

        prev_x, prev_y = None, None
        for i, (x, y) in enumerate(ordered):
            distance = 0.0
            is_jump = False

            if prev_x is not None and prev_y is not None:
                distance = self._distance_fast(prev_x, prev_y, x, y)
                is_jump = distance > self.JUMP_THRESHOLD
                if is_jump:
                    path.jump_count += 1

            step = StitchStep(
                x=x,
                y=y,
                color_index=color_index,
                step_number=i + 1,
                distance_from_prev=distance,
                is_jump=is_jump,
            )
            path.steps.append(step)
            path.total_distance += distance

            prev_x, prev_y = x, y

        return path

    def _optimize_row_by_row(self, positions: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Zeilenweise Optimierung (Schlangenlinie)."""
        if not positions:
            return []

        # Nach Zeilen gruppieren mit dict
        rows: dict[int, list[int]] = {}
        for x, y in positions:
            if y not in rows:
                rows[y] = []
            rows[y].append(x)

        # Zeilen sortieren
        sorted_rows = sorted(rows.keys())

        result: list = []
        left_to_right = True

        for y in sorted_rows:
            x_values = sorted(rows[y], reverse=not left_to_right)
            result.extend((x, y) for x in x_values)
            left_to_right = not left_to_right

        return result

    def _optimize_nearest_neighbor_fast(
        self, positions: list[tuple[int, int]]
    ) -> list[tuple[int, int]]:
        """
        Optimierter Nearest-Neighbor mit Grid-basierter Suche.

        Statt alle Punkte zu durchsuchen (O(n²)), nutzen wir ein Grid
        um nur nahe Punkte zu prüfen.
        """
        if not positions:
            return []

        if len(positions) <= 100:
            # Für kleine Mengen: einfacher Algorithmus
            return self._optimize_nearest_neighbor_simple(positions)

        # Grid-Größe basierend auf durchschnittlicher Dichte
        n = len(positions)

        # Bounding Box berechnen
        min_x = min(p[0] for p in positions)
        max_x = max(p[0] for p in positions)
        min_y = min(p[1] for p in positions)
        max_y = max(p[1] for p in positions)

        width = max_x - min_x + 1
        height = max_y - min_y + 1

        # Grid-Zellengröße: ca. 10-20 Punkte pro Zelle erwünscht
        cell_size = max(1, int(math.sqrt(width * height / (n / 15))))

        # Grid erstellen: dict von (grid_x, grid_y) -> set von Punkten
        grid: dict[tuple[int, int], set[tuple[int, int]]] = {}

        for p in positions:
            gx = (p[0] - min_x) // cell_size
            gy = (p[1] - min_y) // cell_size
            key = (gx, gy)
            if key not in grid:
                grid[key] = set()
            grid[key].add(p)

        # Startpunkt: obere linke Ecke
        start = min(positions, key=lambda p: p[0] + p[1])
        result = [start]

        # Startpunkt aus Grid entfernen
        gx = (start[0] - min_x) // cell_size
        gy = (start[1] - min_y) // cell_size
        grid[(gx, gy)].discard(start)

        current = start
        remaining = n - 1

        while remaining > 0:
            # Grid-Position des aktuellen Punktes
            cx = (current[0] - min_x) // cell_size
            cy = (current[1] - min_y) // cell_size

            # Suche in expandierenden Ringen
            nearest = None
            nearest_dist = float("inf")

            for radius in range(max(width, height) // cell_size + 2):
                if nearest is not None:
                    # Ring `radius` deckt nur Punkte ab, die mindestens
                    # (radius-1) * cell_size entfernt sind. Sobald das schon
                    # weiter ist als der bisher beste (quadrierte!) Kandidat,
                    # kann kein näherer Punkt mehr folgen -- beide Seiten
                    # quadriert vergleichen, `nearest_dist` ist bereits ein
                    # Quadrat (siehe `_distance_squared`).
                    min_ring_dist = max(0, (radius - 1) * cell_size)
                    if min_ring_dist * min_ring_dist > nearest_dist:
                        break

                # Alle Zellen im Ring durchsuchen
                for dx in range(-radius, radius + 1):
                    for dy in range(-radius, radius + 1):
                        # Nur Rand des Rings
                        if abs(dx) != radius and abs(dy) != radius:
                            continue

                        key = (cx + dx, cy + dy)
                        if key not in grid or not grid[key]:
                            continue

                        # Punkte in dieser Zelle prüfen
                        for p in grid[key]:
                            dist = self._distance_squared(current[0], current[1], p[0], p[1])
                            if dist < nearest_dist:
                                nearest_dist = dist
                                nearest = p

            if nearest is None:
                # Fallback: Brute-Force für verbleibende Punkte
                for key, points in grid.items():
                    for p in points:
                        dist = self._distance_squared(current[0], current[1], p[0], p[1])
                        if dist < nearest_dist:
                            nearest_dist = dist
                            nearest = p

            if nearest:
                result.append(nearest)
                gx = (nearest[0] - min_x) // cell_size
                gy = (nearest[1] - min_y) // cell_size
                grid[(gx, gy)].discard(nearest)
                current = nearest
                remaining -= 1
            else:
                break

        return result

    def _optimize_nearest_neighbor_simple(
        self, positions: list[tuple[int, int]]
    ) -> list[tuple[int, int]]:
        """Einfacher Nearest-Neighbor für kleine Punktmengen."""
        if not positions:
            return []

        remaining = set(positions)
        start = min(remaining, key=lambda p: p[0] + p[1])
        result = [start]
        remaining.remove(start)

        current = start
        while remaining:
            nearest = min(
                remaining, key=lambda p: self._distance_squared(current[0], current[1], p[0], p[1])
            )
            result.append(nearest)
            remaining.remove(nearest)
            current = nearest

        return result

    def _optimize_danish(self, positions: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Danish Method Optimierung."""
        if not positions:
            return []

        rows: dict[int, list[int]] = {}
        for x, y in positions:
            if y not in rows:
                rows[y] = []
            rows[y].append(x)

        sorted_rows = sorted(rows.keys())

        result: list = []
        for y in sorted_rows:
            x_values = sorted(rows[y])
            result.extend((x, y) for x in x_values)

        return result

    def _optimize_column_by_column(self, positions: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Spaltenweise Optimierung."""
        if not positions:
            return []

        columns: dict[int, list[int]] = {}
        for x, y in positions:
            if x not in columns:
                columns[x] = []
            columns[x].append(y)

        sorted_columns = sorted(columns.keys())

        result: list = []
        top_to_bottom = True

        for x in sorted_columns:
            y_values = sorted(columns[x], reverse=not top_to_bottom)
            result.extend((x, y) for y in y_values)
            top_to_bottom = not top_to_bottom

        return result

    def _optimize_diagonal(self, positions: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Diagonale Optimierung."""
        if not positions:
            return []

        diagonals: dict[int, list[tuple[int, int]]] = {}
        for x, y in positions:
            diag = x + y
            if diag not in diagonals:
                diagonals[diag] = []
            diagonals[diag].append((x, y))

        sorted_diags = sorted(diagonals.keys())

        result = []
        for diag in sorted_diags:
            points = sorted(diagonals[diag], key=lambda p: p[0])
            result.extend(points)

        return result

    @staticmethod
    def _distance_fast(x1: int, y1: int, x2: int, y2: int) -> float:
        """Berechnet die euklidische Distanz zwischen zwei Punkten."""
        dx = x2 - x1
        dy = y2 - y1
        return math.sqrt(dx * dx + dy * dy)

    @staticmethod
    def _distance_squared(x1: int, y1: int, x2: int, y2: int) -> int:
        """Berechnet das Quadrat der Distanz (schneller für Vergleiche)."""
        dx = x2 - x1
        dy = y2 - y1
        return dx * dx + dy * dy

    def get_statistics(self, result: OptimizationResult) -> dict:
        """Erstellt Statistiken für das Optimierungsergebnis."""
        stats: dict[str, Any] = {
            "strategy": result.strategy.value,
            "total_stitches": result.total_stitches,
            "total_colors": len(result.color_paths),
            "total_distance": round(result.total_distance, 1),
            "total_jumps": result.total_jumps,
            "estimated_thread_cm": round(result.estimated_thread_length, 1),
            "estimated_thread_m": round(result.estimated_thread_length / 100, 2),
            "colors": [],
        }

        for path in result.color_paths:
            entry = self._pattern.get_color_entry(path.color_index)
            color_name = entry.thread.name if entry else f"Farbe {path.color_index}"

            stats["colors"].append(
                {
                    "index": path.color_index,
                    "name": color_name,
                    "stitches": path.stitch_count,
                    "distance": round(path.total_distance, 1),
                    "jumps": path.jump_count,
                }
            )

        return stats


def compare_strategies(
    pattern: "Pattern",
    fabric_count: int = 14,
    progress_callback: ProgressCallback | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> dict[str, OptimizationResult] | None:
    """
    Vergleicht alle Strategien für ein Muster.

    Args:
        pattern: Das zu optimierende Muster
        fabric_count: Stoffzählung
        progress_callback: Callback für Fortschrittsanzeige
        cancel_check: Funktion für Abbruch-Prüfung

    Returns:
        Dict mit Strategie-Name -> Ergebnis, oder None wenn abgebrochen
    """
    results = {}
    strategies = list(OptimizationStrategy)
    total = len(strategies)

    for i, strategy in enumerate(strategies):
        if cancel_check and cancel_check():
            return None

        if progress_callback:
            progress = int((i / total) * 100)
            progress_callback(progress, 100, f"Teste {strategy.value}...")

        # Eigener Optimizer ohne Progress (wäre zu granular)
        optimizer = StitchPathOptimizer(pattern, cancel_check=cancel_check)
        result = optimizer.optimize(strategy, fabric_count)

        if result is None:
            return None

        results[strategy.value] = result

    if progress_callback:
        progress_callback(100, 100, "Vergleich fertig!")

    return results
