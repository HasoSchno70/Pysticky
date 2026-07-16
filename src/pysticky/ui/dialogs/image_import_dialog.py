"""
Dialog für den Bildimport.
"""

from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from ...core import (
    ImportSettings,
    Pattern,
    check_pillow_available,
    get_image_info,
    get_palette_manager,
    import_image,
)
from ...core.constants import (
    DEFAULT_MAX_IMPORT_COLORS,
    MAX_COLORS,
    MAX_IMPORT_DIMENSION,
    MIN_COLORS,
)
from ...core.i18n import t
from ..styles import THEME, Styles
from ..widgets.crop_preview import CropPreviewWidget
from .dialog_sizing import auto_size_dialog
from .image_import_presets import (
    BUILTIN_PRESETS,
    load_user_presets,
    save_user_presets,
)


class _ImageImportWorker(QObject):
    """Worker für Hintergrund-Bildimport."""

    finished = Signal(object)  # Pattern oder None
    error = Signal(str)

    def __init__(self, image_path: str, settings: "ImportSettings", crop: tuple | None) -> None:
        super().__init__()
        self._image_path = image_path
        self._settings = settings
        self._crop = crop

    def run(self) -> None:
        """Führt den Import im Hintergrund aus."""
        try:
            pattern = import_image(self._image_path, self._settings, self._crop)
            self.finished.emit(pattern)
        except (OSError, ValueError) as e:
            self.error.emit(str(e))


