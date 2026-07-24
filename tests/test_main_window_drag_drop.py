# -*- coding: utf-8 -*-
"""
Tests fuer Datei-Drag&Drop auf das Hauptfenster (main_window.py::dragEnterEvent/
dropEvent), Runde 62 des Clean-Code-Audits.

Regression: Die manuelle "Bild importieren..."-Dateiauswahl
(``ImageImportDialog._on_browse`` in ``ui/dialogs/image_import/dialog.py``)
akzeptiert per Filter-String deutlich mehr Bildformate
(``*.webp *.tiff *.tif *.avif *.avifs`` zusaetzlich zu png/jpg/jpeg/bmp/gif)
als die Drag&Drop-Endungsliste in ``MainWindow.dragEnterEvent``/``dropEvent``.
Ein per Drag&Drop auf das Hauptfenster gezogenes ``.webp``/``.tiff``/``.tif``/
``.avif``-Bild wurde daher schon beim ``dragEnterEvent`` mit ``event.ignore()``
abgelehnt (Qt zeigt den "nicht erlaubt"-Cursor, ein Drop ist gar nicht erst
moeglich) -- obwohl genau dieses Format ueber "Datei" -> "Bild importieren..."
anstandslos importiert werden kann. Fuer den Nutzer voellig unnachvollziehbar:
identische Datei, zwei Wege, nur einer funktioniert.

Achtung Lifetime-Falle: ``QDropEvent``/``QDragEnterEvent`` speichern nur einen
Zeiger auf die uebergebene ``QMimeData`` -- die muss vom Aufrufer aktiv
referenziert bleiben, sonst wird sie von Python/PySide vorzeitig eingesammelt
und ``event.mimeData()`` liefert ein kaputtes/geloeschtes Objekt (fuehrt zu
kryptischen ``AttributeError`` oder harten Access-Violation-Abstuerzen). Die
Helper hier geben daher immer ``(event, mimedata)`` zurueck und die Tests
halten ``mimedata`` bis zum Ende des Aufrufs am Leben.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent

pytestmark = pytest.mark.usefixtures("qtbot")


def _make_main_window(qtbot):
    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._autosave_timer.stop()
    return w


def _drag_enter_event(path: str) -> tuple[QDragEnterEvent, QMimeData]:
    md = QMimeData()
    md.setUrls([QUrl.fromLocalFile(path)])
    event = QDragEnterEvent(
        QPointF(5, 5).toPoint(),
        Qt.DropAction.CopyAction,
        md,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    return event, md


def _drop_event(*paths: str) -> tuple[QDropEvent, QMimeData]:
    md = QMimeData()
    md.setUrls([QUrl.fromLocalFile(p) for p in paths])
    event = QDropEvent(
        QPointF(5, 5),
        Qt.DropAction.CopyAction,
        md,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    return event, md


@pytest.mark.parametrize(
    "filename",
    ["bild.png", "bild.jpg", "bild.jpeg", "bild.gif", "bild.bmp", "muster.pxs"],
)
def test_drag_enter_accepts_already_supported_extensions(qtbot, filename):
    """Bereits unterstuetzte Formate duerfen nicht kaputt gehen (Basisschutz)."""
    w = _make_main_window(qtbot)
    event, _md = _drag_enter_event(f"C:/tmp/{filename}")
    w.dragEnterEvent(event)
    accepted = event.isAccepted()
    assert accepted


@pytest.mark.parametrize("filename", ["bild.webp", "bild.tiff", "bild.tif", "bild.avif"])
def test_drag_enter_accepts_image_formats_supported_by_import_dialog(qtbot, filename):
    """Jedes Bildformat, das der manuelle Bildimport-Dialog anbietet
    (siehe Filter-String in ImageImportDialog._on_browse: '*.webp *.tiff
    *.tif *.avif *.avifs'), muss auch per Drag&Drop aufs Hauptfenster
    akzeptiert werden -- sonst zeigt Qt den "nicht erlaubt"-Cursor und ein
    Drop ist fuer diese Dateien gar nicht erst moeglich, obwohl sie ueber
    das Datei-Menu anstandslos importierbar sind.
    """
    w = _make_main_window(qtbot)
    event, _md = _drag_enter_event(f"C:/tmp/{filename}")
    w.dragEnterEvent(event)
    accepted = event.isAccepted()
    assert accepted, (
        f"{filename} wird vom Bildimport-Dialog unterstuetzt, aber dragEnterEvent lehnt den Drag ab"
    )


def test_drag_enter_rejects_unsupported_extension(qtbot):
    w = _make_main_window(qtbot)
    event, _md = _drag_enter_event("C:/tmp/notizen.txt")
    w.dragEnterEvent(event)
    accepted = event.isAccepted()
    assert not accepted


def test_drop_new_image_format_routes_to_image_import(qtbot, monkeypatch):
    """Nach dem Fix muss auch der eigentliche dropEvent (nicht nur
    dragEnterEvent) ein .webp konsequent als Bildimport behandeln."""
    w = _make_main_window(qtbot)
    calls: list[str] = []
    monkeypatch.setattr(w, "_on_import_image", lambda path: calls.append(path))

    event, _md = _drop_event("C:/tmp/bild.webp")
    w.dropEvent(event)

    assert calls == ["C:/tmp/bild.webp"]


def test_drop_pxs_checks_unsaved_changes_before_loading(qtbot, monkeypatch):
    """Ein per Drag&Drop abgelegtes .pxs darf ungespeicherte Aenderungen im
    aktuellen Muster nicht kommentarlos ueberschreiben."""
    w = _make_main_window(qtbot)
    checked = []
    monkeypatch.setattr(w, "_check_save_changes", lambda: checked.append(True) or False)
    loaded = []
    monkeypatch.setattr(w, "_load_pattern_file", lambda path: loaded.append(path))

    event, _md = _drop_event("C:/tmp/muster.pxs")
    w.dropEvent(event)

    assert checked == [True]
    assert loaded == [], "Bei abgelehntem Save-Check darf nicht geladen werden"


def test_drop_multiple_files_uses_first_matching_and_ignores_rest(qtbot, monkeypatch):
    """Mehrere gleichzeitig gedroppte Dateien: die erste unterstuetzte Datei
    in der Liste wird verarbeitet, der Rest wird ignoriert (kein Crash,
    kein Doppel-Import)."""
    w = _make_main_window(qtbot)
    monkeypatch.setattr(w, "_check_save_changes", lambda: True)
    loaded = []
    monkeypatch.setattr(w, "_load_pattern_file", lambda path: loaded.append(path))

    event, _md = _drop_event("C:/tmp/erstes.pxs", "C:/tmp/zweites.pxs")
    w.dropEvent(event)

    assert loaded == ["C:/tmp/erstes.pxs"]
