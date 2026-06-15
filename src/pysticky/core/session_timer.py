"""
Stick-Session-Timer.

Misst die Zeit, die der User im Sticken-Modus verbringt, und schreibt
sie in `pattern.metadata` — pro Pattern persistent ueber die .pxs-Datei.

Konvention auf `Pattern.metadata`:
    total_stitch_seconds: int  — kumulierte Stick-Zeit in Sekunden
    last_session_start:   float — UNIX-Zeitstempel der laufenden Session,
                                  oder fehlend wenn keine Session aktiv

Es gibt absichtlich keinen Bezug auf Qt — das macht den Service in Tests
trivial benutzbar (siehe `tests/`).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .pattern import Pattern


META_TOTAL = "total_stitch_seconds"
META_START = "last_session_start"


def get_total_seconds(pattern: "Pattern") -> int:
    """Liefert die kumulierte Stick-Zeit (ohne aktuelle laufende Session)."""
    return int(pattern.metadata.get(META_TOTAL, 0))


def is_session_active(pattern: "Pattern") -> bool:
    """True, wenn eine Session laeuft (start gesetzt, noch nicht gestoppt)."""
    return META_START in pattern.metadata


def start_session(pattern: "Pattern", now: Optional[float] = None) -> None:
    """Startet eine Session. No-op wenn bereits aktiv."""
    if is_session_active(pattern):
        return
    pattern.metadata[META_START] = float(now if now is not None else time.time())


def stop_session(pattern: "Pattern", now: Optional[float] = None) -> int:
    """Beendet die Session und addiert die Dauer zur Gesamt-Zeit.

    Returns:
        Dauer der gerade beendeten Session in Sekunden (0 wenn keine aktiv).
    """
    start = pattern.metadata.pop(META_START, None)
    if start is None:
        return 0
    end = float(now if now is not None else time.time())
    elapsed = max(0, int(end - float(start)))
    pattern.metadata[META_TOTAL] = get_total_seconds(pattern) + elapsed
    return elapsed


def format_duration(seconds: int) -> str:
    """Formatiert eine Sekunden-Dauer kompakt: '5 Sek', '47 Min', '12h 33min'."""
    s = max(0, int(seconds))
    if s < 60:
        return f"{s} Sek"
    if s < 3600:
        return f"{s // 60} Min"
    h, rest = divmod(s, 3600)
    m = rest // 60
    if m == 0:
        return f"{h}h"
    return f"{h}h {m}min"
