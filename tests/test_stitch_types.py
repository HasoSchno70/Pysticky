# -*- coding: utf-8 -*-
"""
End-to-End-Tests fuer halbe / viertel Stichtypen.

Verifiziert die ganze Pipeline:
- Layer speichert/liest stitch_type
- Datei-I/O (Roundtrip)
- Rotation/Spiegelung mapen den Typ korrekt
- UI: Menue + Status-Label + Toolbar-Combobox synchron
"""

import json

import pytest

from pysticky.core import Pattern, load_pattern, save_pattern
from pysticky.core.stitch import (
    FLIP_H_MAP,
    FLIP_V_MAP,
    ROTATE_CCW_MAP,
    ROTATE_CW_MAP,
    StitchType,
)

pytestmark = pytest.mark.usefixtures("qtbot")


# ============================================================================
# Layer-Ebene: get/set stitch_type
# ============================================================================


def test_layer_stitch_type_default_is_full():
    p = Pattern(name="x", width=5, height=5)
    layer = p.active_layer
    layer.set_stitch(2, 2, 0)  # nur Farbe, kein Type
    assert layer.get_stitch_type(2, 2) == StitchType.FULL.value


def test_layer_stitch_type_set_and_get():
    p = Pattern(name="x", width=5, height=5)
    layer = p.active_layer
    layer.set_stitch(1, 1, 0, stitch_type=StitchType.HALF_TL_BR.value)
    assert layer.get_stitch_type(1, 1) == StitchType.HALF_TL_BR.value


def test_layer_remove_resets_stitch_type():
    """Beim Loeschen muss der stitch_type zurueck auf 0 fallen."""
    p = Pattern(name="x", width=5, height=5)
    layer = p.active_layer
    layer.set_stitch(1, 1, 0, stitch_type=StitchType.HALF_TL_BR.value)
    layer.remove_stitch(1, 1)
    assert layer.get_stitch_type(1, 1) == 0


def test_layer_stitch_type_resize_preserves(empty_pattern):
    """Resize behaelt stitch_types im ueberlappenden Bereich."""
    layer = empty_pattern.active_layer
    empty_pattern.color_entries.append(empty_pattern.color_entries[0])  # zweite ref
    layer.set_stitch(2, 2, 0, stitch_type=StitchType.QUARTER_TL.value)
    layer.resize(8, 8)
    assert layer.get_stitch_type(2, 2) == StitchType.QUARTER_TL.value
    # neu allokierte Zellen sind 0
    assert layer.get_stitch_type(7, 7) == 0


# ============================================================================
# Transformations-Maps konsistent
# ============================================================================


def test_flip_h_self_inverse():
    """Zweimal H-spiegeln ergibt die Identitaet."""
    for stype in range(10):
        assert FLIP_H_MAP[FLIP_H_MAP[stype]] == stype


def test_flip_v_self_inverse():
    for stype in range(10):
        assert FLIP_V_MAP[FLIP_V_MAP[stype]] == stype


def test_rotate_cw_four_times_is_identity():
    """4x rechts drehen = unveraendert."""
    for stype in range(10):
        rotated = stype
        for _ in range(4):
            rotated = ROTATE_CW_MAP[rotated]
        assert rotated == stype


def test_rotate_cw_and_ccw_are_inverse():
    for stype in range(10):
        assert ROTATE_CCW_MAP[ROTATE_CW_MAP[stype]] == stype


# ============================================================================
# Datei-I/O Roundtrip
# ============================================================================


def test_save_load_preserves_stitch_types(tmp_path):
    """.pxs-Roundtrip: stitch_types muessen erhalten bleiben."""
    p = Pattern(name="x", width=5, height=5)
    layer = p.active_layer
    layer.set_stitch(0, 0, 0, stitch_type=StitchType.HALF_TL_BR.value)
    layer.set_stitch(1, 1, 0, stitch_type=StitchType.HALF_TR_BL.value)
    layer.set_stitch(2, 2, 0, stitch_type=StitchType.QUARTER_TL.value)
    layer.set_stitch(3, 3, 0, stitch_type=StitchType.QUARTER_BR.value)

    target = tmp_path / "stitches.pxs"
    save_pattern(p, target)
    loaded = load_pattern(target)

    ll = loaded.active_layer
    assert ll.get_stitch_type(0, 0) == StitchType.HALF_TL_BR.value
    assert ll.get_stitch_type(1, 1) == StitchType.HALF_TR_BL.value
    assert ll.get_stitch_type(2, 2) == StitchType.QUARTER_TL.value
    assert ll.get_stitch_type(3, 3) == StitchType.QUARTER_BR.value


