# -*- coding: utf-8 -*-
"""Tests fuer die mitgelieferte Demo-.pxs-Datei.

Stellt sicher dass:
- Die Datei existiert (im Repo unter resources/examples/)
- Sie ueber load_pattern() ladbar ist
- Sie die erwarteten Layer + Notizen + Farben hat
- Sie roundtrip-bar ist (load → save → load matched)
"""

from pathlib import Path

DEMO_PATH = (
    Path(__file__).parent.parent
    / "src"
    / "pysticky"
    / "resources"
    / "examples"
    / "demo_kreuzstich.pxs"
)


def test_demo_file_exists():
    assert DEMO_PATH.exists(), (
        f"Demo-Datei fehlt: {DEMO_PATH}\nMit `python scripts/generate_demo.py` neu erzeugen."
    )


def test_demo_file_loads():
    from pysticky.core import load_pattern

    pattern = load_pattern(str(DEMO_PATH))
    assert pattern.name == "Demo Kreuzstich"
    assert pattern.width == 40
    assert pattern.height == 40


def test_demo_file_has_three_layers_with_notes():
    from pysticky.core import load_pattern

    pattern = load_pattern(str(DEMO_PATH))
    assert len(pattern.layer_stack) == 3
    names = [l.name for l in pattern.layer_stack]
    assert names == ["Rahmen", "Herz", "Details"]
    # Jeder Layer hat eine Notiz (Sprint-1-Feature live demonstriert)
    for layer in pattern.layer_stack:
        assert layer.note, f"Layer {layer.name!r} hat keine Notiz"


def test_demo_file_has_six_colors():
    from pysticky.core import load_pattern

    pattern = load_pattern(str(DEMO_PATH))
    assert len(pattern.color_entries) == 6


def test_demo_file_has_185_stitches():
    from pysticky.core import load_pattern

    pattern = load_pattern(str(DEMO_PATH))
    total = sum(l.count_stitches() for l in pattern.layer_stack)
    assert total == 185


def test_demo_file_roundtrip(tmp_path):
    """Speichern + neu laden ergibt identische Werte."""
    from pysticky.core import load_pattern, save_pattern

    original = load_pattern(str(DEMO_PATH))
    out = tmp_path / "demo_copy.pxs"
    save_pattern(original, out)
    loaded = load_pattern(str(out))
    assert loaded.name == original.name
    assert loaded.width == original.width
    assert len(loaded.layer_stack) == len(original.layer_stack)
    for orig_l, new_l in zip(original.layer_stack, loaded.layer_stack):
        assert orig_l.name == new_l.name
        assert orig_l.note == new_l.note
        assert orig_l.count_stitches() == new_l.count_stitches()
