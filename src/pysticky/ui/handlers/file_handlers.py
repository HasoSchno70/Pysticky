"""
Datei-bezogene Handler für MainWindow.

Open/Save/Import-Pfade plus direkter Druck. Export-Handler (PDF/HTML/Bild)
und Autosave wohnen in export_handlers.py bzw. autosave_handlers.py.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog, QMessageBox

from ...core.i18n import t
from ...utils import get_logger
from ..color_utils import to_qcolor

if TYPE_CHECKING:
    from ...core import Pattern
    from ..main_window import MainWindow

logger = get_logger(__name__)


class FileHandlersMixin:
    """Mixin-Klasse für Datei-Operationen."""

    def _default_file_dialog_dir(self: "MainWindow") -> str:
        """Liest den in Einstellungen → Dateien → "Speicherort" konfigurierten
        Standard-Ordner für Öffnen/Speichern-Dialoge. Leerer String (Qt-
        Default: aktuelles Arbeitsverzeichnis bzw. zuletzt genutzter Ordner)
        wenn nichts konfiguriert oder der Ordner nicht mehr existiert."""
        configured = self._settings.value("default_path", "", type=str).strip()
        if configured and Path(configured).is_dir():
            return configured
        return ""

    def _check_save_changes(self: "MainWindow") -> bool:
        """
        Prüft ob ungespeicherte Änderungen vorhanden sind.

        Returns:
            True wenn fortgefahren werden kann, False wenn abgebrochen
        """
        if not self._unsaved_changes:
            return True

        reply = QMessageBox.question(
            self,
            t("Ungespeicherte Änderungen"),
            t("Das aktuelle Muster wurde geändert.\nMöchten Sie die Änderungen speichern?"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )

        if reply == QMessageBox.StandardButton.Save:
            self._on_save()
            return not self._unsaved_changes
        elif reply == QMessageBox.StandardButton.Discard:
            return True
        return False

    def _on_new(self: "MainWindow") -> None:
        """Neues Muster erstellen mit Template-Dialog."""
        if not self._check_save_changes():
            return

        from ...core import Pattern
        from ..dialogs import NewProjectDialog

        dialog = NewProjectDialog(self)

        if dialog.exec():
            settings = dialog.get_settings()

            # Wer ein DP-Preset gewählt hat: Pattern direkt im DP-Modus
            # anlegen mit Standard-Drill-Pitch 2.5mm (fabric_count=10).
            is_dp = settings.get("dp_mode", False)
            fabric_count = 10 if is_dp else settings["fabric_count"]

            self.current_file = None
            pattern = Pattern(
                width=settings["width"],
                height=settings["height"],
                fabric_count=fabric_count,
            )
            if is_dp:
                pattern.mode = "diamond"
            pattern.color_entries.clear()

            if settings["template_name"]:
                pattern.name = settings["template_name"]

            # Ein neues Muster ganz ohne Farbe ist eine Falle: alle
            # Zeichenwerkzeuge sind sofort aktiv, verwenden aber Farbindex 0 --
            # ohne eine tatsaechlich vorhandene Farbe an diesem Index wird
            # (seit dem Farbindex-Validierungs-Fix) gar nichts gezeichnet.
            # Eine erste Farbe aus der konfigurierten Standard-Palette
            # vorzubelegen macht "Neu -> sofort loszeichnen" wieder moeglich.
            self._seed_first_color(pattern, is_dp)

            self.set_pattern(pattern)
            self._mark_saved()

            unit = "Drills" if is_dp else "Stiche"
            msg = f"Neues Muster: {settings['width']}×{settings['height']} {unit}"
            if settings["template_name"]:
                msg = f"Neues Muster: {settings['template_name']}"
            self.status_bar.showMessage(msg, self._status_timeout_ms)

    def _seed_first_color(self: "MainWindow", pattern: "Pattern", is_dp: bool) -> None:
        """Legt die erste Farbe der konfigurierten Standard-Palette ins neue
        Muster (Index 0 -- der Default-Zeichenfarbindex von Canvas/ColorBar).
        Diamond-Modus bekommt die erste verfügbare Diamond-Palette statt der
        normalen Garn-Standardpalette, da Garnfarben dort nicht als Drill
        gerendert werden."""
        from ...core import get_palette_manager

        pm = get_palette_manager()
        pm.load_all()

        if is_dp:
            palette_name = next(
                (
                    name
                    for name in sorted(pm.available_palettes)
                    if (p := pm.get_palette(name)) and p.is_diamond
                ),
                None,
            )
        else:
            palette_name = self._settings.value("default_palette", "Anchor", type=str)
            if not pm.get_palette(palette_name):
                palette_name = "Anchor"

        palette = pm.get_palette(palette_name) if palette_name else None
        if palette and palette.threads:
            pattern.add_color(palette.threads[0])

    def _on_open(self: "MainWindow") -> None:
        """Muster öffnen."""
        if not self._check_save_changes():
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            t("Muster öffnen"),
            self._default_file_dialog_dir(),
            "PySticky (*.pxs);;Alle (*.*)",
        )

        if path:
            self._load_pattern_file(path)

    def _load_pattern_file(self: "MainWindow", path: str | Path) -> bool:
        """
        Lädt eine .pxs-Datei.

        Args:
            path: Pfad zur Datei

        Returns:
            True bei Erfolg
        """
        import json

        from ...core import load_pattern

        path = Path(path)
        try:
            pattern = load_pattern(path)
            self.current_file = path
            self.set_pattern(pattern)
            self._mark_saved()
            self._add_recent_file(str(path))
            self.status_bar.showMessage(f"Geöffnet: {path}", self._status_timeout_ms)
            return True
        except FileNotFoundError:
            logger.warning("Datei nicht gefunden: %s", path)
            QMessageBox.critical(
                self, t("Datei nicht gefunden"), f"Die Datei existiert nicht:\n{path}"
            )
        except PermissionError:
            logger.warning("Zugriff verweigert: %s", path)
            QMessageBox.critical(self, t("Zugriff verweigert"), f"Keine Berechtigung:\n{path}")
        except json.JSONDecodeError as e:
            logger.exception("Datei beschädigt: %s", path)
            QMessageBox.critical(self, t("Ungültige Datei"), f"Die Datei ist beschädigt:\n{e}")
        except Exception as e:  # catch-all for unexpected format errors
            logger.exception("Datei konnte nicht geöffnet werden: %s", path)
            QMessageBox.critical(self, t("Fehler"), f"Datei konnte nicht geöffnet werden:\n{e}")
        return False

    def _load_external_pattern_file(self: "MainWindow", path: str | Path) -> bool:
        """
        Lädt eine externe Pattern-Datei (XSD, PAT, OXS) per Drag&Drop.

        Im Gegensatz zu `_load_pattern_file` wird `current_file` nicht gesetzt,
        weil das Original-Format nicht in das interne .pxs zurückgespeichert
        werden kann — der nächste Save geht in eine .pxs-Datei.
        """
        path = Path(path)
        suffix = path.suffix.lower()

        try:
            if suffix == ".oxs":
                from ...io.formats import import_oxs

                pattern, errors, warnings = import_oxs(path)
            elif suffix == ".xsd":
                from ...io.formats import import_xsd

                pattern, errors, warnings = import_xsd(path)
            elif suffix == ".pat":
                from ...io.formats import import_pat

                pattern, errors, warnings = import_pat(path)
            else:
                QMessageBox.warning(
                    self,
                    t("Nicht unterstützt"),
                    f"Dateiformat '{suffix}' wird nicht unterstützt.",
                )
                return False

            if not pattern:
                err_text = "\n".join(errors) or "Unbekannter Fehler"
                QMessageBox.critical(
                    self,
                    t("Import fehlgeschlagen"),
                    f"Die Datei konnte nicht importiert werden:\n{err_text}",
                )
                return False

            if errors:
                QMessageBox.warning(
                    self,
                    t("Import-Warnungen"),
                    f"Beim Import traten Fehler auf:\n{chr(10).join(errors)}",
                )

            self.current_file = None
            self.set_pattern(pattern)
            self._mark_unsaved()  # Nicht-Native-Datei -> als "ungespeichert" markieren
            self.status_bar.showMessage(f"Importiert: {path.name}", self._status_timeout_ms)
            return True
        except (OSError, ValueError) as e:
            logger.exception("Externer Import fehlgeschlagen: %s", path)
            QMessageBox.critical(self, t("Fehler"), f"Datei konnte nicht geöffnet werden:\n{e}")
            return False

    def _on_pattern_properties(self: "MainWindow") -> None:
        """Öffnet den Eigenschaften-Dialog für das aktuelle Muster."""
        from ..dialogs import PatternPropertiesDialog

        dialog = PatternPropertiesDialog(self.current_pattern, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        if dialog.apply_to_pattern():
            self._mark_unsaved()
            self.status_bar.showMessage(t("Eigenschaften aktualisiert"), self._status_timeout_ms)

    def _on_pattern_versions(self: "MainWindow") -> None:
        """Öffnet den Versionen-Dialog (Snapshot-History)."""
        from ..dialogs import SnapshotHistoryDialog

        dialog = SnapshotHistoryDialog(self.current_pattern, self.current_file, self)
        dialog.restore_requested.connect(self._restore_snapshot)
        dialog.exec()

    def _restore_snapshot(self: "MainWindow", path) -> None:
        """Lädt einen Snapshot-Pfad als aktuelles Muster."""
        # Ungespeicherte Änderungen werden vom Snapshot-Dialog bereits explizit
        # bestätigt — kein zweites Confirm hier.
        if not self._load_pattern_file(path):
            return
        # Datei-Kontext leeren — der Snapshot ist nicht „die Datei"
        self.current_file = None
        self._mark_unsaved()
        self._update_title()
        self.status_bar.showMessage(f"Version geladen: {path.name}", self._status_timeout_ms)

    def _on_save(self: "MainWindow") -> None:
        """Muster speichern."""
        from ...core import save_pattern

        if self.current_file:
            try:
                # Einstellungen → Allgemein → "Backup vor Überschreiben
                # erstellen": .bak ist die vorherige Datei-Version, nicht
                # das Autosave-Recovery (das ist ein separater Mechanismus).
                if (
                    self._settings.value("autosave_backup", True, type=bool)
                    and self.current_file.exists()
                ):
                    import shutil

                    backup_path = self.current_file.with_suffix(self.current_file.suffix + ".bak")
                    shutil.copy2(self.current_file, backup_path)

                save_pattern(self.current_pattern, self.current_file)
                self._mark_saved()
                self._add_recent_file(str(self.current_file))
                self.status_bar.showMessage(
                    f"Gespeichert: {self.current_file}", self._status_timeout_ms
                )
                # Bei manuellem Save ist ein Snapshot besonders wertvoll —
                # rate-limit-respektierend, damit nicht jeder Save eine Version erzeugt.
                if hasattr(self, "_maybe_create_snapshot"):
                    self._maybe_create_snapshot()
            except (OSError, TypeError, ValueError) as e:
                # json.dump wirft bei nicht-serialisierbarem Zustand TypeError/ValueError,
                # nicht nur OSError — ohne breiten Catch crasht die App beim Speichern.
                logger.exception("Speichern fehlgeschlagen")
                QMessageBox.critical(
                    self, t("Fehler"), f"Datei konnte nicht gespeichert werden:\n{e}"
                )
        else:
            self._on_save_as()

    def _on_save_as(self: "MainWindow") -> None:
        """Muster speichern unter."""
        from ...core import save_pattern

        # Default-Name aus Pattern-Name vorschlagen, damit der User nicht
        # mit einem leeren Feld konfrontiert wird (besonders nach Demo-Open).
        default_name = ""
        if self.current_pattern.name:
            import re

            safe = re.sub(r"[^a-zA-Z0-9_\- ]+", "_", self.current_pattern.name).strip()
            default_name = f"{safe}.pxs"

        default_dir = self._default_file_dialog_dir()
        initial_path = str(Path(default_dir) / default_name) if default_dir else default_name

        path, _ = QFileDialog.getSaveFileName(
            self, t("Muster speichern"), initial_path, "PySticky (*.pxs);;Alle (*.*)"
        )

        if path:
            if not path.endswith(".pxs"):
                path += ".pxs"

            # Einstellungen → Allgemein → "Vor Überschreiben warnen" --
            # zusaetzliche Sicherheitsabfrage ueber den nativen
            # Dateidialog-Schutz hinaus (der nicht auf jeder Plattform greift).
            if Path(path).exists() and self._settings.value("confirm_overwrite", True, type=bool):
                reply = QMessageBox.question(
                    self,
                    t("Überschreiben bestätigen"),
                    f"{t('Datei existiert bereits:')}\n{path}\n\n{t('Überschreiben?')}",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            try:
                save_pattern(self.current_pattern, path)
                self.current_file = Path(path)
                self.current_pattern.name = self.current_file.stem
                self._mark_saved()
                self._update_title()
                self._add_recent_file(path)
                self.status_bar.showMessage(f"Gespeichert: {path}", self._status_timeout_ms)
            except (OSError, TypeError, ValueError) as e:
                # json.dump wirft bei nicht-serialisierbarem Zustand TypeError/ValueError,
                # nicht nur OSError — ohne breiten Catch crasht die App beim Speichern.
                logger.exception("Speichern fehlgeschlagen")
                QMessageBox.critical(
                    self, t("Fehler"), f"Datei konnte nicht gespeichert werden:\n{e}"
                )

    def _on_import_image(self: "MainWindow", filepath: str | None = None) -> None:
        """Bild importieren."""
        if not self._check_save_changes():
            return

        from ..dialogs import ImageImportDialog

        prefer_diamond = bool(self.current_pattern and self.current_pattern.mode == "diamond")
        dialog = ImageImportDialog(self, prefer_diamond=prefer_diamond)
        if filepath:
            # Bild direkt laden (z.B. bei Drag & Drop)
            dialog._on_browse_with_path(filepath)
        self._exec_import_dialog(dialog, t("Bild importiert"))

    def _on_reimport_image(self: "MainWindow") -> None:
        """Bildimport des aktuellen Musters mit angepassten Einstellungen
        wiederholen (Wizard Recall) -- öffnet den Import-Dialog vorbefüllt
        mit Quellbild, Ausschnitt und Einstellungen des aktuellen Musters,
        statt bei Null anzufangen."""
        from ...core import can_change_palette

        if not self.current_pattern or not can_change_palette(self.current_pattern):
            QMessageBox.warning(
                self,
                t("Bildimport nicht möglich"),
                t(
                    "Das Muster wurde nicht aus einem Bild importiert\n"
                    "oder das Originalbild ist nicht mehr verfügbar."
                ),
            )
            return

        if not self._check_save_changes():
            return

        from ..dialogs import ImageImportDialog

        prefer_diamond = self.current_pattern.mode == "diamond"
        dialog = ImageImportDialog(
            self, prefer_diamond=prefer_diamond, seed_pattern=self.current_pattern
        )
        self._exec_import_dialog(dialog, t("Bild importiert"))

    def _on_import_xsd_pat(self: "MainWindow") -> None:
        """XSD/PAT-Datei importieren."""
        if not self._check_save_changes():
            return

        from ..dialogs import PatternImportDialog

        dialog = PatternImportDialog(self)
        self._exec_import_dialog(dialog, t("Muster importiert"))

    def _on_pattern_library(self: "MainWindow") -> None:
        """Öffnet die Muster-Bibliothek."""
        from ...core import load_pattern
        from ..dialogs import PatternLibraryDialog

        dialog = PatternLibraryDialog(self)

        def open_from_library(filepath: str):
            """Callback wenn Muster aus Bibliothek ausgewählt."""
            if not self._check_save_changes():
                return

            try:
                from pathlib import Path

                pattern_path = Path(filepath)

                # Prüfen ob XSD/PAT oder PXS
                suffix = pattern_path.suffix.lower()

                if suffix == ".pxs":
                    pattern = load_pattern(pattern_path)
                elif suffix == ".xsd":
                    from ...io.formats import import_xsd

                    pattern, errors, warnings = import_xsd(pattern_path)
                    if errors:
                        joined = "\n".join(errors)
                        QMessageBox.warning(
                            self, t("Import-Warnungen"), f"Beim Import traten Fehler auf:\n{joined}"
                        )
                elif suffix == ".pat":
                    from ...io.formats import import_pat

                    pattern, errors, warnings = import_pat(pattern_path)
                    if errors:
                        joined = "\n".join(errors)
                        QMessageBox.warning(
                            self, t("Import-Warnungen"), f"Beim Import traten Fehler auf:\n{joined}"
                        )
                elif suffix == ".oxs":
                    from ...io.formats import import_oxs

                    pattern, errors, warnings = import_oxs(pattern_path)
                    if errors:
                        joined = "\n".join(errors)
                        QMessageBox.warning(
                            self, t("Import-Warnungen"), f"Beim Import traten Fehler auf:\n{joined}"
                        )
                else:
                    QMessageBox.warning(
                        self,
                        t("Nicht unterstützt"),
                        f"Dateiformat '{suffix}' wird nicht unterstützt.",
                    )
                    return

                if pattern:
                    if suffix == ".pxs":
                        self.current_file = pattern_path
                    else:
                        self.current_file = None
                    self.set_pattern(pattern)
                    self._mark_saved()
                    self._add_recent_file(str(pattern_path))
                    self.status_bar.showMessage(
                        f"Aus Bibliothek geöffnet: {pattern_path.name}", 3000
                    )

            except (OSError, ValueError) as e:
                logger.exception("Bibliotheks-Muster konnte nicht geöffnet werden")
                QMessageBox.critical(self, t("Fehler"), f"Datei konnte nicht geöffnet werden:\n{e}")

        dialog.pattern_selected.connect(open_from_library)
        dialog.exec()

    def _on_print(self: "MainWindow") -> None:
        """Druckt das aktuelle Muster direkt."""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QColor, QFont, QPainter
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter

        from ...core import NO_STITCH

        pattern = self.current_pattern
        if not pattern:
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageOrientation(
            printer.pageLayout().Landscape
            if pattern.width > pattern.height
            else printer.pageLayout().Portrait
        )

        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle(t("Muster drucken"))
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return

        painter = QPainter()
        if not painter.begin(printer):
            QMessageBox.critical(self, t("Fehler"), t("Drucker konnte nicht geöffnet werden."))
            return

        try:
            page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
            margin = page_rect.width() * 0.05

            avail_w = page_rect.width() - 2 * margin
            avail_h = page_rect.height() - 2 * margin

            cell_size = min(avail_w / pattern.width, avail_h / pattern.height)
            offset_x = margin + (avail_w - cell_size * pattern.width) / 2
            offset_y = margin + (avail_h - cell_size * pattern.height) / 2

            composite = pattern.layer_stack.get_composite_grid()
            type_grid = pattern.layer_stack.get_composite_stitch_type_grid()
            # Lokaler Import — sonst Top-Level-Import-Schmerz für non-print Pfade
            from ...core.stitch_shapes import is_bead, is_french_knot, is_partial_stitch
            from ...io.image_export import _fill_bead, _fill_french_knot, _fill_partial_stitch

            for y in range(pattern.height):
                for x in range(pattern.width):
                    color_idx = int(composite[y, x])
                    px = offset_x + x * cell_size
                    py = offset_y + y * cell_size

                    if color_idx != NO_STITCH and 0 <= color_idx < len(pattern.color_entries):
                        entry = pattern.color_entries[color_idx]
                        c = entry.thread.color
                        color = to_qcolor(c)
                        stype = int(type_grid[y, x])

                        if is_french_knot(stype):
                            painter.fillRect(
                                QRectF(px, py, cell_size, cell_size),
                                QColor(250, 250, 245),
                            )
                            _fill_french_knot(painter, px, py, cell_size, color)
                        elif is_bead(stype):
                            painter.fillRect(
                                QRectF(px, py, cell_size, cell_size),
                                QColor(250, 250, 245),
                            )
                            _fill_bead(painter, px, py, cell_size, color)
                        elif is_partial_stitch(stype):
                            painter.fillRect(
                                QRectF(px, py, cell_size, cell_size),
                                QColor(250, 250, 245),
                            )
                            _fill_partial_stitch(painter, stype, px, py, cell_size, color)
                        else:
                            painter.fillRect(QRectF(px, py, cell_size, cell_size), color)

                        if cell_size > 8 and entry.symbol:
                            painter.setPen(QColor(0, 0, 0) if c.is_light else QColor(255, 255, 255))
                            font_size = max(4, int(cell_size * 0.6))
                            font = QFont("Segoe UI", font_size)
                            painter.setFont(font)
                            painter.drawText(
                                QRectF(px, py, cell_size, cell_size), 0x0084, entry.symbol
                            )
                    else:
                        painter.fillRect(
                            QRectF(px, py, cell_size, cell_size), QColor(250, 250, 245)
                        )

            # Grid-Linien
            painter.setPen(QColor(200, 200, 200))
            for x in range(pattern.width + 1):
                px = offset_x + x * cell_size
                painter.drawLine(
                    QRectF(px, offset_y, 0, pattern.height * cell_size).toRect().topLeft(),
                    QRectF(px, offset_y, 0, pattern.height * cell_size).toRect().bottomLeft(),
                )
            for y in range(pattern.height + 1):
                py = offset_y + y * cell_size
                painter.drawLine(
                    QRectF(offset_x, py, pattern.width * cell_size, 0).toRect().topLeft(),
                    QRectF(offset_x, py, pattern.width * cell_size, 0).toRect().topRight(),
                )

            self.status_bar.showMessage(t("Muster wurde gedruckt."), 5000)
        except Exception as e:  # catch-all: printing may fail in many ways
            QMessageBox.critical(self, t("Druckfehler"), f"Fehler beim Drucken:\n{e}")
        finally:
            painter.end()