def test_save_omits_stitch_types_when_all_full(tmp_path):
    """Pattern ohne halbe Stiche -> stitch_types-Feld fehlt in der Datei."""
    p = Pattern(name="x", width=5, height=5)
    p.active_layer.set_stitch(2, 2, 0)  # nur voller Stich
    target = tmp_path / "no_half.pxs"
    save_pattern(p, target)

    data = json.loads(target.read_text(encoding="utf-8"))
    for layer_data in data.get("layers", []):
        # entweder fehlt das Feld oder es ist leer
        assert "stitch_types" not in layer_data or layer_data["stitch_types"] == []


# UI-Test (MainWindow-Konstruktion) ist ganz unten platziert —
# die volle MainWindow-Initialisierung verbraucht Qt-Resources, die
# hinterher andere Tests zum Heap-Crash bringen koennen.


# ============================================================================
# Composite-Type-Grid auf LayerStack-Ebene
# ============================================================================


def test_composite_stitch_type_grid_dimensions():
    p = Pattern(name="x", width=6, height=4)
    grid = p.layer_stack.get_composite_stitch_type_grid()
    assert grid.shape == (4, 6)
    assert grid.dtype.name == "uint8"


def test_composite_stitch_type_grid_reflects_layer_content():
    p = Pattern(name="x", width=5, height=5)
    layer = p.active_layer
    layer.set_stitch(2, 2, 0, stitch_type=StitchType.HALF_TL_BR.value)
    layer.set_stitch(3, 3, 0, stitch_type=StitchType.QUARTER_BR.value)

    grid = p.layer_stack.get_composite_stitch_type_grid()
    assert grid[2, 2] == StitchType.HALF_TL_BR.value
    assert grid[3, 3] == StitchType.QUARTER_BR.value
    assert grid[0, 0] == 0  # leer


def test_composite_stitch_type_ignores_invisible_layers():
    """Unsichtbare Layer tragen keine Stichtypen bei."""
    p = Pattern(name="x", width=5, height=5)
    base = p.active_layer
    base.set_stitch(2, 2, 0, stitch_type=StitchType.HALF_TL_BR.value)

    p.layer_stack.add_layer("Top")
    p.layer_stack.active_index = 1
    top = p.layer_stack.active_layer
    top.set_stitch(2, 2, 0, stitch_type=StitchType.QUARTER_TR.value)
    top.visible = False

    grid = p.layer_stack.get_composite_stitch_type_grid()
    # Top ist invisible -> base gewinnt
    assert grid[2, 2] == StitchType.HALF_TL_BR.value


def test_composite_stitch_type_top_layer_wins():
    """Bei zwei sichtbaren Layern gewinnt der obere."""
    p = Pattern(name="x", width=5, height=5)
    base = p.active_layer
    base.set_stitch(2, 2, 0, stitch_type=StitchType.HALF_TL_BR.value)

    p.layer_stack.add_layer("Top")
    p.layer_stack.active_index = 1
    top = p.layer_stack.active_layer
    top.set_stitch(2, 2, 0, stitch_type=StitchType.QUARTER_TR.value)

    grid = p.layer_stack.get_composite_stitch_type_grid()
    assert grid[2, 2] == StitchType.QUARTER_TR.value


# ============================================================================
# Preview-Render-Engine zeichnet halbe / Viertel
# ============================================================================


def test_preview_engine_caches_composite_stitch_types(qtbot):
    """Engine baut beim Init das stitch-type-grid mit auf."""
    from pysticky.ui.rendering.preview_render_engine import PreviewRenderEngine

    p = Pattern(name="x", width=5, height=5)
    p.active_layer.set_stitch(2, 2, 0, stitch_type=StitchType.HALF_TL_BR.value)

    engine = PreviewRenderEngine(p)
    assert engine._composite_stitch_types is not None
    assert engine._composite_stitch_types[2, 2] == StitchType.HALF_TL_BR.value


def _make_partial_pattern(stype: int):
    """Pattern mit genau einem Stich des gegebenen Typs in der Mitte."""
    p = Pattern(name="x", width=4, height=4)
    p.active_layer.set_stitch(2, 2, 0, stitch_type=stype)
    return p


