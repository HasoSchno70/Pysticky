# -*- coding: utf-8 -*-
"""
Regressionstest (Autosave-/Recovery-Robustheit-Audit): _perform_start_action()
ruft _check_autosave_recovery() bewusst ZUERST auf (Kommentar: "falls Recovery
passiert ist, wurde set_pattern() bereits aufgerufen"), aber der Zweig fuer
start_action==2 ("Letzte Datei oeffnen") ignorierte das Ergebnis komplett:

    elif start_action == 2:
        opened = False
        if self._recent_files:
            last_file = self._recent_files[0]
            if Path(last_file).exists():
                self._unsaved_changes = False   # <-- loescht das Recovery-Flag
                self._open_recent_file(last_file)  # <-- ueberschreibt das Pattern
                opened = True

Im Gegensatz zu start_action==0/1/3 (die alle `_already_loaded()` respektieren,
was `_unsaved_changes` mit einschliesst) wurde hier `_unsaved_changes` VOR dem
Oeffnen der letzten Datei hart auf False gesetzt und `_open_recent_file()`
bedingungslos aufgerufen. `_open_recent_file()` ruft intern `_check_save_
changes()` auf, das bei `_unsaved_changes == False` sofort True zurueckgibt
(kein Abfrage-Dialog) -- ein Nutzer, der beim Start "Ja, Autosave
wiederherstellen" anklickt, bekam sein gerade wiederhergestelltes,
UNGESPEICHERTES Pattern im selben Atemzug wieder stillschweigend durch die
zuletzt genutzte Datei ersetzt, ohne jede Rueckfrage -- Datenverlust trotz
expliziter Nutzerbestaetigung.

Fix: der start_action==2-Zweig prueft jetzt genau wie die anderen Zweige
`_already_loaded()`, bevor er die letzte Datei oeffnet.
"""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from pysticky.ui.handlers.autosave_handlers import AutosaveHandlersMixin

# Referenz auf die ECHTE Methode, eingesammelt beim Modul-Import -- also
# BEVOR die autouse-Fixture `_no_autosave_side_effects` sie durch ein No-Op
# ersetzt (siehe tests/test_autosave_recovery.py fuer das gleiche Muster).
_REAL_CHECK_AUTOSAVE_RECOVERY = AutosaveHandlersMixin._check_autosave_recovery


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


def test_recent_file_start_action_does_not_discard_autosave_recovery(
    main_window, monkeypatch, tmp_path
):
    """Bestaetigte Autosave-Recovery beim Start darf nicht durch die
    Start-Aktion "Letzte Datei oeffnen" stillschweigend wieder verworfen
    werden."""
    import tempfile

    from pysticky.core import Pattern, save_pattern

    w = main_window
    monkeypatch.setattr(
        AutosaveHandlersMixin, "_check_autosave_recovery", _REAL_CHECK_AUTOSAVE_RECOVERY
    )

    # Nie gespeichertes Pattern ("current_file is None") stuerzte ab -- die
    # globale Temp-Autosave existiert.
    global_autosave_path = Path(tempfile.gettempdir()) / "pysticky_autosave.pxs"
    recovered_pattern = Pattern(name="Wiederhergestelltes Muster", width=5, height=5)
    save_pattern(recovered_pattern, global_autosave_path)

    # Eine "letzte Datei" existiert ebenfalls und wuerde durch start_action==2
    # normalerweise automatisch geoeffnet.
    last_file = tmp_path / "andere_datei.pxs"
    save_pattern(Pattern(name="Andere Datei", width=3, height=3), last_file)
    w._recent_files = [str(last_file)]

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)

    w._settings.setValue("start_action", 2)
    w._pattern_explicitly_set = False
    w.current_file = None
    w._unsaved_changes = False

    try:
        w._perform_start_action()

        assert w.current_pattern.name == "Wiederhergestelltes Muster", (
            "Regression: die Start-Aktion 'Letzte Datei oeffnen' hat das "
            "gerade per Autosave wiederhergestellte, ungespeicherte Pattern "
            "stillschweigend durch die zuletzt genutzte Datei ersetzt."
        )
        assert w.current_file is None
        assert w._unsaved_changes is True
    finally:
        if global_autosave_path.exists():
            global_autosave_path.unlink()