class ImageImportDialog(QDialog):
    """Dialog für den Bildimport mit Vorschau und Ausschnitt-Auswahl."""

    pattern_created = Signal(object)  # Pattern

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._image_path: Path | None = None
        self._preview_pattern: Pattern | None = None
        self._image_width: int = 0
        self._image_height: int = 0
        self._updating_size: bool = False
        self._crop: tuple[float, float, float, float] = (0, 0, 1, 1)
        self._setup_ui()
        self._connect_signals()
        self._check_dependencies()
        self._auto_size_to_content()

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

    def _populate_presets(self) -> None:
        """Füllt die Preset-ComboBox mit Built-in und User-Presets."""
        self.combo_preset.blockSignals(True)
        self.combo_preset.clear()
        self.combo_preset.addItem(t("— Keine Voreinstellung —"))

        for p in BUILTIN_PRESETS:
            self.combo_preset.addItem(f"📦 {p['name']}")

        user_presets = load_user_presets()
        for p in user_presets:
            self.combo_preset.addItem(f"👤 {p['name']}")

        self.combo_preset.blockSignals(False)

    def _on_preset_changed(self, index: int) -> None:
        """Lädt die ausgewählte Voreinstellung."""
        if index <= 0:
            return  # "Keine Voreinstellung"

        # Built-in Presets: Index 1..len(BUILTIN_PRESETS)
        builtin_count = len(BUILTIN_PRESETS)
        if index <= builtin_count:
            preset = BUILTIN_PRESETS[index - 1]
        else:
            # User Preset
            user_idx = index - builtin_count - 1
            user_presets = load_user_presets()
            if user_idx < len(user_presets):
                preset = user_presets[user_idx]
            else:
                return

        # Einstellungen anwenden (ohne Debounce-Trigger)
        self._updating_size = True
        self.spin_width.setValue(preset.get("width", 80))
        self.spin_height.setValue(preset.get("height", 80))
        self._updating_size = False
        self.spin_colors.setValue(preset.get("max_colors", 20))

        # Dithering
        mode = preset.get("dithering_mode", "none")
        mode_map = {"none": 0, "floyd_steinberg": 1, "ordered": 2}
        self.combo_dithering.setCurrentIndex(mode_map.get(mode, 0))

        # Quantisierung
        quant = preset.get("quantization_method", "nearest")
        quant_map = {"nearest": 0, "median_cut": 1}
        self.combo_quantization.setCurrentIndex(quant_map.get(quant, 0))

        # Backstitches
        self.chk_backstitches.setChecked(preset.get("auto_backstitches", False))

        # Confetti-Reduktion (1 = aus)
        self.spin_confetti.setValue(preset.get("confetti_min_run_size", 1))

        # Palette — DP-Presets springen automatisch auf "DMC Diamond Painting".
        preset_palette = preset.get("palette")
        if preset_palette:
            idx_p = self.combo_palette.findText(preset_palette)
            if idx_p >= 0:
                self.combo_palette.setCurrentIndex(idx_p)

        # DP-Modus-Flag: wird im _get_settings ausgewertet und beim Import
        # an das Pattern weitergegeben.
        self._preset_dp_mode = preset.get("dp_mode", False)

    def _on_save_preset(self) -> None:
        """Speichert die aktuellen Einstellungen als User-Preset."""
        name, ok = QInputDialog.getText(
            self,
            t("Preset speichern"),
            t("Name für die Voreinstellung:"),
        )
        if not ok or not name.strip():
            return

        preset = {
            "name": name.strip(),
            "width": self.spin_width.value(),
            "height": self.spin_height.value(),
            "max_colors": self.spin_colors.value(),
            "dithering_mode": {0: "none", 1: "floyd_steinberg", 2: "ordered"}.get(
                self.combo_dithering.currentIndex(), "none"
            ),
            "quantization_method": {0: "nearest", 1: "median_cut"}.get(
                self.combo_quantization.currentIndex(), "nearest"
            ),
            "auto_backstitches": self.chk_backstitches.isChecked(),
            "confetti_min_run_size": self.spin_confetti.value(),
        }

        user_presets = load_user_presets()
        # Ersetze bei gleichem Namen
        user_presets = [p for p in user_presets if p.get("name") != preset["name"]]
        user_presets.append(preset)
        save_user_presets(user_presets)

        self._populate_presets()
        # Zum neuen Preset wechseln
        for i in range(self.combo_preset.count()):
            if self.combo_preset.itemText(i) == f"👤 {preset['name']}":
                self.combo_preset.setCurrentIndex(i)
                break

    def _groupbox_style(self) -> str:
        return f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {THEME.border_medium};
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """

    def _combo_style(self) -> str:
        return f"""
            QComboBox {{
                background: {THEME.bg_light};
                border: 1px solid {THEME.border_light};
                border-radius: 4px;
                padding: 6px 10px;
                color: {THEME.text_primary};
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background: {THEME.bg_light};
                color: {THEME.text_primary};
                selection-background-color: {THEME.accent_primary};
            }}
        """

    def _button_style(self) -> str:
        return f"""
            QPushButton {{
                background: {THEME.bg_light};
                border: 1px solid {THEME.border_light};
                border-radius: 6px;
                padding: 8px 16px;
                color: {THEME.text_secondary};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {THEME.bg_lighter};
                border-color: {THEME.accent_primary};
            }}
            QPushButton:disabled {{
                background: {THEME.bg_medium};
                color: {THEME.text_disabled};
            }}
        """

    def _setup_ui(self) -> None:
        self.setWindowTitle(t("Bild importieren"))
        self.setMinimumSize(850, 650)

        layout = QHBoxLayout(self)
        layout.setSpacing(20)

        self._left_layout = self._setup_left_panel()
        self._right_panel = self._setup_right_panel()
        layout.addLayout(self._left_layout)
        layout.addWidget(self._right_panel)

    def _setup_left_panel(self) -> QVBoxLayout:
        """Erstellt die linke Seite: Einstellungen, Presets, Buttons."""
        gbs = self._groupbox_style()
        cbs = self._combo_style()
        bts = self._button_style()

        left = QVBoxLayout()
        left.setSpacing(12)

        # Presets
        preset_group = QGroupBox(t("Voreinstellung"))
        preset_group.setStyleSheet(gbs)
        preset_layout = QHBoxLayout(preset_group)

        self.combo_preset = QComboBox()
        self.combo_preset.setStyleSheet(cbs)
        self._populate_presets()
        preset_layout.addWidget(self.combo_preset, 1)

        self.btn_save_preset = QPushButton("\U0001f4be")
        self.btn_save_preset.setToolTip(t("Aktuelle Einstellungen als Preset speichern"))
        self.btn_save_preset.setAutoDefault(False)
        self.btn_save_preset.setDefault(False)
        self.btn_save_preset.setFixedWidth(36)
        self.btn_save_preset.setStyleSheet(bts)
        preset_layout.addWidget(self.btn_save_preset)

        left.addWidget(preset_group)

        # Bild auswählen
        file_group = QGroupBox(t("Bilddatei"))
        file_group.setStyleSheet(gbs)
        file_layout = QVBoxLayout(file_group)

        self.lbl_filename = QLabel(t("Keine Datei ausgewählt"))
        self.lbl_filename.setStyleSheet(f"color: {THEME.text_muted};")
        file_layout.addWidget(self.lbl_filename)

        self.lbl_image_info = QLabel("")
        self.lbl_image_info.setStyleSheet(f"color: {THEME.accent_primary}; font-size: 11px;")
        file_layout.addWidget(self.lbl_image_info)

        self.btn_browse = QPushButton(t("\U0001f4c1 Bild auswählen..."))
        self.btn_browse.setAutoDefault(False)
        self.btn_browse.setDefault(False)
        self.btn_browse.setStyleSheet(bts)
        file_layout.addWidget(self.btn_browse)

        left.addWidget(file_group)

        # Größe
        size_group = QGroupBox(t("Mustergröße"))
        size_group.setStyleSheet(gbs)
        size_layout = QGridLayout(size_group)

        size_layout.addWidget(QLabel(t("Breite:")), 0, 0)
        self.spin_width = QSpinBox()
        self.spin_width.setRange(10, MAX_IMPORT_DIMENSION)
        self.spin_width.setValue(80)
        self.spin_width.setSuffix(t(" Stiche"))
        size_layout.addWidget(self.spin_width, 0, 1)

        size_layout.addWidget(QLabel(t("Höhe:")), 1, 0)
        self.spin_height = QSpinBox()
        self.spin_height.setRange(10, MAX_IMPORT_DIMENSION)
        self.spin_height.setValue(80)
        self.spin_height.setSuffix(t(" Stiche"))
        size_layout.addWidget(self.spin_height, 1, 1)

        self.chk_aspect = QCheckBox(t("Seitenverhältnis beibehalten"))
        self.chk_aspect.setChecked(True)
        size_layout.addWidget(self.chk_aspect, 2, 0, 1, 2)

        self.lbl_size_info = QLabel("")
        self.lbl_size_info.setStyleSheet(f"color: {THEME.text_muted}; font-size: 10px;")
        size_layout.addWidget(self.lbl_size_info, 3, 0, 1, 2)

        left.addWidget(size_group)

        # Farben — Grid mit fester Min-Spaltenbreite, damit Combo-Boxen
        # und Spinner einheitlich breit sind und der Wert nicht von den
        # Up/Down-Pfeilen abgeschnitten wird.
        color_group = QGroupBox(t("Farben"))
        color_group.setStyleSheet(gbs)
        color_layout = QGridLayout(color_group)
        # Linke Label-Spalte: fest 100px (sonst springt sie je nach Text).
        color_layout.setColumnMinimumWidth(0, 100)
        # Rechte Werte-Spalte: gibt allen Widgets dieselbe Mindestbreite.
        color_layout.setColumnStretch(1, 1)

        color_layout.addWidget(QLabel(t("Palette:")), 0, 0)
        self.combo_palette = QComboBox()
        self.combo_palette.setStyleSheet(cbs)
        self.combo_palette.setMinimumWidth(220)
        self._load_palettes()
        color_layout.addWidget(self.combo_palette, 0, 1)

        color_layout.addWidget(QLabel(t("Max. Farben:")), 1, 0)
        self.spin_colors = QSpinBox()
        self.spin_colors.setRange(max(2, MIN_COLORS), MAX_COLORS)
        self.spin_colors.setValue(DEFAULT_MAX_IMPORT_COLORS)
        self.spin_colors.setMinimumWidth(220)
        color_layout.addWidget(self.spin_colors, 1, 1)

        color_layout.addWidget(QLabel(t("Farbauswahl:")), 2, 0)
        self.combo_quantization = QComboBox()
        self.combo_quantization.addItems(
            [
                t("Standard (Nächste Farbe)"),
                t("Median-Cut (Bessere Verteilung)"),
            ]
        )
        self.combo_quantization.setStyleSheet(cbs)
        self.combo_quantization.setMinimumWidth(220)
        color_layout.addWidget(self.combo_quantization, 2, 1)

        color_layout.addWidget(QLabel(t("Dithering:")), 3, 0)
        self.combo_dithering = QComboBox()
        self.combo_dithering.addItems(
            [
                t("Kein Dithering"),
                t("Floyd-Steinberg"),
                t("Ordered (Bayer)"),
            ]
        )
        self.combo_dithering.setStyleSheet(cbs)
        self.combo_dithering.setMinimumWidth(220)
        color_layout.addWidget(self.combo_dithering, 3, 1)

        # Confetti-Reduction: kleine Cluster der Nachbarfarbe zuordnen.
        # Wert = minimale Cluster-Größe. 1 = aus, 2-5 = aktiv.
        lbl_confetti = QLabel(t("Confetti reduzieren:"))
        lbl_confetti.setToolTip(
            t(
                "Filtert isolierte Einzelpixel und kleine Cluster heraus.\n"
                "Sie werden der dominanten Nachbarfarbe zugeordnet, was die\n"
                "Stickanleitung erheblich vereinfacht.\n\n"
                "1 = aus, 2 = dezent (Einzelpixel), 3-5 = aggressiv."
            )
        )
        color_layout.addWidget(lbl_confetti, 4, 0)
        self.spin_confetti = QSpinBox()
        self.spin_confetti.setRange(1, 10)
        self.spin_confetti.setValue(1)
        self.spin_confetti.setToolTip(lbl_confetti.toolTip())
        self.spin_confetti.setSpecialValueText(t("aus"))
        color_layout.addWidget(self.spin_confetti, 4, 1)

        left.addWidget(color_group)

        # Bild-Anpassung (vor Quantisierung)
        adjust_group = QGroupBox(t("Bild-Anpassung"))
        adjust_group.setStyleSheet(gbs)
        adjust_group.setToolTip(
            t(
                "Wird vor der Farbquantisierung angewendet. Hilft bei zu dunklen,\n"
                "blassen oder zu farbstarken Bildern."
            )
        )
        adjust_layout = QGridLayout(adjust_group)

        # Helligkeit
        adjust_layout.addWidget(QLabel(t("Helligkeit:")), 0, 0)
        self.slider_brightness = QSlider(Qt.Orientation.Horizontal)
        self.slider_brightness.setRange(50, 200)  # 0.5 .. 2.0
        self.slider_brightness.setValue(100)  # 1.0
        self.slider_brightness.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_brightness.setTickInterval(25)
        adjust_layout.addWidget(self.slider_brightness, 0, 1)
        self.lbl_brightness = QLabel("100%")
        self.lbl_brightness.setMinimumWidth(45)
        self.lbl_brightness.setStyleSheet(f"color: {THEME.text_muted};")
        adjust_layout.addWidget(self.lbl_brightness, 0, 2)

        # Kontrast
        adjust_layout.addWidget(QLabel(t("Kontrast:")), 1, 0)
        self.slider_contrast = QSlider(Qt.Orientation.Horizontal)
        self.slider_contrast.setRange(50, 200)
        self.slider_contrast.setValue(100)
        self.slider_contrast.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_contrast.setTickInterval(25)
        adjust_layout.addWidget(self.slider_contrast, 1, 1)
        self.lbl_contrast = QLabel("100%")
        self.lbl_contrast.setMinimumWidth(45)
        self.lbl_contrast.setStyleSheet(f"color: {THEME.text_muted};")
        adjust_layout.addWidget(self.lbl_contrast, 1, 2)

        # Sättigung
        adjust_layout.addWidget(QLabel(t("Sättigung:")), 2, 0)
        self.slider_saturation = QSlider(Qt.Orientation.Horizontal)
        self.slider_saturation.setRange(0, 200)  # 0.0 = Graustufen
        self.slider_saturation.setValue(100)
        self.slider_saturation.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_saturation.setTickInterval(25)
        adjust_layout.addWidget(self.slider_saturation, 2, 1)
        self.lbl_saturation = QLabel("100%")
        self.lbl_saturation.setMinimumWidth(45)
        self.lbl_saturation.setStyleSheet(f"color: {THEME.text_muted};")
        adjust_layout.addWidget(self.lbl_saturation, 2, 2)

        # Reset-Button
        self.btn_reset_adjust = QPushButton(t("Zurücksetzen"))
        self.btn_reset_adjust.setAutoDefault(False)
        self.btn_reset_adjust.setDefault(False)
        self.btn_reset_adjust.setStyleSheet(bts)
        adjust_layout.addWidget(self.btn_reset_adjust, 3, 0, 1, 3)

        left.addWidget(adjust_group)

        # Konturen
        contour_group = QGroupBox(t("Konturen"))
        contour_group.setStyleSheet(gbs)
        contour_layout = QVBoxLayout(contour_group)

        self.chk_backstitches = QCheckBox(t("Konturen automatisch erkennen (Rückstiche)"))
        self.chk_backstitches.setToolTip(
            t(
                "Erkennt Kanten im Bild per Sobel-Operator\n"
                "und generiert automatisch Rückstiche entlang der Konturen."
            )
        )
        contour_layout.addWidget(self.chk_backstitches)

        left.addWidget(contour_group)

        # Buttons
        btn_layout = QHBoxLayout()

        self.btn_preview = QPushButton(t("\U0001f50d Vorschau (optional)"))
        self.btn_preview.setEnabled(False)
        self.btn_preview.setAutoDefault(False)
        self.btn_preview.setDefault(False)
        self.btn_preview.setToolTip(
            t("Zeigt eine Vorschau des Ergebnisses - nicht erforderlich für den Import")
        )
        self.btn_preview.setStyleSheet(bts)
        btn_layout.addWidget(self.btn_preview)

        self.btn_reset_crop = QPushButton(t("\u21ba Ausschnitt zurücksetzen"))
        self.btn_reset_crop.setEnabled(False)
        self.btn_reset_crop.setAutoDefault(False)
        self.btn_reset_crop.setDefault(False)
        self.btn_reset_crop.setStyleSheet(bts)
        btn_layout.addWidget(self.btn_reset_crop)

        left.addLayout(btn_layout)

        left.addStretch()

        # Import/Abbrechen Buttons
        action_layout = QHBoxLayout()

        self.btn_cancel = QPushButton(t("Abbrechen"))
        self.btn_cancel.setAutoDefault(False)
        self.btn_cancel.setDefault(False)
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: {THEME.bg_lighter};
                border: 1px solid {THEME.border_light};
                border-radius: 6px;
                padding: 10px 25px;
                color: {THEME.text_secondary};
            }}
            QPushButton:hover {{ background: {THEME.border_light}; }}
        """)
        action_layout.addWidget(self.btn_cancel)

        self.btn_import = QPushButton(t("\u2713 Importieren"))
        self.btn_import.setEnabled(False)
        self.btn_import.setAutoDefault(False)
        self.btn_import.setDefault(False)
        self.btn_import.setStyleSheet(Styles.button_primary())
        action_layout.addWidget(self.btn_import)

        left.addLayout(action_layout)

        return left

    def _setup_right_panel(self) -> QFrame:
        """Erstellt die rechte Seite: Bild-Vorschau mit Crop und Muster-Vorschau."""
        preview_frame = QFrame()
        preview_frame.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_dark};
                border: 2px solid {THEME.border_medium};
                border-radius: 8px;
            }}
        """)
        preview_frame.setMinimumWidth(400)
        preview_layout = QVBoxLayout(preview_frame)

        preview_header = QLabel(t("Vorschau - Ziehe einen Ausschnitt (Doppelklick = zurücksetzen)"))
        preview_header.setStyleSheet(
            f"font-weight: bold; color: {THEME.accent_primary}; font-size: 11px;"
        )
        preview_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(preview_header)

        # Crop Preview Widget
        self.crop_preview = CropPreviewWidget()
        self.crop_preview.setMinimumSize(350, 350)
        self.crop_preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        preview_layout.addWidget(self.crop_preview)

        self.lbl_crop_info = QLabel(t("Ausschnitt: Gesamtes Bild"))
        self.lbl_crop_info.setStyleSheet(f"color: {THEME.text_muted}; font-size: 10px;")
        self.lbl_crop_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.lbl_crop_info)

        # Separator + Muster-Vorschau
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {THEME.border_medium}; max-height: 1px;")
        preview_layout.addWidget(sep)

        lbl_pattern_header = QLabel(t("Muster-Vorschau:"))
        lbl_pattern_header.setStyleSheet(
            f"font-weight: bold; color: {THEME.text_muted}; font-size: 10px;"
        )
        lbl_pattern_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(lbl_pattern_header)

        self._preview_image_label = QLabel()
        self._preview_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_image_label.setMinimumHeight(80)
        self._preview_image_label.setStyleSheet(
            f"background: {THEME.bg_medium}; border-radius: 4px;"
        )
        preview_layout.addWidget(self._preview_image_label)

        self.lbl_preview_info = QLabel("")
        self.lbl_preview_info.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        self.lbl_preview_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.lbl_preview_info)

        return preview_frame

    def _load_palettes(self) -> None:
        """Lädt die verfügbaren Paletten."""
        pm = get_palette_manager()
        pm.load_all()

        for name in sorted(pm.available_palettes):
            self.combo_palette.addItem(name)

        idx = self.combo_palette.findText("DMC")
        if idx >= 0:
            self.combo_palette.setCurrentIndex(idx)
        else:
            idx = self.combo_palette.findText("Anchor")
            if idx >= 0:
                self.combo_palette.setCurrentIndex(idx)

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

        # Bild-Anpassung
        self.slider_brightness.valueChanged.connect(self._on_brightness_changed)
        self.slider_contrast.valueChanged.connect(self._on_contrast_changed)
        self.slider_saturation.valueChanged.connect(self._on_saturation_changed)
        self.btn_reset_adjust.clicked.connect(self._on_reset_adjust)

        self.crop_preview.crop_changed.connect(self._on_crop_changed)

    def _on_brightness_changed(self, value: int) -> None:
        self.lbl_brightness.setText(f"{value}%")
        self._on_settings_changed()

    def _on_contrast_changed(self, value: int) -> None:
        self.lbl_contrast.setText(f"{value}%")
        self._on_settings_changed()

    def _on_saturation_changed(self, value: int) -> None:
        self.lbl_saturation.setText(f"{value}%")
        self._on_settings_changed()

    def _on_reset_adjust(self) -> None:
        """Setzt alle drei Slider auf 100 % zurück."""
        for slider in (self.slider_brightness, self.slider_contrast, self.slider_saturation):
            slider.setValue(100)

    def _on_crop_changed(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """Ausschnitt wurde geändert."""
        self._crop = (x1, y1, x2, y2)

        # Info aktualisieren
        if self._image_width > 0 and self._image_height > 0:
            crop_w = int((x2 - x1) * self._image_width)
            crop_h = int((y2 - y1) * self._image_height)

            if self.crop_preview.has_crop():
                self.lbl_crop_info.setText(f"Ausschnitt: {crop_w} × {crop_h} px")
                self.btn_reset_crop.setEnabled(True)
            else:
                self.lbl_crop_info.setText(t("Ausschnitt: Gesamtes Bild"))
                self.btn_reset_crop.setEnabled(False)

            # Größe neu berechnen basierend auf Ausschnitt
            self._recalculate_size_for_crop()

        self._on_settings_changed()

    def _recalculate_size_for_crop(self) -> None:
        """Berechnet die Mustergröße neu basierend auf dem Ausschnitt."""
        if not self.crop_preview.has_crop():
            return

        x1, y1, x2, y2 = self._crop
        crop_w = int((x2 - x1) * self._image_width)
        crop_h = int((y2 - y1) * self._image_height)

        if crop_w <= 0 or crop_h <= 0:
            return

        # Neue Standardgröße berechnen
        self._updating_size = True
        default_w, default_h = self._calculate_size_for_dimensions(crop_w, crop_h)
        self.spin_width.setValue(default_w)
        self.spin_height.setValue(default_h)
        self._updating_size = False

        self._update_size_info()

    def _on_reset_crop(self) -> None:
        """Ausschnitt zurücksetzen."""
        self.crop_preview.reset_crop()

    def _on_width_changed(self, value: int) -> None:
        """Breite wurde geändert."""
        if self._updating_size or not self.chk_aspect.isChecked():
            self._update_size_info()
            self._on_settings_changed()
            return

        # Seitenverhältnis des Ausschnitts verwenden
        crop_w, crop_h = self._get_crop_dimensions()
        if crop_w > 0 and crop_h > 0:
            self._updating_size = True
            aspect = crop_h / crop_w
            new_height = max(10, int(value * aspect))
            self.spin_height.setValue(new_height)
            self._updating_size = False

        self._update_size_info()
        self._on_settings_changed()

    def _on_height_changed(self, value: int) -> None:
        """Höhe wurde geändert."""
        if self._updating_size or not self.chk_aspect.isChecked():
            self._update_size_info()
            self._on_settings_changed()
            return

        crop_w, crop_h = self._get_crop_dimensions()
        if crop_w > 0 and crop_h > 0:
            self._updating_size = True
            aspect = crop_w / crop_h
            new_width = max(10, int(value * aspect))
            self.spin_width.setValue(new_width)
            self._updating_size = False

        self._update_size_info()
        self._on_settings_changed()

    def _get_crop_dimensions(self) -> tuple[int, int]:
        """Gibt die Dimensionen des aktuellen Ausschnitts zurück."""
        x1, y1, x2, y2 = self._crop
        crop_w = int((x2 - x1) * self._image_width)
        crop_h = int((y2 - y1) * self._image_height)
        return (crop_w, crop_h)

    def _on_aspect_toggled(self, checked: bool) -> None:
        """Seitenverhältnis-Checkbox wurde geändert."""
        if checked:
            self._on_width_changed(self.spin_width.value())

    def _update_size_info(self) -> None:
        """Aktualisiert die Größen-Info."""
        w = self.spin_width.value()
        h = self.spin_height.value()
        w_cm = w / 14 * 2.54
        h_cm = h / 14 * 2.54
        self.lbl_size_info.setText(f"≈ {w_cm:.1f} × {h_cm:.1f} cm bei 14ct Aida")

    def _calculate_size_for_dimensions(self, img_w: int, img_h: int) -> tuple[int, int]:
        """Berechnet eine sinnvolle Standardgröße."""
        if img_w <= 0 or img_h <= 0:
            return (80, 80)

        max_stitches = 100

        if img_w >= img_h:
            width = min(max_stitches, max(20, img_w // 10))
            height = int(width * img_h / img_w)
        else:
            height = min(max_stitches, max(20, img_h // 10))
            width = int(height * img_w / img_h)

        return (max(10, width), max(10, height))

    def _calculate_default_size(self) -> tuple[int, int]:
        """Berechnet die Standardgröße basierend auf Bild/Ausschnitt."""
        crop_w, crop_h = self._get_crop_dimensions()
        if crop_w > 0 and crop_h > 0:
            return self._calculate_size_for_dimensions(crop_w, crop_h)
        return self._calculate_size_for_dimensions(self._image_width, self._image_height)

    @staticmethod
    def _load_pixmap(image_path: Path) -> QPixmap:
        """
        Lädt ein Bild als QPixmap — auch Formate die Qt nicht nativ unterstützt (AVIF, etc.).

        Qt kann nur PNG/JPG/BMP/GIF nativ laden. Für alle anderen Formate
        wird Pillow als Fallback verwendet: Bild → RGB → QImage → QPixmap.
        """
        # Erst Qt probieren (schneller für native Formate)
        pixmap = QPixmap(str(image_path))
        if not pixmap.isNull():
            return pixmap

        # Fallback: über Pillow laden (AVIF, TIFF-Varianten, etc.)
        try:
            from PIL import Image

            pil_img = Image.open(str(image_path))
            # In RGB konvertieren (AVIF kann RGBA sein)
            if pil_img.mode in ("RGBA", "LA", "P", "PA"):
                background = Image.new("RGB", pil_img.size, (255, 255, 255))
                if pil_img.mode == "P":
                    pil_img = pil_img.convert("RGBA")
                if pil_img.mode in ("RGBA", "LA", "PA"):
                    background.paste(pil_img, mask=pil_img.split()[-1])
                    pil_img = background
                else:
                    pil_img = pil_img.convert("RGB")
            elif pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")

            data = pil_img.tobytes("raw", "RGB")
            qimage = QImage(
                data,
                pil_img.width,
                pil_img.height,
                pil_img.width * 3,
                QImage.Format.Format_RGB888,
            )
            # QImage kopieren, da 'data' sonst aus dem Scope fällt
            return QPixmap.fromImage(qimage.copy())
        except (OSError, ValueError, RuntimeError):
            return QPixmap()  # Leeres Pixmap als letzter Fallback

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

        except OSError as e:
            QMessageBox.warning(self, t("Fehler"), f"Bild konnte nicht geladen werden:\n{e}")
            self._image_path = None
            self._image_width = 0
            self._image_height = 0

    def _on_settings_changed(self) -> None:
        """Einstellungen wurden geändert — startet Debounce-Timer für Live-Vorschau."""
        # Vorschau-Pattern ungültig machen
        self._preview_pattern = None

        if self._image_path:
            self.lbl_preview_info.setText(t("⏳ Vorschau wird aktualisiert..."))
            self.lbl_preview_info.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
            # Debounce: Timer (re-)starten
            self._preview_timer.start()

    def _on_auto_preview(self) -> None:
        """Automatische Live-Vorschau nach Debounce-Timer."""
        self._on_preview()

    def _on_preview(self) -> None:
        """Vorschau generieren."""
        if not self._image_path or not check_pillow_available():
            return

        self.lbl_preview_info.setText(t("⏳ Generiere Vorschau..."))
        self.lbl_preview_info.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        self.repaint()

        try:
            settings = self._get_settings()
            self._preview_pattern = import_image(self._image_path, settings, self._crop)

            preview_img = self._pattern_to_image(self._preview_pattern)

            qimage = QImage(
                preview_img.tobytes(),
                preview_img.width,
                preview_img.height,
                preview_img.width * 3,
                QImage.Format.Format_RGB888,
            )
            pixmap = QPixmap.fromImage(qimage)

            # Muster-Vorschau im Label anzeigen (max 250px)
            max_preview = 250
            if pixmap.width() > max_preview or pixmap.height() > max_preview:
                pixmap = pixmap.scaled(
                    max_preview,
                    max_preview,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                )
            self._preview_image_label.setPixmap(pixmap)

            stats = self._preview_pattern.get_statistics()
            self.lbl_preview_info.setText(
                f"✓ {stats['width']} × {stats['height']} Stiche | "
                f"{stats['used_colors']} Farben | {stats['total_stitches']} Stiche"
            )
            self.lbl_preview_info.setStyleSheet(f"color: {THEME.accent_primary}; font-size: 11px;")

        except (OSError, ValueError) as e:
            self.lbl_preview_info.setText(f"❌ Fehler: {e}")
            self.lbl_preview_info.setStyleSheet(f"color: {THEME.error}; font-size: 11px;")

    def _pattern_to_image(self, pattern: Pattern):
        """
        Konvertiert ein Pattern zu einem PIL Image.

        Verwendet numpy-LUT statt putpixel() für drastisch bessere Performance.
        """
        import numpy as np
        from PIL import Image

        from ...core.layer import NO_STITCH

        cell_size = max(1, 300 // max(pattern.width, pattern.height))

        # Farb-LUT erstellen
        bg_color = np.array([250, 250, 245], dtype=np.uint8)
        color_lut = np.zeros((len(pattern.color_entries) + 1, 3), dtype=np.uint8)
        for i, entry in enumerate(pattern.color_entries):
            color_lut[i] = [entry.thread.color.r, entry.thread.color.g, entry.thread.color.b]

        # Grid als numpy-Array
        layer = pattern.active_layer
        grid = layer.grid.copy()

        # Pixel-Array: 1 Pixel pro Stich
        pixel_array = np.full((pattern.height, pattern.width, 3), bg_color, dtype=np.uint8)
        filled_mask = grid != NO_STITCH
        if np.any(filled_mask):
            pixel_array[filled_mask] = color_lut[grid[filled_mask]]

        # Als Image erstellen und auf cell_size hochskalieren (Nearest Neighbor)
        small_img = Image.fromarray(pixel_array, "RGB")
        img_width = pattern.width * cell_size
        img_height = pattern.height * cell_size
        img = small_img.resize((img_width, img_height), Image.Resampling.NEAREST)

        return img

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
        self._import_thread.finished.connect(self._import_thread.deleteLater)

        self._import_thread.start()

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
