# -*- coding: utf-8 -*-
"""Regressionstests für den Dateien-Settings-Tab (2026-07-18): 6 von 11
Einstellungen waren totes UI (default_path, library_path, templates_path,
import_max_colors, dither_method, pdf_cells_per_page). pdf_quality und
html_inline_css wurden entfernt -- kein Ziel im Export-Code (PDF ist rein
vektorbasiert ohne Rasterung, HTML-CSS ist bereits immer inline)."""

from PySide6.QtCore import QSettings


def _qsettings_with_scope():
    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    return QSettings()


def test_library_path_uses_configured_folder(qtbot, tmp_path):
    from pysticky.ui.dialogs.pattern_library_dialog import PatternLibraryDialog

    s = _qsettings_with_scope()
    old = s.value("library_path")
    custom_dir = tmp_path / "meine_bibliothek"
    try:
        s.setValue("library_path", str(custom_dir))
        dlg = PatternLibraryDialog()
        qtbot.addWidget(dlg)
        assert custom_dir.is_dir()
        assert dlg._library_path.parent == custom_dir
    finally:
        if old is None:
            s.remove("library_path")
        else:
            s.setValue("library_path", old)


def test_templates_path_uses_configured_folder(tmp_path):
    from pysticky.ui.dialogs.user_template_dialog import get_templates_path

    s = _qsettings_with_scope()
    old = s.value("templates_path")
    custom_dir = tmp_path / "meine_vorlagen"
    try:
        s.setValue("templates_path", str(custom_dir))
        result = get_templates_path()
        assert result == custom_dir
        assert custom_dir.is_dir()
    finally:
        if old is None:
            s.remove("templates_path")
        else:
            s.setValue("templates_path", old)


def test_default_path_used_as_dialog_start_dir(qtbot, tmp_path):
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old = s.value("default_path")
    try:
        s.setValue("default_path", str(tmp_path))
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()
        assert w._default_file_dialog_dir() == str(tmp_path)
    finally:
        if old is None:
            s.remove("default_path")
        else:
            s.setValue("default_path", old)


def test_default_path_falls_back_to_empty_when_folder_missing(qtbot, tmp_path):
    from pysticky.ui.main_window import MainWindow

    s = _qsettings_with_scope()
    old = s.value("default_path")
    try:
        s.setValue("default_path", str(tmp_path / "existiert_nicht"))
        w = MainWindow()
        qtbot.addWidget(w)
        w._check_save_changes = lambda: True
        w._autosave_timer.stop()
        assert w._default_file_dialog_dir() == ""
    finally:
        if old is None:
            s.remove("default_path")
        else:
            s.setValue("default_path", old)


def test_import_dialog_applies_configured_defaults(qtbot):
    from pysticky.ui.dialogs import ImageImportDialog

    s = _qsettings_with_scope()
    old_colors = s.value("import_max_colors")
    old_dither = s.value("dither_method")
    try:
        s.setValue("import_max_colors", 12)
        s.setValue("dither_method", 2)
        dlg = ImageImportDialog()
        qtbot.addWidget(dlg)
        assert dlg.spin_colors.value() == 12
        assert dlg.combo_dithering.currentIndex() == 2
    finally:
        if old_colors is None:
            s.remove("import_max_colors")
        else:
            s.setValue("import_max_colors", old_colors)
        if old_dither is None:
            s.remove("dither_method")
        else:
            s.setValue("dither_method", old_dither)


def test_pdf_exporter_cells_per_page_overrides_format_default(empty_pattern):
    """PDFExporter selbst wendet cells_per_page an, wenn übergeben (die
    Sicherheits-Beschränkung auf A4/Letter sitzt bewusst eine Ebene höher
    in export_handlers.py, nicht hier -- PDFExporter bleibt eine simple,
    unconditional API)."""
    from pysticky.io.pdf_export import PDFExporter

    default_exporter = PDFExporter(empty_pattern, page_format="A4")
    assert default_exporter.STITCHES_PER_PAGE_X == 40

    custom_exporter = PDFExporter(empty_pattern, page_format="A4", cells_per_page=25)
    assert custom_exporter.STITCHES_PER_PAGE_X == 25
    assert custom_exporter.STITCHES_PER_PAGE_Y == 25


def test_pdf_page_formats_keep_their_own_defaults():
    """A3/A2/A1/A0 haben groessere Format-Standards als A4 -- diese Zahlen
    duerfen sich nicht veraendert haben (die Absicherung gegen ein
    versehentliches Ueberschreiben lebt in export_handlers.py:
    pdf_cells_per_page wird nur fuer page_format in (A4, Letter) gelesen)."""
    from pysticky.io.pdf_export import PDFExporter

    for fmt, expected_default in [
        ("A4", 40),
        ("Letter", 40),
        ("A3", 60),
        ("A2", 90),
        ("A1", 130),
        ("A0", 190),
    ]:
        assert PDFExporter.PAGE_FORMATS[fmt]["stitches_x"] == expected_default
