# -*- coding: utf-8 -*-
"""Tests fuer den Pattern-Diff-Algorithmus."""


def test_diff_of_identical_patterns_has_no_changes(pattern_with_stitches):
    """Pattern mit sich selbst diffed: 0 Aenderungen."""
    from pysticky.core.pattern_diff import compute_diff

    diff = compute_diff(pattern_with_stitches, pattern_with_stitches)
    assert diff.stats.added == 0
    assert diff.stats.removed == 0
    assert diff.stats.changed == 0
    assert diff.has_changes is False


def test_diff_detects_added_stitches(pattern_with_colors):
    """Wenn das neue Pattern Stiche dazu bekommt, werden sie als ADDED markiert."""
    import copy

    from pysticky.core.pattern_diff import DIFF_ADDED, compute_diff

    old = copy.deepcopy(pattern_with_colors)
    new = pattern_with_colors
    new.set_stitch(5, 5, 0)
    new.set_stitch(6, 5, 0)

    diff = compute_diff(old, new)
    assert diff.stats.added == 2
    assert diff.stats.removed == 0
    assert diff.stats.changed == 0
    assert diff.mask[5, 5] == DIFF_ADDED
    assert diff.mask[5, 6] == DIFF_ADDED


def test_diff_detects_removed_stitches(pattern_with_colors):
    """Wenn das neue Pattern Stiche verliert, werden sie als REMOVED markiert."""
    import copy

    from pysticky.core.pattern_diff import DIFF_REMOVED, compute_diff

    pattern_with_colors.set_stitch(3, 3, 0)
    pattern_with_colors.set_stitch(4, 4, 0)
    old = copy.deepcopy(pattern_with_colors)

    pattern_with_colors.remove_stitch(3, 3)
    pattern_with_colors.remove_stitch(4, 4)

    diff = compute_diff(old, pattern_with_colors)
    assert diff.stats.removed == 2
    assert diff.stats.added == 0
    assert diff.mask[3, 3] == DIFF_REMOVED
    assert diff.mask[4, 4] == DIFF_REMOVED


def test_diff_detects_changed_color(pattern_with_colors):
    """Wenn die Farbe an einer Position wechselt: CHANGED."""
    import copy

    from pysticky.core.pattern_diff import DIFF_CHANGED, compute_diff

    pattern_with_colors.set_stitch(2, 2, 0)  # color 0
    old = copy.deepcopy(pattern_with_colors)
    pattern_with_colors.set_stitch(2, 2, 1)  # color 1

    diff = compute_diff(old, pattern_with_colors)
    assert diff.stats.changed == 1
    assert diff.mask[2, 2] == DIFF_CHANGED


def test_diff_detects_changed_stitch_type(pattern_with_colors):
    """Wenn der Stich-Type wechselt: CHANGED."""
    import copy

    from pysticky.core.pattern_diff import DIFF_CHANGED, compute_diff
    from pysticky.core.stitch import StitchType

    pattern_with_colors.set_stitch(2, 2, 0, stitch_type=StitchType.FULL.value)
    old = copy.deepcopy(pattern_with_colors)
    pattern_with_colors.set_stitch(2, 2, 0, stitch_type=StitchType.HALF_TL_BR.value)

    diff = compute_diff(old, pattern_with_colors)
    assert diff.stats.changed == 1
    assert diff.mask[2, 2] == DIFF_CHANGED


def test_diff_with_size_changed(empty_pattern):
    """Wenn die Patterns unterschiedliche Groessen haben, wird das in stats markiert."""
    from pysticky.core import Pattern, Thread
    from pysticky.core.pattern_diff import compute_diff

    old = empty_pattern  # 10x10
    new = Pattern(name="Bigger", width=15, height=15)
    new.color_entries.clear()
    new.add_color(Thread.from_hex("Red", "#FF0000"))
    new.set_stitch(12, 12, 0)

    diff = compute_diff(old, new)
    assert diff.stats.size_changed is True
    assert diff.stats.width == 15
    assert diff.stats.height == 15


def test_diff_mask_shape_matches_max_bounding_box(empty_pattern):
    """Die Diff-Maske hat Shape (max_h, max_w)."""
    from pysticky.core import Pattern
    from pysticky.core.pattern_diff import compute_diff

    old = Pattern(name="A", width=8, height=12)
    new = Pattern(name="B", width=15, height=5)

    diff = compute_diff(old, new)
    assert diff.mask.shape == (12, 15)
    assert diff.stats.width == 15
    assert diff.stats.height == 12


def test_diff_stats_to_dict(pattern_with_stitches):
    """DiffStats.to_dict liefert alle Felder."""
    from pysticky.core.pattern_diff import compute_diff

    diff = compute_diff(pattern_with_stitches, pattern_with_stitches)
    d = diff.stats.to_dict()
    for key in (
        "added",
        "removed",
        "changed",
        "same",
        "total_changes",
        "width",
        "height",
        "size_changed",
    ):
        assert key in d


def test_diff_total_changes_property(pattern_with_colors):
    """total_changes ist die Summe aus added + removed + changed."""
    import copy

    from pysticky.core.pattern_diff import compute_diff

    pattern_with_colors.set_stitch(1, 1, 0)
    pattern_with_colors.set_stitch(2, 2, 0)
    old = copy.deepcopy(pattern_with_colors)
    pattern_with_colors.remove_stitch(1, 1)
    pattern_with_colors.set_stitch(3, 3, 0)
    pattern_with_colors.set_stitch(2, 2, 1)

    diff = compute_diff(old, pattern_with_colors)
    assert diff.stats.total_changes == (diff.stats.added + diff.stats.removed + diff.stats.changed)
    assert diff.stats.total_changes > 0


def test_diff_has_changes_property():
    """has_changes ist True wenn total_changes > 0."""
    from pysticky.core import Pattern, Thread
    from pysticky.core.pattern_diff import compute_diff

    a = Pattern(name="A", width=5, height=5)
    a.color_entries.clear()
    a.add_color(Thread.from_hex("Red", "#FF0000"))

    b = Pattern(name="B", width=5, height=5)
    b.color_entries.clear()
    b.add_color(Thread.from_hex("Red", "#FF0000"))
    b.set_stitch(2, 2, 0)

    diff = compute_diff(a, b)
    assert diff.has_changes is True
    assert diff.stats.added == 1
