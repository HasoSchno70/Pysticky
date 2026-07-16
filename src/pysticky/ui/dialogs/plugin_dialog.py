"""
Plugin-Picker- und -Runner-Dialog.

Zeigt eine Liste aller entdeckten Plugins und lässt den User eines
auswählen und ausführen. Der Dialog ist gleichzeitig der `PluginContext`
für die Plugin-Laufzeit — er beantwortet `prompt_int`/`prompt_str` via
Qt-Input-Dialoge und zeigt `show_message`/`show_error` als Toast.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ...core.i18n import t
from ...plugins import Plugin, PluginError, discover_plugins, run_plugin


class PluginDialog(QDialog):
    """Dialog zur Auswahl und Ausführung eines Plugins."""

    def __init__(self, pattern, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("Plugin ausführen"))
        self.setMinimumSize(560, 420)
        self._pattern = pattern
        self._plugins: list[Plugin] = []
        self._executed = False  # True wenn ein Plugin gelaufen ist (UI muss neu rendern)

        self._setup_ui()
        self._load_plugins()

    @property
    def executed(self) -> bool:
        return self._executed

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QLabel(t("Verfuegbare Plugins"))
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header)

        body = QHBoxLayout()

        # Liste
        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(220)
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        body.addWidget(self.list_widget, 1)

        # Detail-Anzeige
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMinimumWidth(280)
        body.addWidget(self.detail, 2)

        layout.addLayout(body)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_run = QPushButton(t("Plugin ausführen"))
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self._on_run)
        btn_row.addWidget(self.btn_run)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.reject)
        btn_row.addWidget(button_box)

        layout.addLayout(btn_row)

    def _load_plugins(self) -> None:
        self._plugins = discover_plugins()
        if not self._plugins:
            empty = QListWidgetItem(t("Keine Plugins gefunden."))
            empty.setFlags(empty.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.list_widget.addItem(empty)
            self.detail.setPlainText(t("Keine Plugins gefunden."))
            return

        for plugin in self._plugins:
            item = QListWidgetItem(plugin.name)
            item.setData(Qt.ItemDataRole.UserRole, plugin)
            item.setToolTip(plugin.description or plugin.name)
            self.list_widget.addItem(item)
        self.list_widget.setCurrentRow(0)

    def _on_selection_changed(self, current, _previous) -> None:
        if current is None:
            self.detail.clear()
            self.btn_run.setEnabled(False)
            return
        plugin = current.data(Qt.ItemDataRole.UserRole)
        if not isinstance(plugin, Plugin):
            self.btn_run.setEnabled(False)
            return
        self.btn_run.setEnabled(True)
        self.detail.setHtml(
            f"<h3>{plugin.name}</h3>"
            f"<p><b>ID:</b> {plugin.id}<br>"
            f"<b>Version:</b> {plugin.manifest.version}</p>"
            f"<p>{plugin.description}</p>"
            f"<p style='color:#888;font-size:11px;'>Quelle: {plugin.directory}</p>"
        )

    def _on_run(self) -> None:
        current = self.list_widget.currentItem()
        if current is None:
            return
        plugin = current.data(Qt.ItemDataRole.UserRole)
        if not isinstance(plugin, Plugin):
            return

        try:
            run_plugin(plugin, self._pattern, self)
            self._executed = True
        except PluginError as e:
            QMessageBox.critical(self, t("Plugin-Fehler"), str(e))
            return

        QMessageBox.information(
            self,
            t("Plugin ausgeführt"),
            t("Plugin: %s") % plugin.name,
        )
        self.accept()

    # ---------- PluginContext-Implementierung ----------

    def show_message(self, text: str) -> None:
        QMessageBox.information(self, t("Information"), text)

    def show_error(self, text: str) -> None:
        QMessageBox.warning(self, t("Plugin-Fehler"), text)

    def prompt_int(
        self,
        question: str,
        default: int = 0,
        minimum: int = 0,
        maximum: int = 1_000_000,
    ) -> int | None:
        value, ok = QInputDialog.getInt(self, question, question, default, minimum, maximum)
        return value if ok else None

    def prompt_str(self, question: str, default: str = "") -> str | None:
        value, ok = QInputDialog.getText(self, question, question, text=default)
        return value if ok else None

    def progress(self, value: float, text: str = "") -> None:
        # Aktuell keine Progress-Bar im Dialog — Hook offen halten.
        # Wenn Plugins lange laufen, kann man das später mit QProgressBar füllen.
        _ = value
        _ = text
