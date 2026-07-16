"""
Settings-Tab-Helpers.

Zentralisiert Layout/Spacing-Konventionen, damit alle Tabs gleich aussehen
und keine Überlappungen mehr passieren. Die Tabs verwenden weiterhin
QGroupBox + QFormLayout, aber über `make_section_form()` werden Margins/
Spacing immer konsistent gesetzt.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
)

from ....core.i18n import t
from ...styles import THEME


def make_section_form(
    title: str,
    icon: str | None = None,
) -> tuple[QGroupBox, QFormLayout]:
    """Erzeugt eine Settings-Section (GroupBox + sauber konfiguriertes Form-Layout).

    Args:
        title: Sichtbarer Titel der Sektion (z.B. "Automatisches Speichern").
        icon: Optionales Emoji, das vor dem Titel steht (z.B. "\U0001f4be").

    Returns:
        Tuple aus (group_box, form_layout). `group_box` direkt ins Tab-Layout
        einfügen; `form_layout` zum Hinzufügen von Feldern via `addRow()`
        oder `addRow(label, widget)`.

    Konsistente Werte (alle in Pixel):
        - GroupBox-Padding-Top: 26 (Platz für den Title)
        - Form-Margins: links/rechts 14, oben 8 (zus. zu Title-Padding), unten 12
        - VerticalSpacing: 10  → keine Überlappung mehr
        - HorizontalSpacing: 14
        - LabelAlignment: rechts (saubere Ausrichtung mit Inputs)
        - FieldGrowthPolicy: AllNonFixedFieldsGrow (Felder füllen die Spalte)
    """
    translated = t(title)
    full_title = f"{icon}  {translated}" if icon else translated
    box = QGroupBox(full_title)

    form = QFormLayout(box)
    form.setContentsMargins(14, 8, 14, 12)
    form.setVerticalSpacing(10)
    form.setHorizontalSpacing(14)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
    return box, form


def make_help_text(text: str) -> QLabel:
    """Kleiner grauer Hilfstext (z.B. unterhalb einer Setting-Group)."""
    lbl = QLabel(t(text))
    lbl.setWordWrap(True)
    lbl.setStyleSheet(
        f"color: {THEME.text_muted}; font-size: 10px; font-style: italic; "
        f"padding: 0 4px 4px 4px; background: transparent;"
    )
    return lbl
