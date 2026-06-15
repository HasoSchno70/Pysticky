"""
Versionen-Dialog: zeigt alle Snapshots eines Patterns mit Datum,
Stich-Anzahl + Restore-/Loesch-Buttons.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ...core.i18n import t
from ...core.snapshots import (
    delete_snapshot,
    list_snapshots,
    parse_snapshot_timestamp,
    pattern_key_for,
)
from ..styles import THEME

if TYPE_CHECKING:
    from ...core import Pattern


class SnapshotHistoryDialog(QDialog):
    """Dialog zur Anzeige + Wiederherstellung versionierter Snapshots."""

    # Wird mit dem ausgewaehlten Snapshot-Pfad emittiert, wenn der User
    # "Wiederherstellen" klickt.
    restore_requested = Signal(Path)

    def __init__(
        self,
        pattern: "Pattern",
        current_file: Path | None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._pattern = pattern
        self._key = pattern_key_for(pattern, current_file)

        self.setWindowTitle(t("Versionen"))
        self.setMinimumSize(560, 480)
        self._setup_ui()
        self._reload()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header
        header = QLabel(f"Versionen für '{self._key}'")
        header.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {THEME.accent_primary};")
        layout.addWidget(header)

        intro = QLabel(
            t(
                "Automatische Versionen werden alle 30 Minuten angelegt, sobald "
                "ungespeicherte Änderungen vorhanden sind. Doppelklick zeigt "
                "Details, der Button 'Wiederherstellen' laedt diese Version "
                "wieder als aktives Muster."
            )
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {THEME.text_muted}; font-size: 11px;")
        layout.addWidget(intro)

        self._list = QListWidget()
        self._list.itemSelectionChanged.connect(self._update_buttons)
        self._list.itemDoubleClicked.connect(self._on_double_clicked)
        layout.addWidget(self._list, 1)

        # Detail-Frame
        self._detail_frame = QFrame()
        self._detail_frame.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_medium};
                border: 1px solid {THEME.border_medium};
                border-left: 3px solid {THEME.accent_primary};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        detail_layout = QVBoxLayout(self._detail_frame)
        detail_layout.setContentsMargins(8, 6, 8, 6)
        self._detail_label = QLabel(t("Wähle eine Version aus der Liste."))
        self._detail_label.setStyleSheet(f"color: {THEME.text_secondary};")
        self._detail_label.setWordWrap(True)
        detail_layout.addWidget(self._detail_label)
        layout.addWidget(self._detail_frame)

        # Buttons
        btn_row = QHBoxLayout()

        self._btn_restore = QPushButton(t("⟲ Wiederherstellen"))
        self._btn_restore.clicked.connect(self._on_restore)
        self._btn_restore.setEnabled(False)
        btn_row.addWidget(self._btn_restore)

        self._btn_delete = QPushButton(t("🗑 Löschen"))
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_delete.setEnabled(False)
        btn_row.addWidget(self._btn_delete)

        self._btn_diff = QPushButton(t("⇄ Mit aktuellem vergleichen"))
        self._btn_diff.clicked.connect(self._on_diff)
        self._btn_diff.setEnabled(False)
        self._btn_diff.setToolTip(
            t(
                "Vergleicht den ausgewaehlten Snapshot visuell mit dem aktuell "
                "geoeffneten Pattern — markiert hinzugefuegte, entfernte und "
                "geaenderte Stiche."
            )
        )
        btn_row.addWidget(self._btn_diff)

        btn_row.addStretch(1)

        btn_close = QPushButton(t("Schließen"))
        btn_close.clicked.connect(self.accept)
        btn_close.setDefault(True)
        btn_row.addWidget(btn_close)

        layout.addLayout(btn_row)

    def _reload(self) -> None:
        """Aktualisiert die Liste der Snapshots aus dem Dateisystem."""
        self._list.clear()
        for path in list_snapshots(self._key):
            ts = parse_snapshot_timestamp(path)
            label = self._format_entry(path, ts)
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, path)
            if ts is not None:
                item.setToolTip(f"{ts.strftime('%A, %d.%m.%Y %H:%M:%S')}\n{path}")
            self._list.addItem(item)

        if self._list.count() == 0:
            empty = QListWidgetItem(
                t(
                    "Noch keine Versionen vorhanden.\n"
                    "Speichern oder warten bis die naechste Auto-Version erstellt wird."
                )
            )
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(empty)

        self._update_buttons()

    def _format_entry(self, path: Path, ts: datetime | None) -> str:
        size_kb = max(1, path.stat().st_size // 1024) if path.exists() else 0
        if ts is None:
            return f"📄  {path.name}    ({size_kb} KB)"
        return f"📅  {ts.strftime('%d.%m.%Y %H:%M:%S')}    ({size_kb} KB)"

    def _selected_path(self) -> Path | None:
        items = self._list.selectedItems()
        if not items:
            return None
        path = items[0].data(Qt.ItemDataRole.UserRole)
        return path if isinstance(path, Path) else None

    def _update_buttons(self) -> None:
        path = self._selected_path()
        enabled = path is not None
        self._btn_restore.setEnabled(enabled)
        self._btn_delete.setEnabled(enabled)
        self._btn_diff.setEnabled(enabled)
        if path is None:
            self._detail_label.setText(t("Wähle eine Version aus der Liste."))
            return
        self._update_detail(path)

    def _update_detail(self, path: Path) -> None:
        """Versucht den Snapshot zu laden und schreibt Stichzahl/Farben rein."""
        ts = parse_snapshot_timestamp(path)
        try:
            from ...core import load_pattern

            p = load_pattern(path)
            n_stitches = p.total_stitches
            n_colors = len(p.color_entries)
            size = f"{p.width} × {p.height}"
        except Exception:  # noqa: BLE001 — Snapshot kann beschaedigt sein
            self._detail_label.setText(
                f"⚠ Diese Version konnte nicht gelesen werden ({path.name})."
            )
            return
        when = ts.strftime("%d.%m.%Y %H:%M:%S") if ts else "?"
        self._detail_label.setText(
            f"Datum: {when}\nGröße: {size}    ·    Stiche: {n_stitches}    ·    Farben: {n_colors}"
        )

    def _on_double_clicked(self, item: QListWidgetItem) -> None:
        # Detail-Update reicht — Restore explizit ueber Button
        path = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(path, Path):
            self._update_detail(path)

    def _on_restore(self) -> None:
        path = self._selected_path()
        if path is None:
            return
        reply = QMessageBox.question(
            self,
            t("Version wiederherstellen"),
            t(
                "Aktuelles Muster durch diese Version ersetzen?\n\n"
                "Nicht gespeicherte Änderungen gehen verloren."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.restore_requested.emit(path)
            self.accept()

    def _on_diff(self) -> None:
        """Oeffnet den Diff-Dialog mit ausgewaehltem Snapshot vs. aktuellem Pattern."""
        path = self._selected_path()
        if path is None:
            return
        try:
            from ...core import load_pattern
            from ...core.pattern_diff import compute_diff
            from .pattern_diff_dialog import PatternDiffDialog

            old_pattern = load_pattern(path)
            diff = compute_diff(old_pattern, self._pattern)
            dialog = PatternDiffDialog(old_pattern, self._pattern, diff, path.name, parent=self)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(
                self,
                t("Vergleich fehlgeschlagen"),
                f"Snapshot konnte nicht geladen werden:\n{e}",
            )

    def _on_delete(self) -> None:
        path = self._selected_path()
        if path is None:
            return
        reply = QMessageBox.question(
            self,
            t("Version löschen"),
            f"Diese Version dauerhaft löschen?\n\n{path.name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if delete_snapshot(path):
                self._reload()
