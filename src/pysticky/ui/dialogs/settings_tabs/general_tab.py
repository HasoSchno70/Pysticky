"""
Allgemein-Tab für Settings-Dialog.
"""

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ....core.i18n import t
from ._helpers import make_section_form


class GeneralTab(QWidget):
    """Tab: Allgemeine Einstellungen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(4, 4, 4, 4)

        # === Autosave ===
        group_autosave, form = make_section_form("Automatisches Speichern", "💾")
        self.chk_autosave = QCheckBox(t("Autosave aktivieren"))
        self.chk_autosave.setToolTip(
            t("Speichert das Muster automatisch in regelmäßigen Abständen")
        )
        form.addRow(self.chk_autosave)

        self.spin_autosave_interval = QSpinBox()
        self.spin_autosave_interval.setRange(1, 60)
        self.spin_autosave_interval.setSuffix(" " + t("Minuten"))
        self.spin_autosave_interval.setToolTip(t("Intervall zwischen automatischen Speicherungen"))
        form.addRow(t("Intervall:"), self.spin_autosave_interval)

        self.chk_autosave_backup = QCheckBox(t("Backup vor Überschreiben erstellen"))
        self.chk_autosave_backup.setToolTip(t("Erstellt eine .bak-Datei vor dem Speichern"))
        form.addRow(self.chk_autosave_backup)
        layout.addWidget(group_autosave)

        # === Snapshots & Sticken ===
        group_stitching, form = make_section_form("Sticken & Snapshots", "🧵")
        self.spin_snapshot_interval = QSpinBox()
        self.spin_snapshot_interval.setRange(5, 240)
        self.spin_snapshot_interval.setSuffix(" " + t("Minuten"))
        self.spin_snapshot_interval.setToolTip(
            t(
                "Wie oft eine versionierte Kopie des Musters in der "
                "Snapshot-Historie abgelegt wird (Datei → Versionen…)."
            )
        )
        form.addRow(t("Snapshot-Intervall:"), self.spin_snapshot_interval)

        self.chk_stitch_timer = QCheckBox(t("Session-Timer im Sticken-Modus"))
        self.chk_stitch_timer.setToolTip(
            t(
                "Misst die Zeit, die du im Sticken-Modus verbringst, und "
                "speichert sie pro Muster. Nach Beenden des Modus erscheint "
                "ein Hinweis mit Sitzungs- und Gesamtzeit."
            )
        )
        form.addRow(self.chk_stitch_timer)
        layout.addWidget(group_stitching)

        # === Start-Verhalten ===
        group_start, form = make_section_form("Programmstart", "🚀")
        self.combo_start_action = QComboBox()
        self.combo_start_action.addItems(
            [
                t("Leeres Muster erstellen"),
                t("Neues Projekt Dialog"),
                t("Letzte Datei öffnen"),
                t("Nichts tun"),
            ]
        )
        self.combo_start_action.setToolTip(t("Aktion beim Programmstart"))
        form.addRow(t("Beim Start:"), self.combo_start_action)

        self.spin_recent_files = QSpinBox()
        self.spin_recent_files.setRange(0, 20)
        self.spin_recent_files.setToolTip(t("Maximale Anzahl der zuletzt geöffneten Dateien"))
        form.addRow(t("Max. Recent Files:"), self.spin_recent_files)

        self.chk_restore_window = QCheckBox(t("Fensterposition wiederherstellen"))
        self.chk_restore_window.setToolTip(
            t("Stellt Größe und Position des Fensters beim Start wieder her")
        )
        form.addRow(self.chk_restore_window)
        layout.addWidget(group_start)

        # === Erscheinungsbild ===
        group_appearance, form = make_section_form("Erscheinungsbild", "🎨")
        self.combo_theme = QComboBox()
        self.combo_theme.addItems([t("Dark"), t("Light")])
        self.combo_theme.setToolTip(t("Farbschema der Anwendung (wird sofort angewendet)"))
        form.addRow(t("Theme:"), self.combo_theme)

        # Sprache: Auto + alle gefundenen Sprach-JSON-Dateien
        from ....core.i18n import get_translation_manager

        self.combo_language = QComboBox()
        self.combo_language.addItem(t("Auto (System)"), userData="auto")
        for code in get_translation_manager().available_languages():
            label = {"de": "Deutsch", "en": "English"}.get(code, code)
            self.combo_language.addItem(label, userData=code)
        self.combo_language.setToolTip(
            t("Sprache der Benutzeroberflaeche. Aenderungen werden beim naechsten Start aktiv.")
        )
        form.addRow(t("Sprache:"), self.combo_language)

        layout.addWidget(group_appearance)

        # === Benachrichtigungen ===
        group_notify, form = make_section_form("Benachrichtigungen", "🔔")
        self.chk_confirm_exit = QCheckBox(t("Vor Beenden bestätigen"))
        self.chk_confirm_exit.setToolTip(t("Fragt nach, bevor das Programm geschlossen wird"))
        form.addRow(self.chk_confirm_exit)

        self.chk_confirm_overwrite = QCheckBox(t("Vor Überschreiben warnen"))
        self.chk_confirm_overwrite.setToolTip(t("Warnt, wenn eine Datei überschrieben wird"))
        form.addRow(self.chk_confirm_overwrite)

        self.spin_status_timeout = QSpinBox()
        self.spin_status_timeout.setRange(1, 30)
        self.spin_status_timeout.setSuffix(" " + t("Sekunden"))
        self.spin_status_timeout.setToolTip(t("Wie lange Statusmeldungen angezeigt werden"))
        form.addRow(t("Statusmeldungen:"), self.spin_status_timeout)
        layout.addWidget(group_notify)

        # === Export-Wasserzeichen ===
        group_watermark, form = make_section_form("Export-Wasserzeichen", "🖋️")
        self.edit_default_author = QLineEdit()
        self.edit_default_author.setPlaceholderText(t("z.B. Anna Müller"))
        self.edit_default_author.setToolTip(
            t(
                "Wird als Autor in HTML- und PDF-Exporten angezeigt,\n"
                "wenn das Muster selbst keinen Autor hat."
            )
        )
        form.addRow(t("Standard-Autor:"), self.edit_default_author)

        self.edit_default_copyright = QLineEdit()
        self.edit_default_copyright.setPlaceholderText(t("z.B. © 2026 Anna Müller"))
        self.edit_default_copyright.setToolTip(t("Erscheint als Footer in HTML/PDF-Exporten."))
        form.addRow(t("Copyright-Hinweis:"), self.edit_default_copyright)
        layout.addWidget(group_watermark)
        layout.addStretch()

    def load_settings(self, settings: QSettings):
        """Lädt Einstellungen."""
        self.chk_autosave.setChecked(settings.value("autosave_enabled", True, type=bool))
        self.spin_autosave_interval.setValue(settings.value("autosave_interval", 5, type=int))
        self.chk_autosave_backup.setChecked(settings.value("autosave_backup", True, type=bool))
        self.spin_snapshot_interval.setValue(
            settings.value("snapshot_interval_minutes", 30, type=int)
        )
        self.chk_stitch_timer.setChecked(settings.value("stitch_timer_enabled", True, type=bool))
        self.combo_start_action.setCurrentIndex(settings.value("start_action", 0, type=int))
        self.spin_recent_files.setValue(settings.value("max_recent_files", 10, type=int))
        self.chk_restore_window.setChecked(settings.value("restore_window", True, type=bool))
        theme = settings.value("theme", "dark", type=str)
        self.combo_theme.setCurrentIndex(0 if theme == "dark" else 1)
        # Sprache laden
        lang = settings.value("ui_language", "auto", type=str)
        for i in range(self.combo_language.count()):
            if self.combo_language.itemData(i) == lang:
                self.combo_language.setCurrentIndex(i)
                break
        self.chk_confirm_exit.setChecked(settings.value("confirm_exit", False, type=bool))
        self.chk_confirm_overwrite.setChecked(settings.value("confirm_overwrite", True, type=bool))
        self.spin_status_timeout.setValue(settings.value("status_timeout", 3, type=int))
        self.edit_default_author.setText(settings.value("default_author", "", type=str))
        self.edit_default_copyright.setText(settings.value("default_copyright", "", type=str))

    def save_settings(self, settings: QSettings):
        """Speichert Einstellungen."""
        settings.setValue("autosave_enabled", self.chk_autosave.isChecked())
        settings.setValue("autosave_interval", self.spin_autosave_interval.value())
        settings.setValue("autosave_backup", self.chk_autosave_backup.isChecked())
        settings.setValue("snapshot_interval_minutes", self.spin_snapshot_interval.value())
        settings.setValue("stitch_timer_enabled", self.chk_stitch_timer.isChecked())
        settings.setValue("start_action", self.combo_start_action.currentIndex())
        settings.setValue("max_recent_files", self.spin_recent_files.value())
        settings.setValue("restore_window", self.chk_restore_window.isChecked())
        settings.setValue("theme", "dark" if self.combo_theme.currentIndex() == 0 else "light")
        settings.setValue("confirm_exit", self.chk_confirm_exit.isChecked())
        settings.setValue("confirm_overwrite", self.chk_confirm_overwrite.isChecked())
        settings.setValue("status_timeout", self.spin_status_timeout.value())
        settings.setValue("default_author", self.edit_default_author.text().strip())
        settings.setValue("default_copyright", self.edit_default_copyright.text().strip())
        settings.setValue("ui_language", self.combo_language.currentData() or "auto")

    def reset_to_defaults(self):
        """Setzt auf Standardwerte zurück."""
        self.chk_autosave.setChecked(True)
        self.spin_autosave_interval.setValue(5)
        self.chk_autosave_backup.setChecked(True)
        self.spin_snapshot_interval.setValue(30)
        self.chk_stitch_timer.setChecked(True)
        self.combo_start_action.setCurrentIndex(0)
        self.spin_recent_files.setValue(10)
        self.chk_restore_window.setChecked(True)
        self.combo_theme.setCurrentIndex(0)
        self.chk_confirm_exit.setChecked(False)
        self.chk_confirm_overwrite.setChecked(True)
        self.spin_status_timeout.setValue(3)
        self.edit_default_author.setText("")
        self.edit_default_copyright.setText("")
        # Sprache: Auto-Default
        for i in range(self.combo_language.count()):
            if self.combo_language.itemData(i) == "auto":
                self.combo_language.setCurrentIndex(i)
                break
