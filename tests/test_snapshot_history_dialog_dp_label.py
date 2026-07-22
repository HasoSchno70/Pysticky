# -*- coding: utf-8 -*-
"""
Regressionstest (Runde 20): SnapshotHistoryDialog._update_detail() zeigte
die Stich-/Drill-Anzahl fuer JEDES Pattern hart-codiert als "Stiche:" an,
auch fuer Diamond-Painting-Muster (pattern.mode == "diamond"), wo laut
etablierter DP/Sticken-Parity-Konvention (siehe pattern_preview_dialog.py)
"Drills:" verwendet werden muss.
"""

import pytest

from pysticky.core.snapshots import create_snapshot, pattern_key_for


@pytest.fixture
def isolated_snapshot_root(tmp_path, monkeypatch):
    monkeypatch.setattr("pysticky.core.snapshots.get_snapshots_root", lambda: tmp_path)
    return tmp_path


def test_detail_label_uses_drills_for_diamond_painting_mode(
    qtbot, isolated_snapshot_root, pattern_with_stitches
):
    from pysticky.ui.dialogs.snapshot_history_dialog import SnapshotHistoryDialog

    pattern_with_stitches.mode = "diamond"
    key = pattern_key_for(pattern_with_stitches, None)
    path = create_snapshot(pattern_with_stitches, key)

    dialog = SnapshotHistoryDialog(pattern_with_stitches, None)
    qtbot.addWidget(dialog)
    dialog._update_detail(path)

    text = dialog._detail_label.text()
    assert "Drills:" in text
    assert "Stiche:" not in text


def test_detail_label_uses_stiche_for_cross_stitch_mode(
    qtbot, isolated_snapshot_root, pattern_with_stitches
):
    from pysticky.ui.dialogs.snapshot_history_dialog import SnapshotHistoryDialog

    assert getattr(pattern_with_stitches, "mode", "stitch") == "stitch"
    key = pattern_key_for(pattern_with_stitches, None)
    path = create_snapshot(pattern_with_stitches, key)

    dialog = SnapshotHistoryDialog(pattern_with_stitches, None)
    qtbot.addWidget(dialog)
    dialog._update_detail(path)

    text = dialog._detail_label.text()
    assert "Stiche:" in text
    assert "Drills:" not in text
