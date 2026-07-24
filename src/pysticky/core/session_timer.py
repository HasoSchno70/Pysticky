"""
Stick-Session-Timer.

Misst die Zeit, die der User im Sticken-Modus verbringt, und schreibt
sie in `pattern.metadata` — pro Pattern persistent über die .pxs-Datei.

Konvention auf `Pattern.metadata`:
    total_stitch_seconds: int  — kumulierte Stick-Zeit in Sekunden
    last_session_start:   float — UNIX-Zeitstempel der laufenden Session,
                                  oder fehlend wenn keine Session aktiv

Es gibt absichtlich keinen Bezug auf Qt — das macht den Service in Tests
trivial benutzbar (siehe `tests/`).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pattern import Pattern


META_TOTAL = "total_stitch_seconds"
META_START = "last_session_start"

# stop_session() läuft nur über closeEvent()/den Sticken-Modus-Toggle. Ein
# Crash/Kill dazwischen lässt META_START im gespeicherten Pattern stehen;
# beim nächsten echten stop_session() (Tage später) würde die Differenz
# sonst als riesige, aber komplett unplausible Dauer in total_stitch_seconds
# einfließen. Eine einzelne Sitzung länger als das hier ist praktisch immer
# ein Hinweis auf genau diesen Fall, nicht auf echte Stickzeit.
MAX_PLAUSIBLE_SESSION_SECONDS = 12 * 3600  # 12h


def get_total_seconds(pattern: "Pattern") -> int:
    """Liefert die kumulierte Stick-Zeit (ohne aktuelle laufende Session)."""
    try:
        return int(pattern.metadata.get(META_TOTAL, 0))
    except (TypeError, ValueError):
        # metadata kommt ungeprueft aus der .pxs-Datei (file_io.py laedt es
        # als rohes dict) -- ein hand-editierter oder korrupter Wert (z.B.
        # ein String oder eine Liste statt einer Zahl) darf hier nicht mit
        # einem rohen ValueError/TypeError crashen, sondern soll wie "noch
        # keine Zeit erfasst" behandelt werden.
        return 0


def is_session_active(pattern: "Pattern") -> bool:
    """True, wenn eine Session läuft (start gesetzt, noch nicht gestoppt)."""
    return META_START in pattern.metadata


def start_session(pattern: "Pattern", now: float | None = None) -> None:
    """Startet eine Session.

    Ueberschreibt eine ggf. bereits vorhandene last_session_start-Zeit.
    start_session() wird in der Praxis nur ueber den Sticken-Modus-Toggle
    aufgerufen (_on_toggle_stitch_mode) und ist dort immer 1:1 mit einem
    stop_session()-Aufruf gepaart (Aus-Klick oder closeEvent/set_pattern
    erzwingen das Stoppen vor jedem neuen Start). Ist beim Aufruf trotzdem
    schon ein last_session_start gesetzt, kann das nur eine verwaiste Zeit
    aus einer VORHERIGEN, nie sauber gestoppten Session sein (Crash/Kill,
    siehe stop_session()) -- z.B. wenn die .pxs-Datei kurz nach einem Absturz
    neu geoeffnet und der Sticken-Modus erneut aktiviert wird. Ein simples
    No-op wuerde diese uralte Startzeit fuer die neue Sitzung weiterverwenden;
    beim naechsten stop_session() wuerde dann die komplette App-war-
    geschlossen-Luecke faelschlich als Stickzeit mitgezaehlt (sofern sie
    unter MAX_PLAUSIBLE_SESSION_SECONDS bleibt und so nicht ohnehin verworfen
    wird). Deshalb hier hart auf `now` ueberschreiben statt die Altlast
    stillschweigend zu uebernehmen.
    """
    pattern.metadata[META_START] = float(now if now is not None else time.time())


def stop_session(pattern: "Pattern", now: float | None = None) -> int:
    """Beendet die Session und addiert die Dauer zur Gesamt-Zeit.

    Returns:
        Dauer der gerade beendeten Session in Sekunden (0 wenn keine aktiv).
    """
    start = pattern.metadata.pop(META_START, None)
    if start is None:
        return 0
    try:
        start_f = float(start)
    except (TypeError, ValueError):
        # Kaputter last_session_start-Wert (z.B. ein String oder eine Liste
        # in einer hand-editierten/korrupten .pxs-Datei) -- kann keine
        # gueltige Dauer ergeben. Wurde oben bereits aus metadata entfernt
        # (pop), also wie "keine Session aktiv" behandeln statt mit einem
        # rohen ValueError/TypeError zu crashen (z.B. beim Verlassen des
        # Sticken-Modus oder beim Schliessen der App).
        return 0
    end = float(now if now is not None else time.time())
    elapsed = max(0, int(end - start_f))
    if elapsed > MAX_PLAUSIBLE_SESSION_SECONDS:
        # Vermutlich ein liegen gebliebener Zeitstempel aus einem
        # abgestürzten Prozess, keine echte Stickzeit -- verwerfen statt
        # eine Bogus-Dauer in die Gesamtsumme einzurechnen.
        return 0
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