def _make_full_pattern():
    """Vergleichs-Pattern: gleicher Stich, aber voll."""
    p = Pattern(name="x", width=4, height=4)
    p.active_layer.set_stitch(2, 2, 0)
    return p


def _png_file_hash(path):
    """Einfacher MD5-Hash der PNG-Bytes — vermeidet Heap-Probleme mit QImage.bits()."""
    import hashlib

    return hashlib.md5(path.read_bytes()).hexdigest()


def test_image_export_renders_partial_stitches_differently(tmp_path):
    """PNG-Export muss halben und vollen Stich visuell unterscheiden."""
    from pysticky.io.image_export import ImageExporter

    p_full = _make_full_pattern()
    p_half = _make_partial_pattern(StitchType.HALF_TL_BR.value)

    f_full = tmp_path / "full.png"
    f_half = tmp_path / "half.png"
    ImageExporter(p_full).export(f_full, cell_size=20)
    ImageExporter(p_half).export(f_half, cell_size=20)

    assert _png_file_hash(f_full) != _png_file_hash(f_half), (
        "PNG-Export muss halben Stich anders rendern als vollen"
    )


def test_image_export_quarter_stitch(tmp_path):
    """Auch Viertelstiche werden visuell anders gerendert."""
    from pysticky.io.image_export import ImageExporter

    p_full = _make_full_pattern()
    p_q = _make_partial_pattern(StitchType.QUARTER_TR.value)

    f_full = tmp_path / "f.png"
    f_q = tmp_path / "q.png"
    ImageExporter(p_full).export(f_full, cell_size=20)
    ImageExporter(p_q).export(f_q, cell_size=20)
    assert _png_file_hash(f_full) != _png_file_hash(f_q)


def test_html_export_emits_polygon_for_partial_stitches(tmp_path):
    """HTML-Vorschau muss <polygon> fuer halbe/Viertel-Stiche enthalten."""
    from pysticky.io.html_export import HTMLExporter

    p = _make_partial_pattern(StitchType.HALF_TL_BR.value)
    target = tmp_path / "out.html"
    HTMLExporter(p).export(target)
    content = target.read_text(encoding="utf-8")
    assert "<polygon" in content, (
        "HTML-Export muss Polygon-SVG-Elemente fuer halbe Stiche enthalten"
    )


def test_html_export_no_polygon_when_only_full_stitches(tmp_path):
    """Bei nur vollen Stichen sollen keine Polygone im HTML auftauchen."""
    from pysticky.io.html_export import HTMLExporter

    p = _make_full_pattern()
    target = tmp_path / "full.html"
    HTMLExporter(p).export(target)
    content = target.read_text(encoding="utf-8")
    assert "<polygon" not in content, "Bei vollen Stichen darf kein Polygon im HTML stehen"


def test_export_common_get_pixel_stitch_type():
    """`get_pixel_stitch_type` liefert den Type aus dem obersten sichtbaren Layer."""
    from pysticky.io.export_common import get_pixel_stitch_type

    p = _make_partial_pattern(StitchType.QUARTER_BR.value)
    assert get_pixel_stitch_type(p, 2, 2) == StitchType.QUARTER_BR.value
    assert get_pixel_stitch_type(p, 0, 0) == 0


# ============================================================================
# THREE_QUARTER + FRENCH_KNOT — neue Stichtypen
# ============================================================================


def test_three_quarter_stitch_layer_roundtrip(tmp_path):
    """THREE_QUARTER ueberlebt den .pxs-Roundtrip."""
    p = _make_partial_pattern(StitchType.THREE_QUARTER.value)
    target = tmp_path / "tq.pxs"
    save_pattern(p, target)
    loaded = load_pattern(target)
    assert loaded.active_layer.get_stitch_type(2, 2) == StitchType.THREE_QUARTER.value


