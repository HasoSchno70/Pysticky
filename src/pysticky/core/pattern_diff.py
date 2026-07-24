"""
Pattern-Diff: vergleicht zwei Patterns und liefert eine Diff-Maske + Statistik.

Headless-fokussiert — keine UI-Imports. Die UI-Schicht visualisiert
das Ergebnis (DiffDialog).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np

from .backstitch_manager import Backstitch
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
    backstitches_added: int = 0  # Anzahl neu hinzugefügter Rückstich-Linien
    backstitches_removed: int = 0  # Anzahl entfernter Rückstich-Linien

    @property
    def total_changes(self) -> int:
        return self.added + self.removed + self.changed + self.backstitch_changes

    @property
    def backstitch_changes(self) -> int:
        return self.backstitches_added + self.backstitches_removed

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
            "backstitches_added": self.backstitches_added,
            "backstitches_removed": self.backstitches_removed,
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

    # old_val/new_val enthalten rohe Farb-INDIZES (Position in
    # pattern.color_entries) -- NICHT die Farbe selbst. Ein Snapshot-Diff
    # vergleicht aber typischerweise zwei UNABHAENGIGE Pattern-Objekte
    # (Snapshot von der Platte vs. aktuelles Pattern im Speicher), deren
    # Paletten zwischenzeitlich bearbeitet worden sein koennen (Farbe
    # geloescht -> Pattern.remove_color() schiebt alle hoeheren Indizes um 1
    # runter, siehe pattern.py). Ein roher Index-Vergleich haette dann bei
    # unveraenderten Zellen faelschlich CHANGED gemeldet (weil derselbe
    # Stich jetzt einen anderen Index traegt), und umgekehrt echte
    # Farbaenderungen uebersehen, wenn zwei verschiedene Paletten zufaellig
    # denselben Index fuer unterschiedliche Farben verwenden. Deshalb wird
    # hier auf die TATSAECHLICHE Farbe jedes Patterns aufgeloest (per Index
    # -> RGB-Lookup-Tabelle, vektorisiert per numpy fuer grosse Grids).
    old_colors = _resolve_colors(old_val, _color_key_lookup(old_pattern))
    new_colors = _resolve_colors(new_val, _color_key_lookup(new_pattern))

    added_mask = ~old_has & new_has
    removed_mask = old_has & ~new_has
    changed_mask = both & ((old_colors != new_colors) | (old_t != new_t))
    same_mask = both & ~changed_mask

    mask[added_mask] = DIFF_ADDED
    mask[removed_mask] = DIFF_REMOVED
    mask[changed_mask] = DIFF_CHANGED

    added = int(np.count_nonzero(added_mask))
    removed = int(np.count_nonzero(removed_mask))
    changed = int(np.count_nonzero(changed_mask))
    same = int(np.count_nonzero(same_mask))

    backstitches_added, backstitches_removed = _diff_backstitches(old_pattern, new_pattern)

    stats = DiffStats(
        added=added,
        removed=removed,
        changed=changed,
        same=same,
        width=diff_w,
        height=diff_h,
        backstitches_added=backstitches_added,
        backstitches_removed=backstitches_removed,
        size_changed=(old_w != new_w or old_h != new_h),
    )
    return DiffResult(mask=mask, stats=stats)


def _color_key_lookup(pattern: Pattern) -> np.ndarray:
    """Baut eine Index -> Farbwert-Lookup-Tabelle für ein Pattern.

    Jede Farbe wird als einzelnes int32 kodiert (r<<16 | g<<8 | b), damit
    sich Farben zwischen zwei Patterns mit unterschiedlichen/verschobenen
    Paletten per einfachem Zahlenvergleich vergleichen lassen — unabhängig
    davon, an welcher Position die Farbe jeweils in `color_entries` steht.
    """
    n = len(pattern.color_entries)
    keys = np.empty(n, dtype=np.int32)
    for i, entry in enumerate(pattern.color_entries):
        color = entry.thread.color
        keys[i] = (color.r << 16) | (color.g << 8) | color.b
    return keys


def _resolve_colors(index_grid: np.ndarray, color_keys: np.ndarray) -> np.ndarray:
    """Löst ein Farb-INDEX-Grid vektorisiert in tatsächliche Farbwerte auf.

    NO_STITCH-Zellen bleiben auf -1 (Sentinel außerhalb des gültigen
    Farbwert-Bereichs 0..0xFFFFFF, kollidiert also nie mit einer echten
    Farbe). Indizes außerhalb der Palette (sollte nicht vorkommen, aber
    defensiv gegen inkonsistente Daten) werden auf 0 geklemmt, bevor sie
    als Lookup-Index verwendet werden.
    """
    out = np.full(index_grid.shape, -1, dtype=np.int32)
    valid = index_grid != NO_STITCH
    if color_keys.size > 0 and valid.any():
        safe_idx = np.clip(index_grid, 0, color_keys.size - 1)
        out[valid] = color_keys[safe_idx[valid]]
    return out


def _diff_backstitches(old_pattern: Pattern, new_pattern: Pattern) -> tuple[int, int]:
    """Vergleicht zwei Rückstich-Listen als Multimengen (Wert-Identität).

    Rückstiche haben keine stabile ID über Snapshots hinweg — nur Koordinaten
    + Farbe. Ein Vergleich per Listen-Index würde bei Einfügungen/Löschungen
    in der Mitte der Liste sofort desynchronisieren (jeder nachfolgende
    Eintrag würde als "geändert" erscheinen, obwohl er identisch ist, nur an
    anderer Listen-Position). Multimengen-Differenz per Counter ist robust
    gegen Reihenfolge UND gegen echte Duplikate (zwei identische Rückstiche
    zählen als zwei, nicht als einer).

    Der Vergleichs-Key löst `color_index` in die tatsächliche RGB-Farbe DES
    JEWEILIGEN Patterns auf (statt den rohen Index zu vergleichen) — aus
    demselben Grund wie beim Kreuzstich-Grid oben: verschiebt sich die
    Palette zwischen Snapshot und aktuellem Pattern (Farbe gelöscht/neu
    sortiert), bliebe ein reiner Index-Vergleich an farblich identischen
    Rückstichen hängen und würde sie faelschlich als "entfernt + hinzugefügt"
    zählen.

    Returns:
        (hinzugefügt, entfernt) — Anzahl Rückstich-Linien, die nur im neuen
        bzw. nur im alten Pattern vorkommen.
    """

    def _color_key(pattern: Pattern, color_index: int) -> int:
        if 0 <= color_index < len(pattern.color_entries):
            color = pattern.color_entries[color_index].thread.color
            return (color.r << 16) | (color.g << 8) | color.b
        return -1

    def _key(pattern: Pattern, bs: Backstitch) -> tuple[int, int, int, int, int]:
        return (bs.x1, bs.y1, bs.x2, bs.y2, _color_key(pattern, bs.color_index))

    old_counts = Counter(_key(old_pattern, bs) for bs in old_pattern.backstitches)
    new_counts = Counter(_key(new_pattern, bs) for bs in new_pattern.backstitches)

    added = new_counts - old_counts
    removed = old_counts - new_counts
    return sum(added.values()), sum(removed.values())
