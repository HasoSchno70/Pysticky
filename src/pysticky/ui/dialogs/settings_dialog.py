"""
Zentraler Einstellungs-Dialog für PySticky.

Fasst alle Anwendungseinstellungen in einem übersichtlichen Dialog zusammen.
Die einzelnen Tabs sind in separate Widgets ausgelagert.
"""

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
)

from ...core.i18n import t
from ..styles import THEME, Styles
from .settings_tabs import CanvasTab, ColorsTab, FilesTab, GeneralTab, ShortcutsTab, ToolsTab


class SettingsDialog(QDialog):
    """
    Zentraler Einstellungs-Dialog.

    Tabs:
    - Allgemein: Autosave, Start-Verhalten, Sprache
    - Canvas: Grid, Zoom, Snap, Hintergrund
    - Werkzeuge: Standard-Werkzeug, Optionen
    - Farben: Paletten, Symbole
    - Dateien: Pfade, Export-Optionen
    - Tastenkürzel: Anpassbare Shortcuts
    """

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = QSettings()

        self.setWindowTitle(t("Einstellungen"))
        # Kompaktere Default-Größe — Tabs mit viel Inhalt sind ohnehin scrollbar
        self.setMinimumSize(680, 560)
        self.resize(780, 680)

        self._setup_ui()
        self._load_settings()
        self._apply_styles()

    def _setup_ui(self):
        """Erstellt die UI-Struktur."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Tab-Widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs)

        # Tab-Widgets erstellen
        self.general_tab = GeneralTab()
        self.canvas_tab = CanvasTab()
        self.tools_tab = ToolsTab()
        self.colors_tab = ColorsTab()
        self.files_tab = FilesTab()
        self.shortcuts_tab = ShortcutsTab()

        # Tabs in scrollbarer Area — bei kleinem Fenster bleiben alle Felder
        # erreichbar statt abgeschnitten zu werden.
        for tab, label in [
            (self.general_tab, "⚙️  " + t("Allgemein")),
            (self.canvas_tab, "🖌  " + t("Canvas")),
            (self.tools_tab, "🛠  " + t("Werkzeuge")),
            (self.colors_tab, "🎨  " + t("Farben")),
            (self.files_tab, "📁  " + t("Dateien")),
            (self.shortcuts_tab, "⌨  " + t("Tastenkürzel")),
        ]:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setWidget(tab)
            self.tabs.addTab(scroll, label)

        # Button-Box
        button_layout = QHBoxLayout()

        self.btn_reset = QPushButton(t("Zurücksetzen"))
        self.btn_reset.setToolTip(t("Alle Einstellungen auf Standardwerte zurücksetzen"))
        self.btn_reset.clicked.connect(self._reset_to_defaults)
        button_layout.addWidget(self.btn_reset)

        button_layout.addStretch()

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self._apply_settings
        )
        button_layout.addWidget(self.button_box)

        layout.addLayout(button_layout)

    def _load_settings(self):
        """Lädt alle Einstellungen in die Tab-Widgets."""
        self.general_tab.load_settings(self._settings)
        self.canvas_tab.load_settings(self._settings)
        self.tools_tab.load_settings(self._settings)
        self.colors_tab.load_settings(self._settings)
        self.files_tab.load_settings(self._settings)
        self.shortcuts_tab.load_settings(self._settings)

    def _save_settings(self):
        """Speichert alle Einstellungen aus den Tab-Widgets."""
        self.general_tab.save_settings(self._settings)
        self.canvas_tab.save_settings(self._settings)
        self.tools_tab.save_settings(self._settings)
        self.colors_tab.save_settings(self._settings)
        self.files_tab.save_settings(self._settings)
        self.shortcuts_tab.save_settings(self._settings)

    def _apply_settings(self):
        """Wendet Einstellungen an ohne den Dialog zu schließen."""
        self._save_settings()
        self.settings_changed.emit()

    def _on_accept(self):
        """Speichert und schließt den Dialog."""
        self._save_settings()
        self.settings_changed.emit()
        self.accept()

    def _reset_to_defaults(self):
        """Setzt alle Einstellungen auf Standardwerte zurück."""
        reply = QMessageBox.question(
            self,
            t("Einstellungen zurücksetzen"),
            t(
                "Alle Einstellungen auf Standardwerte zurücksetzen?\n\n"
                "Dies kann nicht rückgängig gemacht werden."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.general_tab.reset_to_defaults()
            self.canvas_tab.reset_to_defaults()
            self.tools_tab.reset_to_defaults()
            self.colors_tab.reset_to_defaults()
            self.files_tab.reset_to_defaults()
            self.shortcuts_tab.reset_to_defaults()

    def _apply_styles(self):
        """Wendet das zentrale Styling an."""
        self.setStyleSheet(f"""
            QDialog {{
                background: {THEME.bg_dark};
                color: {THEME.text_primary};
            }}
            QTabWidget::pane {{
                border: 1px solid {THEME.border_medium};
                border-top: 2px solid {THEME.accent_primary};
                border-radius: 6px;
                background: {THEME.bg_medium};
                padding: 12px;
            }}
            QTabBar::tab {{
                background: {THEME.bg_light};
                color: {THEME.text_muted};
                border: 1px solid {THEME.border_medium};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 10px 18px;
                margin-right: 3px;
                min-width: 90px;
                font-weight: 500;
            }}
            QTabBar::tab:selected {{
                background: {THEME.bg_medium};
                color: {THEME.accent_primary};
                border-color: {THEME.accent_primary};
                border-bottom: none;
                font-weight: 700;
            }}
            QTabBar::tab:hover:!selected {{
                background: {THEME.bg_lighter};
                color: {THEME.text_primary};
            }}
            /* GroupBox: Title sitzt sauber oben, Inhalts-Padding kommt
               aus dem Layout (siehe make_section_form), nicht aus dem
               Stylesheet — sonst kollidiert beides und Felder ueberlappen. */
            QGroupBox {{
                font-weight: 700;
                color: {THEME.accent_primary};
                background: {THEME.bg_light};
                border: 1px solid {THEME.border_medium};
                border-left: 3px solid {THEME.accent_primary};
                border-radius: 8px;
                margin-top: 14px;
                padding: 0;
                padding-top: 26px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 14px;
                top: 2px;
                padding: 2px 10px;
                background: {THEME.bg_lighter};
                border-radius: 4px;
                color: {THEME.accent_primary};
                font-size: 12px;
                letter-spacing: 0.5px;
            }}
            QLabel {{
                color: {THEME.text_secondary};
                min-height: 24px;
                padding: 2px 0;
            }}
            QCheckBox {{
                color: {THEME.text_primary};
                spacing: 8px;
                min-height: 24px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {THEME.border_medium};
                border-radius: 4px;
                background: {THEME.bg_dark};
            }}
            QCheckBox::indicator:checked {{
                background: {THEME.accent_primary};
                border-color: {THEME.accent_primary};
            }}
            QCheckBox::indicator:hover {{
                border-color: {THEME.accent_primary};
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox {{
                background: {THEME.bg_dark};
                color: {THEME.text_primary};
                border: 2px solid {THEME.border_medium};
                border-radius: 6px;
                padding: 6px 10px;
                min-height: 28px;
                min-width: 80px;
            }}
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border-color: {THEME.accent_primary};
            }}
            QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
                border-color: {THEME.border_light};
            }}
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 20px;
                border: none;
                background: {THEME.bg_light};
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover,
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
                background: {THEME.bg_lighter};
            }}
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 5px solid {THEME.text_secondary};
                width: 0; height: 0;
            }}
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {THEME.text_secondary};
                width: 0; height: 0;
            }}
            QComboBox {{
                background: {THEME.bg_dark};
                color: {THEME.text_primary};
                border: 2px solid {THEME.border_medium};
                border-radius: 6px;
                padding: 6px 12px;
                min-height: 28px;
                min-width: 120px;
            }}
            QComboBox:hover {{
                border-color: {THEME.accent_primary};
                background: {THEME.bg_medium};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {THEME.accent_primary};
            }}
            QComboBox QAbstractItemView {{
                background: {THEME.bg_dark};
                color: {THEME.text_primary};
                border: 2px solid {THEME.accent_primary};
                border-radius: 6px;
                selection-background-color: {THEME.accent_primary};
                selection-color: {THEME.bg_dark};
            }}
            QFontComboBox {{
                background: {THEME.bg_dark};
                color: {THEME.text_primary};
                border: 2px solid {THEME.border_medium};
                border-radius: 6px;
                padding: 6px 12px;
                min-height: 28px;
                min-width: 150px;
            }}
            QFontComboBox:hover {{
                border-color: {THEME.accent_primary};
            }}
            QFontComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QFontComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {THEME.accent_primary};
            }}
            {Styles.list_widget()}
            {Styles.scrollbar()}
            QSlider::groove:horizontal {{
                height: 6px;
                background: {THEME.bg_lighter};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                width: 16px;
                height: 16px;
                background: {THEME.accent_primary};
                border-radius: 8px;
                margin: -5px 0;
            }}
            QSlider::handle:horizontal:hover {{
                background: {THEME.success};
            }}
            QPushButton {{
                background: {THEME.bg_light};
                color: {THEME.text_primary};
                border: 1px solid {THEME.border_medium};
                border-radius: 6px;
                padding: 8px 16px;
                min-height: 28px;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background: {THEME.bg_lighter};
                border-color: {THEME.accent_primary};
            }}
            QPushButton:pressed {{
                background: {THEME.border_light};
            }}
            QDialogButtonBox QPushButton {{
                min-width: 90px;
            }}
            QListWidget {{
                background: {THEME.bg_dark};
                border: 1px solid {THEME.border_dark};
                border-radius: 6px;
                outline: none;
            }}
            QListWidget::item {{
                background: {THEME.bg_medium};
                border: 1px solid transparent;
                border-radius: 4px;
                margin: 2px 4px;
                padding: 6px 8px;
                min-height: 20px;
            }}
            QListWidget::item:hover {{
                background: {THEME.bg_light};
                border-color: {THEME.border_light};
            }}
            QListWidget::item:selected {{
                background: {THEME.bg_lighter};
                border-color: {THEME.accent_primary};
            }}
            QKeySequenceEdit {{
                background: {THEME.bg_dark};
                color: {THEME.text_primary};
                border: 2px solid {THEME.border_medium};
                border-radius: 6px;
                padding: 6px 10px;
                min-height: 28px;
            }}
            QKeySequenceEdit:focus {{
                border-color: {THEME.accent_primary};
            }}
        """)

    def get_setting(self, key: str, default=None):
        """Hilfsmethode zum Abrufen einer Einstellung."""
        return self._settings.value(key, default)

    @staticmethod
    def get_settings() -> QSettings:
        """Gibt eine QSettings-Instanz für den globalen Zugriff zurück."""
        return QSettings()
