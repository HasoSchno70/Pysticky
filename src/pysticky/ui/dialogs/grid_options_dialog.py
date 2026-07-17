"""
Dialog für Raster-Optionen.
"""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ...core.i18n import t
from ..styles import THEME


class ColorButton(QPushButton):
    """Button zur Farbauswahl."""

    def __init__(self, color: QColor, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(60, 28)
        self._update_style()
        self.clicked.connect(self._on_click)

    def _update_style(self) -> None:
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color.name()};
                border: 2px solid {THEME.border_medium};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border-color: {THEME.border_light};
            }}
        """)

    def _on_click(self) -> None:
        color = QColorDialog.getColor(self._color, self, t("Farbe wählen"))
        if color.isValid():
            self._color = color
            self._update_style()

    @property
    def color(self) -> QColor:
        return self._color

    @color.setter
    def color(self, value: QColor) -> None:
        self._color = value
        self._update_style()


class GridOptionsDialog(QDialog):
    """Dialog für Raster-Einstellungen."""

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas

        self.setWindowTitle(t("Raster-Optionen"))
        self.setMinimumWidth(350)

        self._setup_ui()
        self._load_values()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # === Intervalle ===
        interval_group = QGroupBox(t("Linien-Intervalle"))
        interval_layout = QFormLayout(interval_group)

        # Haupt-Raster (10er)
        self.spin_major = QSpinBox()
        self.spin_major.setRange(5, 50)
        self.spin_major.setSuffix(t(" Stiche"))
        interval_layout.addRow(t("Haupt-Raster:"), self.spin_major)

        # Neben-Raster (5er)
        self.chk_minor = QCheckBox(t("Neben-Raster anzeigen"))
        interval_layout.addRow(self.chk_minor)

        self.spin_minor = QSpinBox()
        self.spin_minor.setRange(1, 20)
        self.spin_minor.setSuffix(t(" Stiche"))
        interval_layout.addRow(t("Neben-Raster:"), self.spin_minor)

        self.chk_minor.toggled.connect(self.spin_minor.setEnabled)

        layout.addWidget(interval_group)

        # === Farben ===
        color_group = QGroupBox(t("Raster-Farben"))
        color_layout = QFormLayout(color_group)

        # Normal
        self.btn_color_normal = ColorButton(QColor(80, 80, 80))
        color_layout.addRow(t("Normal:"), self.btn_color_normal)

        # Neben-Linien
        self.btn_color_minor = ColorButton(QColor(120, 120, 120))
        color_layout.addRow(t("Neben-Linien:"), self.btn_color_minor)

        # Haupt-Linien
        self.btn_color_major = ColorButton(QColor(100, 100, 100))
        color_layout.addRow(t("Haupt-Linien:"), self.btn_color_major)

        layout.addWidget(color_group)

        # === Voreinstellungen ===
        presets_group = QGroupBox(t("Voreinstellungen"))
        presets_layout = QHBoxLayout(presets_group)

        btn_default = QPushButton(t("Standard"))
        btn_default.clicked.connect(self._preset_default)
        presets_layout.addWidget(btn_default)

        btn_light = QPushButton(t("Hell"))
        btn_light.clicked.connect(self._preset_light)
        presets_layout.addWidget(btn_light)

        btn_blue = QPushButton(t("Blau"))
        btn_blue.clicked.connect(self._preset_blue)
        presets_layout.addWidget(btn_blue)

        btn_red = QPushButton(t("Rot"))
        btn_red.clicked.connect(self._preset_red)
        presets_layout.addWidget(btn_red)

        layout.addWidget(presets_group)

        # === Buttons ===
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._apply)
        layout.addWidget(button_box)

    def _load_values(self) -> None:
        """Lädt die aktuellen Werte vom Canvas."""
        self.spin_major.setValue(self.canvas.major_grid_interval)
        self.spin_minor.setValue(self.canvas.minor_grid_interval)
        self.chk_minor.setChecked(self.canvas.show_minor_grid)
        self.spin_minor.setEnabled(self.canvas.show_minor_grid)

        self.btn_color_normal.color = self.canvas.grid_color
        self.btn_color_minor.color = self.canvas.grid_minor_color
        self.btn_color_major.color = self.canvas.grid_major_color

    def _apply(self) -> None:
        """Wendet die Einstellungen an."""
        self.canvas.major_grid_interval = self.spin_major.value()
        self.canvas.minor_grid_interval = self.spin_minor.value()
        self.canvas.show_minor_grid = self.chk_minor.isChecked()

        self.canvas.grid_color = self.btn_color_normal.color
        self.canvas.grid_minor_color = self.btn_color_minor.color
        self.canvas.grid_major_color = self.btn_color_major.color

    def _on_accept(self) -> None:
        self._apply()
        self.accept()

    def _preset_default(self) -> None:
        """Standard-Voreinstellung."""
        self.spin_major.setValue(10)
        self.spin_minor.setValue(5)
        self.chk_minor.setChecked(True)
        self.btn_color_normal.color = QColor(80, 80, 80)
        self.btn_color_minor.color = QColor(120, 120, 120)
        self.btn_color_major.color = QColor(100, 100, 100)

    def _preset_light(self) -> None:
        """Helle Voreinstellung."""
        self.spin_major.setValue(10)
        self.spin_minor.setValue(5)
        self.chk_minor.setChecked(True)
        self.btn_color_normal.color = QColor(180, 180, 180)
        self.btn_color_minor.color = QColor(140, 140, 140)
        self.btn_color_major.color = QColor(100, 100, 100)

    def _preset_blue(self) -> None:
        """Blaue Voreinstellung."""
        self.spin_major.setValue(10)
        self.spin_minor.setValue(5)
        self.chk_minor.setChecked(True)
        self.btn_color_normal.color = QColor(60, 80, 100)
        self.btn_color_minor.color = QColor(80, 120, 160)
        self.btn_color_major.color = QColor(40, 100, 180)

    def _preset_red(self) -> None:
        """Rote Voreinstellung."""
        self.spin_major.setValue(10)
        self.spin_minor.setValue(5)
        self.chk_minor.setChecked(True)
        self.btn_color_normal.color = QColor(100, 60, 60)
        self.btn_color_minor.color = QColor(160, 80, 80)
        self.btn_color_major.color = QColor(180, 40, 40)
