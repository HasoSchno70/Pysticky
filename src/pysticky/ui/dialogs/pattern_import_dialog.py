"""
Dialog zum Importieren von XSD/PAT/OXS-Dateien.
"""

from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressDialog,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...config import UI_CONFIG
from ...core.i18n import t
from ...core.pattern import Pattern
from ..styles import THEME, Styles


class _PatternImportWorker(QObject):
    """Worker für Hintergrund-Musterimport."""

    finished = Signal(object, list, list, str)  # pattern, errors, warnings, format_name
    error = Signal(str)

    def __init__(self, filepath: Path) -> None:
        super().__init__()
        self._filepath = filepath

    def run(self) -> None:
        """Führt den Import im Hintergrund aus."""
        errors: list[str] = []
        warnings: list[str] = []
        suffix = self._filepath.suffix.lower()

        try:
            if suffix == ".xsd":
                from ...io.formats import import_xsd

                pattern, errors, warnings = import_xsd(self._filepath)
                format_name = "Pattern Maker (XSD)"
            elif suffix == ".pat":
                from ...io.formats import import_pat

                pattern, errors, warnings = import_pat(self._filepath)
                format_name = "PCStitch (PAT)"
            elif suffix == ".oxs":
                from ...io.formats import import_oxs

                pattern, errors, warnings = import_oxs(self._filepath)
                format_name = "Open Cross Stitch (OXS)"
            else:
                self.error.emit(f"Unbekanntes Format: {suffix}")
                return

            self.finished.emit(pattern, errors, warnings, format_name)
        except (OSError, ValueError) as e:
            self.error.emit(str(e))


