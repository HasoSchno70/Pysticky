# -*- coding: utf-8 -*-
"""Smoke-Test fuer den Druck-Render-Pfad — schreibt in eine PDF statt
auf einen physischen Drucker, damit wir testen koennen ohne QPrintDialog.

Pruegt den Code-Pfad aus `_on_print`, allerdings ohne den interaktiven
Dialog. Failt wenn der Render irgendwo NPE-mässig knallt oder die PDF
leer rauskommt.
"""

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtPrintSupport import QPrinter

pytestmark = pytest.mark.usefixtures("qtbot")


def _render_pattern_to_printer(pattern, printer):
    """Re-implementiert die Render-Logik aus _on_print, ohne UI."""
    from pysticky.core import NO_STITCH
    from pysticky.core.stitch_shapes import is_bead, is_french_knot, is_partial_stitch
    from pysticky.io.image_export import _fill_bead, _fill_french_knot, _fill_partial_stitch

    painter = QPainter()
    if not painter.begin(printer):
        raise RuntimeError("Drucker konnte nicht geöffnet werden")
    try:
        page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        margin = page_rect.width() * 0.05
        avail_w = page_rect.width() - 2 * margin
        avail_h = page_rect.height() - 2 * margin
        cell_size = min(avail_w / pattern.width, avail_h / pattern.height)
        offset_x = margin + (avail_w - cell_size * pattern.width) / 2
        offset_y = margin + (avail_h - cell_size * pattern.height) / 2

        composite = pattern.layer_stack.get_composite_grid()
        type_grid = pattern.layer_stack.get_composite_stitch_type_grid()

        for y in range(pattern.height):
            for x in range(pattern.width):
                color_idx = int(composite[y, x])
                px = offset_x + x * cell_size
                py = offset_y + y * cell_size
                if color_idx != NO_STITCH and 0 <= color_idx < len(pattern.color_entries):
                    entry = pattern.color_entries[color_idx]
                    c = entry.thread.color
                    color = QColor(c.r, c.g, c.b)
                    stype = int(type_grid[y, x])
                    if is_french_knot(stype):
                        _fill_french_knot(painter, px, py, cell_size, color)
                    elif is_bead(stype):
                        _fill_bead(painter, px, py, cell_size, color)
                    elif is_partial_stitch(stype):
                        _fill_partial_stitch(painter, stype, px, py, cell_size, color)
                    else:
                        painter.fillRect(QRectF(px, py, cell_size, cell_size), color)
                    if cell_size > 8 and entry.symbol:
                        painter.setPen(QColor(0, 0, 0) if c.is_light else QColor(255, 255, 255))
                        font = QFont("Segoe UI", max(4, int(cell_size * 0.6)))
                        painter.setFont(font)
                        painter.drawText(QRectF(px, py, cell_size, cell_size), 0x0084, entry.symbol)
    finally:
        painter.end()


def test_print_path_renders_to_pdf(pattern_with_stitches, tmp_path):
    """Pattern via QPrinter in PDF rendern — dient als Smoke fuer _on_print."""
    pdf_path = tmp_path / "print_smoke.pdf"
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(pdf_path))

    _render_pattern_to_printer(pattern_with_stitches, printer)
    assert pdf_path.exists(), "PDF wurde nicht erzeugt"
    assert pdf_path.stat().st_size > 1000, "PDF verdaechtig klein (Render fehlgeschlagen?)"


def test_print_path_handles_special_stitches(pattern_with_colors, tmp_path):
    """French-Knot, Bead, Partial-Stitches duerfen den Render nicht killen."""
    p = pattern_with_colors
    # Zwei Farben rumwerfen mit Sonderstichen
    layer = p.layer_stack[0]
    layer.set_stitch(2, 2, 0, stitch_type=1)  # HALF_TL_BR
    layer.set_stitch(3, 3, 0, stitch_type=2)  # HALF_TR_BL
    layer.set_stitch(4, 4, 1, stitch_type=9)  # FRENCH_KNOT
    layer.set_stitch(5, 5, 1, stitch_type=10)  # BEAD

    pdf_path = tmp_path / "special.pdf"
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(pdf_path))

    _render_pattern_to_printer(p, printer)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 500


def test_print_path_handles_empty_pattern(empty_pattern, tmp_path):
    """Leeres Pattern — Render darf nicht crashen, PDF-Datei darf leer-ish sein."""
    pdf_path = tmp_path / "empty.pdf"
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(pdf_path))

    _render_pattern_to_printer(empty_pattern, printer)
    assert pdf_path.exists()
