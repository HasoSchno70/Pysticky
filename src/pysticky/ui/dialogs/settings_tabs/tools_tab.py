"""
Werkzeuge-Tab für Settings-Dialog.
"""

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ....core.i18n import t
from ...tools.tool_enum import Tool
from ._helpers import make_section_form


class ToolsTab(QWidget):
    """Tab: Werkzeug-Einstellungen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(4, 4, 4, 4)

        # === Standard-Werkzeug ===
        group_default, form = make_section_form("Standard-Werkzeug", "🛠️")

        self.combo_default_tool = QComboBox()
        tool_items = [
            (t("Stift"), Tool.PENCIL),
            (t("Radierer"), Tool.ERASER),
            (t("Füllen"), Tool.FILL),
            (t("Linie"), Tool.LINE),
            (t("Rechteck"), Tool.RECT),
            (t("Auswahl"), Tool.SELECT),
        ]
        for name, tool in tool_items:
            self.combo_default_tool.addItem(name, tool)
        self.combo_default_tool.setToolTip(t("Werkzeug, das beim Start ausgewählt ist"))
        form.addRow(t("Beim Start:"), self.combo_default_tool)

        self.chk_remember_tool = QCheckBox(t("Letztes Werkzeug merken"))
        self.chk_remember_tool.setToolTip(
            t("Verwendet beim nächsten Start das zuletzt verwendete Werkzeug")
        )
        form.addRow(self.chk_remember_tool)

        layout.addWidget(group_default)

        # === Pipette ===
        group_pipette, form = make_section_form("Pipette", "💧")

        self.combo_pipette_behavior = QComboBox()
        self.combo_pipette_behavior.addItems(
            [t("Zum Stift wechseln"), t("Beim Werkzeug bleiben"), t("Zur Auswahl wechseln")]
        )
        self.combo_pipette_behavior.setToolTip(t("Verhalten nach Farbaufnahme"))
        form.addRow(t("Nach Aufnahme:"), self.combo_pipette_behavior)

        self.chk_pipette_show_info = QCheckBox(t("Farbinfo in Statusleiste"))
        self.chk_pipette_show_info.setToolTip(t("Zeigt Farbinformationen bei Hover"))
        form.addRow(self.chk_pipette_show_info)

        layout.addWidget(group_pipette)

        # === Füllen ===
        group_fill, form = make_section_form("Füllen", "🪣")

        self.chk_fill_diagonal = QCheckBox(t("Diagonal füllen"))
        self.chk_fill_diagonal.setToolTip(t("Berücksichtigt diagonale Nachbarn beim Füllen"))
        form.addRow(self.chk_fill_diagonal)

        self.spin_fill_tolerance = QSpinBox()
        self.spin_fill_tolerance.setRange(0, 100)
        self.spin_fill_tolerance.setSuffix(" %")
        self.spin_fill_tolerance.setToolTip(
            t("Farbtoleranz beim Füllen (0 = exakte Übereinstimmung)")
        )
        form.addRow(t("Toleranz:"), self.spin_fill_tolerance)

        layout.addWidget(group_fill)

        # === Auswahl ===
        group_select, form = make_section_form("Auswahl", "⬚")

        self.combo_select_mode = QComboBox()
        self.combo_select_mode.addItems([t("Ersetzen"), t("Hinzufügen"), t("Subtrahieren")])
        self.combo_select_mode.setToolTip(t("Standard-Modus für neue Auswahlen"))
        form.addRow(t("Standard-Modus:"), self.combo_select_mode)

        self.chk_marching_ants = QCheckBox(t("Laufende Ameisen"))
        self.chk_marching_ants.setToolTip(t("Animierte Auswahlkanten"))
        form.addRow(self.chk_marching_ants)

        layout.addWidget(group_select)

        # === Rückstich ===
        group_backstitch, form = make_section_form("Rückstich", "↙️")

        self.spin_backstitch_width = QSpinBox()
        self.spin_backstitch_width.setRange(1, 5)
        self.spin_backstitch_width.setSuffix(" px")
        self.spin_backstitch_width.setToolTip(t("Linienbreite für Rückstiche"))
        form.addRow(t("Linienbreite:"), self.spin_backstitch_width)

        self.chk_backstitch_snap = QCheckBox(t("An Zellenecken einrasten"))
        self.chk_backstitch_snap.setToolTip(t("Rückstiche rasten automatisch an Zellenecken ein"))
        form.addRow(self.chk_backstitch_snap)

        layout.addWidget(group_backstitch)

        # === Tablet / Stift ===
        group_tablet, form = make_section_form("Tablet & Stift", "✒️")

        self.chk_tablet_pressure = QCheckBox(t("Druck nutzen (Wacom / Surface Pen / iPad)"))
        self.chk_tablet_pressure.setToolTip(
            t(
                "Wenn aktiv und ein Stift erkannt wird:\n"
                "Brush-Groesse des Stifts skaliert mit dem Stift-Druck.\n"
                "Maus-Eingabe bleibt 1 Stich pro Click (unveraendert)."
            )
        )
        form.addRow(self.chk_tablet_pressure)

        self.spin_tablet_max_brush = QSpinBox()
        self.spin_tablet_max_brush.setRange(1, 20)
        self.spin_tablet_max_brush.setSuffix(" " + t("Stiche").lower())
        self.spin_tablet_max_brush.setToolTip(
            t(
                "Maximale Brush-Groesse bei 100 % Stift-Druck (Radius).\n"
                "1 = kein Brush (immer einzelner Stich), 5 = Standard, "
                "10+ = sehr dick."
            )
        )
        form.addRow(t("Max. Brush-Groesse:"), self.spin_tablet_max_brush)

        self.chk_touch_gestures = QCheckBox(t("Touch-Gesten (Pinch-Zoom)"))
        self.chk_touch_gestures.setToolTip(
            t(
                "Aktiviert Pinch-Zoom auf Touchscreens (Surface, iPad mit Apple Pencil, ...).\n"
                "Standardmaessig AUS, weil Windows auf manchen Geraeten einen "
                "Toast-Hinweis beim langen Drag zeigt, wenn Touch akzeptiert wird.\n"
                "Aenderung wird sofort uebernommen."
            )
        )
        form.addRow(self.chk_touch_gestures)

        layout.addWidget(group_tablet)
        layout.addStretch()

    def load_settings(self, settings: QSettings):
        """Lädt Einstellungen."""
        tool_index = settings.value("default_tool", 0, type=int)
        if 0 <= tool_index < self.combo_default_tool.count():
            self.combo_default_tool.setCurrentIndex(tool_index)
        self.chk_remember_tool.setChecked(settings.value("remember_tool", False, type=bool))
        self.combo_pipette_behavior.setCurrentIndex(settings.value("pipette_behavior", 0, type=int))
        self.chk_pipette_show_info.setChecked(settings.value("pipette_show_info", True, type=bool))
        self.chk_fill_diagonal.setChecked(settings.value("fill_diagonal", False, type=bool))
        self.spin_fill_tolerance.setValue(settings.value("fill_tolerance", 0, type=int))
        self.combo_select_mode.setCurrentIndex(settings.value("select_mode", 0, type=int))
        self.chk_marching_ants.setChecked(settings.value("marching_ants", True, type=bool))
        self.spin_backstitch_width.setValue(settings.value("backstitch_width", 2, type=int))
        self.chk_backstitch_snap.setChecked(settings.value("backstitch_snap", True, type=bool))
        self.chk_tablet_pressure.setChecked(
            settings.value("tablet/pressure_enabled", True, type=bool)
        )
        self.spin_tablet_max_brush.setValue(settings.value("tablet/max_brush_size", 5, type=int))
        self.chk_touch_gestures.setChecked(
            settings.value("touch/gestures_enabled", False, type=bool)
        )

    def save_settings(self, settings: QSettings):
        """Speichert Einstellungen."""
        settings.setValue("default_tool", self.combo_default_tool.currentIndex())
        settings.setValue("remember_tool", self.chk_remember_tool.isChecked())
        settings.setValue("pipette_behavior", self.combo_pipette_behavior.currentIndex())
        settings.setValue("pipette_show_info", self.chk_pipette_show_info.isChecked())
        settings.setValue("fill_diagonal", self.chk_fill_diagonal.isChecked())
        settings.setValue("fill_tolerance", self.spin_fill_tolerance.value())
        settings.setValue("select_mode", self.combo_select_mode.currentIndex())
        settings.setValue("marching_ants", self.chk_marching_ants.isChecked())
        settings.setValue("backstitch_width", self.spin_backstitch_width.value())
        settings.setValue("backstitch_snap", self.chk_backstitch_snap.isChecked())
        settings.setValue("tablet/pressure_enabled", self.chk_tablet_pressure.isChecked())
        settings.setValue("tablet/max_brush_size", self.spin_tablet_max_brush.value())
        settings.setValue("touch/gestures_enabled", self.chk_touch_gestures.isChecked())

    def reset_to_defaults(self):
        """Setzt auf Standardwerte zurück."""
        self.combo_default_tool.setCurrentIndex(0)
        self.chk_remember_tool.setChecked(False)
        self.combo_pipette_behavior.setCurrentIndex(0)
        self.chk_pipette_show_info.setChecked(True)
        self.chk_fill_diagonal.setChecked(False)
        self.spin_fill_tolerance.setValue(0)
        self.combo_select_mode.setCurrentIndex(0)
        self.chk_marching_ants.setChecked(True)
        self.spin_backstitch_width.setValue(2)
        self.chk_backstitch_snap.setChecked(True)
        self.chk_tablet_pressure.setChecked(True)
        self.spin_tablet_max_brush.setValue(5)
        self.chk_touch_gestures.setChecked(False)
