"""
Canvas-Tab für Settings-Dialog.
"""

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ....core.constants import (
    DEFAULT_CELL_SIZE,
    MAJOR_GRID_INTERVAL,
    MAX_CELL_SIZE,
    MIN_CELL_SIZE,
)
from ....core.i18n import t
from ._helpers import make_section_form
from .color_button import ColorButton


class CanvasTab(QWidget):
    """Tab: Canvas-Einstellungen."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(4, 4, 4, 4)

        # === Grid ===
        group_grid, form = make_section_form("Raster", "📐")

        self.chk_show_grid = QCheckBox(t("Gitter anzeigen"))
        self.chk_show_grid.setToolTip(t("Zeigt das Gitter auf dem Canvas"))
        form.addRow(self.chk_show_grid)

        self.spin_major_grid = QSpinBox()
        self.spin_major_grid.setRange(5, 50)
        self.spin_major_grid.setToolTip(t("Intervall für Hauptgitterlinien"))
        form.addRow(t("Haupt-Raster alle:"), self.spin_major_grid)

        self.spin_minor_grid = QSpinBox()
        self.spin_minor_grid.setRange(1, 20)
        self.spin_minor_grid.setToolTip(t("Intervall für Nebengitterlinien"))
        form.addRow(t("Neben-Raster alle:"), self.spin_minor_grid)

        # Grid-Farben
        grid_colors_layout = QHBoxLayout()
        self.btn_grid_color_major = ColorButton("#404060")
        self.btn_grid_color_major.setToolTip(t("Farbe der Hauptgitterlinien"))
        grid_colors_layout.addWidget(QLabel(t("Haupt:")))
        grid_colors_layout.addWidget(self.btn_grid_color_major)
        grid_colors_layout.addSpacing(20)
        self.btn_grid_color_minor = ColorButton("#303050")
        self.btn_grid_color_minor.setToolTip(t("Farbe der Nebengitterlinien"))
        grid_colors_layout.addWidget(QLabel(t("Neben:")))
        grid_colors_layout.addWidget(self.btn_grid_color_minor)
        grid_colors_layout.addStretch()
        form.addRow(t("Gitterfarben:"), grid_colors_layout)

        layout.addWidget(group_grid)

        # === Zoom ===
        group_zoom, form = make_section_form("Zoom", "🔍")

        self.spin_default_cell_size = QSpinBox()
        self.spin_default_cell_size.setRange(MIN_CELL_SIZE, MAX_CELL_SIZE)
        self.spin_default_cell_size.setSuffix(" px")
        self.spin_default_cell_size.setToolTip(t("Standard-Zellengröße beim Start"))
        form.addRow(t("Standard-Zellgröße:"), self.spin_default_cell_size)

        self.spin_min_cell_size = QSpinBox()
        self.spin_min_cell_size.setRange(2, 20)
        self.spin_min_cell_size.setSuffix(" px")
        self.spin_min_cell_size.setToolTip(t("Minimale Zellengröße beim Zoomen"))
        form.addRow(t("Min. Zellgröße:"), self.spin_min_cell_size)

        self.spin_max_cell_size = QSpinBox()
        self.spin_max_cell_size.setRange(30, 100)
        self.spin_max_cell_size.setSuffix(" px")
        self.spin_max_cell_size.setToolTip(t("Maximale Zellengröße beim Zoomen"))
        form.addRow(t("Max. Zellgröße:"), self.spin_max_cell_size)

        zoom_speed_layout = QHBoxLayout()
        self.slider_zoom_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_zoom_speed.setRange(10, 50)
        self.slider_zoom_speed.setToolTip(t("Geschwindigkeit des Zoomens mit Mausrad"))
        self.label_zoom_speed = QLabel("1.2x")
        zoom_speed_layout.addWidget(self.slider_zoom_speed)
        zoom_speed_layout.addWidget(self.label_zoom_speed)
        self.slider_zoom_speed.valueChanged.connect(
            lambda v: self.label_zoom_speed.setText(f"{v / 10:.1f}x")
        )
        form.addRow(t("Zoom-Geschwindigkeit:"), zoom_speed_layout)

        layout.addWidget(group_zoom)

        # === Snap ===
        group_snap, form = make_section_form("Magnetisches Raster", "🧲")

        self.chk_snap_enabled = QCheckBox(t("Snap-to-Grid aktivieren"))
        self.chk_snap_enabled.setToolTip(t("Rastet Werkzeuge am Gitter ein"))
        form.addRow(self.chk_snap_enabled)

        self.spin_snap_interval = QSpinBox()
        self.spin_snap_interval.setRange(1, 20)
        self.spin_snap_interval.setToolTip(t("Intervall für magnetisches Einrasten"))
        form.addRow(t("Snap-Intervall:"), self.spin_snap_interval)

        layout.addWidget(group_snap)

        # === Hintergrund ===
        group_bg, form = make_section_form("Hintergrund", "🖼️")

        self.btn_canvas_bg = ColorButton("#1a1a2e")
        self.btn_canvas_bg.setToolTip(t("Hintergrundfarbe des Canvas"))
        form.addRow(t("Canvas-Hintergrund:"), self.btn_canvas_bg)

        self.btn_empty_cell = ColorButton("#2a2a4a")
        self.btn_empty_cell.setToolTip(t("Farbe leerer Zellen"))
        form.addRow(t("Leere Zellen:"), self.btn_empty_cell)

        self.chk_fabric_texture = QCheckBox(t("Stoff-Textur (Aida-Optik) auf leeren Zellen"))
        self.chk_fabric_texture.setToolTip(
            t(
                "Zeigt eine dezente Stoff-Textur statt einer gleichmäßigen Farbe.\n"
                "Macht das Muster realistischer beim Sticken."
            )
        )
        form.addRow(self.chk_fabric_texture)

        layout.addWidget(group_bg)
        layout.addStretch()

    def load_settings(self, settings: QSettings) -> None:
        """Lädt Einstellungen."""
        self.chk_show_grid.setChecked(settings.value("show_grid", True, type=bool))
        self.spin_major_grid.setValue(
            settings.value("major_grid_interval", MAJOR_GRID_INTERVAL, type=int)
        )
        self.spin_minor_grid.setValue(settings.value("minor_grid_interval", 5, type=int))
        self.btn_grid_color_major.color = settings.value("grid_color_major", "#404060")
        self.btn_grid_color_minor.color = settings.value("grid_color_minor", "#303050")
        self.spin_default_cell_size.setValue(
            settings.value("default_cell_size", DEFAULT_CELL_SIZE, type=int)
        )
        self.spin_min_cell_size.setValue(settings.value("min_cell_size", MIN_CELL_SIZE, type=int))
        self.spin_max_cell_size.setValue(settings.value("max_cell_size", MAX_CELL_SIZE, type=int))
        self.slider_zoom_speed.setValue(settings.value("zoom_speed", 12, type=int))
        self.chk_snap_enabled.setChecked(settings.value("snap_enabled", False, type=bool))
        self.spin_snap_interval.setValue(settings.value("snap_interval", 5, type=int))
        self.btn_canvas_bg.color = settings.value("canvas_bg", "#1a1a2e")
        self.btn_empty_cell.color = settings.value("empty_cell_color", "#2a2a4a")
        self.chk_fabric_texture.setChecked(settings.value("fabric_texture", True, type=bool))

    def save_settings(self, settings: QSettings) -> None:
        """Speichert Einstellungen."""
        settings.setValue("show_grid", self.chk_show_grid.isChecked())
        settings.setValue("major_grid_interval", self.spin_major_grid.value())
        settings.setValue("minor_grid_interval", self.spin_minor_grid.value())
        settings.setValue("grid_color_major", self.btn_grid_color_major.color)
        settings.setValue("grid_color_minor", self.btn_grid_color_minor.color)
        settings.setValue("default_cell_size", self.spin_default_cell_size.value())
        settings.setValue("min_cell_size", self.spin_min_cell_size.value())
        settings.setValue("max_cell_size", self.spin_max_cell_size.value())
        settings.setValue("zoom_speed", self.slider_zoom_speed.value())
        settings.setValue("snap_enabled", self.chk_snap_enabled.isChecked())
        settings.setValue("snap_interval", self.spin_snap_interval.value())
        settings.setValue("canvas_bg", self.btn_canvas_bg.color)
        settings.setValue("empty_cell_color", self.btn_empty_cell.color)
        settings.setValue("fabric_texture", self.chk_fabric_texture.isChecked())

    def reset_to_defaults(self) -> None:
        """Setzt auf Standardwerte zurück."""
        self.chk_show_grid.setChecked(True)
        self.spin_major_grid.setValue(MAJOR_GRID_INTERVAL)
        self.spin_minor_grid.setValue(5)
        self.btn_grid_color_major.color = "#404060"
        self.btn_grid_color_minor.color = "#303050"
        self.spin_default_cell_size.setValue(DEFAULT_CELL_SIZE)
        self.spin_min_cell_size.setValue(MIN_CELL_SIZE)
        self.spin_max_cell_size.setValue(MAX_CELL_SIZE)
        self.slider_zoom_speed.setValue(12)
        self.chk_snap_enabled.setChecked(False)
        self.spin_snap_interval.setValue(5)
        self.btn_canvas_bg.color = "#1a1a2e"
        self.btn_empty_cell.color = "#2a2a4a"
        self.chk_fabric_texture.setChecked(True)