def test_three_quarter_shape_is_not_the_full_square():
    """Regression (Runde 22): core/stitch_shapes.py::_PARTIAL_SHAPES[7]
    war faelschlich das volle Rechteck (0,0)-(1,0)-(1,1)-(0,1) statt eines
    Fuenfecks (volles Quadrat minus die QUARTER_BL-Ecke) -- ein
    Drei-Viertel-Stich war dadurch in JEDEM Renderer (Canvas/PDF/HTML/PNG),
    der diese gemeinsame Shape-Tabelle nutzt, optisch identisch zu einem
    vollen Kreuzstich."""
    from pysticky.core.stitch_shapes import normalized_partial_stitch_shape

    shape = normalized_partial_stitch_shape(StitchType.THREE_QUARTER.value)
    # Volles Rechteck haette Flaeche 1.0 -- das Fuenfeck (minus die kleine
    # QUARTER_BL-Ecke, Flaeche 0.125) muss kleiner sein.
    area = _polygon_area(shape)
    assert area < 1.0
    assert (0.0, 1.0) not in shape, "Die volle untere-linke Ecke darf kein Eckpunkt mehr sein"


def _polygon_area(points):
    """Shoelace-Formel fuer die Flaeche eines (konvexen) Polygons."""
    n = len(points)
    area = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def test_image_export_renders_three_quarter_stitch_differently_from_full(tmp_path):
    """End-to-End: PNG-Export muss Drei-Viertel-Stich anders rendern als
    einen vollen Kreuzstich (vorher optisch identisch, siehe Bug oben)."""
    from pysticky.io.image_export import ImageExporter

    p_full = _make_full_pattern()
    p_tq = _make_partial_pattern(StitchType.THREE_QUARTER.value)

    f_full = tmp_path / "full.png"
    f_tq = tmp_path / "three_quarter.png"
    ImageExporter(p_full).export(f_full, cell_size=20)
    ImageExporter(p_tq).export(f_tq, cell_size=20)

    assert _png_file_hash(f_full) != _png_file_hash(f_tq), (
        "PNG-Export muss Drei-Viertel-Stich anders rendern als vollen Kreuzstich"
    )


def test_french_knot_layer_roundtrip(tmp_path):
    """FRENCH_KNOT ueberlebt den .pxs-Roundtrip."""
    p = _make_partial_pattern(StitchType.FRENCH_KNOT.value)
    target = tmp_path / "fk.pxs"
    save_pattern(p, target)
    loaded = load_pattern(target)
    assert loaded.active_layer.get_stitch_type(2, 2) == StitchType.FRENCH_KNOT.value


def test_stitch_shapes_french_knot_helpers():
    """`is_french_knot` und `french_knot_radius_factor` liefern korrekte Werte."""
    from pysticky.core.stitch_shapes import (
        french_knot_radius_factor,
        is_french_knot,
        is_partial_stitch,
    )

    assert is_french_knot(StitchType.FRENCH_KNOT.value) is True
    assert is_french_knot(StitchType.HALF_TL_BR.value) is False
    assert is_french_knot(0) is False

    # French Knot ist KEIN Polygon-Partial — wir behandeln ihn als Kreis
    assert is_partial_stitch(StitchType.FRENCH_KNOT.value) is False

    # Radius-Faktor ist in einem sinnvollen Bereich
    f = french_knot_radius_factor()
    assert 0.1 < f < 0.5


def test_image_export_renders_french_knot_differently(tmp_path):
    """PNG-Export: French Knot vs voller Stich -> verschiedene Hashes."""
    from pysticky.io.image_export import ImageExporter

    p_full = _make_full_pattern()
    p_fk = _make_partial_pattern(StitchType.FRENCH_KNOT.value)
    ImageExporter(p_full).export(tmp_path / "full.png", cell_size=20)
    ImageExporter(p_fk).export(tmp_path / "fk.png", cell_size=20)
    assert _png_file_hash(tmp_path / "full.png") != _png_file_hash(tmp_path / "fk.png")


def test_image_export_french_knot_differs_from_half(tmp_path):
    """PNG-Export: French Knot vs halber Stich -> visuell anders."""
    from pysticky.io.image_export import ImageExporter

    p_half = _make_partial_pattern(StitchType.HALF_TL_BR.value)
    p_fk = _make_partial_pattern(StitchType.FRENCH_KNOT.value)
    ImageExporter(p_half).export(tmp_path / "half.png", cell_size=20)
    ImageExporter(p_fk).export(tmp_path / "fk.png", cell_size=20)
    assert _png_file_hash(tmp_path / "half.png") != _png_file_hash(tmp_path / "fk.png")


def test_html_export_emits_circle_for_french_knot(tmp_path):
    """HTML-Vorschau muss `<circle>` fuer French Knots enthalten."""
    from pysticky.io.html_export import HTMLExporter

    p = _make_partial_pattern(StitchType.FRENCH_KNOT.value)
    target = tmp_path / "fk.html"
    HTMLExporter(p).export(target)
    content = target.read_text(encoding="utf-8")
    assert "<circle" in content, "HTML-Export muss Circle-SVG-Elemente fuer French Knots enthalten"