class PatternImportDialog(QDialog):
    """
    Dialog zum Importieren von Pattern Maker (XSD), PCStitch (PAT)
    und Open Cross Stitch (OXS) Dateien.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("Muster importieren (XSD/PAT/OXS)"))
        self.setMinimumSize(*UI_CONFIG.dialog_min_medium)

        self._pattern: Pattern | None = None
        self._filepath: Path | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Erstellt die UI-Elemente."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Titel
        title = QLabel(t("Muster Import (XSD/PAT/OXS)"))
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {THEME.accent_primary};
        """)
        layout.addWidget(title)

        # Beschreibung
        desc = QLabel(
            t(
                "Importiere Kreuzstich-Muster aus Pattern Maker (.xsd), "
                "PCStitch (.pat) oder Open Cross Stitch (.oxs) Dateien."
            )
        )
        desc.setStyleSheet(f"color: {THEME.text_secondary};")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Dateiauswahl
        file_group = QGroupBox(t("Datei"))
        file_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_medium};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
        """)

        file_layout = QHBoxLayout(file_group)

        self._file_label = QLabel(t("Keine Datei ausgewählt"))
        self._file_label.setStyleSheet(f"""
            background: {THEME.bg_medium};
            border: 1px solid {THEME.border_dark};
            border-radius: 4px;
            padding: 8px;
            color: {THEME.text_muted};
        """)
        file_layout.addWidget(self._file_label, 1)

        browse_btn = QPushButton(t("Durchsuchen..."))
        browse_btn.setStyleSheet(Styles.button_primary())
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)

        layout.addWidget(file_group)

        # Vorschau
        preview_group = QGroupBox(t("Vorschau"))
        preview_group.setStyleSheet(file_group.styleSheet())

        preview_layout = QVBoxLayout(preview_group)

        # Preview-Frame
        preview_frame = QFrame()
        preview_frame.setFixedHeight(200)
        preview_frame.setStyleSheet(f"""
            background: {THEME.bg_medium};
            border: 1px solid {THEME.border_dark};
            border-radius: 4px;
        """)

        preview_inner = QVBoxLayout(preview_frame)

        self._preview_label = QLabel(t("Keine Vorschau verfügbar"))
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setStyleSheet(f"color: {THEME.text_muted};")
        preview_inner.addWidget(self._preview_label)

        preview_layout.addWidget(preview_frame)

        layout.addWidget(preview_group)

        # Info
        info_group = QGroupBox(t("Informationen"))
        info_group.setStyleSheet(file_group.styleSheet())

        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(8)

        self._info_labels = {}
        for key, label in [
            ("name", t("Name:")),
            ("size", t("Größe:")),
            ("colors", t("Farben:")),
            ("stitches", t("Stiche:")),
            ("format", t("Format:")),
        ]:
            value_label = QLabel("-")
            value_label.setStyleSheet(f"color: {THEME.text_secondary};")
            info_layout.addRow(label, value_label)
            self._info_labels[key] = value_label

        layout.addWidget(info_group)

        # Warnungen/Fehler
        self._messages_edit = QTextEdit()
        self._messages_edit.setReadOnly(True)
        self._messages_edit.setMaximumHeight(80)
        self._messages_edit.setStyleSheet(f"""
            background: {THEME.bg_medium};
            border: 1px solid {THEME.border_dark};
            border-radius: 4px;
            color: {THEME.text_secondary};
            font-family: monospace;
        """)
        self._messages_edit.hide()
        layout.addWidget(self._messages_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton(t("Abbrechen"))
        cancel_btn.setStyleSheet(Styles.button_secondary())
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self._import_btn = QPushButton(t("Importieren"))
        self._import_btn.setStyleSheet(Styles.button_primary())
        self._import_btn.setEnabled(False)
        self._import_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._import_btn)

        layout.addLayout(btn_layout)

    def _browse_file(self) -> None:
        """Öffnet den Datei-Dialog."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("Muster-Datei öffnen"),
            "",
            t(
                "Kreuzstich-Muster (*.xsd *.pat *.oxs);;Pattern Maker (*.xsd);;PCStitch (*.pat);;Open Cross Stitch (*.oxs);;Alle (*.*)"
            ),
        )

        if path:
            self._load_file(Path(path))

    def _load_file(self, filepath: Path) -> None:
        """Lädt und analysiert die Datei im Hintergrund-Thread."""
        self._filepath = filepath
        self._file_label.setText(filepath.name)
        self._file_label.setStyleSheet(f"""
            background: {THEME.bg_medium};
            border: 1px solid {THEME.border_dark};
            border-radius: 4px;
            padding: 8px;
            color: {THEME.text_primary};
        """)

        # Progress-Dialog anzeigen
        self._load_progress = QProgressDialog(t("Muster wird importiert..."), None, 0, 0, self)
        self._load_progress.setWindowTitle(t("Muster importieren"))
        self._load_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._load_progress.setMinimumDuration(0)
        self._load_progress.setCancelButton(None)
        self._load_progress.show()

        # Worker im Hintergrund-Thread starten
        self._load_thread = QThread()
        self._load_worker = _PatternImportWorker(filepath)
        self._load_worker.moveToThread(self._load_thread)

        self._load_thread.started.connect(self._load_worker.run)
        self._load_worker.finished.connect(self._on_load_finished)
        self._load_worker.error.connect(self._on_load_error)
        self._load_worker.finished.connect(self._load_thread.quit)
        self._load_worker.error.connect(self._load_thread.quit)
        self._load_thread.finished.connect(self._load_thread.deleteLater)

        self._load_thread.start()

    def _on_load_finished(
        self,
        pattern: Pattern | None,
        errors: list[str],
        warnings: list[str],
        format_name: str,
    ) -> None:
        """Callback wenn Import erfolgreich."""
        self._load_progress.close()
        self._pattern = pattern

        if self._pattern:
            self._update_info(format_name)
            self._update_preview()
            self._import_btn.setEnabled(True)
        else:
            self._clear_info()
            self._import_btn.setEnabled(False)

        self._show_messages(errors, warnings)

    def _on_load_error(self, error_msg: str) -> None:
        """Callback wenn Import fehlschlägt."""
        self._load_progress.close()
        self._clear_info()
        self._import_btn.setEnabled(False)
        self._show_messages([f"Import-Fehler: {error_msg}"], [])

    def _update_info(self, format_name: str) -> None:
        """Aktualisiert die Muster-Informationen."""
        if not self._pattern:
            return

        p = self._pattern
        w_cm, h_cm = p.size_cm

        self._info_labels["name"].setText(p.name)
        self._info_labels["size"].setText(
            f"{p.width} × {p.height} Stiche ({w_cm:.1f} × {h_cm:.1f} cm)"
        )
        self._info_labels["colors"].setText(str(p.color_count))
        self._info_labels["stitches"].setText(str(p.total_stitches))
        self._info_labels["format"].setText(format_name)

    def _clear_info(self) -> None:
        """Leert die Informationsanzeige."""
        for label in self._info_labels.values():
            label.setText("-")

        self._preview_label.setPixmap(QPixmap())
        self._preview_label.setText(t("Keine Vorschau verfügbar"))

    def _update_preview(self) -> None:
        """Erstellt eine Vorschau des Musters."""
        if not self._pattern:
            return

        # Thumbnail erstellen
        p = self._pattern

        # Skalierung berechnen
        max_size = 180
        scale = min(max_size / p.width, max_size / p.height, 4)

        img_width = max(1, int(p.width * scale))
        img_height = max(1, int(p.height * scale))

        # QImage erstellen
        image = QImage(img_width, img_height, QImage.Format.Format_RGB32)
        image.fill(QColor(255, 255, 255))

        painter = QPainter(image)

        # Pixel setzen
        for y in range(p.height):
            for x in range(p.width):
                color_idx = p.get_stitch(x, y)
                if color_idx is not None and 0 <= color_idx < len(p.color_entries):
                    color = p.color_entries[color_idx].thread.color
                    qcolor = QColor(color.r, color.g, color.b)

                    px = int(x * scale)
                    py = int(y * scale)
                    pw = max(1, int(scale))
                    ph = max(1, int(scale))

                    painter.fillRect(px, py, pw, ph, qcolor)

        painter.end()

        # Anzeigen
        pixmap = QPixmap.fromImage(image)
        self._preview_label.setPixmap(pixmap)
        self._preview_label.setText("")

    def _show_messages(self, errors: list[str], warnings: list[str]) -> None:
        """Zeigt Fehler und Warnungen an."""
        if not errors and not warnings:
            self._messages_edit.hide()
            return

        messages = []

        for error in errors:
            messages.append(f"❌ FEHLER: {error}")

        for warning in warnings:
            messages.append(f"⚠️ Warnung: {warning}")

        self._messages_edit.setText("\n".join(messages))
        self._messages_edit.show()

    def get_pattern(self) -> Pattern | None:
        """Gibt das importierte Muster zurück."""
        return self._pattern
