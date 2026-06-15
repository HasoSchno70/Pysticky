"""Generiert das Demo-Muster und speichert es als
src/pysticky/resources/examples/demo_kreuzstich.pxs.

Ein-mal-Lauf-Skript — wird in CI nicht aufgerufen, sondern manuell beim
Aktualisieren des Demo-Patterns. Die erzeugte .pxs landet im Repo und
wird beim Demo-Klick im UI geladen.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pysticky.core import Pattern, get_palette_manager, save_pattern


def build_demo_pattern() -> Pattern:
    pm = get_palette_manager()
    pm.load_all()
    anchor = pm.get_palette("Anchor")
    if not anchor:
        raise RuntimeError("Anchor-Palette nicht gefunden — kann Demo nicht erzeugen.")

    pattern = Pattern(name="Demo Kreuzstich", width=40, height=40)
    pattern.color_entries.clear()
    anchor_colors = [
        ("403", "Schwarz"),
        ("47", "Rot"),
        ("309", "Gelb"),
        ("228", "Gruen"),
        ("134", "Blau"),
        ("1", "Weiss"),
    ]
    for num, _ in anchor_colors:
        thread = anchor.find_by_number(num)
        if thread:
            pattern.add_color(thread)
    if len(pattern.color_entries) < 5:
        raise RuntimeError("Nicht genug Anchor-Farben fuer Demo gefunden.")

    # Layer 0: Rahmen + Eck-Diagonals
    pattern.layer_stack[0].name = "Rahmen"
    pattern.layer_stack[0].note = "Aussenrahmen + Eck-Diagonalen (Blau)"
    for x in range(5, 35):
        pattern.set_stitch(x, 5, 4)   # 4 = Blau
        pattern.set_stitch(x, 34, 4)
    for y in range(5, 35):
        pattern.set_stitch(5, y, 4)
        pattern.set_stitch(34, y, 4)
    for i in range(3):
        pattern.set_stitch(6 + i, 6 + i, 2)  # 2 = Gelb
        pattern.set_stitch(33 - i, 6 + i, 2)
        pattern.set_stitch(6 + i, 33 - i, 2)
        pattern.set_stitch(33 - i, 33 - i, 2)

    # Layer 1: Herz
    pattern.layer_stack.add_layer("Herz")
    pattern.layer_stack[1].note = "Vordergrund-Herz in Rot"
    heart = [
        "  ##  ##  ", " ######## ", "##########", "##########",
        " ######## ", "  ######  ", "   ####   ", "    ##    ",
    ]
    for dy, row in enumerate(heart):
        for dx, char in enumerate(row):
            if char == "#":
                pattern.set_stitch(15 + dx, 12 + dy, 1)  # 1 = Rot

    # Layer 2: Details
    pattern.layer_stack.add_layer("Details")
    pattern.layer_stack[2].note = "Akzent-Sterne in Gelb"
    for sx, sy in [(8, 10), (31, 10), (8, 30), (31, 30), (20, 25)]:
        pattern.set_stitch(sx, sy, 2)

    pattern.layer_stack.active_index = 0
    pattern.recalculate_stitch_counts()
    return pattern


def main():
    pattern = build_demo_pattern()
    out = Path(__file__).parent.parent / "src" / "pysticky" / "resources" / "examples" / "demo_kreuzstich.pxs"
    out.parent.mkdir(parents=True, exist_ok=True)
    save_pattern(pattern, out)
    size = out.stat().st_size
    stitches = sum(l.count_stitches() for l in pattern.layer_stack)
    print(f"Demo gespeichert: {out}")
    print(f"  Groesse:  {size} Bytes")
    print(f"  Stiche:   {stitches}")
    print(f"  Layer:    {[l.name for l in pattern.layer_stack]}")
    print(f"  Farben:   {len(pattern.color_entries)}")


if __name__ == "__main__":
    main()