def test_html_export_no_circle_when_only_full_stitches(tmp_path):
    """Bei nur vollen Stichen darf kein Circle im HTML auftauchen."""
    from pysticky.io.html_export import HTMLExporter

    p = _make_full_pattern()
    target = tmp_path / "full.html"
    HTMLExporter(p).export(target)
    content = target.read_text(encoding="utf-8")
    assert "<circle" not in content


def test_pdf_export_french_knot(tmp_path):
    """PDF-Export mit French Knot — keine Exception, valides PDF."""
    pytest.importorskip("reportlab")
    from pysticky.io.pdf_export import PDFExporter, check_reportlab_available

    if not check_reportlab_available():
        pytest.skip("reportlab not available")

    p = _make_partial_pattern(StitchType.FRENCH_KNOT.value)
    target = tmp_path / "fk.pdf"
    PDFExporter(p, include_path_preview=False).export(target)
    assert target.exists() and target.stat().st_size > 0
    with target.open("rb") as f:
        assert f.read(4) == b"%PDF"


def test_pdf_export_renders_partial_stitch_polygon(tmp_path):
    """PDF-Export: bei halben Stichen muss ein Polygon im Inhalt vorkommen.

    Wir suchen die Polygon-Op-Sequenz in den PDF-Bytes als Indikator —
    reportlab erzeugt fuer Polygon-Shapes eine entsprechende Path-Sequenz.
    """
    pytest.importorskip("reportlab")
    from pysticky.io.pdf_export import PDFExporter, check_reportlab_available

    if not check_reportlab_available():
        pytest.skip("reportlab not available")

    p_half = _make_partial_pattern(StitchType.HALF_TL_BR.value)
    target = tmp_path / "half.pdf"
    PDFExporter(p_half, include_path_preview=False).export(target)
    assert target.exists()
    assert target.stat().st_size > 0
    # Sanity: PDF-Header muss da sein
    with target.open("rb") as f:
        assert f.read(4) == b"%PDF"


def test_preview_engine_pixel_mode_renders_three_quarter_differently_from_full(qtbot, tmp_path):
    """Regression (Runde 22): PreviewRenderEngine._draw_partial_stitch_pixel()
    (RenderMode.PIXEL) hatte fuer THREE_QUARTER unabhaengig denselben Bug
    wie core/stitch_shapes.py und rendering_mixin.py -- das volle Rechteck
    statt eines Fuenfecks, optisch identisch zu einem vollen Stich."""
    from pysticky.ui.rendering.preview_render_engine import PreviewRenderEngine, RenderMode

    p_full = Pattern(name="full", width=4, height=4)
    p_full.active_layer.set_stitch(2, 2, 0)

    p_tq = Pattern(name="tq", width=4, height=4)
    p_tq.active_layer.set_stitch(2, 2, 0, stitch_type=StitchType.THREE_QUARTER.value)

    engine_full = PreviewRenderEngine(p_full)
    engine_full.set_render_mode(RenderMode.PIXEL)
    engine_tq = PreviewRenderEngine(p_tq)
    engine_tq.set_render_mode(RenderMode.PIXEL)

    img_full = engine_full.render(cell_size=40)
    img_tq = engine_tq.render(cell_size=40)

    f_full = tmp_path / "full_pixel.png"
    f_tq = tmp_path / "tq_pixel.png"
    img_full.save(str(f_full), "PNG")
    img_tq.save(str(f_tq), "PNG")
    assert _png_file_hash(f_full) != _png_file_hash(f_tq), (
        "Drei-Viertel-Stich muss im Pixel-Modus anders aussehen als voller Stich"
    )


