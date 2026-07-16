"""
Pattern-Diff: vergleicht zwei Patterns und liefert eine Diff-Maske + Statistik.

Headless-fokussiert — keine UI-Imports. Die UI-Schicht visualisiert
das Ergebnis (DiffDialog).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .layer import NO_STITCH
from .pattern import Pattern

# Werte der Diff-Maske
DIFF_UNCHANGED: int = 0  # An dieser Position kein Unterschied
DIFF_ADDED: int = 1  # Im neuen Pattern Stich, im alten nicht
DIFF_REMOVED: int = 2  # Im alten Pattern Stich, im neuen nicht
DIFF_CHANGED: int = 3  # In beiden Stich, aber andere Farbe oder Stitch-Type


@dataclass
class DiffStats:
    """Statistik eines Pattern-Diffs."""

    added: int  # Anzahl neu hinzugefügter Stiche
    removed: int  # Anzahl entfernter Stiche
    changed: int  # Anzahl modifizierter Stiche (Farbe oder Type anders)
    same: int  # Anzahl unveränderter Stiche
    width: int
    height: int
    size_changed: bool  # True wenn Width/Height unterschiedlich sind

    @property
    def total_changes(self) -> int:
        return self.added + self.removed + self.changed

    def to_dict(self) -> dict:
        return {
            "added": self.added,
            "removed": self.removed,
            "changed": self.changed,
            "same": self.same,
            "total_changes": self.total_changes,
            "width": self.width,
            "height": self.height,
            "size_changed": self.size_changed,
        }


@dataclass
class DiffResult:
    """Vollständiges Ergebnis eines Pattern-Diffs."""

    mask: np.ndarray  # uint8 Array mit DIFF_*-Werten, Shape (height, width)
    stats: DiffStats

    @property
    def has_changes(self) -> bool:
        return self.stats.total_changes > 0


def compute_diff(old_pattern: Pattern, new_pattern: Pattern) -> DiffResult:
    """
    Vergleicht zwei Patterns und liefert eine Diff-Maske + Statistik.

    Wenn die Patterns unterschiedliche Größen haben, wird die kleinere
    Bounding-Box als Vergleichsbereich genommen. Felder ausserhalb gelten
    als added/removed.

    Args:
        old_pattern: Das ältere Pattern (z.B. Snapshot)
        new_pattern: Das neuere Pattern (z.B. aktuell)

    Returns:
        DiffResult mit Maske (Shape = max-bounding-box) und Statistik.
    """
    old_w, old_h = old_pattern.width, old_pattern.height
    new_w, new_h = new_pattern.width, new_pattern.height

    diff_w = max(old_w, new_w)
    diff_h = max(old_h, new_h)
    mask = np.full((diff_h, diff_w), DIFF_UNCHANGED, dtype=np.uint8)

    # Composite-Grids + Stitch-Type-Grids holen
    old_grid = old_pattern.layer_stack.get_composite_grid()
    new_grid = new_pattern.layer_stack.get_composite_grid()
    old_types = old_pattern.layer_stack.get_composite_stitch_type_grid()
    new_types = new_pattern.layer_stack.get_composite_stitch_type_grid()

    # Auf gemeinsame Bounding-Box padden: Felder ausserhalb des jeweiligen
    # Patterns gelten als NO_STITCH (Wert) bzw. Type 0 — exakt wie die
    # früheren in_old/in_new-Guards der Zell-für-Zell-Schleife.
    old_val = np.full((diff_h, diff_w), NO_STITCH, dtype=np.int16)
    old_val[:old_h, :old_w] = old_grid
    new_val = np.full((diff_h, diff_w), NO_STITCH, dtype=np.int16)
    new_val[:new_h, :new_w] = new_grid
    old_t = np.zeros((diff_h, diff_w), dtype=np.uint8)
    old_t[:old_h, :old_w] = old_types
    new_t = np.zeros((diff_h, diff_w), dtype=np.uint8)
    new_t[:new_h, :new_w] = new_types

    old_has = old_val != NO_STITCH
    new_has = new_val != NO_STITCH
    both = old_has & new_has

    added_mask = ~old_has & new_has
    removed_mask = old_has & ~new_has
    changed_mask = both & ((old_val != new_val) | (old_t != new_t))
    same_mask = both & ~changed_mask

    mask[added_mask] = DIFF_ADDED
    mask[removed_mask] = DIFF_REMOVED
    mask[changed_mask] = DIFF_CHANGED

    added = int(np.count_nonzero(added_mask))
    removed = int(np.count_nonzero(removed_mask))
    changed = int(np.count_nonzero(changed_mask))
    same = int(np.count_nonzero(same_mask))

    stats = DiffStats(
        added=added,
        removed=removed,
        changed=changed,
        same=same,
        width=diff_w,
        height=diff_h,
        size_changed=(old_w != new_w or old_h != new_h),
    )
    return DiffResult(mask=mask, stats=stats)
