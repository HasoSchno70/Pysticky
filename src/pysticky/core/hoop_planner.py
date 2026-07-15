"""
Rahmenaufteilung: teilt ein grosses Muster in mehrere Stickrahmen-Sektoren
mit konfigurierbarer Ueberlappung.

Pure Funktionen — kein Qt, keine UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pattern import Pattern


@dataclass(frozen=True)
class HoopSector:
    """Ein einzelner Stickrahmen-Sektor des Musters.

    Koordinaten in Stichen. Der Sektor enthaelt sowohl den Hauptbereich
    als auch ggf. die Ueberlappungs-Zone zum naechsten Sektor.
    """

    index: int  # 0-basierter laufender Index
    row: int  # Sektor-Reihe (0..rows-1)
    col: int  # Sektor-Spalte (0..cols-1)
    x_start: int  # linke Kante in Stichen (inklusiv)
    y_start: int  # obere Kante in Stichen (inklusiv)
    x_end: int  # rechte Kante in Stichen (exklusiv)
    y_end: int  # untere Kante in Stichen (exklusiv)
    stitch_count: int  # gesetzte Stiche im Sektor (sichtbare Layer)

    @property
    def width(self) -> int:
        return self.x_end - self.x_start

    @property
    def height(self) -> int:
        return self.y_end - self.y_start


@dataclass(frozen=True)
class HoopPlan:
    """Ergebnis der Rahmenaufteilungs-Berechnung."""

    pattern_width: int
    pattern_height: int
    hoop_width: int  # Innen-Breite des Stickrahmens in Stichen
    hoop_height: int  # Innen-Hoehe des Stickrahmens in Stichen
    overlap: int  # Ueberlappungs-Breite in Stichen
    rows: int
    cols: int
    sectors: list[HoopSector]

    @property
    def total_sectors(self) -> int:
        return self.rows * self.cols

    @property
    def fits_single_hoop(self) -> bool:
        return self.total_sectors <= 1


def plan_hoops(
    pattern: "Pattern",
    hoop_width: int,
    hoop_height: int,
    overlap: int = 0,
) -> HoopPlan:
    """Teilt ein Pattern in Sektoren auf, die in den Stickrahmen passen.

    Args:
        pattern: das Muster
        hoop_width: Innen-Breite des Rahmens in Stichen (z.B. 40)
        hoop_height: Innen-Hoehe des Rahmens in Stichen
        overlap: Anzahl Stiche die zwei benachbarte Sektoren teilen (Default 0).
            Empfohlen: 2-4 fuer nahtlose Uebergaenge.

    Returns:
        HoopPlan mit Liste aller Sektoren.
    """
    if hoop_width <= 0 or hoop_height <= 0:
        raise ValueError("hoop_width und hoop_height muessen > 0 sein")
    if overlap < 0:
        raise ValueError("overlap muss >= 0 sein")
    if overlap >= hoop_width or overlap >= hoop_height:
        raise ValueError("overlap muss kleiner als Hoop-Groesse sein")

    pw = pattern.width
    ph = pattern.height

    # Effektive Schritt-Weite pro Sektor: hoop_size minus Overlap
    step_x = hoop_width - overlap
    step_y = hoop_height - overlap

    cols = max(1, ceil((pw - overlap) / step_x)) if pw > hoop_width else 1
    rows = max(1, ceil((ph - overlap) / step_y)) if ph > hoop_height else 1

    sectors: list[HoopSector] = []
    idx = 0
    for r in range(rows):
        for c in range(cols):
            x_start = c * step_x
            y_start = r * step_y
            x_end = min(x_start + hoop_width, pw)
            y_end = min(y_start + hoop_height, ph)
            # Bei letzten Sektoren in Zeile/Spalte zurueckschieben, damit die
            # volle Hoop-Groesse genutzt wird (sofern Pattern breit/hoch genug).
            if c == cols - 1 and x_end - x_start < hoop_width and pw >= hoop_width:
                x_start = pw - hoop_width
                x_end = pw
            if r == rows - 1 and y_end - y_start < hoop_height and ph >= hoop_height:
                y_start = ph - hoop_height
                y_end = ph

            stitch_count = _count_stitches_in_region(pattern, x_start, y_start, x_end, y_end)

            sectors.append(
                HoopSector(
                    index=idx,
                    row=r,
                    col=c,
                    x_start=x_start,
                    y_start=y_start,
                    x_end=x_end,
                    y_end=y_end,
                    stitch_count=stitch_count,
                )
            )
            idx += 1

    return HoopPlan(
        pattern_width=pw,
        pattern_height=ph,
        hoop_width=hoop_width,
        hoop_height=hoop_height,
        overlap=overlap,
        rows=rows,
        cols=cols,
        sectors=sectors,
    )


def _count_stitches_in_region(
    pattern: "Pattern",
    x0: int,
    y0: int,
    x1: int,
    y1: int,
) -> int:
    """Zaehlt sichtbare Stiche im Rechteck [x0,y0) bis [x1,y1) — exklusiv x1/y1."""
    try:
        import numpy as np

        from .layer import NO_STITCH

        composite = pattern.layer_stack.get_composite_grid()
        region = composite[y0:y1, x0:x1]
        return int(np.count_nonzero(region != NO_STITCH))
    except Exception:  # noqa: BLE001 — Fallback ohne numpy
        count = 0
        for y in range(y0, y1):
            for x in range(x0, x1):
                if pattern.get_stitch(x, y) is not None:
                    count += 1
        return count