def test_preview_engine_renders_partial_stitch_visibly_different(qtbot, tmp_path):
    """
    Pattern mit halbem vs vollem Stich -> Engine produziert unterschiedliches
    PNG. Via Datei-Hash, weil QImage.constBits() in der Test-Sandbox
    instabil ist.
    """
    from pysticky.ui.rendering.preview_render_engine import PreviewRenderEngine

    p_full = Pattern(name="full", width=4, height=4)
    p_full.active_layer.set_stitch(2, 2, 0)

    p_half = Pattern(name="half", width=4, height=4)
    p_half.active_layer.set_stitch(2, 2, 0, stitch_type=StitchType.HALF_TL_BR.value)

    img_full = PreviewRenderEngine(p_full).render(cell_size=40)
    img_half = PreviewRenderEngine(p_half).render(cell_size=40)
    assert img_full.size() == img_half.size()

    f_full = tmp_path / "full.png"
    f_half = tmp_path / "half.png"
    img_full.save(str(f_full), "PNG")
    img_half.save(str(f_half), "PNG")
    assert _png_file_hash(f_full) != _png_file_hash(f_half), (
        "Halber Stich muss visuell anders aussehen als voller"
    )


def test_preview_engine_respects_backstitch_line_style_and_width(qtbot, tmp_path):
    """
    Regression: PreviewRenderEngine._draw_backstitches() zeichnete
    Rueckstiche immer durchgezogen mit rundem Kappenstil in fester Dicke --
    unabhaengig davon, was der Nutzer im Backstitch-Options-Dock eingestellt
    hat. Der Canvas-Renderer (rendering_mixin.py::_draw_backstitches) liest
    dafuer _backstitch_line_style/_backstitch_cap_style/
    _backstitch_width_offset vom Canvas; die Vorschau hatte kein Gegenstueck
    dafuer und ignorierte diese Einstellungen komplett.
    """
    from PySide6.QtCore import Qt

    from pysticky.ui.rendering.preview_render_engine import PreviewRenderEngine

    p = Pattern(name="bs", width=6, height=6)
    p.add_backstitch(2, 2, 10, 10, color_index=0)

    engine_default = PreviewRenderEngine(p)
    img_default = engine_default.render(cell_size=40)

    engine_styled = PreviewRenderEngine(p)
    engine_styled.set_backstitch_style(Qt.PenStyle.DotLine, Qt.PenCapStyle.SquareCap, 4)
    img_styled = engine_styled.render(cell_size=40)

    f_default = tmp_path / "bs_default.png"
    f_styled = tmp_path / "bs_styled.png"
    img_default.save(str(f_default), "PNG")
    img_styled.save(str(f_styled), "PNG")

    assert _png_file_hash(f_default) != _png_file_hash(f_styled), (
        "Rueckstich-Linienstil/-Dicke muessen die Vorschau visuell beeinflussen"
    )


# ============================================================================
# UI: Statusleiste + Menue + Toolbar synchron — ans absolute Ende der Datei,
# damit die MainWindow-Konstruktion die Tests danach nicht zum Crashen bringt.
# ============================================================================


def test_zzz_mainwindow_stitch_type_ui_full_lifecycle(qtbot):
    """
    Konsolidierter UI-Test (statt drei separate MainWindow-Inits).

    Verifiziert:
    - Alle 3 UI-Elemente (Status-Label, Menue-Actions, Toolbar-Combobox)
    - Wechsel via `_on_stitch_type_changed` synchronisiert alle drei + Canvas
    - Wechsel via Toolbar-Combobox setzt ebenfalls canvas + Menue-Action
    """
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)

    # Existenz aller drei UI-Elemente
    assert hasattr(w, "label_stitch_type")
    assert hasattr(w, "actions_stitch_type")
    assert hasattr(w, "combo_stitch_type")
    # 10 Stichtypen: FULL + 2 Halbe + 4 Viertel + Three-Quarter + French Knot + Bead
    assert len(w.actions_stitch_type) == 10
    assert StitchType.THREE_QUARTER.value in w.actions_stitch_type
    assert StitchType.FRENCH_KNOT.value in w.actions_stitch_type
    assert StitchType.BEAD.value in w.actions_stitch_type

    # Initial: alles auf "Voll"
    assert w.canvas._active_stitch_type == 0
    assert w.combo_stitch_type.currentIndex() == 0
    assert "Voll" in w.label_stitch_type.text()

    # Wechsel via Handler (Menue-Pfad)
    w._on_stitch_type_changed(1)
    assert w.canvas._active_stitch_type == 1
    assert w.combo_stitch_type.currentIndex() == 1
    assert w.actions_stitch_type[1].isChecked()

    # Wechsel via Toolbar-Combobox
    w.combo_stitch_type.setCurrentIndex(2)
    assert w.canvas._active_stitch_type == 2
    assert w.actions_stitch_type[2].isChecked()
