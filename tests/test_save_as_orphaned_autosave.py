# -*- coding: utf-8 -*-
"""
Regressionstest (Autosave-/Snapshot-/Recovery-Robustheit-Audit): "Speichern
unter" liess die datei-spezifische Autosave der ALTEN Datei als Datenleiche
liegen.

Szenario: Nutzer arbeitet an "alt.pxs" (current_file). _on_autosave() legt
periodisch "alt.pxs.autosave" daneben ab. Der Nutzer macht dann "Speichern
unter" -> "neu.pxs" (current_file wechselt). "alt.pxs.autosave" wird dabei
nicht angefasst -- bleibt als veralteter Stand liegen. Oeffnet der Nutzer
spaeter irgendwann wieder "alt.pxs" (z.B. weil er parallel noch daran
weiterarbeitet, oder Monate spaeter aus Neugier), bietet _load_pattern_file()
via _check_autosave_recovery(path.with_suffix(".pxs.autosave")) faelschlich
diesen laengst ueberholten Autosave-Stand als Recovery an -- obwohl die
eigentliche Fortsetzung der Arbeit laengst unter "neu.pxs" existiert. Klickt
der Nutzer aus Gewohnheit "Ja", ueberschreibt er sein tatsaechlich aktuelles
"alt.pxs" mit veralteten Daten.

Fix: _on_save_as() raeumt die alte datei-spezifische Autosave auf, sobald der
Dateipfad wechselt (die Daten sind durch den frischen Save unter dem neuen
Namen ohnehin sicher persistiert -- die alte Autosave ist ab diesem Moment
nur noch potenziell irrefuehrend).
"""

import pytest
from PySide6.QtWidgets import QFileDialog


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
    w._settings.setValue("confirm_overwrite", False)
    w._settings.setValue("autosave_backup", False)
    return w


def test_save_as_cleans_up_old_files_sibling_autosave(main_window, monkeypatch, tmp_path):
    from pysticky.core import Pattern, save_pattern

    w = main_window

    old_path = tmp_path / "alt.pxs"
    save_pattern(Pattern(name="Alt", width=5, height=5), old_path)
    w.current_file = old_path

    # _on_autosave() legt periodisch neben der aktuellen Datei ab.
    old_autosave = old_path.with_suffix(".pxs.autosave")
    w.current_pattern = Pattern(name="Alt in Arbeit", width=5, height=5)
    w._unsaved_changes = True
    w._on_autosave()
    assert old_autosave.exists()

    new_path = tmp_path / "neu.pxs"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *a, **k: (str(new_path), "PySticky (*.pxs)")
    )

    w._on_save_as()

    assert w.current_file == new_path
    assert new_path.exists()
    assert not old_autosave.exists(), (
        "Regression: 'Speichern unter' hinterlaesst die datei-spezifische "
        "Autosave der ALTEN Datei -- sie wird spaeter beim erneuten Oeffnen "
        "von 'alt.pxs' faelschlich als Recovery angeboten, obwohl die Arbeit "
        "laengst unter 'neu.pxs' weitergefuehrt wird."
    )


def test_save_as_does_not_touch_autosave_when_never_saved_before(
    main_window, monkeypatch, tmp_path
):
    """Regressionsschutz: ohne vorherige current_file (noch nie gespeichert)
    gibt es keine datei-spezifische Autosave, die aufgeraeumt werden
    koennte -- darf nicht crashen."""
    from pysticky.core import Pattern

    w = main_window
    w.current_file = None
    w.current_pattern = Pattern(name="Neu", width=5, height=5)

    new_path = tmp_path / "frisch.pxs"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *a, **k: (str(new_path), "PySticky (*.pxs)")
    )

    w._on_save_as()

    assert w.current_file == new_path
    assert new_path.exists()
