"""
Pattern-Eigenschaften-Dialog.

Editor fuer pattern.metadata-Felder die heute schon im Daten-Modell existieren,
aber bisher kein UI hatten:
- author, copyright
- started_date (neu)
- notes (neu, persistent)

Werte landen direkt in `pattern.metadata`. PDF/HTML-Export liest sie ueber
`get_watermark()` und `metadata.get("notes")`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from ..styles import THEME

if TYPE_CHECKING:
    from ...core import Pattern


class PatternPropertiesDialog(QDialog):
    """Dialog zum Bearbeiten der Pattern-Metadata."""

    def __init__(self, pattern: "Pattern", parent=None) -> None:
        super().__init__(parent)
        self._pattern = pattern
        self.setWindowTitle("Eigenschaften")
        self.setMinimumWidth(520)
        self._setup_ui()
        self._load_from_pattern()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # === Read-only Info-Block ===
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background: {THEME.bg_medium};
                border: 1px solid {THEME.border_medium};
                border-left: 4px solid {THEME.accent_primary};
                border-radius: 6px;
            }}
        """)
        info_layout = QFormLayout(info_frame)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setHorizontalSpacing(20)

        muted = f"color: {THEME.text_muted}; font-weight: 600;"
        value = f"color: {THEME.text_primary};"

        title_lbl = QLabel("MUSTER")
        title_lbl.setStyleSheet(
            f"color: {THEME.accent_primary}; font-weight: 700; letter-spacing: 1px; font-size: 10px;"
        )
        info_layout.addRow(title_lbl)

        size_label = QLabel(f"{self._pattern.width} × {self._pattern.height} Stiche")
        size_label.setStyleSheet(value)
        info_layout.addRow(self._mk_label("Größe:", muted), size_label)

        colors_label = QLabel(f"{len(self._pattern.color_entries)} Farben")
        colors_label.setStyleSheet(value)
        info_layout.addRow(self._mk_label("Farben:", muted), colors_label)

        fabric_label = QLabel(f"{self._pattern.fabric_count} ct Aida")
        fabric_label.setStyleSheet(value)
        info_layout.addRow(self._mk_label("Stoff:", muted), fabric_label)

        layout.addWidget(info_frame)

        # === Bearbeitbare Felder ===
        form = QFormLayout()
        form.setSpacing(10)

        self._edit_author = QLineEdit()
        self._edit_author.setPlaceholderText("z.B. Anna Schmidt")
        form.addRow("Autor:", self._edit_author)

        self._edit_copyright = QLineEdit()
        self._edit_copyright.setPlaceholderText("z.B. © 2026 Anna Schmidt")
        form.addRow("Copyright:", self._edit_copyright)

        # Stickdatum: Checkbox + Date-Picker, damit "kein Datum" moeglich ist
        date_row = QHBoxLayout()
        self._chk_started = QCheckBox("Begonnen am:")
        self._chk_started.toggled.connect(self._on_started_toggled)
        date_row.addWidget(self._chk_started)
        self._date_started = QDateEdit()
        self._date_started.setCalendarPopup(True)
        self._date_started.setDisplayFormat("dd.MM.yyyy")
        self._date_started.setDate(QDate.currentDate())
        self._date_started.setEnabled(False)
        date_row.addWidget(self._date_started)
        date_row.addStretch(1)
        form.addRow("Stickdatum:", date_row)

        self._txt_notes = QPlainTextEdit()
        self._txt_notes.setPlaceholderText(
            "Freie Notizen — werden auch im HTML/PDF-Export auf dem Deckblatt angezeigt.\n"
            "Z.B. 'Geschenk für Mama zum Geburtstag', 'Riesenherausforderung'."
        )
        self._txt_notes.setMaximumHeight(140)
        form.addRow("Notizen:", self._txt_notes)

        layout.addLayout(form)

        # === Buttons ===
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _mk_label(self, text: str, style: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(style)
        return lbl

    def _on_started_toggled(self, checked: bool) -> None:
        self._date_started.setEnabled(checked)

    def _load_from_pattern(self) -> None:
        md = self._pattern.metadata
        self._edit_author.setText(md.get("author", ""))
        self._edit_copyright.setText(md.get("copyright", ""))
        notes = md.get("notes", "")
        # Fallback: alte pdf_notes uebernehmen, wenn keine `notes` existieren
        if not notes and md.get("pdf_notes"):
            notes = md["pdf_notes"]
        self._txt_notes.setPlainText(notes)

        started_iso = md.get("started_date", "")
        if started_iso:
            qd = QDate.fromString(started_iso, Qt.DateFormat.ISODate)
            if qd.isValid():
                self._chk_started.setChecked(True)
                self._date_started.setEnabled(True)
                self._date_started.setDate(qd)

    def apply_to_pattern(self) -> bool:
        """Schreibt die Felder in pattern.metadata. Liefert True bei Aenderungen."""
        md = self._pattern.metadata

        new_author = self._edit_author.text().strip()
        new_copyright = self._edit_copyright.text().strip()
        new_notes = self._txt_notes.toPlainText().strip()

        if self._chk_started.isChecked():
            new_started = self._date_started.date().toString(Qt.DateFormat.ISODate)
        else:
            new_started = ""

        changed = False
        if md.get("author", "") != new_author:
            if new_author:
                md["author"] = new_author
            else:
                md.pop("author", None)
            changed = True

        if md.get("copyright", "") != new_copyright:
            if new_copyright:
                md["copyright"] = new_copyright
            else:
                md.pop("copyright", None)
            changed = True

        if md.get("notes", "") != new_notes:
            if new_notes:
                md["notes"] = new_notes
            else:
                md.pop("notes", None)
            changed = True

        if md.get("started_date", "") != new_started:
            if new_started:
                md["started_date"] = new_started
            else:
                md.pop("started_date", None)
            changed = True

        return changed
