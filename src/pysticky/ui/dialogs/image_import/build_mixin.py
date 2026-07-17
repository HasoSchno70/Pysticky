"""
UI-Aufbau-Mixin für den Bildimport-Dialog.

Enthält den kompletten Widget-Aufbau (linkes Einstellungs-Panel,
rechtes Vorschau-Panel) sowie die geteilten Style-Helfer.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from ....core.constants import (
    DEFAULT_MAX_IMPORT_COLORS,
    MAX_COLORS,
    MAX_IMPORT_DIMENSION,
    MIN_COLORS,
)
from ....core.i18n import t
from ...styles import THEME, Styles
from ...widgets.crop_preview import CropPreviewWidget

if TYPE_CHECKING:
    from .dialog import ImageImportDialog


class BuildMixin:
    """Mixin für den UI-Aufbau des Bildimport-Dialogs."""

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

    def _setup_ui(self: "ImageImportDialog") -> None:
        self.setWindowTitle(t("Bild importieren"))
        self.setMinimumSize(850, 650)

        layout = QHBoxLayout(self)
        layout.setSpacing(20)

        self._left_layout = self._setup_left_panel()
        self._right_panel = self._setup_right_panel()
        layout.addLayout(self._left_layout)
        layout.addWidget(self._right_panel)

    def _setup_left_panel(self: "ImageImportDialog") -> QVBoxLayout:
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

    def _setup_right_panel(self: "ImageImportDialog") -> QFrame:
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
