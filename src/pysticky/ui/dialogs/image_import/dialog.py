"""
Dialog für den Bildimport.

Die Dialogklasse selbst: Lebenszyklus, Signal-Verkabelung, Bild-Laden,
Einstellungs-Abfrage und der Hintergrund-Import. UI-Aufbau, Größen-/
Crop-Logik, Vorschau und Presets stecken in den Mixins dieses Packages.
"""

from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QMessageBox,
    QProgressDialog,
)

from ....core import (
    ImportSettings,
    Pattern,
    check_pillow_available,
    get_image_info,
    get_palette_manager,
)
from ....core.i18n import t
from ...styles import THEME
from ..dialog_sizing import auto_size_dialog
from .build_mixin import BuildMixin
from .presets_mixin import PresetsMixin
from .preview_mixin import PreviewMixin
from .size_mixin import SizeMixin
from .worker import _ImageImportWorker


class ImageImportDialog(BuildMixin, SizeMixin, PreviewMixin, PresetsMixin, QDialog):
    """Dialog für den Bildimport mit Vorschau und Ausschnitt-Auswahl."""

    pattern_created = Signal(object)  # Pattern

    def __init__(
        self,
        parent=None,
        *,
        prefer_diamond: bool = False,
        seed_pattern: Pattern | None = None,
    ) -> None:
        super().__init__(parent)
        self._image_path: Path | None = None
        self._preview_pattern: Pattern | None = None
        self._image_width: int = 0
        self._image_height: int = 0
        self._updating_size: bool = False
        self._crop: tuple[float, float, float, float] = (0, 0, 1, 1)
        self._prefer_diamond = prefer_diamond
        self._setup_ui()
        self._apply_default_settings()
        self._connect_signals()
        self._check_dependencies()
        if seed_pattern is not None:
            self._seed_from_pattern(seed_pattern)
        self._auto_size_to_content()

    def _apply_default_settings(self) -> None:
        """Wendet die in Einstellungen → Dateien → "Import" konfigurierten
        Vorgaben an (Max. Farben, Dithering). Läuft vor _connect_signals(),
        damit keine Live-Vorschau durch das Setzen ausgelöst wird, und vor
        einem eventuellen _seed_from_pattern()-Aufruf, der Wizard-Recall-
        Werte Vorrang geben soll."""
        from PySide6.QtCore import QSettings

        from ....config import APP_NAME, ORG_NAME

        settings = QSettings(ORG_NAME, APP_NAME)
        self.spin_colors.setValue(settings.value("import_max_colors", 20, type=int))
        self.combo_dithering.setCurrentIndex(settings.value("dither_method", 0, type=int))

    def _seed_from_pattern(self, pattern: Pattern) -> None:
        """Befüllt den Dialog aus einem bereits importierten Muster
        ("Bildimport wiederholen"/Wizard Recall) -- Quellbild, Ausschnitt,
        Palette und alle Import-Einstellungen kommen aus pattern.source_*
        bzw. pattern.metadata, damit der Import mit angepassten Werten
        wiederholt werden kann, ohne das Bild erneut auszuwählen."""
        if not pattern.source_image_path:
            return

        self._load_image_from_path(pattern.source_image_path)
        if self._image_path is None:
            return  # Datei fehlt/beschädigt -- Warnung kam schon von _load_image_from_path

        # Ausschnitt setzen (löst _on_crop_changed aus, das Breite/Höhe
        # zunächst auf einen Ausschnitt-Default umrechnet) -- die exakte
        # gespeicherte Mustergröße wird direkt danach wiederhergestellt.
        self.crop_preview.set_crop(*pattern.source_image_crop)

        self._updating_size = True
        self.spin_width.setValue(pattern.width)
        self.spin_height.setValue(pattern.height)
        self._updating_size = False
        self._update_size_info()

        if pattern.source_palette_name:
            palette_index = self.combo_palette.findText(pattern.source_palette_name)
            if palette_index >= 0:
                self.combo_palette.setCurrentIndex(palette_index)

        meta = pattern.metadata
        self.spin_colors.setValue(meta.get("max_colors", self.spin_colors.value()))

        mode_map = {"none": 0, "floyd_steinberg": 1, "ordered": 2}
        self.combo_dithering.setCurrentIndex(mode_map.get(meta.get("dithering_mode", "none"), 0))

        quant_map = {"nearest": 0, "median_cut": 1}
        self.combo_quantization.setCurrentIndex(
            quant_map.get(meta.get("quantization_method", "nearest"), 0)
        )

        self.chk_backstitches.setChecked(bool(meta.get("auto_backstitches", False)))
        self.chk_aspect.setChecked(bool(meta.get("keep_aspect_ratio", True)))
        self.spin_confetti.setValue(meta.get("confetti_min_run_size", 1))

        self.slider_brightness.setValue(round(meta.get("brightness", 1.0) * 100))
        self.slider_contrast.setValue(round(meta.get("contrast", 1.0) * 100))
        self.slider_saturation.setValue(round(meta.get("saturation", 1.0) * 100))

    def _auto_size_to_content(self) -> None:
        """Größe so wählen, dass die linke Einstellungs-Spalte nicht
        gestaucht wird -- bei fixer Default-Größe wirkte v.a. die
        "Farben"-Sektion (5 Zeilen Combos/Spinner) gedrungen und schwer
        lesbar/bedienbar, weil 6 Gruppen (Voreinstellung, Bilddatei,
        Mustergröße, Farben, Bild-Anpassung, Konturen) untereinander in
        die feste Höhe von 650px gequetscht wurden.
        """
        left_hint = self._left_layout.sizeHint()
        content_w = left_hint.width() + self._right_panel.minimumWidth() + 20
        content_h = left_hint.height()
        auto_size_dialog(self, [], content_size=(content_w, content_h), chrome_w=40, chrome_h=40)

    def _check_dependencies(self) -> None:
        """Prüft ob alle Abhängigkeiten installiert sind."""
        if not check_pillow_available():
            QMessageBox.warning(
                self,
                t("Fehlende Abhängigkeiten"),
                t(
                    "Für den Bildimport werden Pillow und numpy benötigt.\n\n"
                    "Installiere mit:\n"
                    "pip install Pillow numpy"
                ),
            )

    def _update_size_suffix(self) -> None:
        """Passt das Breite/Höhe-Suffix an die gewählte Palette an.

        "Stiche" ergibt für Diamond-Painting-Paletten keinen Sinn (dort
        gibt's keine Stiche, sondern Drills/Steine).
        """
        pm = get_palette_manager()
        palette = pm.get_palette(self.combo_palette.currentText())
        is_diamond = palette is not None and palette.is_diamond
        suffix = t(" Drills") if is_diamond else t(" Stiche")
        self.spin_width.setSuffix(suffix)
        self.spin_height.setSuffix(suffix)

    def _load_palettes(self) -> None:
        """Lädt die verfügbaren Paletten."""
        pm = get_palette_manager()
        pm.load_all()

        for name in sorted(pm.available_palettes):
            self.combo_palette.addItem(name)

        # Wenn das aktuell offene Projekt schon im Diamond-Painting-Modus
        # ist, macht ein Garnhersteller-Default keinen Sinn -- zuerst eine
        # DP-Palette suchen, erst danach auf DMC/Anchor zurückfallen.
        if self._prefer_diamond:
            dp_name = next(
                (
                    n
                    for n in sorted(pm.available_palettes)
                    if (pal := pm.get_palette(n)) is not None and pal.is_diamond
                ),
                None,
            )
            if dp_name is not None:
                index = self.combo_palette.findText(dp_name)
                if index >= 0:
                    self.combo_palette.setCurrentIndex(index)
                    return

        index = self.combo_palette.findText("DMC")
        if index >= 0:
            self.combo_palette.setCurrentIndex(index)
        else:
            index = self.combo_palette.findText("Anchor")
            if index >= 0:
                self.combo_palette.setCurrentIndex(index)

    def _connect_signals(self) -> None:
        # Debounce-Timer für Live-Vorschau (800ms)
        self._preview_timer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(800)
        self._preview_timer.timeout.connect(self._on_auto_preview)

        # Presets
        self.combo_preset.currentIndexChanged.connect(self._on_preset_changed)
        self.btn_save_preset.clicked.connect(self._on_save_preset)

        self.btn_browse.clicked.connect(self._on_browse)
        self.btn_preview.clicked.connect(self._on_preview)
        self.btn_reset_crop.clicked.connect(self._on_reset_crop)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_import.clicked.connect(self._on_import)

        self.spin_width.valueChanged.connect(self._on_width_changed)
        self.spin_height.valueChanged.connect(self._on_height_changed)
        self.spin_colors.valueChanged.connect(self._on_settings_changed)
        self.combo_palette.currentIndexChanged.connect(self._on_settings_changed)
        self.combo_dithering.currentIndexChanged.connect(self._on_settings_changed)
        self.combo_quantization.currentIndexChanged.connect(self._on_settings_changed)
        self.spin_confetti.valueChanged.connect(self._on_settings_changed)
        self.chk_backstitches.toggled.connect(self._on_settings_changed)
        self.chk_aspect.toggled.connect(self._on_aspect_toggled)
        self.combo_palette.currentIndexChanged.connect(self._update_size_suffix)
        self._update_size_suffix()

        # Bild-Anpassung
        self.slider_brightness.valueChanged.connect(self._on_brightness_changed)
        self.slider_contrast.valueChanged.connect(self._on_contrast_changed)
        self.slider_saturation.valueChanged.connect(self._on_saturation_changed)
        self.btn_reset_adjust.clicked.connect(self._on_reset_adjust)

        self.crop_preview.crop_changed.connect(self._on_crop_changed)

    def _on_browse_with_path(self, path: str) -> None:
        """Lädt ein Bild direkt über einen Pfad (z.B. bei Drag & Drop)."""
        if not check_pillow_available():
            return
        self._load_image_from_path(path)

    def _on_browse(self) -> None:
        """Bild auswählen."""
        if not check_pillow_available():
            QMessageBox.warning(
                self,
                t("Fehlende Abhängigkeiten"),
                t("Pillow und numpy sind nicht installiert.\n\npip install Pillow numpy"),
            )
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            t("Bild auswählen"),
            "",
            "Bilder (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff *.tif *.avif *.avifs);;Alle (*.*)",
        )

        if path:
            self._load_image_from_path(path)

    def _load_image_from_path(self, path: str) -> None:
        """Lädt ein Bild aus dem angegebenen Pfad in den Dialog."""
        self._image_path = Path(path)
        self.lbl_filename.setText(self._image_path.name)
        self.lbl_filename.setStyleSheet(f"color: {THEME.text_primary};")

        try:
            info = get_image_info(path)
            self._image_width = info["width"]
            self._image_height = info["height"]

            self.lbl_image_info.setText(
                f"📐 {info['width']} × {info['height']} px | {info['format']}"
            )

            # Bild in Crop-Widget laden
            pixmap = self._load_pixmap(self._image_path)
            self.crop_preview.set_image(pixmap)
            self._crop = (0, 0, 1, 1)

            # Standardgröße setzen
            self._updating_size = True
            default_w, default_h = self._calculate_default_size()
            self.spin_width.setValue(default_w)
            self.spin_height.setValue(default_h)
            self._updating_size = False

            self._update_size_info()
            self.lbl_crop_info.setText("Ausschnitt: Gesamtes Bild")
            self.lbl_preview_info.setText(t("✅ Bereit zum Importieren"))
            self.lbl_preview_info.setStyleSheet(f"color: {THEME.accent_primary}; font-size: 11px;")

            self.btn_preview.setEnabled(True)
            self.btn_import.setEnabled(True)
            self.btn_reset_crop.setEnabled(False)

        except Exception as e:  # noqa: BLE001 - siehe worker.py::_ImageImportWorker.run()
            # Bewusst breiter Catch-all statt nur OSError: get_image_info()
            # ruft PIL.Image.open() auf, das bei einem sehr grossen (aber
            # technisch validen) Bild ein PIL.Image.DecompressionBombError
            # wirft -- eine ganz normale Exception, KEIN OSError. Mit dem
            # schmalen except blieb das hier unbehandelt: self._image_path
            # zeigte danach auf ein Bild, das nie tatsaechlich geladen wurde,
            # waehrend Crop-Vorschau/Groesse/Dateiname noch das vorherige
            # Bild zeigten (oder bei der allerersten Bildwahl auf
            # inkonsistenten Nullwerten blieben). Gleiche Bug-Klasse wie
            # worker.py (Runde 14).
            QMessageBox.warning(self, t("Fehler"), f"Bild konnte nicht geladen werden:\n{e}")
            self._image_path = None
            self._image_width = 0
            self._image_height = 0

    def _get_settings(self) -> ImportSettings:
        """Gibt die aktuellen Einstellungen zurück."""
        # Dithering-ComboBox → mode string
        dithering_map = {0: "none", 1: "floyd_steinberg", 2: "ordered"}
        dithering_mode = dithering_map.get(self.combo_dithering.currentIndex(), "none")

        # Quantisierung-ComboBox → method string
        quant_map = {0: "nearest", 1: "median_cut"}
        quantization_method = quant_map.get(self.combo_quantization.currentIndex(), "nearest")

        return ImportSettings(
            width=self.spin_width.value(),
            height=self.spin_height.value(),
            max_colors=self.spin_colors.value(),
            palette_name=self.combo_palette.currentText(),
            dithering_mode=dithering_mode,
            quantization_method=quantization_method,
            keep_aspect_ratio=self.chk_aspect.isChecked(),
            auto_backstitches=self.chk_backstitches.isChecked(),
            brightness=self.slider_brightness.value() / 100.0,
            contrast=self.slider_contrast.value() / 100.0,
            saturation=self.slider_saturation.value() / 100.0,
            confetti_min_run_size=self.spin_confetti.value(),
        )

    def _on_import(self) -> None:
        """Muster importieren im Hintergrund-Thread."""
        if not self._image_path:
            QMessageBox.warning(self, t("Kein Bild"), t("Bitte wähle zuerst ein Bild aus."))
            return

        if not check_pillow_available():
            QMessageBox.warning(self, t("Fehler"), t("Pillow ist nicht installiert."))
            return

        # UI deaktivieren
        self.btn_import.setEnabled(False)
        self.btn_import.setText(t("⏳ Importiere..."))

        # Progress-Dialog anzeigen
        self._import_progress = QProgressDialog(
            t("Bild wird importiert und konvertiert..."), None, 0, 0, self
        )
        self._import_progress.setWindowTitle(t("Bild importieren"))
        self._import_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._import_progress.setMinimumDuration(0)
        self._import_progress.setCancelButton(None)
        self._import_progress.show()

        # Worker im Hintergrund-Thread starten
        settings = self._get_settings()
        self._import_thread = QThread()
        self._import_worker = _ImageImportWorker(self._image_path, settings, self._crop)
        self._import_worker.moveToThread(self._import_thread)

        self._import_thread.started.connect(self._import_worker.run)
        self._import_worker.finished.connect(self._on_import_finished)
        self._import_worker.error.connect(self._on_import_error)
        self._import_worker.finished.connect(self._import_thread.quit)
        self._import_worker.error.connect(self._import_thread.quit)
        self._import_worker.finished.connect(self._import_worker.deleteLater)
        self._import_worker.error.connect(self._import_worker.deleteLater)
        self._import_thread.finished.connect(self._import_thread.deleteLater)

        self._import_thread.start()

    def _import_running(self) -> bool:
        thread = getattr(self, "_import_thread", None)
        return thread is not None and thread.isRunning()

    def reject(self) -> None:
        """Verhindert das Schließen, während der Hintergrund-Import läuft."""
        if self._import_running():
            return
        super().reject()

    def closeEvent(self, event) -> None:
        """Verhindert das Schließen (z.B. per Fenster-X), während der
        Hintergrund-Import läuft -- sonst könnte ein später feuerndes
        finished/error-Signal auf ein bereits zerstörtes Dialog-Objekt
        zugreifen."""
        if self._import_running():
            event.ignore()
            return
        super().closeEvent(event)

    def _on_import_finished(self, pattern: Pattern) -> None:
        """Callback wenn Import erfolgreich."""
        self._import_progress.close()
        self._imported_pattern = pattern
        self.pattern_created.emit(pattern)
        self.accept()

    def _on_import_error(self, error_msg: str) -> None:
        """Callback wenn Import fehlschlägt."""
        self._import_progress.close()
        QMessageBox.critical(self, t("Fehler"), f"Import fehlgeschlagen:\n{error_msg}")
        self.btn_import.setEnabled(True)
        self.btn_import.setText(t("✓ Importieren"))

    def get_pattern(self) -> Pattern | None:
        """Gibt das importierte Pattern zurück."""
        return getattr(self, "_imported_pattern", None)
