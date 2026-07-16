"""
Confetti-Reduction für den Bild-Import.

"Confetti" sind isolierte Einzelpixel- oder Mini-Cluster im quantisierten
Pattern, die beim Sticken unverhältnismäßig viele Garn-Wechsel erzeugen
und kaum sichtbar sind. Die typische Profi-Quantisierung filtert sie nach
der Quantisierung heraus, indem kleine zusammenhängende Komponenten der
naheliegendsten dominanten Nachbarfarbe zugeordnet werden.

Algorithmus:
1. Connected-Component-Labeling auf dem Farbindex-Grid (4-Nachbarschaft).
   Jeder Cluster hat eine Farbe und eine Größe.
2. Cluster mit `size < min_run_size` werden zur dominanten Nachbarfarbe
   reassigned. "Dominante Nachbarfarbe" = häufigste Farbe in den 8
   Nachbarn der Cluster-Pixel, die NICHT die eigene Farbe ist.
3. Wiederhole bis nichts mehr geändert wird oder Max-Iter erreicht.

Iterativ, weil das Reassignen kleiner Cluster zwei vorher getrennte
Cluster zu einem größeren mergen kann, der dann wieder unter dem
Threshold liegen kann. In der Praxis konvergiert das in 2-3 Iterationen.

Komplexität pro Iteration: O(N) wo N = width*height.

Hinweis zur Performance: Das Connected-Component-Labeling läuft als
Python-BFS. Eine numpy-Union-Find-Variante wurde evaluiert, brachte aber
nur ~1.1x (der Flaschenhals ist die Python-Traversierung, nicht die
Kantenerkennung). Ein echter Speedup ginge nur mit scipy.ndimage.label —
bewusst nicht als Dependency aufgenommen. Confetti läuft ohnehin nur
einmalig beim Import, nicht interaktiv.
"""

from __future__ import annotations

import numpy as np

NO_STITCH: int = -1


def reduce_confetti(
    grid: np.ndarray,
    min_run_size: int,
    max_iterations: int = 5,
) -> np.ndarray:
    """
    Reduziert Confetti im Farbindex-Grid.

    Args:
        grid: 2D-int16-Array mit Farbindizes; NO_STITCH (-1) für leere Zellen.
        min_run_size: Minimale Cluster-Größe. Cluster mit size < min_run_size
                      werden absorbiert. min_run_size <= 1 ist No-Op.
        max_iterations: Max. Anzahl Iterationen. Default 5 reicht in der Praxis.

    Returns:
        Neues Grid (Kopie) mit reduziertem Confetti. Original bleibt unverändert.
    """
    if min_run_size <= 1:
        return grid.copy()
    if grid.size == 0:
        return grid.copy()

    result = grid.copy()
    for _ in range(max_iterations):
        new_result, changed = _reduce_once(result, min_run_size)
        result = new_result
        if not changed:
            break
    return result


def _reduce_once(
    grid: np.ndarray,
    min_run_size: int,
) -> tuple[np.ndarray, bool]:
    """Eine Iteration der Confetti-Reduktion. Liefert (neues_grid, changed)."""
    labels, sizes = _connected_components(grid)
    # labels[y,x] = Cluster-ID (>=0) oder -1 für NO_STITCH
    # sizes[i] = Anzahl Pixel im Cluster i

    if labels.max() < 0:
        return grid.copy(), False

    h, w = grid.shape
    new_grid = grid.copy()
    changed = False

    # Welche Cluster sind zu klein?
    small_cluster_ids = np.where(sizes < min_run_size)[0]
    if len(small_cluster_ids) == 0:
        return new_grid, False

    # Pixel der kleinen Cluster vektorisiert einsammeln (np.isin/argwhere)
    # statt das ganze Grid in Python zu durchlaufen — argwhere liefert
    # Raster-Reihenfolge, also identische Gruppierung wie eine y/x-Schleife.
    small_mask = np.isin(labels, small_cluster_ids)
    cluster_pixels: dict[int, list[tuple[int, int]]] = {}
    for y, x in np.argwhere(small_mask):
        cluster_pixels.setdefault(int(labels[y, x]), []).append((int(y), int(x)))

    for cluster_id, pixels in cluster_pixels.items():
        # Dominante Nachbarfarbe finden (8-Nachbarschaft, andere Farbe)
        own_color = int(grid[pixels[0]])
        neighbor_counts: dict[int, int] = {}
        for py, px in pixels:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = py + dy, px + dx
                    if 0 <= ny < h and 0 <= nx < w:
                        nc = int(grid[ny, nx])
                        if nc != NO_STITCH and nc != own_color:
                            neighbor_counts[nc] = neighbor_counts.get(nc, 0) + 1

        if not neighbor_counts:
            # Kein Nachbar mit anderer Farbe -> Cluster bleibt
            continue

        # Häufigste Nachbarfarbe (ties brechen durch kleineren Index)
        best_color = max(neighbor_counts.items(), key=lambda kv: (kv[1], -kv[0]))[0]
        for py, px in pixels:
            new_grid[py, px] = best_color
        changed = True

    return new_grid, changed


def _connected_components(grid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    4-Nachbarschaft Connected-Component-Labeling.

    Returns:
        labels: int32-Array, gleiche Shape wie grid.
                labels[y,x] = Cluster-ID (>=0) oder -1 für NO_STITCH.
        sizes:  int32-Array mit sizes[i] = Pixel-Count für Cluster i.
    """
    h, w = grid.shape
    labels = np.full((h, w), -1, dtype=np.int32)
    sizes_list: list[int] = []
    next_id = 0

    # Iteratives Flood-Fill (BFS) — vermeidet Python-Recursion-Limit
    for start_y in range(h):
        for start_x in range(w):
            if labels[start_y, start_x] != -1:
                continue
            color = int(grid[start_y, start_x])
            if color == NO_STITCH:
                continue

            # BFS
            cluster_id = next_id
            next_id += 1
            stack = [(start_y, start_x)]
            size = 0
            while stack:
                y, x = stack.pop()
                if labels[y, x] != -1:
                    continue
                if int(grid[y, x]) != color:
                    continue
                labels[y, x] = cluster_id
                size += 1
                if y > 0:
                    stack.append((y - 1, x))
                if y < h - 1:
                    stack.append((y + 1, x))
                if x > 0:
                    stack.append((y, x - 1))
                if x < w - 1:
                    stack.append((y, x + 1))
            sizes_list.append(size)

    return labels, np.array(sizes_list, dtype=np.int32)
