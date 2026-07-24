"""
Autosave-Handler für MainWindow.

Ausgelagert aus file_handlers.py, damit File-I/O- und Autosave-Logik
nicht in derselben Datei wohnen.
"""

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox

from ...core.i18n import t
from ...utils import get_logger

if TYPE_CHECKING:
    from ..main_window import MainWindow

logger = get_logger(__name__)

# Dateiname-Muster fuer die Temp-Autosave nie gespeicherter Patterns. PID-
# spezifisch, damit zwei gleichzeitig laufende Instanzen (je ein nie
# gespeichertes Pattern, z.B. zwei "Datei -> Neu"-Fenster) nicht denselben
# globalen Pfad ueberschreiben -- sonst gewinnt schlicht, wessen Autosave-
# Timer zuletzt feuert, und die andere Instanz verliert ihren Stand
# stillschweigend (kein Fehler, keine Warnung).
_TEMP_AUTOSAVE_PREFIX = "pysticky_autosave_"
_TEMP_AUTOSAVE_SUFFIX = ".pxs"
_TEMP_AUTOSAVE_GLOB = f"{_TEMP_AUTOSAVE_PREFIX}*{_TEMP_AUTOSAVE_SUFFIX}"


def _own_temp_autosave_path() -> Path:
    """Pfad der Temp-Autosave dieses Prozesses (PID-spezifisch)."""
    temp_dir = Path(tempfile.gettempdir())
    return temp_dir / f"{_TEMP_AUTOSAVE_PREFIX}{os.getpid()}{_TEMP_AUTOSAVE_SUFFIX}"


def _stale_temp_autosave_candidates(exclude: Path) -> list[Path]:
    """Findet alle Temp-Autosave-Dateien anderer (vermutlich abgestuerzter)
    Prozesse, aelteste zuerst -- falls der Nutzer mehrere Recovery-Angebote
    hintereinander mit "Ja" bestaetigt, gewinnt so am Ende der NEUESTE Stand
    (jede Bestaetigung ersetzt das gerade geladene Pattern durch das
    naechste), statt umgekehrt ein aelterer Stand einen bereits geladenen
    neueren stillschweigend zu ueberschreiben. `exclude` ist typischerweise
    der eigene PID-Pfad -- der existiert bei einem frischen Prozess noch
    nicht, wird also nie ausgefiltert. Nur im (astronomisch seltenen) Fall
    einer wiederverwendeten PID koennte hier tatsaechlich eine fremde,
    liegen gebliebene Datei ausgeschlossen werden -- die wird dann einfach
    beim naechsten Programmstart (mit garantiert anderer PID) gefunden und
    aufgeraeumt, statt sie faelschlich fuer den eigenen (nicht existenten)
    Stand zu halten."""
    temp_dir = Path(tempfile.gettempdir())

    def _mtime(p: Path) -> float:
        try:
            return p.stat().st_mtime
        except OSError:
            return 0.0

    candidates = [p for p in temp_dir.glob(_TEMP_AUTOSAVE_GLOB) if p != exclude]
    candidates.sort(key=_mtime)
    return candidates


