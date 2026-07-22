# -*- coding: utf-8 -*-
"""
Regressionstests (Runde 20) für zwei Bugs in PatternLibraryDialog:

1. _update_category_list() sprang nach JEDER Aktion (Favorit umschalten,
   Kategorie umschalten, Eintrag entfernen, ...) stumm auf "Alle" zurueck,
   statt die gerade aktive Kategorie-Ansicht (z.B. "Favoriten") beizubehalten.
2. _notes_save_timer (500ms debounced) wurde beim Wechsel des ausgewaehlten
   Eintrags oder beim Schliessen des Dialogs NICHT geflusht -- ein Notiz-Edit
   innerhalb des Debounce-Fensters ging dadurch verloren bzw. wurde dem
   FALSCHEN (neu ausgewaehlten) Eintrag zugeschrieben.

Nutzt dasselbe QSettings-Isolationsmuster wie test_files_settings_wiring.py
(library_path auf tmp_path umbiegen), damit kein Test die echte Bibliothek
des Nutzers beruehrt.
"""

from PySide6.QtCore import QCoreApplication, QSettings


def _qsettings_with_scope():
    app = QCoreApplication.instance()
    app.setOrganizationName("PySticky")
    app.setApplicationName("PySticky")
    return QSettings()


def _make_dialog(qtbot, tmp_path):
    from pysticky.ui.dialogs.pattern_library_dialog import PatternLibraryDialog

    s = _qsettings_with_scope()
    old = s.value("library_path")
    custom_dir = tmp_path / "bibliothek"
    s.setValue("library_path", str(custom_dir))
    dlg = PatternLibraryDialog()
    qtbot.addWidget(dlg)

    def _restore():
        if old is None:
            s.remove("library_path")
        else:
            s.setValue("library_path", old)

    return dlg, _restore


def _make_entry(name: str, favorite: bool = False):
    from pysticky.ui.dialogs.pattern_library_data import LibraryEntry

    return LibraryEntry(
        filepath=f"{name}.pxs",
        name=name,
        width=10,
        height=10,
        color_count=1,
        stitch_count=10,
        favorite=favorite,
    )


def test_category_selection_survives_toggle_favorite(qtbot, tmp_path):
    dlg, restore = _make_dialog(qtbot, tmp_path)
    try:
        entry = _make_entry("Blume", favorite=True)
        dlg._library.entries.append(entry)
        dlg._update_category_list()

        fav_row = dlg._library.categories.index("Favoriten")
        dlg._category_list.setCurrentRow(fav_row)
        assert dlg._category_list.currentRow() == fav_row

        dlg._toggle_favorite(entry)

        assert dlg._category_list.currentRow() == fav_row
        assert dlg._category_list.currentItem().text().startswith("Favoriten")
    finally:
        restore()


def test_category_selection_survives_remove_entry(qtbot, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    dlg, restore = _make_dialog(qtbot, tmp_path)
    try:
        entry_a = _make_entry("A", favorite=True)
        entry_b = _make_entry("B", favorite=True)
        dlg._library.entries.extend([entry_a, entry_b])
        dlg._update_category_list()

        fav_row = dlg._library.categories.index("Favoriten")
        dlg._category_list.setCurrentRow(fav_row)

        monkeypatch.setattr(
            QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Yes
        )
        dlg._remove_entry(entry_a)

        assert dlg._category_list.currentRow() == fav_row
    finally:
        restore()


def test_notes_flushed_before_switching_selected_entry(qtbot, tmp_path):
    dlg, restore = _make_dialog(qtbot, tmp_path)
    try:
        entry_a = _make_entry("A")
        entry_b = _make_entry("B")
        dlg._library.entries.extend([entry_a, entry_b])

        dlg._on_thumbnail_clicked(entry_a)
        dlg._notes_edit.setPlainText("Neue Notiz fuer A")
        dlg._on_notes_changed()
        assert dlg._notes_save_timer.isActive()

        # Wechsel zu B, BEVOR der 500ms-Timer natuerlich abgelaufen waere.
        dlg._on_thumbnail_clicked(entry_b)

        assert entry_a.notes == "Neue Notiz fuer A"
        assert not dlg._notes_save_timer.isActive()
    finally:
        restore()


def test_notes_flushed_on_close(qtbot, tmp_path):
    dlg, restore = _make_dialog(qtbot, tmp_path)
    try:
        entry = _make_entry("A")
        dlg._library.entries.append(entry)

        dlg._on_thumbnail_clicked(entry)
        dlg._notes_edit.setPlainText("Letzte Aenderung vor dem Schliessen")
        dlg._on_notes_changed()
        assert dlg._notes_save_timer.isActive()

        dlg.close()

        assert entry.notes == "Letzte Aenderung vor dem Schliessen"
    finally:
        restore()


def test_generate_thumbnail_survives_deleted_widget(qtbot, monkeypatch):
    """thumbnail_widget.py: RuntimeError aus setPixmap() auf einem bereits
    deleteLater()'d Label darf nicht unkontrolliert propagieren."""
    from pysticky.core import Pattern
    from pysticky.ui.dialogs.thumbnail_widget import ThumbnailWidget

    entry = _make_entry("Dummy")
    widget = ThumbnailWidget(entry)
    qtbot.addWidget(widget)

    fake_pattern = Pattern(width=5, height=5)
    monkeypatch.setattr(
        "pysticky.ui.dialogs.thumbnail_widget.load_pattern", lambda path: fake_pattern
    )

    def _raise_runtime_error(*args, **kwargs):
        raise RuntimeError("wrapped C/C++ object of type QLabel has been deleted")

    monkeypatch.setattr(widget._thumb_label, "setPixmap", _raise_runtime_error)

    widget._generate_thumbnail()  # darf NICHT raisen
