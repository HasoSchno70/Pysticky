"""
Export-Handler fuer MainWindow.

Enthaelt den ExportWorker (laufender QThread fuer PDF/HTML) sowie die
Menue-Slots fuer PDF-, HTML- und Bild-Export.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog

if TYPE_CHECKING:
    from ...core import Pattern
    from ..main_window import MainWindow


class ExportWorker(QObject):
    """Worker fuer Hintergrund-Export (PDF/HTML)."""

    finished = Signal(bool, str)  # success, message
    start_export = Signal(str, str, str, str)  # export_type, filepath, page_format, notes

    def __init__(
        self,
        pattern: "Pattern",
        cross_ref_palettes: list[str] | None = None,
        page_overlap_stitches: int = 0,
        pdf_protection: dict | None = None,
    ) -> None:
        super().__init__()
        self._pattern = pattern
        self._cross_ref_palettes = cross_ref_palettes or []
        self._page_overlap = max(0, int(page_overlap_stitches))
        self._pdf_protection = pdf_protection or {}

    def _run_export(
        self, export_type: str, filepath: str, page_format: str, notes: str = ""
    ) -> None:
        """Fuehrt den Export im Hintergrund aus."""
        try:
            if export_type == "pdf":
                from ...io import PDFExporter

                exporter = PDFExporter(
                    self._pattern,
                    page_format=page_format,
                    notes=notes,
                    cross_ref_palettes=self._cross_ref_palettes,
                    page_overlap_stitches=self._page_overlap,
                    password=self._pdf_protection.get("password"),
                    watermark_text=self._pdf_protection.get("watermark_text"),
                    allow_printing=self._pdf_protection.get("allow_printing", True),
                    allow_copying=self._pdf_protection.get("allow_copying", True),
                )
                success = exporter.export(filepath)
            elif export_type == "html":
                from ...io import HTMLExporter

                exporter = HTMLExporter(
                    self._pattern,
                    cross_ref_palettes=self._cross_ref_palettes,
                    page_overlap_stitches=self._page_overlap,
                )
                success = exporter.export(filepath)
            elif export_type == "bundle":
                from ...io import export_bundle

                # page_format wird hier als PDF-Format weitergegeben
                result = export_bundle(
                    self._pattern,
                    filepath,
                    pdf_page_format=page_format or "A4",
                )
                # Skipped-Komponenten in der Status-Message zurueckgeben,
                # damit der User merkt wenn z.B. PDF fehlte.
                msg = filepath
                if result["skipped"]:
                    msg = filepath + " | übersprungen: " + ", ".join(result["skipped"])
                self.finished.emit(True, msg)
                return
            else:
                self.finished.emit(False, f"Unbekannter Exporttyp: {export_type}")
                return

            if success:
                self.finished.emit(True, filepath)
            else:
                self.finished.emit(False, "Export fehlgeschlagen.")
        except Exception as e:  # catch-all: export may fail in many ways
            self.finished.emit(False, str(e))


class ExportHandlersMixin:
    """Mixin fuer PDF-, HTML- und Bild-Export."""

    def _on_export_html(self: "MainWindow") -> None:
        """Exportiert das Muster als HTML im Hintergrund-Thread."""
        default_name = ""
        if self.current_file:
            default_name = self.current_file.stem + ".html"
        elif self.current_pattern.name:
            default_name = self.current_pattern.name + ".html"

        path, _ = QFileDialog.getSaveFileName(
            self, "Als HTML exportieren", default_name, "HTML-Dateien (*.html);;Alle (*.*)"
        )

        if path:
            self.status_bar.showMessage("Erstelle HTML...", 0)
            self._start_export_worker("html", path, "")

    def _on_export_pdf(self: "MainWindow") -> None:
        """Exportiert das Muster als PDF im Hintergrund-Thread."""
        from PySide6.QtWidgets import QInputDialog

        from ...io import PDFExporter, check_reportlab_available

        if not check_reportlab_available():
            QMessageBox.warning(
                self,
                "PDF-Export nicht verfuegbar",
                "PDF-Export benoetigt die Bibliothek 'reportlab'.\n\n"
                "Bitte installieren mit:\n"
                "pip install reportlab\n\n"
                "Alternativ koennen Sie den HTML-Export nutzen und\n"
                "im Browser als PDF drucken.",
            )
            return

        # Papierformat-Auswahl. Im DP-Modus markieren wir das empfohlene
        # Format mit einem ✓ und waehlen es vor, damit der User die 1:1-
        # Klebefolie auf moeglichst wenigen Seiten erhaelt.
        from ...io.export_common import (
            is_diamond_mode,
            recommend_paper_format_for_dp,
        )

        dp_mode = is_diamond_mode(self.current_pattern)
        recommended = recommend_paper_format_for_dp(self.current_pattern) if dp_mode else None

        formats = list(PDFExporter.PAGE_FORMATS.keys())
        format_labels = []
        for name in formats:
            fmt = PDFExporter.PAGE_FORMATS[name]
            pw, ph = fmt["pagesize"]
            pw_mm = pw / (72 / 25.4)
            ph_mm = ph / (72 / 25.4)
            marker = " ✓ empfohlen für 1:1" if name == recommended else ""
            if dp_mode:
                # Im DP-Modus: zeige wie viele Drills bei 1:1 pro Seite passen
                from ...io.export_common import drill_pitch_mm

                pitch = drill_pitch_mm(self.current_pattern)
                margin_mm = fmt["margin"]
                width_reserve_mm = 12.0
                height_reserve_mm = 50.0
                drills_x = max(1, int((pw_mm - 2 * margin_mm - width_reserve_mm) / pitch))
                drills_y = max(1, int((ph_mm - 2 * margin_mm - height_reserve_mm) / pitch))
                import math

                px = math.ceil(self.current_pattern.width / drills_x)
                py = math.ceil(self.current_pattern.height / drills_y)
                format_labels.append(
                    f"{name} ({pw_mm:.0f}×{ph_mm:.0f} mm, "
                    f"~{drills_x}×{drills_y} Drills/Seite → {px * py} Seiten){marker}"
                )
            else:
                format_labels.append(
                    f"{name} ({pw_mm:.0f}×{ph_mm:.0f} mm, "
                    f"{fmt['stitches_x']}×{fmt['stitches_y']} Stiche/Seite)"
                )

        default_idx = formats.index(recommended) if recommended in formats else 0

        chosen, ok = QInputDialog.getItem(
            self,
            "Papierformat",
            (
                "Papierformat fuer den DP-Export (1:1-Massstab):"
                if dp_mode
                else "Papierformat fuer den PDF-Export:"
            ),
            format_labels,
            default_idx,
            False,
        )
        if not ok:
            return

        page_format = formats[format_labels.index(chosen)]

        # Optionale Notizen — Default = die persistenten Pattern-Notizen
        # (aus Eigenschaften-Dialog) oder die letzten PDF-spezifischen Notizen.
        default_notes = self.current_pattern.metadata.get(
            "notes", ""
        ) or self.current_pattern.metadata.get("pdf_notes", "")
        notes, ok_notes = QInputDialog.getMultiLineText(
            self,
            "PDF-Notizen",
            "Optionale Notizen fuer das PDF (leer lassen zum Ueberspringen):",
            default_notes,
        )
        if not ok_notes:
            return
        self.current_pattern.metadata["pdf_notes"] = notes

        # PDF-Schutz-Dialog (optional)
        from ..dialogs import PdfProtectDialog

        protect = PdfProtectDialog(self)
        if protect.exec() != PdfProtectDialog.DialogCode.Accepted:
            return

        default_name = ""
        if self.current_file:
            default_name = self.current_file.stem + ".pdf"
        elif self.current_pattern.name:
            default_name = self.current_pattern.name + ".pdf"

        path, _ = QFileDialog.getSaveFileName(
            self, "Als PDF exportieren", default_name, "PDF-Dateien (*.pdf);;Alle (*.*)"
        )

        if path:
            self.status_bar.showMessage(f"Erstelle PDF ({page_format})...", 0)
            self._pending_pdf_protection = {
                "password": protect.password,
                "watermark_text": protect.watermark,
                "allow_printing": protect.allow_printing,
                "allow_copying": protect.allow_copying,
            }
            self._start_export_worker("pdf", path, page_format, notes)

    def _on_export_image(self: "MainWindow") -> None:
        """Exportiert das Muster als Rasterbild (PNG/JPG/BMP)."""
        from PySide6.QtWidgets import (
            QCheckBox,
            QDialog,
            QDialogButtonBox,
            QHBoxLayout,
            QLabel,
            QSpinBox,
            QVBoxLayout,
        )

        # Optionen-Dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("Bild-Export Optionen")
        layout = QVBoxLayout(dlg)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Pixelgroesse pro Stich:"))
        spin_cell = QSpinBox()
        spin_cell.setRange(4, 100)
        spin_cell.setValue(10)
        row1.addWidget(spin_cell)
        layout.addLayout(row1)

        chk_grid = QCheckBox("Rasterlinien anzeigen")
        chk_grid.setChecked(True)
        layout.addWidget(chk_grid)

        chk_symbols = QCheckBox("Symbole anzeigen")
        layout.addWidget(chk_symbols)

        size_label = QLabel()

        def _update_size():
            cs = spin_cell.value()
            w = self.current_pattern.width * cs
            h = self.current_pattern.height * cs
            size_label.setText(f"Bildgroesse: {w} x {h} Pixel")

        spin_cell.valueChanged.connect(_update_size)
        _update_size()
        layout.addWidget(size_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        cell_size = spin_cell.value()
        show_grid = chk_grid.isChecked()
        show_symbols = chk_symbols.isChecked()

        default_name = ""
        if self.current_file:
            default_name = self.current_file.stem + ".png"
        elif self.current_pattern.name:
            default_name = self.current_pattern.name + ".png"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Als Bild exportieren",
            default_name,
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp);;Alle (*.*)",
        )
        if not path:
            return

        from ...io import ImageExporter

        exporter = ImageExporter(self.current_pattern)
        try:
            exporter.export(
                path, cell_size=cell_size, show_grid=show_grid, show_symbols=show_symbols
            )
            self.status_bar.showMessage(f"Bild exportiert: {path}", 5000)
        except Exception as e:  # noqa: BLE001 - Fehlerdetail dem User zeigen
            QMessageBox.critical(self, "Fehler", f"Bild-Export fehlgeschlagen:\n{e}")

    def _on_export_oxs(self: "MainWindow") -> None:
        """Exportiert das Muster als OXS (Open Cross Stitch XML)."""
        from ...io.formats import OXSExportError, export_oxs

        default_name = ""
        if self.current_file:
            default_name = self.current_file.stem + ".oxs"
        elif self.current_pattern.name:
            default_name = self.current_pattern.name + ".oxs"

        path, _ = QFileDialog.getSaveFileName(
            self, "Als OXS exportieren", default_name, "Open Cross Stitch (*.oxs);;Alle (*.*)"
        )
        if not path:
            return

        try:
            export_oxs(self.current_pattern, path)
            self.status_bar.showMessage(f"OXS exportiert: {path}", 5000)
        except OXSExportError as e:
            QMessageBox.critical(self, "OXS-Export fehlgeschlagen", str(e))

    def _on_export_bundle(self: "MainWindow") -> None:
        """Exportiert ein komplettes Bundle (.pxs + html + png + pdf + Garnliste) als ZIP."""
        default_name = ""
        if self.current_file:
            default_name = self.current_file.stem + "_bundle.zip"
        elif self.current_pattern.name:
            default_name = self.current_pattern.name + "_bundle.zip"

        path, _ = QFileDialog.getSaveFileName(
            self, "Als Bundle exportieren", default_name, "ZIP-Dateien (*.zip);;Alle (*.*)"
        )
        if not path:
            return

        self.status_bar.showMessage("Erstelle Bundle…", 0)
        # page_format = A4 als Default fuer das enthaltene PDF
        self._start_export_worker("bundle", path, "A4")

    def _start_export_worker(
        self: "MainWindow",
        export_type: str,
        filepath: str,
        page_format: str,
        notes: str = "",
    ) -> None:
        """Startet den Export im Hintergrund-Thread."""
        from PySide6.QtCore import Qt

        labels = {"pdf": "PDF", "html": "HTML", "bundle": "Bundle"}
        export_label = labels.get(export_type, export_type.upper())
        # Default-Dialog ist zu klein — Label-Text wird abgeschnitten und
        # der Busy-Indikator (Indeterminate-Bar) ist nicht sichtbar. Wir
        # setzen eine explizite Mindestbreite und einen sprechenden Text,
        # damit der User sieht, dass das Programm arbeitet.
        progress_msg = (
            f"{export_label}-Export wird erstellt — "
            f"bei grossen Mustern kann das einige Sekunden dauern."
        )
        self._export_progress = QProgressDialog(progress_msg, None, 0, 0, self)
        self._export_progress.setWindowTitle(f"{export_label}-Export")
        self._export_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._export_progress.setMinimumDuration(0)
        self._export_progress.setCancelButton(None)
        self._export_progress.setMinimumWidth(420)
        self._export_progress.setMinimumHeight(110)
        self._export_progress.show()
        # processEvents damit der Dialog SOFORT erscheint statt erst wenn
        # der Worker bereits laeuft.
        from PySide6.QtWidgets import QApplication

        QApplication.processEvents()

        # Cross-Reference-Paletten + Page-Overlap aus Settings holen
        from PySide6.QtCore import QSettings

        s = QSettings()
        cross_ref_csv = s.value("export/cross_ref_palettes", "", type=str)
        cross_ref_palettes = [p.strip() for p in cross_ref_csv.split(",") if p.strip()]
        page_overlap = s.value("export/page_overlap_stitches", 0, type=int)

        # PDF-Schutz aus dem letzten _on_export_pdf-Aufruf (None wenn HTML/Bundle)
        pdf_protection = getattr(self, "_pending_pdf_protection", None) or {}
        # Verbrauchen — naechste Export-Runde startet ohne Schutz, falls
        # nicht erneut konfiguriert.
        self._pending_pdf_protection = None

        self._export_thread = QThread()
        self._export_worker = ExportWorker(
            self.current_pattern,
            cross_ref_palettes=cross_ref_palettes,
            page_overlap_stitches=page_overlap,
            pdf_protection=pdf_protection,
        )
        self._export_worker.moveToThread(self._export_thread)

        # QueuedConnection: Slot laeuft im Worker-Thread
        self._export_worker.start_export.connect(
            self._export_worker._run_export, Qt.ConnectionType.QueuedConnection
        )
        self._export_worker.finished.connect(
            self._on_export_finished, Qt.ConnectionType.QueuedConnection
        )
        self._export_thread.finished.connect(self._export_thread.deleteLater)

        self._pending_export_type = export_type
        self._pending_export_path = filepath

        self._export_thread.start()
        self._export_worker.start_export.emit(export_type, filepath, page_format, notes)

    def _on_export_finished(self: "MainWindow", success: bool, message: str) -> None:
        """Callback wenn Export abgeschlossen."""
        export_type = getattr(self, "_pending_export_type", "")

        progress = getattr(self, "_export_progress", None)
        if progress:
            progress.close()
            self._export_progress = None
        filepath = getattr(self, "_pending_export_path", "")

        thread = getattr(self, "_export_thread", None)
        if thread and thread.isRunning():
            self._export_thread.quit()
            self._export_thread.wait(2000)
        self._export_worker = None
        self._export_thread = None

        labels = {"pdf": "PDF", "html": "HTML", "bundle": "Bundle"}
        label = labels.get(export_type, export_type.upper())

        if success:
            self.status_bar.showMessage(f"{label} exportiert: {message}", 5000)
            if export_type == "pdf":
                reply = QMessageBox.question(
                    self,
                    "Export erfolgreich",
                    "Das Muster wurde als PDF exportiert.\n\nMoechten Sie die Datei oeffnen?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    import os

                    if os.name == "nt":
                        os.startfile(filepath)
                    else:
                        os.system(f'xdg-open "{filepath}"')
            elif export_type == "html":
                reply = QMessageBox.question(
                    self,
                    "Export erfolgreich",
                    "Das Muster wurde als HTML exportiert.\n\n"
                    "Moechten Sie die Datei im Browser oeffnen?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    import webbrowser

                    webbrowser.open(filepath)
            elif export_type == "bundle":
                # Den Ordner anzeigen, wo das ZIP liegt — User will meist die Datei finden
                reply = QMessageBox.question(
                    self,
                    "Bundle erstellt",
                    "Bundle gespeichert.\n\nMoechten Sie den Ordner oeffnen?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    import os
                    from pathlib import Path

                    folder = str(Path(filepath).parent)
                    if os.name == "nt":
                        os.startfile(folder)
                    else:
                        os.system(f'xdg-open "{folder}"')
        else:
            self.status_bar.showMessage("Export fehlgeschlagen.", 5000)
            QMessageBox.critical(self, "Fehler", f"{label}-Export fehlgeschlagen:\n{message}")
