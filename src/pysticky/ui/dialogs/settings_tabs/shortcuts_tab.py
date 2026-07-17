"""
Tastenkürzel-Tab für Settings-Dialog.

Zeigt/bearbeitet die von MainWindow._register_shortcut_targets()
gesammelte ShortcutRegistry. Bearbeitungen werden erst als "pending"
gehalten und erst in save_settings() auf die echten QAction-/ToolButton-
Ziele angewendet + persistiert -- konsistent mit den anderen Tabs
(Cancel im Settings-Dialog verwirft alles, auch Shortcut-Änderungen).

Vorher speicherte dieser Tab eine eigene, komplett losgelöste
DEFAULT_SHORTCUTS-Liste, die nirgends gelesen wurde -- "Bearbeiten"
hatte buchstäblich keine Wirkung auf die echten Tastenkürzel.
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
from ...shortcuts_registry import ShortcutRegistry
from ...styles import THEME


class ShortcutsTab(QWidget):
    """Tab: Tastenkürzel-Einstellungen."""

    def __init__(
        self,
        parent: QWidget | None = None,
        registry: ShortcutRegistry | None = None,
    ) -> None:
        super().__init__(parent)
        self._registry = registry
        # Pending-Edits: id -> neue Tastenkombination. Erst bei
        # save_settings() auf die echten Ziele angewendet.
        self._pending: dict[str, str] = {}
        self._setup_ui()

    def _effective_shortcut(self, shortcut_id: str) -> str:
        """Anzeige-Wert: Pending-Edit falls vorhanden, sonst der Live-Wert."""
        if shortcut_id in self._pending:
            return self._pending[shortcut_id]
        return self._registry.current(shortcut_id) if self._registry else ""

    def _setup_ui(self) -> None:
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

    def _populate_list(self) -> None:
        """Füllt die Liste mit Shortcuts aus der Registry."""
        self.shortcuts_list.clear()
        if not self._registry:
            return
        for shortcut_id in self._registry.ids():
            label = self._registry.label(shortcut_id)
            shortcut = self._effective_shortcut(shortcut_id)
            item = QListWidgetItem(
                t("{action}: {shortcut}").format(action=label, shortcut=shortcut)
            )
            item.setData(Qt.ItemDataRole.UserRole, shortcut_id)
            self.shortcuts_list.addItem(item)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Bearbeitet Shortcut bei Doppelklick."""
        self._edit_shortcut()

    def _find_pending_conflict(self, key_sequence: str, exclude_id: str) -> str | None:
        """Wie ShortcutRegistry.find_conflict, aber gegen den effektiven
        (Pending-Edits mit einschließenden) Zustand statt nur den Live-Zustand
        -- sonst könnte man versehentlich zwei Pending-Edits auf denselben
        Shortcut setzen, ohne dass es auffällt."""
        if not self._registry or not key_sequence:
            return None
        normalized = QKeySequence(key_sequence).toString()
        for shortcut_id in self._registry.ids():
            if shortcut_id == exclude_id:
                continue
            if self._effective_shortcut(shortcut_id) == normalized:
                return shortcut_id
        return None

    def _edit_shortcut(self) -> None:
        """Bearbeitet das ausgewählte Tastenkürzel."""
        if not self._registry:
            return
        current = self.shortcuts_list.currentItem()
        if not current:
            return

        shortcut_id = current.data(Qt.ItemDataRole.UserRole)
        label = self._registry.label(shortcut_id)

        dialog = QDialog(self)
        dialog.setWindowTitle(t("Tastenkürzel: {action}").format(action=label))
        dialog.setFixedSize(300, 120)

        layout = QVBoxLayout(dialog)

        info_label = QLabel(t("Neues Tastenkürzel für '{action}':").format(action=label))
        layout.addWidget(info_label)

        key_edit = QKeySequenceEdit()
        key_edit.setKeySequence(QKeySequence(self._effective_shortcut(shortcut_id)))
        layout.addWidget(key_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_shortcut = key_edit.keySequence().toString()
            if not new_shortcut:
                return

            conflict_id = self._find_pending_conflict(new_shortcut, exclude_id=shortcut_id)
            if conflict_id is not None:
                QMessageBox.warning(
                    self,
                    t("Tastenkürzel bereits vergeben"),
                    t("'{shortcut}' wird schon für '{other}' verwendet.").format(
                        shortcut=new_shortcut, other=self._registry.label(conflict_id)
                    ),
                )
                return

            self._pending[shortcut_id] = new_shortcut
            current.setText(t("{action}: {shortcut}").format(action=label, shortcut=new_shortcut))

    def _reset_shortcuts(self) -> None:
        """Setzt alle Shortcuts auf Standardwerte zurück (pending, bis gespeichert)."""
        reply = QMessageBox.question(
            self,
            t("Tastenkürzel zurücksetzen"),
            t("Alle Tastenkürzel auf Standardwerte zurücksetzen?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes and self._registry:
            for shortcut_id in self._registry.ids():
                self._pending[shortcut_id] = self._registry.default(shortcut_id)
            self._populate_list()

    def load_settings(self, settings: QSettings) -> None:
        """Lädt Einstellungen.

        Die Registry ist beim MainWindow-Start bereits mit den
        gespeicherten Overrides initialisiert (apply_saved_overrides) --
        die Liste zeigt also direkt den aktuellen Live-Zustand, Pending-
        Edits aus einer vorherigen (abgebrochenen) Öffnung werden verworfen.
        """
        self._pending.clear()
        self._populate_list()

    def save_settings(self, settings: QSettings) -> None:
        """Wendet Pending-Edits live an und persistiert den Gesamtzustand."""
        if not self._registry:
            return
        for shortcut_id, key_sequence in self._pending.items():
            self._registry.set_shortcut(shortcut_id, key_sequence)
        self._pending.clear()
        settings.setValue("shortcuts", self._registry.all_current())

    def reset_to_defaults(self) -> None:
        """Setzt auf Standardwerte zurück (pending, wie _reset_shortcuts ohne Nachfrage)."""
        if not self._registry:
            return
        for shortcut_id in self._registry.ids():
            self._pending[shortcut_id] = self._registry.default(shortcut_id)
        self._populate_list()