def _offer_single_autosave_recovery(window: "MainWindow", autosave_path: Path) -> None:
    """Bietet Recovery fuer genau eine Autosave-Datei an und raeumt sie
    danach auf (unabhaengig von der Entscheidung).

    Modulfunktion statt Methode auf AutosaveHandlersMixin, damit hier kein
    weiteres `self: "MainWindow"`-Mixin-Methodensignatur-Muster entsteht
    (jede solche Methode erzeugt einen zusaetzlichen mypy-"erased type of
    self"-Fehler -- ein bekanntes, akzeptiertes Rauschen in diesem Projekt,
    das aber nicht ohne Grund weiter vermehrt werden soll)."""
    from ...core import load_pattern

    if not autosave_path.exists():
        return

    reply = QMessageBox.question(
        window,
        t("Autosave gefunden"),
        t(
            "Es wurde eine ungespeicherte Autosave-Datei gefunden.\n"
            "Möchten Sie diese wiederherstellen?"
        ),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply == QMessageBox.StandardButton.Yes:
        try:
            pattern = load_pattern(str(autosave_path))
            window.set_pattern(pattern)
            window._mark_unsaved()
            window.status_bar.showMessage(t("Autosave wiederhergestellt"), 5000)
        except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            # Bewusst breiter als load_pattern()'s eigenes Vertragsversprechen
            # (FileNotFoundError/ValueError): das ist der Recovery-Pfad, der
            # genau dann greift, wenn etwas mit der Datei nicht stimmt --
            # eine aeltere Programmversion mit inzwischen entferntem
            # Pflichtfeld, ein Systemabsturz mitten im os.replace() der
            # Autosave selbst, oder eine versehentlich umbenannte fremde
            # Datei koennten theoretisch auch andere Exception-Typen als
            # die dokumentierten ausloesen. Ein Crash beim naechsten
            # Programmstart waere hier der schlimmstmoegliche Fall (Nutzer
            # koennte PySticky gar nicht mehr oeffnen) -- also lieber
            # defensiv eine verstaendliche Fehlermeldung zeigen.
            logger.exception("Autosave-Recovery fehlgeschlagen")
            QMessageBox.warning(
                window,
                t("Fehler"),
                f"Autosave konnte nicht geladen werden:\n{e}",
            )
    # Autosave-Datei nach Entscheidung aufräumen
    try:
        autosave_path.unlink()
    except OSError:
        logger.warning("Autosave-Datei konnte nicht entfernt werden: %s", autosave_path)


class AutosaveHandlersMixin:
    """Mixin für Autosave und Recovery."""

    def _on_autosave(self: "MainWindow") -> None:
        """
        Automatisches Speichern mit sicherer Schreibstrategie.

        Schreibt zuerst in eine temporäre .autosave-Datei,
        dann wird die alte Backup-Datei erst ersetzt wenn der
        Schreibvorgang erfolgreich war.

        Erzeugt zusätzlich periodisch versionierte Snapshots
        (Datei → Versionen…) — unabhängig vom Autosave-Recovery-Punkt.
        """
        from ...core import save_pattern

        if not self._unsaved_changes:
            return

        if self.current_file:
            autosave_path = self.current_file.with_suffix(".pxs.autosave")
        else:
            autosave_path = _own_temp_autosave_path()

        temp_path = autosave_path.with_suffix(".autosave.tmp")
        try:
            save_pattern(self.current_pattern, temp_path)

            # Path.replace() (== os.replace()) statt unlink()+rename(): eine
            # einzige atomare Betriebssystem-Operation. unlink()+rename() als
            # zwei getrennte Schritte oeffnet ein Zeitfenster, in dem (nach
            # einem Crash exakt dazwischen) WEDER die alte noch die neue
            # Autosave-Datei existiert, obwohl die neuen Daten bereits
            # vollstaendig auf der Platte liegen (in temp_path) --
            # _check_autosave_recovery() sucht nur nach dem finalen Namen und
            # wuerde die Autosave in diesem Fenster faelschlich als "nicht
            # vorhanden" behandeln.
            temp_path.replace(autosave_path)

            self.status_bar.showMessage(f"Autosave: {autosave_path.name}", self._status_timeout_ms)
        except (OSError, TypeError, ValueError) as e:
            # json.dump kann auch TypeError/ValueError werfen — Autosave darf
            # die App nie crashen, aber der Fehler muss im Log sichtbar sein.
            logger.exception("Autosave fehlgeschlagen")
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                logger.warning("Autosave-Tempdatei konnte nicht entfernt werden: %s", temp_path)
            self.status_bar.showMessage(f"Autosave fehlgeschlagen: {e}", 5000)

        # Snapshot wenn überfällig (rate-limited via should_snapshot)
        self._maybe_create_snapshot()

    def _maybe_create_snapshot(self: "MainWindow") -> None:
        """Erzeugt einen versionierten Snapshot wenn der letzte > Intervall her ist."""
        from ...core.snapshots import (
            create_snapshot,
            pattern_key_for,
            should_snapshot,
        )

        key = pattern_key_for(self.current_pattern, self.current_file)
        if not should_snapshot(key):
            return
        try:
            create_snapshot(self.current_pattern, key)
        except (OSError, TypeError, ValueError):
            # Versionen sind ein "nice-to-have", nicht kritisch — aber loggen,
            # damit ein dauerhaft fehlschlagender Snapshot nicht unsichtbar bleibt.
            logger.exception("Snapshot konnte nicht erzeugt werden")

    def _check_autosave_recovery(self: "MainWindow", autosave_path: Path | None = None) -> None:
        """
        Prüft ob eine Autosave-Datei existiert und bietet Recovery an.

        Ohne Argument: prüft ALLE Temp-Autosaves nie gespeicherter Patterns
        (wird von _perform_start_action beim Start aufgerufen) -- mehrere
        koennen existieren, wenn mehrere gleichzeitig laufende Instanzen
        abgestuerzt sind (jede schreibt PID-spezifisch, siehe
        _own_temp_autosave_path()). Der eigene, gerade erst ermittelte
        PID-Pfad wird von der Suche ausgenommen, damit dieser frische
        Prozess (der garantiert noch keine eigene Autosave geschrieben hat)
        sich nicht selbst eine Recovery anbietet.
        Mit `autosave_path`: prüft die datei-spezifische `<name>.pxs.autosave`
        neben einer geöffneten Datei (wird von _load_pattern_file nach dem
        Öffnen aufgerufen — _on_autosave schreibt genau dorthin, wenn
        current_file gesetzt ist, aber vorher prüfte NICHTS diesen Pfad
        beim nächsten Öffnen wieder, die datei-spezifische Autosave war
        also faktisch nie wiederherstellbar).
        """
        if autosave_path is None:
            for candidate in _stale_temp_autosave_candidates(exclude=_own_temp_autosave_path()):
                _offer_single_autosave_recovery(self, candidate)
            return

        _offer_single_autosave_recovery(self, autosave_path)
