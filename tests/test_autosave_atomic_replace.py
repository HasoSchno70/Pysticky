# -*- coding: utf-8 -*-
"""
Regressionstest (Autosave-/Snapshot-/Recovery-Robustheit-Audit):
_on_autosave() schrieb bisher NICHT atomar:

    if autosave_path.exists():
        autosave_path.unlink()
    temp_path.rename(autosave_path)

Das sind zwei getrennte Dateisystem-Operationen. Stuerzt der Prozess (Crash,
Stromausfall, taskkill) exakt zwischen unlink() und rename() ab, existiert
WEDER die alte Autosave-Datei (geloescht) NOCH die neue (noch nicht dorthin
umbenannt) -- obwohl die neuen, vollstaendig geschriebenen Daten bereits
komplett auf der Platte liegen (als "*.autosave.tmp"). _check_autosave_
recovery() sucht aber ausschliesslich nach dem finalen Namen, nie nach der
".tmp"-Datei -- die Autosave ist in diesem Zeitfenster faktisch komplett
verloren, obwohl die Daten physisch vorhanden waeren.

Fix: `temp_path.replace(autosave_path)` (== os.replace()) ersetzt beide
Schritte durch eine einzige atomare Betriebssystem-Operation (auf Windows
via MoveFileEx/MOVEFILE_REPLACE_EXISTING, auf POSIX via rename(2)) -- es
gibt keinen Zwischenzustand mehr, in dem beide Dateien fehlen.
"""

from pathlib import Path

import pytest


@pytest.fixture
def main_window(qtbot):
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])

    from pysticky.ui.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w._check_save_changes = lambda: True
    w._autosave_timer.stop()
    return w


def test_autosave_replace_is_a_single_atomic_operation(main_window, tmp_path, monkeypatch):
    """_on_autosave() darf die alte Autosave-Datei nicht separat loeschen,
    bevor die neue an ihren Platz kommt -- ein Crash zwischen beiden
    Operationen wuerde die Autosave komplett unsichtbar machen, obwohl die
    Daten physisch vorhanden sind. `Path.replace()` (os.replace()) macht
    daraus eine einzige, plattformuebergreifend atomare Operation."""
    from pysticky.core import Pattern, save_pattern

    w = main_window
    w.current_file = tmp_path / "mein_muster.pxs"
    w.current_pattern = Pattern(name="Aktuell", width=5, height=5)
    w._unsaved_changes = True

    autosave_path = w.current_file.with_suffix(".pxs.autosave")
    save_pattern(Pattern(name="Alter Stand", width=5, height=5), autosave_path)
    assert autosave_path.exists()

    unlink_calls: list[Path] = []
    orig_unlink = Path.unlink

    def _tracking_unlink(self, *a, **k):
        if self == autosave_path:
            unlink_calls.append(self)
        return orig_unlink(self, *a, **k)

    monkeypatch.setattr(Path, "unlink", _tracking_unlink)

    w._on_autosave()

    assert autosave_path.exists()
    assert unlink_calls == [], (
        "Regression: die alte Autosave-Datei wurde separat per unlink() "
        "entfernt statt per atomarem Path.replace() ersetzt -- das oeffnet "
        "ein Crash-Fenster, in dem weder alte noch neue Autosave existiert."
    )

    from pysticky.core import load_pattern

    recovered = load_pattern(str(autosave_path))
    assert recovered.name == "Aktuell"
