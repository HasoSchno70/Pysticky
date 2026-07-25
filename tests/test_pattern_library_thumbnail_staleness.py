# -*- coding: utf-8 -*-
"""Regressionstest (Runde 80): ThumbnailWidget._load_thumbnail() cachte ein
einmal generiertes Thumbnail unter self.entry.thumbnail_path und lud es bei
jedem weiteren Anzeigen (Bibliothek neu geöffnet, Kategorie/Suche gewechselt)
einfach erneut von der Platte -- OHNE jemals zu prüfen, ob sich die
zugrundeliegende Pattern-Datei seit der Generierung geändert hat.

Szenario: Nutzer bearbeitet ein Muster aus der Bibliothek, speichert es
(gleicher Dateipfad, neuer Inhalt), öffnet die Bibliothek erneut -- das
Thumbnail zeigt weiterhin den alten Stand, weil "thumb_path.exists()" allein
als Kriterium fürs Wiederverwenden des Caches diente.

Fix: _load_thumbnail() vergleicht die mtime der Pattern-Datei mit der mtime
des gecachten Thumbnails; ist die Pattern-Datei neuer, wird der Cache als
veraltet behandelt und (wie beim allerersten Mal) per QTimer.singleShot()
neu generiert, statt den stale Cache stillschweigend weiterzuverwenden.
"""

import os
import time

from pysticky.ui.dialogs.pattern_library_data import LibraryEntry


def _make_entry(filepath: str) -> LibraryEntry:
    return LibraryEntry(
        filepath=filepath,
        name="Test",
        width=5,
        height=5,
        color_count=1,
        stitch_count=10,
    )


def test_stale_cached_thumbnail_is_regenerated_after_pattern_change(qtbot, tmp_path, monkeypatch):
    from pysticky.core import Pattern
    from pysticky.core.file_io import save_pattern
    from pysticky.ui.dialogs.thumbnail_widget import ThumbnailWidget

    pattern_file = tmp_path / "muster.pxs"
    save_pattern(Pattern(name="Muster", width=5, height=5), pattern_file)

    entry = _make_entry(str(pattern_file))
    thumb_dir = tmp_path / ".thumbnails"
    thumb_dir.mkdir()

    # Erste Generierung -- synchron statt über den 50ms-QTimer, um den Test
    # deterministisch zu halten.
    widget1 = ThumbnailWidget(entry, thumbnails_dir=thumb_dir)
    qtbot.addWidget(widget1)
    widget1._generate_thumbnail()

    assert entry.thumbnail_path is not None
    cache_path = entry.thumbnail_path
    assert os.path.exists(cache_path)

    # widget1's eigener __init__ hat (bei noch leerem Cache) bereits einen
    # QTimer.singleShot(50, self._generate_thumbnail) fuer sich selbst
    # eingeplant. PySide6 loest den Slot fuer QObject-gebundene Methoden
    # beim Feuern per Name neu auf -- ein spaeteres Monkeypatchen der
    # Klassenmethode (unten) wuerde also faelschlich AUCH diesen alten,
    # zu widget1 gehoerenden Timer umlenken und den Test verfaelschen.
    # Deshalb hier erst abwarten, bis dieser Timer abgelaufen ist (er
    # regeneriert widget1's eigenes Thumbnail ein zweites Mal, real und
    # harmlos) -- ERST DANACH die mtime als Referenz festhalten, BEVOR
    # gepatcht und widget2 erzeugt wird.
    qtbot.wait(100)
    mtime_before = os.path.getmtime(cache_path)

    # Pattern-Datei "bearbeiten": Inhalt UND mtime ändern sich (mtime der
    # Cache-Datei muss garantiert älter sein als die neue Pattern-mtime).
    time.sleep(0.05)
    os.utime(pattern_file, None)  # mtime auf "jetzt" setzen
    future = time.time() + 5
    os.utime(pattern_file, (future, future))

    # Zweites Anzeigen desselben Eintrags (z.B. Bibliothek neu geladen) --
    # muss die Regenerierung einplanen statt den stale Cache zu übernehmen.
    calls: list[bool] = []
    monkeypatch.setattr(ThumbnailWidget, "_generate_thumbnail", lambda self: calls.append(True))

    widget2 = ThumbnailWidget(entry, thumbnails_dir=thumb_dir)
    qtbot.addWidget(widget2)

    # QTimer.singleShot(50, ...) -- kurz auf das Event-Loop-Ticken warten.
    qtbot.wait(150)

    assert calls, (
        "Cache-Datei war aelter als die Pattern-Datei -- ThumbnailWidget "
        "haette eine Neu-Generierung einplanen muessen, statt den stale "
        "Cache stillschweigend weiterzuverwenden."
    )

    # Cache-Datei selbst darf durch das (gemockte) _generate_thumbnail nicht
    # anders angefasst worden sein -- reine Kontrolle, dass der Test die
    # richtige Datei prüft.
    assert os.path.getmtime(cache_path) == mtime_before
