"""
Autosave-Handler für MainWindow.

Ausgelagert aus file_handlers.py, damit File-I/O- und Autosave-Logik
nicht in derselben Datei wohnen.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox

from ...utils import get_logger

if TYPE_CHECKING:
    from ..main_window import MainWindow

logger = get_logger(__name__)


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
            import tempfile

            temp_dir = Path(tempfile.gettempdir())
            autosave_path = temp_dir / "pysticky_autosave.pxs"

        temp_path = autosave_path.with_suffix(".autosave.tmp")
        try:
            save_pattern(self.current_pattern, temp_path)

            if autosave_path.exists():
                autosave_path.unlink()
            temp_path.rename(autosave_path)

            self.status_bar.showMessage(f"Autosave: {autosave_path.name}", 3000)
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

    def _check_autosave_recovery(self: "MainWindow") -> None:
        """
        Prüft beim Start ob eine Autosave-Datei existiert und bietet Recovery an.

        Wird von _perform_start_action aufgerufen.
        """
        import tempfile

        from ...core import load_pattern

        temp_autosave = Path(tempfile.gettempdir()) / "pysticky_autosave.pxs"

        if not temp_autosave.exists():
            return

        reply = QMessageBox.question(
            self,
            "Autosave gefunden",
            "Es wurde eine ungespeicherte Autosave-Datei gefunden.\n"
            "Moechten Sie diese wiederherstellen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                pattern = load_pattern(str(temp_autosave))
                self.set_pattern(pattern)
                self._mark_unsaved()
                self.status_bar.showMessage("Autosave wiederhergestellt", 5000)
            except (OSError, ValueError) as e:
                QMessageBox.warning(
                    self,
                    "Fehler",
                    f"Autosave konnte nicht geladen werden:\n{e}",
                )
        # Autosave-Datei nach Entscheidung aufräumen
        try:
            temp_autosave.unlink()
        except OSError:
            logger.warning("Autosave-Datei konnte nicht entfernt werden: %s", temp_autosave)
