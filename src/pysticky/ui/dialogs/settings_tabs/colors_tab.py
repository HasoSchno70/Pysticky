"""
Farben-Tab für Settings-Dialog.
"""

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFontComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ....core.i18n import t
from ...styles import THEME
from ._helpers import make_section_form


class ColorsTab(QWidget):
    """Tab: Farb- und Symbol-Einstellungen."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(4, 4, 4, 4)

        # === Standard-Palette ===
        group_palette, form = make_section_form(t("Standard-Palette"), "🧵")

        self.combo_default_palette = QComboBox()
        self.combo_default_palette.addItems(self._available_regular_palette_names())
        self.combo_default_palette.setToolTip(t("Palette, die standardmäßig geladen wird"))
        form.addRow(t("Standard:"), self.combo_default_palette)

        self.chk_show_catalog = QCheckBox(t("Katalognummern anzeigen"))
        self.chk_show_catalog.setToolTip(t("Zeigt Katalognummern in der Farbauswahl"))
        form.addRow(self.chk_show_catalog)

        layout.addWidget(group_palette)

        # === Symbole ===
        group_symbols, form = make_section_form(t("Symbole"), "🔣")

        self.combo_symbol_font = QFontComboBox()
        self.combo_symbol_font.setToolTip(t("Schriftart für Symbole"))
        form.addRow(t("Symbol-Schriftart:"), self.combo_symbol_font)

        self.spin_symbol_size = QSpinBox()
        self.spin_symbol_size.setRange(6, 20)
        self.spin_symbol_size.setSuffix(" pt")
        self.spin_symbol_size.setToolTip(t("Größe der Symbole"))
        form.addRow(t("Symbol-Größe:"), self.spin_symbol_size)

        self.chk_auto_symbols = QCheckBox(t("Symbole automatisch zuweisen"))
        self.chk_auto_symbols.setToolTip(t("Weist neuen Farben automatisch Symbole zu"))
        form.addRow(self.chk_auto_symbols)

        self._symbol_preview_frame = QFrame()
        self._symbol_preview_frame.setFixedHeight(40)
        self.label_symbol_preview = QLabel("A B C 1 2 3 ● ○ ■ □ ▲ △")
        self.label_symbol_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout = QHBoxLayout(self._symbol_preview_frame)
        preview_layout.addWidget(self.label_symbol_preview)
        symbol_preview = self._symbol_preview_frame
        form.addRow(t("Vorschau:"), symbol_preview)

        layout.addWidget(group_symbols)

        # === Farbanzeige ===
        group_display, form = make_section_form(t("Farbanzeige"), "🎨")

        self.combo_color_display = QComboBox()
        self.combo_color_display.addItems(
            [t("Nur Farbe"), t("Farbe + Symbol"), t("Nur Symbol"), t("Farbe + Name")]
        )
        self.combo_color_display.setToolTip(t("Wie Farben im Canvas angezeigt werden"))
        form.addRow(t("Anzeige-Modus:"), self.combo_color_display)

        self.chk_highlight_selected = QCheckBox(t("Ausgewählte Farbe hervorheben"))
        self.chk_highlight_selected.setToolTip(t("Hebt Stiche der ausgewählten Farbe hervor"))
        form.addRow(self.chk_highlight_selected)

        self.spin_color_bar_size = QSpinBox()
        self.spin_color_bar_size.setRange(20, 60)
        self.spin_color_bar_size.setSuffix(" px")
        self.spin_color_bar_size.setToolTip(t("Größe der Farbfelder in der Farbleiste"))
        form.addRow(t("Farbleisten-Größe:"), self.spin_color_bar_size)

        layout.addWidget(group_display)
        layout.addStretch()

        self._apply_theme()

    def _apply_theme(self) -> None:
        """Setzt die THEME-abhaengigen Stylesheets neu.

        Wird sowohl beim initialen Aufbau als auch bei einem Live-Theme-
        Wechsel aufgerufen (SettingsDialog bleibt bei "Anwenden" offen,
        _restyle_widget_tree() findet dieses Tab-Widget ueber
        findChildren() automatisch). Vorher wurden Symbol-Vorschau-Rahmen
        und -Label nur einmalig in _setup_ui() gesetzt.
        """
        self._symbol_preview_frame.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_dark};
                border: 1px solid {THEME.border_medium};
                border-radius: 4px;
            }}
        """)
        self.label_symbol_preview.setStyleSheet(f"color: {THEME.text_primary}; font-size: 14px;")

    def load_settings(self, settings: QSettings) -> None:
        """Lädt Einstellungen."""
        palette_name = settings.value("default_palette", "Anchor", type=str)
        index = self.combo_default_palette.findText(palette_name)
        if index >= 0:
            self.combo_default_palette.setCurrentIndex(index)
        self.chk_show_catalog.setChecked(settings.value("show_catalog", True, type=bool))
        font_family = settings.value("symbol_font", "Segoe UI Symbol")
        self.combo_symbol_font.setCurrentFont(QFont(font_family))
        self.spin_symbol_size.setValue(settings.value("symbol_size", 10, type=int))
        self.chk_auto_symbols.setChecked(settings.value("auto_symbols", True, type=bool))
        self.combo_color_display.setCurrentIndex(settings.value("color_display", 0, type=int))
        self.chk_highlight_selected.setChecked(
            settings.value("highlight_selected", True, type=bool)
        )
        self.spin_color_bar_size.setValue(settings.value("color_bar_size", 48, type=int))

    def save_settings(self, settings: QSettings) -> None:
        """Speichert Einstellungen."""
        settings.setValue("default_palette", self.combo_default_palette.currentText())
        settings.setValue("show_catalog", self.chk_show_catalog.isChecked())
        settings.setValue("symbol_font", self.combo_symbol_font.currentFont().family())
        settings.setValue("symbol_size", self.spin_symbol_size.value())
        settings.setValue("auto_symbols", self.chk_auto_symbols.isChecked())
        settings.setValue("color_display", self.combo_color_display.currentIndex())
        settings.setValue("highlight_selected", self.chk_highlight_selected.isChecked())
        settings.setValue("color_bar_size", self.spin_color_bar_size.value())

    def reset_to_defaults(self) -> None:
        """Setzt auf Standardwerte zurück."""
        self.combo_default_palette.setCurrentText("Anchor")
        self.chk_show_catalog.setChecked(True)
        self.combo_symbol_font.setCurrentFont(QFont("Segoe UI Symbol"))
        self.spin_symbol_size.setValue(10)
        self.chk_auto_symbols.setChecked(True)
        self.combo_color_display.setCurrentIndex(0)
        self.chk_highlight_selected.setChecked(True)
        self.spin_color_bar_size.setValue(48)

    @staticmethod
    def _available_regular_palette_names() -> list[str]:
        """Liefert alle geladenen Garn-Paletten (ohne reine Bead-/Diamond-
        Paletten -- fuer "Standard-Palette eines neuen Kreuzstich-Musters"
        ergeben die keinen Sinn). Vorher war diese Liste hart-codiert und
        hinkte dem tatsaechlichen Paletten-Bestand hinterher (z.B. "DMC
        Diamant"/"DMC Light Effects" fehlten, obwohl beides normale
        Garn-Paletten sind) -- gleiches dynamisches Muster wie
        files_tab.py::_populate_cross_ref_list()."""
        from ....core.palette import get_palette_manager

        pm = get_palette_manager()
        pm.load_all()
        names = []
        for name in sorted(pm.available_palettes):
            palette = pm.get_palette(name)
            if palette and not palette.is_beads and not palette.is_diamond:
                names.append(name)
        return names
