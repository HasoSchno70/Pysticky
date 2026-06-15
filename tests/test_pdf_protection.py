# -*- coding: utf-8 -*-
"""Tests fuer PDF-Schutz (Password, Watermark, Print/Copy-Flags)."""

import pytest


def test_pdf_exporter_accepts_protection_params(pattern_with_stitches):
    """PDFExporter akzeptiert alle vier Protection-Parameter."""
    pytest.importorskip("reportlab")
    from pysticky.io import PDFExporter

    exp = PDFExporter(
        pattern_with_stitches,
        password="secret",
        watermark_text="DRAFT",
        allow_printing=False,
        allow_copying=False,
    )
    assert exp.password == "secret"
    assert exp.watermark_text == "DRAFT"
    assert exp.allow_printing is False
    assert exp.allow_copying is False


def test_pdf_exporter_defaults_to_no_protection(pattern_with_stitches):
    """Default: kein Passwort, kein Watermark, alles erlaubt."""
    pytest.importorskip("reportlab")
    from pysticky.io import PDFExporter

    exp = PDFExporter(pattern_with_stitches)
    assert exp.password is None
    assert exp.watermark_text is None
    assert exp.allow_printing is True
    assert exp.allow_copying is True


def test_empty_watermark_is_normalized_to_none(pattern_with_stitches):
    """Leerer/whitespace-only Watermark wird zu None."""
    pytest.importorskip("reportlab")
    from pysticky.io import PDFExporter

    assert PDFExporter(pattern_with_stitches, watermark_text="").watermark_text is None
    assert PDFExporter(pattern_with_stitches, watermark_text="   ").watermark_text is None
    assert PDFExporter(pattern_with_stitches, watermark_text="X").watermark_text == "X"


def test_empty_password_is_normalized_to_none(pattern_with_stitches):
    """Leeres Passwort wird zu None (kein Schutz)."""
    pytest.importorskip("reportlab")
    from pysticky.io import PDFExporter

    assert PDFExporter(pattern_with_stitches, password="").password is None
    assert PDFExporter(pattern_with_stitches, password=None).password is None
    assert PDFExporter(pattern_with_stitches, password="x").password == "x"


def test_pdf_export_with_password_produces_encrypted_file(pattern_with_stitches, tmp_path):
    """Mit Passwort: das PDF startet mit %PDF- (gueltig), enthaelt aber 'Encrypt'."""
    pytest.importorskip("reportlab")
    from pysticky.io import PDFExporter

    out = tmp_path / "protected.pdf"
    exp = PDFExporter(pattern_with_stitches, password="secret123")
    assert exp.export(out) is True

    # Erste Bytes pruefen — sollte ein gueltiges PDF sein
    data = out.read_bytes()
    assert data[:4] == b"%PDF"
    # Verschluesselte PDFs enthalten "/Encrypt" im Trailer
    assert b"/Encrypt" in data


def test_pdf_export_without_password_has_no_encrypt(pattern_with_stitches, tmp_path):
    """Ohne Passwort: kein /Encrypt im PDF."""
    pytest.importorskip("reportlab")
    from pysticky.io import PDFExporter

    out = tmp_path / "open.pdf"
    PDFExporter(pattern_with_stitches).export(out)
    data = out.read_bytes()
    assert data[:4] == b"%PDF"
    assert b"/Encrypt" not in data


def test_pdf_export_with_watermark_produces_valid_file(pattern_with_stitches, tmp_path):
    """Mit Watermark: PDF wird erfolgreich erstellt."""
    pytest.importorskip("reportlab")
    from pysticky.io import PDFExporter

    out = tmp_path / "watermarked.pdf"
    exp = PDFExporter(pattern_with_stitches, watermark_text="ENTWURF")
    assert exp.export(out) is True
    data = out.read_bytes()
    assert data[:4] == b"%PDF"


def test_pdf_export_with_all_protection_features(pattern_with_stitches, tmp_path):
    """Alle Schutz-Features zusammen: encrypt + watermark + allow_printing=False."""
    pytest.importorskip("reportlab")
    from pysticky.io import PDFExporter

    out = tmp_path / "fully_protected.pdf"
    exp = PDFExporter(
        pattern_with_stitches,
        password="topsecret",
        watermark_text="VERTRAULICH",
        allow_printing=False,
        allow_copying=False,
    )
    assert exp.export(out) is True
    data = out.read_bytes()
    assert data[:4] == b"%PDF"
    assert b"/Encrypt" in data


# ---------- PdfProtectDialog ----------


def test_pdf_protect_dialog_defaults(qtbot):
    """PdfProtectDialog hat sinnvolle Defaults (keine Schutz)."""
    pytest.importorskip("PySide6")
    from pysticky.ui.dialogs import PdfProtectDialog

    dialog = PdfProtectDialog()
    qtbot.addWidget(dialog)
    assert dialog.password is None
    assert dialog.watermark is None
    assert dialog.allow_printing is True
    assert dialog.allow_copying is True


def test_pdf_protect_dialog_returns_set_values(qtbot):
    """Felder werden korrekt ausgelesen."""
    pytest.importorskip("PySide6")
    from pysticky.ui.dialogs import PdfProtectDialog

    dialog = PdfProtectDialog()
    qtbot.addWidget(dialog)
    dialog.edit_password.setText("abc")
    dialog.edit_watermark.setText("DRAFT")
    dialog.chk_print.setChecked(False)
    dialog.chk_copy.setChecked(False)

    assert dialog.password == "abc"
    assert dialog.watermark == "DRAFT"
    assert dialog.allow_printing is False
    assert dialog.allow_copying is False
