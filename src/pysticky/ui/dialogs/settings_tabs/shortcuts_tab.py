"""
Tastenkürzel-Tab für Settings-Dialog.
"""

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ....core.i18n import t
from ...styles import THEME


class ShortcutsTab(QWidget):
    """Tab: Tastenkürzel-Einstellungen."""

    # Standard-Shortcuts
    DEFAULT_SHORTCUTS = {
        "Neu": "Ctrl+N",
        "Öffnen": "Ctrl+O",
        "Speichern": "Ctrl+S",
        "Speichern unter": "Ctrl+Shift+S",
        "Rückgängig": "Ctrl+Z",
        "Wiederholen": "Ctrl+Y",
        "Kopieren": "Ctrl+C",
        "Ausschneiden": "Ctrl+X",
        "Einfügen": "Ctrl+V",
        "Löschen": "Del",
        "Alles auswählen": "Ctrl+A",
        "Vergrößern": "Ctrl++",
        "Verkleinern": "Ctrl+-",
        "Einpassen": "Ctrl+0",
        "100%": "Ctrl+1",
        "Stift": "P",
        "Radierer": "E",
        "Füllen": "G",
        "Pipette": "I",
        "Linie": "L",
        "Rechteck": "R",
        "Ellipse": "O",
        "Text": "T",
        "Auswahl": "S",
        "Rückstich": "B",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._shortcuts = dict(self.DEFAULT_SHORTCUTS)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Info-Label
        info = QLabel(
            t(
                "ℹ️ Hier können Sie Tastenkürzel anpassen. "
                "Doppelklicken Sie auf ein Kürzel, um es zu ändern."
            )
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {THEME.text_muted}; padding: 8px;")
        layout.addWidget(info)

        # Shortcuts-Liste
        self.shortcuts_list = QListWidget()
        self.shortcuts_list.setAlternatingRowColors(True)
        self.shortcuts_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._populate_list()
        layout.addWidget(self.shortcuts_list)

        # Buttons
        btn_layout = QHBoxLayout()

        btn_edit = QPushButton(t("Bearbeiten"))
        btn_edit.clicked.connect(self._edit_shortcut)
        btn_layout.addWidget(btn_edit)

        btn_reset_shortcuts = QPushButton(t("Alle zurücksetzen"))
        btn_reset_shortcuts.clicked.connect(self._reset_shortcuts)
        btn_layout.addWidget(btn_reset_shortcuts)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _populate_list(self):
        """Füllt die Liste mit Shortcuts."""
        self.shortcuts_list.clear()
        for action, shortcut in self._shortcuts.items():
            item = QListWidgetItem(f"{t(action)}: {shortcut}")
            item.setData(Qt.ItemDataRole.UserRole, action)
            self.shortcuts_list.addItem(item)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Bearbeitet Shortcut bei Doppelklick."""
        self._edit_shortcut()

    def _edit_shortcut(self):
        """Bearbeitet das ausgewählte Tastenkürzel."""
        current = self.shortcuts_list.currentItem()
        if not current:
            return

        action = current.data(Qt.ItemDataRole.UserRole)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"{t('Tastenkürzel:')} {t(action)}")
        dialog.setFixedSize(300, 120)

        layout = QVBoxLayout(dialog)

        label = QLabel(f"{t('Neues Tastenkürzel für')} '{t(action)}':")
        layout.addWidget(label)

        key_edit = QKeySequenceEdit()
        key_edit.setKeySequence(QKeySequence(self._shortcuts.get(action, "")))
        layout.addWidget(key_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_shortcut = key_edit.keySequence().toString()
            if new_shortcut:
                self._shortcuts[action] = new_shortcut
                current.setText(f"{t(action)}: {new_shortcut}")

    def _reset_shortcuts(self):
        """Setzt alle Shortcuts auf Standardwerte zurück."""
        reply = QMessageBox.question(
            self,
            t("Tastenkürzel zurücksetzen"),
            t("Alle Tastenkürzel auf Standardwerte zurücksetzen?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._shortcuts = dict(self.DEFAULT_SHORTCUTS)
            self._populate_list()

    def load_settings(self, settings: QSettings):
        """Lädt Einstellungen."""
        shortcuts = settings.value("shortcuts", {})
        if shortcuts:
            self._shortcuts.update(shortcuts)
            self._populate_list()

    def save_settings(self, settings: QSettings):
        """Speichert Einstellungen."""
        settings.setValue("shortcuts", self._shortcuts)

    def reset_to_defaults(self):
        """Setzt auf Standardwerte zurück."""
        self._shortcuts = dict(self.DEFAULT_SHORTCUTS)
        self._populate_list()
