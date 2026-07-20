# -*- coding: utf-8 -*-
"""Tests fuer den Stick-Session-Timer (core.session_timer)."""

import pytest

from pysticky.core import session_timer


def test_initial_state_no_session_no_total(empty_pattern):
    assert session_timer.get_total_seconds(empty_pattern) == 0
    assert not session_timer.is_session_active(empty_pattern)


def test_start_then_stop_accumulates(empty_pattern):
    session_timer.start_session(empty_pattern, now=1000.0)
    assert session_timer.is_session_active(empty_pattern)
    elapsed = session_timer.stop_session(empty_pattern, now=1077.0)
    assert elapsed == 77
    assert session_timer.get_total_seconds(empty_pattern) == 77
    assert not session_timer.is_session_active(empty_pattern)


def test_multiple_sessions_sum(empty_pattern):
    session_timer.start_session(empty_pattern, now=0.0)
    session_timer.stop_session(empty_pattern, now=60.0)
    session_timer.start_session(empty_pattern, now=100.0)
    session_timer.stop_session(empty_pattern, now=130.0)
    assert session_timer.get_total_seconds(empty_pattern) == 90


def test_start_while_active_is_noop(empty_pattern):
    session_timer.start_session(empty_pattern, now=10.0)
    session_timer.start_session(empty_pattern, now=99.0)  # ignoriert
    elapsed = session_timer.stop_session(empty_pattern, now=20.0)
    assert elapsed == 10  # Erste Startzeit gilt


def test_stop_without_start_returns_zero(empty_pattern):
    assert session_timer.stop_session(empty_pattern) == 0
    assert session_timer.get_total_seconds(empty_pattern) == 0


def test_stop_with_negative_delta_clamps_to_zero(empty_pattern):
    """Bei Uhr-Drift (Stop vor Start) keine negative Zeit akkumulieren."""
    session_timer.start_session(empty_pattern, now=100.0)
    elapsed = session_timer.stop_session(empty_pattern, now=50.0)
    assert elapsed == 0
    assert session_timer.get_total_seconds(empty_pattern) == 0


def test_stop_discards_implausibly_long_stale_session(empty_pattern):
    """Regression: stop_session() wird nur ueber closeEvent()/den Sticken-
    Modus-Toggle aufgerufen -- ein Crash dazwischen laesst last_session_start
    im Pattern stehen. Wird die Datei Tage spaeter geoeffnet und die Session
    dann regulaer beendet, darf diese riesige (unplausible) Differenz NICHT
    als echte Stickzeit in die Gesamtsumme einfliessen."""
    session_timer.start_session(empty_pattern, now=0.0)
    two_days_later = 2 * 24 * 3600
    elapsed = session_timer.stop_session(empty_pattern, now=two_days_later)
    assert elapsed == 0
    assert session_timer.get_total_seconds(empty_pattern) == 0
    assert not session_timer.is_session_active(empty_pattern)  # trotzdem sauber geschlossen


def test_stop_accepts_session_just_under_plausible_cap(empty_pattern):
    """Grenzfall: eine sehr lange, aber noch plausible Sitzung (< 12h) wird
    weiterhin normal gezaehlt -- die Kappung darf nicht zu aggressiv sein."""
    session_timer.start_session(empty_pattern, now=0.0)
    just_under_cap = session_timer.MAX_PLAUSIBLE_SESSION_SECONDS - 1
    elapsed = session_timer.stop_session(empty_pattern, now=just_under_cap)
    assert elapsed == just_under_cap
    assert session_timer.get_total_seconds(empty_pattern) == just_under_cap


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (0, "0 Sek"),
        (5, "5 Sek"),
        (59, "59 Sek"),
        (60, "1 Min"),
        (3599, "59 Min"),
        (3600, "1h"),
        (3660, "1h 1min"),
        (3 * 3600 + 30 * 60, "3h 30min"),
    ],
)
def test_format_duration(seconds, expected):
    assert session_timer.format_duration(seconds) == expected


def test_session_metadata_round_trips_through_save_load(empty_pattern, temp_pattern_file):
    """Stick-Zeit ueberlebt save/load (.pxs 1.4)."""
    from pysticky.core import load_pattern, save_pattern

    session_timer.start_session(empty_pattern, now=0.0)
    session_timer.stop_session(empty_pattern, now=42.0)
    save_pattern(empty_pattern, temp_pattern_file)
    loaded = load_pattern(temp_pattern_file)
    assert session_timer.get_total_seconds(loaded) == 42
    assert not session_timer.is_session_active(loaded)


def test_layer_note_round_trips_through_save_load(empty_pattern, temp_pattern_file):
    """Layer-Note ueberlebt save/load (.pxs 1.4)."""
    from pysticky.core import load_pattern, save_pattern

    empty_pattern.layer_stack.active_layer.note = "Vordergrund-Schatten"
    save_pattern(empty_pattern, temp_pattern_file)
    loaded = load_pattern(temp_pattern_file)
    assert loaded.layer_stack.active_layer.note == "Vordergrund-Schatten"


def test_layer_note_default_empty_for_old_files(temp_pattern_file):
    """Files ohne `note`-Feld laden mit leerem String (Backward-Compat)."""
    import json

    from pysticky.core import load_pattern

    data = {
        "format": "pysticky",
        "version": "1.3",
        "saved_at": "2025-01-01T00:00:00",
        "pattern": {
            "name": "Old File",
            "width": 5,
            "height": 5,
            "fabric_count": 14,
            "metadata": {},
            "colors": [{"name": "Schwarz", "color": "#000000", "symbol": "x"}],
            "layers": [
                {
                    "name": "L1",
                    "visible": True,
                    "locked": False,
                    "opacity": 1.0,
                    "stitches": [],
                    "completed_stitches": [],
                }
            ],
            "active_layer": 0,
            "backstitches": [],
            "source_image_path": None,
            "source_image_crop": [0, 0, 1, 1],
            "source_palette_name": None,
        },
    }
    temp_pattern_file.write_text(json.dumps(data), encoding="utf-8")
    loaded = load_pattern(temp_pattern_file)
    assert loaded.layer_stack[0].note == ""
