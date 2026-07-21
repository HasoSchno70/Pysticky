# -*- coding: utf-8 -*-
"""Tests fuer das Snapshot-System (core/snapshots.py)."""

import time
from pathlib import Path

import pytest

from pysticky.core.snapshots import (
    _safe_key,
    create_snapshot,
    delete_snapshot,
    list_snapshots,
    parse_snapshot_timestamp,
    pattern_key_for,
    should_snapshot,
)


@pytest.fixture
def isolated_snapshot_root(tmp_path, monkeypatch):
    """Lenkt get_snapshots_root() in einen Test-tmp_path um."""
    monkeypatch.setattr(
        "pysticky.core.snapshots.get_snapshots_root",
        lambda: tmp_path,
    )
    return tmp_path


def test_safe_key_strips_special_chars():
    assert _safe_key("Hello World!") == "Hello_World"
    assert _safe_key("a/b\\c:d") == "a_b_c_d"
    assert _safe_key("") == "_unnamed"
    assert _safe_key("___") == "_unnamed"


def test_parse_snapshot_timestamp_valid():
    p = Path("v_2026-05-13_14-30-00.pxs")
    ts = parse_snapshot_timestamp(p)
    assert ts is not None
    assert ts.year == 2026 and ts.month == 5 and ts.day == 13
    assert ts.hour == 14 and ts.minute == 30


def test_parse_snapshot_timestamp_invalid():
    assert parse_snapshot_timestamp(Path("random.pxs")) is None
    assert parse_snapshot_timestamp(Path("v_garbage.pxs")) is None


def test_create_snapshot_and_list(isolated_snapshot_root, pattern_with_stitches):
    snap = create_snapshot(pattern_with_stitches, "test_key")
    assert snap.exists()
    snaps = list_snapshots("test_key")
    assert len(snaps) == 1
    assert snaps[0] == snap


def test_create_multiple_snapshots_sorted_newest_first(
    isolated_snapshot_root, pattern_with_stitches
):
    s1 = create_snapshot(pattern_with_stitches, "test_multi")
    time.sleep(1.1)  # eine Sekunde Pause damit der Filename-Timestamp anders ist
    s2 = create_snapshot(pattern_with_stitches, "test_multi")
    snaps = list_snapshots("test_multi")
    assert len(snaps) == 2
    assert snaps[0] == s2  # neuester zuerst
    assert snaps[1] == s1


def test_create_snapshot_same_second_collision_stays_parseable(
    isolated_snapshot_root, pattern_with_stitches, monkeypatch
):
    """Regression: bei zwei Snapshots innerhalb derselben Sekunde haengte
    create_snapshot() frueher einen "_1"-Suffix an den Dateinamen an
    (z.B. "v_2026-05-13_14-30-00_1.pxs"). parse_snapshot_timestamp()s
    striktes Format erkennt das NICHT -> der Snapshot verschwindet
    dauerhaft aus list_snapshots() (unsichtbar in der Versions-Historie)
    UND aus der max_keep-Zaehlung von _cleanup_old_snapshots() (wird nie
    aufgeraeumt) -- ein Datei-Leck. Jetzt wird bei einer Kollision der
    Zeitstempel um 1s vorgerueckt statt ein Suffix anzuhaengen, der
    Dateiname bleibt also immer parsebar."""
    from pysticky.core import snapshots as snapshots_mod

    pdir = snapshots_mod.get_pattern_dir("collision_key")
    existing = pdir / "v_2026-05-13_14-30-00.pxs"
    existing.write_bytes(b"dummy")

    from datetime import datetime as _dt

    class _FixedDatetime(_dt):
        @classmethod
        def now(cls, tz=None):
            return _dt(2026, 5, 13, 14, 30, 0)

    monkeypatch.setattr(snapshots_mod, "datetime", _FixedDatetime)
    snap = create_snapshot(pattern_with_stitches, "collision_key")

    assert snap != existing
    assert snap.name == "v_2026-05-13_14-30-01.pxs"  # 1s vorgerueckt, nicht "_1"-Suffix
    assert parse_snapshot_timestamp(snap) is not None

    snaps = list_snapshots("collision_key")
    assert snap in snaps  # sichtbar in der Versions-Historie
    assert existing in snaps


def test_cleanup_keeps_only_max_snapshots(isolated_snapshot_root, pattern_with_stitches):
    # 5 Snapshots, max_keep=3
    paths = []
    for _ in range(5):
        p = create_snapshot(pattern_with_stitches, "test_max", max_keep=3)
        paths.append(p)
        time.sleep(1.05)  # damit Filenames sich unterscheiden
    snaps = list_snapshots("test_max")
    assert len(snaps) == 3
    # Die juengsten 3 muessen drin sein
    assert paths[-1] in snaps
    assert paths[-2] in snaps
    assert paths[-3] in snaps


def test_delete_snapshot(isolated_snapshot_root, pattern_with_stitches):
    snap = create_snapshot(pattern_with_stitches, "test_del")
    assert delete_snapshot(snap) is True
    assert not snap.exists()
    assert list_snapshots("test_del") == []


def test_delete_nonexistent_snapshot_returns_false(tmp_path):
    fake = tmp_path / "ghost.pxs"
    assert delete_snapshot(fake) is False


def test_should_snapshot_empty_dir_returns_true(isolated_snapshot_root):
    assert should_snapshot("brand_new") is True


def test_should_snapshot_after_interval(isolated_snapshot_root, pattern_with_stitches):
    create_snapshot(pattern_with_stitches, "rate_test")
    # Direkt danach: zu frueh
    assert should_snapshot("rate_test", interval_seconds=3600) is False
    # Mit interval=0: jederzeit erlaubt
    assert should_snapshot("rate_test", interval_seconds=0) is True


def test_pattern_key_for_uses_file_path_stem(pattern_with_stitches, tmp_path):
    fp = tmp_path / "mein_muster.pxs"
    assert pattern_key_for(pattern_with_stitches, fp) == "mein_muster"


def test_pattern_key_for_falls_back_to_pattern_name(pattern_with_stitches):
    pattern_with_stitches.name = "Test-Pattern"
    assert pattern_key_for(pattern_with_stitches, None) == "Test-Pattern"
