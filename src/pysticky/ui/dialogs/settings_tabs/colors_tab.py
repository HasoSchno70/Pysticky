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
        palettes = [
            "DMC",
            "Anchor",
            "Madeira",
            "Cosmo",
            "Olympus",
            "Weeks Dye Works",
            "Valdani",
            "Venus",
            "Finca",
            "Sullivans",
            "Riolis Gamma",
            "Classic Colorworks",
            "Gentle Art Sampler Threads",
        ]
        self.combo_default_palette.addItems(palettes)
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

        symbol_preview = QFrame()
        symbol_preview.setFixedHeight(40)
        symbol_preview.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_dark};
                border: 1px solid {THEME.border_medium};
                border-radius: 4px;
            }}
        """)
        self.label_symbol_preview = QLabel("A B C 1 2 3 ● ○ ■ □ ▲ △")
        self.label_symbol_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_symbol_preview.setStyleSheet(f"color: {THEME.text_primary}; font-size: 14px;")
        preview_layout = QHBoxLayout(symbol_preview)
        preview_layout.addWidget(self.label_symbol_preview)
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

    def load_settings(self, settings: QSettings) -> None:
        """Lädt Einstellungen."""
        palette_index = settings.value("default_palette", 0, type=int)
        if 0 <= palette_index < self.combo_default_palette.count():
            self.combo_default_palette.setCurrentIndex(palette_index)
        self.chk_show_catalog.setChecked(settings.value("show_catalog", True, type=bool))
        font_family = settings.value("symbol_font", "Arial")
        self.combo_symbol_font.setCurrentFont(QFont(font_family))
        self.spin_symbol_size.setValue(settings.value("symbol_size", 10, type=int))
        self.chk_auto_symbols.setChecked(settings.value("auto_symbols", True, type=bool))
        self.combo_color_display.setCurrentIndex(settings.value("color_display", 0, type=int))
        self.chk_highlight_selected.setChecked(
            settings.value("highlight_selected", True, type=bool)
        )
        self.spin_color_bar_size.setValue(settings.value("color_bar_size", 32, type=int))

    def save_settings(self, settings: QSettings) -> None:
        """Speichert Einstellungen."""
        settings.setValue("default_palette", self.combo_default_palette.currentIndex())
        settings.setValue("show_catalog", self.chk_show_catalog.isChecked())
        settings.setValue("symbol_font", self.combo_symbol_font.currentFont().family())
        settings.setValue("symbol_size", self.spin_symbol_size.value())
        settings.setValue("auto_symbols", self.chk_auto_symbols.isChecked())
        settings.setValue("color_display", self.combo_color_display.currentIndex())
        settings.setValue("highlight_selected", self.chk_highlight_selected.isChecked())
        settings.setValue("color_bar_size", self.spin_color_bar_size.value())

    def reset_to_defaults(self) -> None:
        """Setzt auf Standardwerte zurück."""
        self.combo_default_palette.setCurrentIndex(0)
        self.chk_show_catalog.setChecked(True)
        self.combo_symbol_font.setCurrentFont(QFont("Arial"))
        self.spin_symbol_size.setValue(10)
        self.chk_auto_symbols.setChecked(True)
        self.combo_color_display.setCurrentIndex(0)
        self.chk_highlight_selected.setChecked(True)
        self.spin_color_bar_size.setValue(32)
